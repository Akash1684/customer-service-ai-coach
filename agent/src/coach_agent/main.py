"""Agent entry point.

Joins the rep's LiveKit room, runs `faster-whisper` STT in-process on the
rep's mic, publishes partial + final transcripts, runs the tight-lane
detectors, and publishes a rate-limited ``metrics`` snapshot.

Turn detection is delegated entirely to Silero VAD via the SDK. The
``CoachAgent.stt_node`` override captures a handle on the active
``LocalFasterWhisperStream`` and the ``user_state_changed`` handler flushes
it the moment Silero reports ``speaking → listening/away``. The STT stream
itself does no VAD — Whisper only transcribes, Silero only detects speech
boundaries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterable
from typing import Any

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import Agent, AgentServer, AgentSession, JobContext, cli, utils
from livekit.plugins import silero
from livekit.rtc.participant import PublishDataError

from coach_agent.config import CoachSettings
from coach_agent.pipeline import MetricsSnapshotBuilder
from coach_agent.stt import LocalFasterWhisperStream, LocalFasterWhisperSTT

load_dotenv(".env.local")

logger = logging.getLogger("coach_agent.main")

TRANSCRIPT_TOPIC = "transcript"
METRICS_TOPIC = "metrics"

# Shared across all sessions so the faster-whisper model loads exactly
# once (at worker-process startup via `prewarm()` below), not on the
# first user utterance. Without sharing, each session pays a ~4-5 s
# cold-start hit while `base.en` weights (~140 MB) page into memory.
_STT = LocalFasterWhisperSTT()

server = AgentServer()


class CoachAgent(Agent):
    """Listen-only agent that overrides ``stt_node`` to capture the live stream.

    The override mirrors ``Agent.default.stt_node`` exactly, except we keep
    a reference to the active :class:`LocalFasterWhisperStream` on
    ``self.active_stream`` so the session-level ``user_state_changed``
    handler can flush it when Silero VAD reports end-of-speech.
    """

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "Listen-only transcription agent for the Customer Service AI Coach. "
                "Do not speak or generate output."
            )
        )
        self.active_stream: LocalFasterWhisperStream | None = None

    async def stt_node(
        self,
        audio: AsyncIterable[rtc.AudioFrame],
        model_settings: Any,
    ):
        activity = self._get_activity_or_raise()
        assert activity.stt is not None, "stt_node called but no STT is configured"

        conn_options = activity.session.conn_options.stt_conn_options
        async with activity.stt.stream(conn_options=conn_options) as stream:
            assert isinstance(stream, LocalFasterWhisperStream), (
                f"expected LocalFasterWhisperStream, got {type(stream).__name__}"
            )
            self.active_stream = stream

            @utils.log_exceptions(logger=logger)
            async def _forward_input() -> None:
                async for frame in audio:
                    stream.push_frame(frame)

            forward_task = asyncio.create_task(_forward_input())
            try:
                async for event in stream:
                    yield event
            finally:
                await utils.aio.cancel_and_wait(forward_task)
                self.active_stream = None


async def _publish_json(ctx: JobContext, topic: str, payload: dict) -> None:
    """Publish a JSON payload on a LiveKit data-channel topic.

    Safe against the room closing mid-publish — swallows `PublishDataError`
    on the race and logs everything else. Callers:
      - in async code, ``await _publish_json(...)``
      - in sync event handlers, ``asyncio.create_task(_publish_json(...))``
    """
    if not ctx.room.isconnected():
        return
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    try:
        await ctx.room.local_participant.publish_data(data, reliable=True, topic=topic)
    except PublishDataError:
        # Room closed between our check and the publish — not a bug.
        pass
    except Exception:
        logger.exception("publish failed topic=%s", topic)


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Join the room, run Whisper STT on the rep's mic, and publish transcripts + metrics."""
    logger.info("coach-agent joining room=%s", ctx.room.name)
    await ctx.connect()

    # Silero is the only voice-activity detector in the system; the STT
    # stream does no VAD of its own.
    vad = silero.VAD.load()
    session = AgentSession(stt=_STT, vad=vad)
    agent = CoachAgent()

    # The builder owns all four detectors and rate-limits metrics publish
    # to ~250 ms trailing-edge.
    settings = CoachSettings()
    metrics_builder = MetricsSnapshotBuilder(
        settings=settings,
        publish=lambda snap: _publish_json(ctx, METRICS_TOPIC, snap),
    )

    @session.on("user_input_transcribed")
    def on_transcribed(event: Any) -> None:
        text = getattr(event, "transcript", "") or ""
        is_final = bool(getattr(event, "is_final", False))
        if not text.strip():
            return
        logger.info("transcript is_final=%s text=%r", is_final, text[:80])
        asyncio.create_task(
            _publish_json(ctx, TRANSCRIPT_TOPIC, {"text": text, "is_final": is_final})
        )

        if is_final:
            t_ms = int(time.time() * 1000)
            metrics_builder.on_final(text, t_ms=t_ms)

    @session.on("user_state_changed")
    def on_user_state(event: Any) -> None:
        """Flush the STT stream when Silero says the user stopped speaking.

        Every `speaking → listening/away` transition emits a `_FlushSentinel`
        into the current stream's input channel; the stream then does one
        last Whisper pass and emits `FINAL_TRANSCRIPT`. Interim updates
        continue to fire on the 500 ms cadence inside the stream itself.
        """
        old_state = getattr(event, "old_state", None)
        new_state = getattr(event, "new_state", None)
        if old_state != "speaking" or new_state not in ("listening", "away"):
            return
        stream = agent.active_stream
        if stream is None:
            return
        try:
            stream.flush()
        except Exception:
            logger.exception("stream.flush() failed on user_state_changed")

    await session.start(agent=agent, room=ctx.room)

    # Block until the room closes. Previously this loop also published a
    # liveness heartbeat; removed — the UI no longer has a debug pane and
    # room state is the source of truth.
    while ctx.room.isconnected():
        await asyncio.sleep(1.0)

    logger.info("coach-agent entrypoint exiting cleanly (room=%s)", ctx.room.name)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    # Pre-load the faster-whisper model BEFORE starting the worker so the
    # first user utterance doesn't eat a ~4-5 s cold-start hit. This is a
    # synchronous load; `uv run src/coach_agent/main.py dev` stays blocked
    # here until the model is in memory, then `agent ready` prints.
    logger.info("pre-loading faster-whisper (%s)…", _STT.model)
    _STT.prewarm()
    logger.info("agent ready — open the UI and speak")
    cli.run_app(server)
