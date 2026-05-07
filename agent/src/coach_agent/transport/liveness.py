"""Liveness heartbeat payloads.

Step 2 uses this to prove the agent→UI data-channel loop works end-to-end,
before any real ASR, detectors, or LLM are wired in. The source is kept
small, pure, and dependency-free so it can be unit-tested with a fake clock.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Literal

LIVENESS_TOPIC = "liveness"


@dataclass(frozen=True)
class Heartbeat:
    """Agent heartbeat payload emitted on the `liveness` topic."""

    seq: int
    t_ms: int
    status: Literal["alive"] = "alive"

    def to_bytes(self) -> bytes:
        """Serialize as JSON utf-8 bytes, matching the UI's TextDecoder flow."""
        return json.dumps(asdict(self), separators=(",", ":")).encode("utf-8")


class HeartbeatSource:
    """Generates heartbeats with monotonically non-decreasing `t_ms`.

    Independent of real wall time so tests can pin it with a fake clock.
    Backed by `time.monotonic_ns()` in production.
    """

    def __init__(self, now_ms: Callable[[], int] | None = None) -> None:
        self._now_ms = now_ms or (lambda: time.monotonic_ns() // 1_000_000)
        self._start_ms = self._now_ms()
        self._seq = 0

    def next(self) -> Heartbeat:
        """Return the next heartbeat. `seq` starts at 1 and increases by 1."""
        self._seq += 1
        t = max(0, self._now_ms() - self._start_ms)
        return Heartbeat(seq=self._seq, t_ms=t)

    @property
    def count(self) -> int:
        """Number of heartbeats emitted so far."""
        return self._seq
