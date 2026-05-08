"""Pacing detector — rolling + cumulative words-per-minute.

Consumes final transcript segments annotated with their monotonic-time
stamp. Tracks:

- **current WPM**: words within the last ``window_s`` seconds of speech,
  annualized to a per-minute rate.
- **average WPM**: cumulative words / cumulative seconds of session time.
- **band**: ``"slow"`` if avg WPM is below ``wpm_low``, ``"fast"`` if above
  ``wpm_high``, else ``"ok"``.

The clock used is whatever the caller passes as ``t_ms`` — use a single
monotonic source throughout a session so the arithmetic is consistent.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .base import DetectorEvent


@dataclass(frozen=True)
class _Segment:
    t_ms: int
    words: int


class PacingDetector:
    """Rolling/cumulative WPM tracker with band transitions.

    Emits ``pace_fast`` / ``pace_slow`` events on the transition into a band,
    not on every update, so consumers can react once per transition.
    """

    def __init__(
        self,
        *,
        wpm_low: float = 110.0,
        wpm_high: float = 165.0,
        window_s: float = 10.0,
    ) -> None:
        if wpm_low >= wpm_high:
            raise ValueError("wpm_low must be < wpm_high")
        if window_s <= 0:
            raise ValueError("window_s must be positive")
        self._wpm_low = wpm_low
        self._wpm_high = wpm_high
        self._window_ms = int(window_s * 1000)

        self._segments: deque[_Segment] = deque()
        self._cum_words: int = 0
        self._session_start_ms: int | None = None
        self._last_t_ms: int | None = None
        self._last_band: str = "ok"

    def reset(self) -> None:
        self._segments.clear()
        self._cum_words = 0
        self._session_start_ms = None
        self._last_t_ms = None
        self._last_band = "ok"

    def on_final(self, text: str, t_ms: int) -> list[DetectorEvent]:
        words = len(text.split())
        if words == 0:
            return []

        if self._session_start_ms is None:
            self._session_start_ms = t_ms
        self._last_t_ms = t_ms

        self._cum_words += words
        self._segments.append(_Segment(t_ms=t_ms, words=words))
        self._evict_stale(t_ms)

        events: list[DetectorEvent] = []
        band = self.band()
        if band != self._last_band:
            if band == "fast":
                events.append(DetectorEvent(kind="pace_fast", t_ms=t_ms, detail=f"{self.wpm_avg():.0f} wpm"))
            elif band == "slow":
                events.append(DetectorEvent(kind="pace_slow", t_ms=t_ms, detail=f"{self.wpm_avg():.0f} wpm"))
            self._last_band = band
        return events

    def _evict_stale(self, now_ms: int) -> None:
        cutoff = now_ms - self._window_ms
        while self._segments and self._segments[0].t_ms < cutoff:
            self._segments.popleft()

    def wpm_current(self, *, now_ms: int | None = None) -> float:
        """Words/minute over the last ``window_s`` seconds of speech."""
        if self._last_t_ms is None:
            return 0.0
        reference = now_ms if now_ms is not None else self._last_t_ms
        self._evict_stale(reference)
        if not self._segments:
            return 0.0
        words = sum(s.words for s in self._segments)
        # Use the effective span: either the full window or from the first
        # segment onwards, whichever is shorter. This keeps early values
        # sensible before the window is fully populated.
        span_ms = min(self._window_ms, max(1, reference - self._segments[0].t_ms + 1))
        minutes = span_ms / 60_000.0
        return words / minutes if minutes > 0 else 0.0

    def wpm_avg(self) -> float:
        """Cumulative words/minute since session start."""
        if self._session_start_ms is None or self._last_t_ms is None:
            return 0.0
        span_ms = max(1, self._last_t_ms - self._session_start_ms)
        minutes = span_ms / 60_000.0
        return self._cum_words / minutes if minutes > 0 else 0.0

    def band(self) -> str:
        avg = self.wpm_avg()
        if avg == 0:
            return "ok"
        if avg < self._wpm_low:
            return "slow"
        if avg > self._wpm_high:
            return "fast"
        return "ok"
