"""Unit tests for `coach_agent.stt.ring_buffer`."""

from __future__ import annotations

import numpy as np
import pytest

from coach_agent.stt.ring_buffer import AudioRingBuffer


def test_constructor_rejects_bad_args():
    with pytest.raises(ValueError):
        AudioRingBuffer(0, 1.0)
    with pytest.raises(ValueError):
        AudioRingBuffer(16000, 0)


def test_append_within_capacity_accumulates():
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=1.0)
    buf.append(np.ones(8000, dtype=np.int16))
    buf.append(np.ones(4000, dtype=np.int16) * 2)
    assert buf.size == 12000
    snap = buf.snapshot_float32()
    assert snap.shape == (12000,)
    # first 8000 samples are 1/32768, next 4000 are 2/32768
    assert snap[0] == pytest.approx(1 / 32768, rel=1e-3)
    assert snap[8001] == pytest.approx(2 / 32768, rel=1e-3)


def test_append_beyond_capacity_keeps_tail():
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=0.5)  # 8000-sample capacity
    # Push 10 seconds (160000 samples) of a repeating pattern that fits in int16.
    # Sample value = i % 30000 so eviction behavior is testable without wrapping.
    data = (np.arange(160000) % 30000).astype(np.int16)
    buf.append(data)
    assert buf.size == 8000  # capped
    snap = buf.snapshot_float32()
    # Should contain the LAST 8000 samples: indices 152000..159999.
    expected_first = (152000 % 30000) / 32768
    expected_last = (159999 % 30000) / 32768
    assert snap[0] == pytest.approx(expected_first, rel=1e-3)
    assert snap[-1] == pytest.approx(expected_last, rel=1e-3)


def test_append_across_capacity_boundary_shifts_left():
    buf = AudioRingBuffer(sample_rate=100, window_seconds=1.0)  # capacity = 100
    buf.append(np.full(60, 7, dtype=np.int16))  # size=60
    buf.append(np.full(60, 11, dtype=np.int16))  # would overflow; shifts by 20
    assert buf.size == 100
    snap = buf.snapshot_float32()
    # First 40 should be 7s (shifted-in remainder from old data), then 60 of 11s.
    assert np.allclose(snap[:40], 7 / 32768)
    assert np.allclose(snap[40:], 11 / 32768)


def test_duration_and_total_seen():
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=2.0)
    buf.append(np.zeros(16000, dtype=np.int16))
    assert buf.duration_s == pytest.approx(1.0)
    assert buf.total_seen_samples == 16000
    buf.append(np.zeros(40000, dtype=np.int16))
    assert buf.duration_s == pytest.approx(2.0)  # capped
    assert buf.total_seen_samples == 56000  # unbounded


def test_clear_empties_buffer_but_preserves_total_seen():
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=1.0)
    buf.append(np.ones(1000, dtype=np.int16))
    buf.clear()
    assert buf.size == 0
    assert buf.duration_s == 0.0
    assert buf.total_seen_samples == 1000


def test_snapshot_is_a_copy():
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=1.0)
    buf.append(np.full(100, 1000, dtype=np.int16))
    snap = buf.snapshot_float32()
    snap[0] = 999.0  # mutation must not leak back into buffer
    again = buf.snapshot_float32()
    assert again[0] == pytest.approx(1000 / 32768)


def test_empty_snapshot_returns_zero_len_array():
    buf = AudioRingBuffer(sample_rate=16000, window_seconds=1.0)
    snap = buf.snapshot_float32()
    assert snap.shape == (0,)
    assert snap.dtype == np.float32
