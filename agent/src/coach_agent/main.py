"""Agent entry point.

Step 2: Joined the room and published liveness heartbeats.
Step 3: Adds an `AgentSession` wired to the local `faster-whisper` STT. Transcripts
        (partial + final) are published as JSON data packets on the
        ``transcript`` topic so the UI can render them live.
Step 5: Adds the tight-lane text detectors (filler, pacing, prohibited,
        sentiment). Each final transcript feeds a shared
        ``MetricsSnapshotBuilder``; composed ``MetricsSnapshot`` packets are
        published on the ``metrics`` topic so the UI can render live counters.

Turn detection: delegated entirely to Silero VAD via the SDK. The
`CoachAgent.stt_node` override captures a handle on the active
``LocalFasterWhisperStream`` and the ``user_state_changed`` handler flushes
it the moment Silero reports ``speaking → listening/away``. This removes
all custom VAD/silence heuristics from the STT stream itself — Whisper
only transcribes and Silero only detects speech boundaries.
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
from coach_agent.stt import LocalFasterWhisperSTT, LocalFasterWhisperStream
from coach_agent.transport.liveness import LIVENESS_TOPIC, HeartbeatSource

load_dotenv(".env.local")

logger = logging.getLogger("coach_agent.main")

HEARTBEAT_INTERVAL_S = 2.0
TRANSCRIPT_TOPIC = "transcript"
METRICS_TOPIC = "metrics"

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


def _publish_transcript(ctx: JobContext, *, text: str, is_final: bool) -> asyncio.Task | None:
    """Fire-and-forget publish of a transcript data packet."""
    payload = json.dumps(
        {"text": text, "is_final": bool(is_final)}, separators=(",", ":")
    ).encode("utf-8")
    try:
        return asyncio.create_task(
            ctx.room.local_participant.publish_data(
                payload, reliable=True, topic=TRANSCRIPT_TOPIC
            )
        )
    except Exception:
        logger.exception("failed to schedule transcript publish")
        return None


async def _publish_metrics(ctx: JobContext, snapshot: dict) -> None:
    """Awaitable publish used by `MetricsSnapshotBuilder`."""
    if not ctx.room.isconnected():
        return  # session ended; silently drop the snapshot
    payload = json.dumps(snapshot, separators=(",", ":")).encode("utf-8")
    try:
        await ctx.room.local_participant.publish_data(
            payload, reliable=True, topic=METRICS_TOPIC
        )
    except PublishDataError:
        # Closed between our check and the publish — silent, not a bug.
        pass
    except Exception:
        logger.exception("failed to publish metrics snapshot")


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Join the room, run Whisper STT on the rep's mic, and publish transcripts + metrics."""
    logger.info("coach-agent joining room=%s", ctx.room.name)
    await ctx.connect()

    # AgentSession with Silero VAD — Silero is the only voice-activity
    # detector in the system; the STT stream does no VAD of its own.
    stt = LocalFasterWhisperSTT()
    vad = silero.VAD.load()
    session = AgentSession(stt=stt, vad=vad)
    agent = CoachAgent()

    # Step 5: shared detector pipeline. The builder owns all four P0
    # detectors and rate-limits the metrics publish to ~250 ms trailing.
    settings = CoachSettings.defaults()
    metrics_builder = MetricsSnapshotBuilder(
        settings=settings,
        publish=lambda snap: _publish_metrics(ctx, snap),
    )

    @session.on("user_input_transcribed")
    def on_transcribed(event: Any) -> None:
        text = getattr(event, "transcript", "") or ""
        is_final = bool(getattr(event, "is_final", False))
        if not text.strip():
            return
        logger.info("transcript is_final=%s text=%r", is_final, text[:80])
        _publish_transcript(ctx, text=text, is_final=is_final)

        if is_final:
            t_ms = int(time.time() * 1000)
            events = metrics_builder.on_final(text, t_ms=t_ms)
            if events:
                logger.info(
                    "detector events: %s",
                    [f"{e.kind}:{e.detail}" for e in events],
                )

    @session.on("user_state_changed")
    def on_user_state(event: Any) -> None:
        """Flush the STT stream when Silero says the user stopped speaking.

        This is the finalization driver. Every `speaking → listening` (or
        `speaking → away`) transition emits a `_FlushSentinel` into the
        current stream's input channel; the stream then does one last
        Whisper pass and emits `FINAL_TRANSCRIPT`. Interim updates continue
        to fire on the 500 ms cadence inside the stream itself.
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
            logger.info(
                "flushed STT stream on user_state %s->%s", old_state, new_state
            )
        except Exception:
            logger.exception("stream.flush() failed on user_state_changed")

    await session.start(agent=agent, room=ctx.room)

    # Keep the liveness heartbeat going so the UI can still detect the agent.
    # Exit the loop as soon as the room closes — otherwise `publish_data`
    # raises `PublishDataError("engine is closed")` repeatedly, blocking the
    # entrypoint from returning and forcing the SDK to cancel the job.
    source = HeartbeatSource()
    while ctx.room.isconnected():
        hb = source.next()
        try:
            await ctx.room.local_participant.publish_data(
                hb.to_bytes(), reliable=True, topic=LIVENESS_TOPIC
            )
        except PublishDataError as e:
            logger.info("room closed during heartbeat publish (%s); exiting loop", e)
            break
        except Exception:
            logger.exception("failed to publish heartbeat seq=%d", hb.seq)
        await asyncio.sleep(HEARTBEAT_INTERVAL_S)

    logger.info("coach-agent entrypoint exiting cleanly (room=%s)", ctx.room.name)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    cli.run_app(server)
