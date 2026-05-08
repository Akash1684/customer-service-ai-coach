"""Coaching detectors.

Each detector consumes final transcript segments (plus a monotonic timestamp)
and contributes state to the next `MetricsSnapshot`. They are intentionally
tiny and pure so they test cleanly in isolation.

- `FillerDetector`     — counts filler words per configured list
- `ProhibitedDetector` — exact + fuzzy match against a phrase list
- `SentimentDetector`  — VADER-based tone tag (Positive / Neutral / Negative)
"""

from .base import DetectorEvent
from .filler import FillerDetector
from .prohibited import ProhibitedDetector
from .sentiment import SentimentDetector

__all__ = [
    "DetectorEvent",
    "FillerDetector",
    "ProhibitedDetector",
    "SentimentDetector",
]
