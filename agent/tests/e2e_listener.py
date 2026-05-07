"""E2E test participant — NOT part of the product, just a manual verification tool.

Joins `coach-room` on a local LiveKit server, listens for `liveness` data
packets from the agent, and prints them. Exits after a fixed duration.

Usage:
    uv run agent/tests/e2e_listener.py [duration_seconds]

Requires:
    livekit-server --dev   (running on ws://127.0.0.1:7880)
    uv run src/coach_agent/main.py dev   (agent connected)
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timedelta

from livekit import api, rtc

LK_URL = "ws://127.0.0.1:7880"
API_KEY = "devkey"
API_SECRET = "secret"
ROOM = "coach-room"
IDENTITY = "e2e-listener"


def mint_token() -> str:
    tok = (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity(IDENTITY)
        .with_name(IDENTITY)
        .with_grants(api.VideoGrants(room_join=True, room=ROOM, can_publish=True))
        .with_ttl(timedelta(minutes=15))
    )
    return tok.to_jwt()


async def main(duration_s: float) -> None:
    room = rtc.Room()
    heartbeats = []

    @room.on("data_received")
    def on_data(packet: rtc.DataPacket):
        try:
            topic = packet.topic
            text = packet.data.decode("utf-8")
            payload = json.loads(text)
            print(f"[{datetime.now().isoformat(timespec='seconds')}] topic={topic!r}  payload={payload}")
            if topic == "liveness":
                heartbeats.append(payload)
        except Exception as e:
            print(f"!! bad packet: {e}")

    token = mint_token()
    print(f"Connecting to {LK_URL} as {IDENTITY} in room={ROOM}...")
    await room.connect(LK_URL, token)
    print(f"Connected. Listening for {duration_s:.0f}s...")

    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        await asyncio.sleep(0.2)

    await room.disconnect()
    print("\n=== Summary ===")
    print(f"Heartbeats received: {len(heartbeats)}")
    if heartbeats:
        print(f"First:  seq={heartbeats[0]['seq']}  t_ms={heartbeats[0]['t_ms']}")
        print(f"Last:   seq={heartbeats[-1]['seq']}  t_ms={heartbeats[-1]['t_ms']}")


if __name__ == "__main__":
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
    asyncio.run(main(dur))
