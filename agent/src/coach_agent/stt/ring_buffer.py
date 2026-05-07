"""Fixed-capacity audio ring buffer for sliding-window streaming ASR.

Appends int16 PCM samples and returns a view of the most recent N seconds
as normalized float32 in [-1.0, 1.0], which is what `faster-whisper`
expects. Kept deliberately dependency-light (only numpy) so it can be
unit-tested without the model or the LiveKit runtime.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np


class AudioRingBuffer:
    """Fixed-size ring buffer for int16 PCM samples at a fixed sample rate.

    The buffer holds at most `window_seconds` of audio; older samples are
    evicted as new ones arrive. `snapshot_float32()` returns a copy of the
    currently-held samples normalized to the float32 range Whisper expects.
    """

    def __init__(self, sample_rate: int, window_seconds: float) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self._sample_rate = sample_rate
        self._capacity = int(sample_rate * window_seconds)
        self._buf = np.zeros(self._capacity, dtype=np.int16)
        self._size = 0  # number of valid samples in _buf
        self._total_seen = 0  # cumulative samples ever appended

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def capacity_samples(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        """Number of samples currently held (0 .. capacity)."""
        return self._size

    @property
    def duration_s(self) -> float:
        """Duration of audio currently held, in seconds."""
        return self._size / self._sample_rate

    @property
    def total_seen_samples(self) -> int:
        """Cumulative samples ever appended, even after eviction."""
        return self._total_seen

    def append(self, samples: Iterable[int] | np.ndarray) -> None:
        """Append int16 PCM samples; oldest samples are evicted if at capacity."""
        arr = np.asarray(samples, dtype=np.int16)
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        if arr.size == 0:
            return

        self._total_seen += arr.size

        if arr.size >= self._capacity:
            # Take only the tail that fits.
            self._buf[:] = arr[-self._capacity :]
            self._size = self._capacity
            return

        free = self._capacity - self._size
        if arr.size <= free:
            self._buf[self._size : self._size + arr.size] = arr
            self._size += arr.size
        else:
            # Shift existing samples left to make room.
            shift = arr.size - free
            self._buf[: self._size - shift] = self._buf[shift : self._size]
            self._buf[self._size - shift : self._capacity] = arr
            self._size = self._capacity

    def snapshot_float32(self) -> np.ndarray:
        """Return the currently-held samples as float32 in [-1.0, 1.0].

        The returned array is a fresh copy so the buffer can continue being
        mutated while the caller is running Whisper on the snapshot.
        """
        if self._size == 0:
            return np.zeros(0, dtype=np.float32)
        return self._buf[: self._size].astype(np.float32) / 32768.0

    def clear(self) -> None:
        self._size = 0
