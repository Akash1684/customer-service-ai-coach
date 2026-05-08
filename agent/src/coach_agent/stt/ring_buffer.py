"""Fixed-capacity audio ring buffer for sliding-window streaming ASR.

Appends int16 PCM samples and returns a view of the most recent N seconds
as normalized float32 in [-1.0, 1.0], which is what `faster-whisper`
expects. Kept deliberately dependency-light (only numpy) so it can be
unit-tested without the model or the LiveKit runtime.
"""

from __future__ import annotations

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

        self._capacity = int(sample_rate * window_seconds)
        self._buf = np.zeros(self._capacity, dtype=np.int16)
        self._size = 0  # number of valid samples in _buf

    @property
    def size(self) -> int:
        """Number of samples currently held (0 .. capacity)."""
        return self._size

    def append(self, samples: np.ndarray) -> None:
        """Append int16 PCM samples; oldest samples are evicted beyond capacity."""
        arr = np.asarray(samples, dtype=np.int16).reshape(-1)
        if arr.size == 0:
            return
        # Combine live samples + new, keep only the tail that fits in the window.
        combined = np.concatenate([self._buf[: self._size], arr])
        tail = combined[-self._capacity :]
        self._size = tail.size
        self._buf[: self._size] = tail

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
