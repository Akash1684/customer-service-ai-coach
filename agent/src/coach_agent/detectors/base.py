"""Shared detector primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DetectorEvent:
    """A single coaching signal emitted by a detector.

    Kept intentionally generic so Step 8's NudgeWorker can consume the same
    stream without each detector having its own event subclass.
    """

    kind: str  # e.g. "filler", "prohibited", "pace_fast", "sentiment_dip"
    t_ms: int  # wall-clock timestamp of the trigger
    detail: str = ""  # human-readable specifics (e.g. the offending phrase)
    meta: dict[str, Any] | None = None  # optional structured payload
