"""Runtime configuration for the coaching detectors and pacing heuristics.

Ships a single frozen defaults bundle; instantiate with ``CoachSettings()``.
A future ``update_settings`` RPC would mutate a live instance from the UI.
"""

from __future__ import annotations

from dataclasses import dataclass

# Tuned for North-American customer-service speech. Baseline reading pace is
# ~150 wpm; anything slower sounds tentative, anything faster sounds rushed.
DEFAULT_WPM_LOW = 110.0
DEFAULT_WPM_HIGH = 165.0

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
    wpm_low: float = DEFAULT_WPM_LOW
    wpm_high: float = DEFAULT_WPM_HIGH
    # Window over which `PacingDetector.wpm_current` is computed.
    pacing_window_s: float = 10.0
    # Rate-limit window for MetricsSnapshot publishes. A burst of detector
    # events within this interval is coalesced into a single packet emitted
    # on the trailing edge.
    metrics_publish_interval_s: float = 0.25
