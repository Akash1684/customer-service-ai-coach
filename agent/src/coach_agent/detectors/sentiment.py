"""Text-level sentiment detector using VADER.

Accumulates final transcript segments in a rolling window and reports a tag:

- ``Positive``  — compound ≥ 0.30
- ``Neutral``   — -0.05 ≤ compound < 0.30  (covers factual / flat-tone speech)
- ``Negative``  — compound < -0.05

An earlier revision split the middle band into ``Neutral`` (mildly positive)
and ``Flat`` (no lexical signal at all). The distinction wasn't actionable
for a coach — both are "tone not worth flagging" — so the two were merged
into a single ``Neutral`` tag.

Emits ``sentiment_dip`` events only on *downgrades* (tone becoming more
negative) so the nudger can highlight moments the rep's tone slipped rather
than firing on every minor fluctuation.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from .base import DetectorEvent

_TAG_ORDER = ("Negative", "Neutral", "Positive")
_TAG_INDEX = {t: i for i, t in enumerate(_TAG_ORDER)}


@dataclass(frozen=True)
class _Segment:
    t_ms: int
    text: str


def _classify(compound: float) -> str:
    if compound >= 0.30:
        return "Positive"
    if compound >= -0.05:
        return "Neutral"
    return "Negative"


class SentimentDetector:
    def __init__(self, *, window_s: float = 20.0) -> None:
        self._analyzer = SentimentIntensityAnalyzer()
        self._window_ms = int(window_s * 1000)
        self._segments: deque[_Segment] = deque()
        self._current_tag: str = "Neutral"
        self._last_compound: float = 0.0

    @property
    def current_tag(self) -> str:
        return self._current_tag

    def tag(self) -> str:
        return self._current_tag

    def compound(self) -> float:
        return self._last_compound

    def reset(self) -> None:
        self._segments.clear()
        self._current_tag = "Neutral"
        self._last_compound = 0.0

    def on_final(self, text: str, t_ms: int) -> list[DetectorEvent]:
        stripped = text.strip()
        if not stripped:
            return []

        self._segments.append(_Segment(t_ms=t_ms, text=stripped))
        self._evict_stale(t_ms)

        merged = " ".join(seg.text for seg in self._segments)
        score = self._analyzer.polarity_scores(merged)
        compound = float(score.get("compound", 0.0))
        new_tag = _classify(compound)
        self._last_compound = compound

        events: list[DetectorEvent] = []
        if new_tag != self._current_tag:
            # Only emit dips (tone becoming more negative).
            if _TAG_INDEX[new_tag] < _TAG_INDEX[self._current_tag]:
                events.append(
                    DetectorEvent(
                        kind="sentiment_dip",
                        t_ms=t_ms,
                        detail=new_tag,
                        meta={"compound": compound, "from": self._current_tag},
                    )
                )
            self._current_tag = new_tag
        return events

    def _evict_stale(self, now_ms: int) -> None:
        cutoff = now_ms - self._window_ms
        while self._segments and self._segments[0].t_ms < cutoff:
            self._segments.popleft()
