"""Coaching detectors — Step 5.

Each detector consumes final transcript segments (plus a monotonic timestamp)
and contributes state to the next `MetricsSnapshot`. They are intentionally
tiny and pure so they test cleanly in isolation.

- `FillerDetector`   — counts filler words per configured list
- `PacingDetector`   — rolling + cumulative words-per-minute (WPM)
- `ProhibitedDetector` — exact + fuzzy match against a phrase list
- `SentimentDetector`  — VADER-based tone tag (Positive / Neutral / Flat / Negative)
"""

from .base import DetectorEvent
from .filler import FillerDetector
from .pacing import PacingDetector
from .prohibited import ProhibitedDetector
from .sentiment import SentimentDetector

__all__ = [
    "DetectorEvent",
    "FillerDetector",
    "PacingDetector",
    "ProhibitedDetector",
    "SentimentDetector",
]
