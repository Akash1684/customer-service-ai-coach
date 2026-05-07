"""Prohibited-phrase detector — exact substring + fuzzy fallback.

Matches each configured phrase against final transcript text, case-insensitive.
Uses plain substring first, then ``rapidfuzz.fuzz.partial_ratio >= 88`` to
catch minor misrecognitions from Whisper (``"dont know"`` vs ``"don't know"``,
``"thats not my problem"`` vs ``"that's not my problem"``).

Tracks cumulative hit count and the most recent matched phrase for UI
display.
"""

from __future__ import annotations

from collections.abc import Iterable

from rapidfuzz import fuzz

from .base import DetectorEvent

FUZZY_THRESHOLD = 88


def _normalize(s: str) -> str:
    return " ".join(s.lower().split())


class ProhibitedDetector:
    def __init__(self, phrases: Iterable[str]) -> None:
        self._phrases: list[str] = [p for p in (_normalize(p) for p in phrases) if p]
        self._hits: int = 0
        self._last_match: str | None = None

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def last_match(self) -> str | None:
        return self._last_match

    def set_phrases(self, phrases: Iterable[str]) -> None:
        """Replace the phrase list live — preserves hit counters."""
        self._phrases = [p for p in (_normalize(p) for p in phrases) if p]

    def reset(self) -> None:
        self._hits = 0
        self._last_match = None

    def on_final(self, text: str, t_ms: int) -> list[DetectorEvent]:
        normalized = _normalize(text)
        if not normalized:
            return []

        events: list[DetectorEvent] = []
        for phrase in self._phrases:
            if phrase in normalized:
                events.append(DetectorEvent(kind="prohibited", t_ms=t_ms, detail=phrase))
                self._hits += 1
                self._last_match = phrase
                continue
            # Fuzzy fallback — partial_ratio is robust to missing apostrophes,
            # minor substitutions, and extra tokens on either side.
            score = fuzz.partial_ratio(phrase, normalized)
            if score >= FUZZY_THRESHOLD:
                events.append(
                    DetectorEvent(
                        kind="prohibited",
                        t_ms=t_ms,
                        detail=phrase,
                        meta={"match": "fuzzy", "score": score},
                    )
                )
                self._hits += 1
                self._last_match = phrase
        return events
