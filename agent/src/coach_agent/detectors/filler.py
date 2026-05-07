"""Filler-word detector.

Counts case-insensitive matches of configured filler phrases in **final**
transcripts only — interim transcripts are ignored so we never double-count
when an interim is promoted to final.

Matching strategy:
- Tokenize the transcript by stripping trailing/leading punctuation and
  lowercasing.
- For single-word fillers (``um``, ``uh``), check token equality.
- For multi-word fillers (``you know``, ``i mean``), check bigram equality on
  successive tokens.

The same word can appear multiple times in one final and all occurrences
count: ``"um um um"`` registers as three fillers.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .base import DetectorEvent

_PUNCT_STRIP_RE = re.compile(r"^[^\w]+|[^\w]+$")


def _normalize_token(tok: str) -> str:
    """Lowercase and strip surrounding punctuation from a token."""
    return _PUNCT_STRIP_RE.sub("", tok.lower())


def _tokenize(text: str) -> list[str]:
    """Whitespace-split then punctuation-strip. Empty tokens are dropped."""
    return [t for t in (_normalize_token(raw) for raw in text.split()) if t]


class FillerDetector:
    """Counts filler hits across an ongoing session."""

    def __init__(self, filler_words: Iterable[str]) -> None:
        # Split configured filler phrases into unigrams vs bigrams so we can
        # match each with a single pass over the token list.
        self._unigrams: set[str] = set()
        self._bigrams: set[tuple[str, str]] = set()
        for phrase in filler_words:
            tokens = [_normalize_token(t) for t in phrase.split()]
            tokens = [t for t in tokens if t]
            if len(tokens) == 1:
                self._unigrams.add(tokens[0])
            elif len(tokens) == 2:
                self._bigrams.add((tokens[0], tokens[1]))
            # Longer phrases aren't supported in the P0 filler list.

        self._total: int = 0
        self._last_word: str | None = None

    @property
    def total(self) -> int:
        """Cumulative filler count for the current session."""
        return self._total

    @property
    def last_word(self) -> str | None:
        """Most recently heard filler, or ``None`` if none yet."""
        return self._last_word

    def reset(self) -> None:
        self._total = 0
        self._last_word = None

    def on_final(self, text: str, t_ms: int) -> list[DetectorEvent]:
        """Process a final transcript segment; return per-hit events."""
        events: list[DetectorEvent] = []
        tokens = _tokenize(text)

        # Bigrams first so that "you know" isn't double-counted by a lone "you".
        skip_next = False
        for i, tok in enumerate(tokens):
            if skip_next:
                skip_next = False
                continue
            if i + 1 < len(tokens) and (tok, tokens[i + 1]) in self._bigrams:
                phrase = f"{tok} {tokens[i + 1]}"
                events.append(DetectorEvent(kind="filler", t_ms=t_ms, detail=phrase))
                self._total += 1
                self._last_word = phrase
                skip_next = True
                continue
            if tok in self._unigrams:
                events.append(DetectorEvent(kind="filler", t_ms=t_ms, detail=tok))
                self._total += 1
                self._last_word = tok
        return events
