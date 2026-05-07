"""E2E combined speaker + listener — single participant.

Publishes a WAV as an audio track AND listens for the agent's transcript data
packets on the same LiveKit connection. This ensures the AgentSession picks
up *our* audio track (vs a non-publishing bystander).

Usage:
    uv run tests/e2e_speaker_listener.py /tmp/coach-test.wav
"""

from __future__ import annotations

import asyncio
import json
import sys
import wave
from datetime import timedelta

from livekit import api, rtc

LK_URL = "ws://127.0.0.1:7880"
API_KEY = "devkey"
API_SECRET = "secret"
ROOM = "coach-room"
IDENTITY = "e2e-rep"

FRAME_MS = 20


def mint_token() -> str:
    return (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity(IDENTITY)
        .with_name(IDENTITY)
        .with_grants(api.VideoGrants(room_join=True, room=ROOM, can_publish=True))
        .with_ttl(timedelta(minutes=15))
        .to_jwt()
    )


async def publish_wav(source: rtc.AudioSource, wav_path: str) -> None:
    with wave.open(wav_path, "rb") as w:
        sample_rate = w.getframerate()
        num_channels = w.getnchannels()
        assert w.getsampwidth() == 2
        frames = w.readframes(w.getnframes())

    samples_per_frame = int(sample_rate * FRAME_MS / 1000)
    bytes_per_frame = samples_per_frame * num_channels * 2

    pos = 0
    sent = 0
    while pos + bytes_per_frame <= len(frames):
        chunk = frames[pos : pos + bytes_per_frame]
        frame = rtc.AudioFrame(
            data=chunk,
            sample_rate=sample_rate,
            num_channels=num_channels,
            samples_per_channel=samples_per_frame,
        )
        await source.capture_frame(frame)
        pos += bytes_per_frame
        sent += 1
        await asyncio.sleep(FRAME_MS / 1000)
    print(f"  pushed {sent} frames ({pos} bytes) of audio", flush=True)


async def main(wav_path: str, hold_after_audio_s: float = 8.0) -> None:
    room = rtc.Room()
    packets: list[dict] = []

    @room.on("data_received")
    def on_data(packet: rtc.DataPacket):
        try:
            text = packet.data.decode("utf-8")
            obj = json.loads(text)
            print(f"[{packet.topic}] {obj}", flush=True)
            packets.append({"topic": packet.topic, "payload": obj})
        except Exception as e:
            print(f"!! bad packet: {e}")

    token = mint_token()
    print(f"Connecting as {IDENTITY} to {LK_URL}...", flush=True)
    await room.connect(LK_URL, token)

    with wave.open(wav_path, "rb") as w:
        sample_rate = w.getframerate()
        num_channels = w.getnchannels()
    source = rtc.AudioSource(sample_rate=sample_rate, num_channels=num_channels)
    track = rtc.LocalAudioTrack.create_audio_track("mic", source)
    publication = await room.local_participant.publish_track(
        track, rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
    )
    print(f"Published audio track sid={publication.sid}", flush=True)

    # Give the agent a moment to subscribe + start Whisper.
    await asyncio.sleep(0.5)

    print(f"Streaming {wav_path}...", flush=True)
    await publish_wav(source, wav_path)

    print(f"Holding {hold_after_audio_s}s for STT to finalize...", flush=True)
    await asyncio.sleep(hold_after_audio_s)

    await room.disconnect()

    transcripts = [p for p in packets if p["topic"] == "transcript"]
    print("\n=== SUMMARY ===")
    print(f"Data packets total: {len(packets)}")
    print(f"Transcript packets: {len(transcripts)}")
    if transcripts:
        print(f"First: {transcripts[0]['payload']}")
        print(f"Last:  {transcripts[-1]['payload']}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/coach-test.wav"
    asyncio.run(main(path))
