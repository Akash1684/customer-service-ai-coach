"""Agent entry point — Step 2.

Boots an `AgentServer` and joins each LiveKit room as the `coach` agent. For
Step 2 the agent's only job is to publish a `liveness` heartbeat every 2 s so
the UI's DebugPane can confirm end-to-end transport is working. Real audio,
STT, detectors, and LLM wiring arrive in Steps 3+.

Run locally with:

    uv run src/coach_agent/main.py dev

requires `livekit-server --dev` to be running on 127.0.0.1:7880, and the
`.env.local` (copy from `.env.local.example`) to point at it.
"""

from __future__ import annotations

import asyncio
import logging

from dotenv import load_dotenv
from livekit.agents import AgentServer, JobContext, cli

from coach_agent.transport.liveness import LIVENESS_TOPIC, HeartbeatSource

load_dotenv(".env.local")

logger = logging.getLogger("coach_agent.main")

HEARTBEAT_INTERVAL_S = 2.0
# Leave `agent_name` empty so this agent auto-dispatches to every new room
# (matches the LiveKit agent-starter-python default). Named dispatch can be
# added later if we introduce multiple agent types in the same project.

server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    """Join the room and emit periodic liveness heartbeats."""
    logger.info("coach-agent joining room=%s", ctx.room.name)

    await ctx.connect()
    logger.info("connected to room=%s participants=%d",
                ctx.room.name, len(ctx.room.remote_participants))

    source = HeartbeatSource()

    async def publish_heartbeats() -> None:
        while True:
            hb = source.next()
            try:
                await ctx.room.local_participant.publish_data(
                    hb.to_bytes(),
                    reliable=True,
                    topic=LIVENESS_TOPIC,
                )
                logger.debug("published heartbeat seq=%d t_ms=%d", hb.seq, hb.t_ms)
            except Exception:
                logger.exception("failed to publish heartbeat seq=%d", hb.seq)
            await asyncio.sleep(HEARTBEAT_INTERVAL_S)

    # Keep the entrypoint alive until the room disconnects; the heartbeat task
    # runs until cancelled by the agent runtime when the session ends.
    await publish_heartbeats()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    cli.run_app(server)
