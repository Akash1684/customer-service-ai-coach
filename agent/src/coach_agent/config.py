"""Runtime configuration for the coaching detectors.

Ships a single frozen defaults bundle; instantiate with ``CoachSettings()``.
A future ``update_settings`` RPC would mutate a live instance from the UI.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_FILLER_WORDS: tuple[str, ...] = (
    "um",
    "uh",
    "er",
    "ah",
    "like",
    "you know",
    "basically",
    "literally",
    "actually",
    "right",
    "well",
    "i mean",
    "sort of",
    "kind of",
)

DEFAULT_PROHIBITED_PHRASES: tuple[str, ...] = (
    "i don't know",
    "i don't care",
    "not my job",
    "deal with it",
    "i can't help you",
    "that's not my problem",
    "not my fault",
    "calm down",
    "you should have",
    "whatever",
    "nothing i can do",
)


@dataclass(frozen=True)
class CoachSettings:
    """Immutable settings bundle passed to the detector suite."""

    filler_words: tuple[str, ...] = DEFAULT_FILLER_WORDS
    prohibited_phrases: tuple[str, ...] = DEFAULT_PROHIBITED_PHRASES
    # Rate-limit window for MetricsSnapshot publishes. A burst of detector
    # events within this interval is coalesced into a single packet emitted
    # on the trailing edge.
    metrics_publish_interval_s: float = 0.25
