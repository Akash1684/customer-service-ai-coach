"""Shared detector primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DetectorEvent:
    """A single coaching signal emitted by a detector.

    Detectors return these alongside mutating their own state; today only
    the `MetricsSnapshotBuilder` consumes them (for logging/debug).
    """

    kind: str  # e.g. "filler", "prohibited", "pace_fast", "sentiment_dip"
    t_ms: int  # wall-clock timestamp of the trigger
    detail: str = ""  # human-readable specifics (e.g. the offending phrase)
    meta: dict[str, Any] | None = None  # optional structured payload
