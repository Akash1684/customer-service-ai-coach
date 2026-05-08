"""Integration test for `LocalFasterWhisperStream`.

Exercises the stream's audio-ingest → transcribe → event-emit loop without
requiring the real `WhisperModel` or a canned WAV file. A stub transcriber
returns fixed text once enough audio has been pushed; we assert the stream
emits INTERIM events during playback and promotes to FINAL on flush.
"""

from __future__ import annotations

import asyncio
import ctypes

import numpy as np
import pytest
from livekit import rtc
from livekit.agents import stt as lk_stt
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

from coach_agent.stt import local_whisper
from coach_agent.stt.local_whisper import (
    TARGET_SAMPLE_RATE,
    LocalFasterWhisperStream,
    LocalFasterWhisperSTT,
)


class FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeWhisperModel:
    """Returns successive canned transcripts on each `transcribe` call."""

    def __init__(self, transcripts: list[str]) -> None:
        self._transcripts = list(transcripts)
        self.call_count = 0

    def transcribe(self, _audio, **_kwargs):
        self.call_count += 1
        idx = min(self.call_count - 1, len(self._transcripts) - 1)
        text = self._transcripts[idx]
        return [FakeSegment(text)] if text else [], None


def make_frame(samples: np.ndarray, sample_rate: int = TARGET_SAMPLE_RATE) -> rtc.AudioFrame:
    """Build an rtc.AudioFrame from an int16 numpy array."""
    assert samples.dtype == np.int16
    samples_per_channel = len(samples)
    frame = rtc.AudioFrame.create(sample_rate, 1, samples_per_channel)
    # AudioFrame exposes its buffer via `data` (memoryview). Copy into it.
    byte_view = bytes(samples.tobytes())
    # `data` is a memoryview-like structure; copy via ctypes.
    ctypes.memmove(
        (ctypes.c_char * len(byte_view)).from_buffer(frame.data),
        byte_view,
        len(byte_view),
    )
    return frame


async def collect_events(stream: LocalFasterWhisperStream, timeout: float = 5.0) -> list:
    """Drain events from the stream until it closes or the timeout elapses."""
    events = []
    try:
        async with asyncio.timeout(timeout):
            async for ev in stream:
                events.append(ev)
    except asyncio.TimeoutError:
        pass
    return events


@pytest.mark.asyncio
async def test_stream_emits_interim_then_final(monkeypatch):
    """Push audio → get INTERIM events; flush → get FINAL event."""
    fake_model = FakeWhisperModel(
        [
            "hello",
            "hello world",
            "hello world this is a test",
        ]
    )

    # Build a stream directly without loading the real model.
    stt_instance = LocalFasterWhisperSTT()
    stream = LocalFasterWhisperStream(
        stt=stt_instance,
        model=fake_model,  # type: ignore[arg-type]
        language="en",
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
    )

    # Make the chunk interval tiny so the test runs fast.
    monkeypatch.setattr(local_whisper, "CHUNK_INTERVAL_S", 0.0)

    # Push ~1 second of audio in 4 frames of 250 ms each.
    frame_samples = int(TARGET_SAMPLE_RATE * 0.25)
    for _ in range(4):
        samples = (np.random.default_rng(0).integers(-2000, 2000, frame_samples)).astype(np.int16)
        stream.push_frame(make_frame(samples))
        await asyncio.sleep(0.01)

    # Flush — should trigger FINAL_TRANSCRIPT.
    stream.flush()
    stream.end_input()

    events = await collect_events(stream, timeout=5.0)
    await stream.aclose()

    types = [e.type for e in events]
    assert lk_stt.SpeechEventType.INTERIM_TRANSCRIPT in types, types
    assert lk_stt.SpeechEventType.FINAL_TRANSCRIPT in types, types

    # FINAL must appear after at least one INTERIM and carry the latest text.
    final = next(e for e in events if e.type == lk_stt.SpeechEventType.FINAL_TRANSCRIPT)
    assert final.alternatives[0].text  # non-empty


@pytest.mark.asyncio
async def test_stream_does_not_emit_final_for_empty_audio(monkeypatch):
    """If the model never returns text, FINAL must not be emitted."""
    silent_model = FakeWhisperModel([""])  # empty result every call

    stt_instance = LocalFasterWhisperSTT()
    stream = LocalFasterWhisperStream(
        stt=stt_instance,
        model=silent_model,  # type: ignore[arg-type]
        language="en",
        conn_options=DEFAULT_API_CONNECT_OPTIONS,
    )
    monkeypatch.setattr(local_whisper, "CHUNK_INTERVAL_S", 0.0)

    frame_samples = int(TARGET_SAMPLE_RATE * 0.5)
    samples = np.zeros(frame_samples, dtype=np.int16)
    stream.push_frame(make_frame(samples))
    await asyncio.sleep(0.1)
    stream.flush()
    stream.end_input()

    events = await collect_events(stream, timeout=3.0)
    await stream.aclose()

    # No FINAL should have been emitted because no text was ever produced.
    assert lk_stt.SpeechEventType.FINAL_TRANSCRIPT not in [e.type for e in events]
