"""Unit tests for `coach_agent.transport.liveness`."""

from __future__ import annotations

import json

from coach_agent.transport.liveness import (
    LIVENESS_TOPIC,
    Heartbeat,
    HeartbeatSource,
)


class FakeClock:
    """Pinned-time clock returning successive values from a script."""

    def __init__(self, ticks_ms: list[int]) -> None:
        self._ticks = list(ticks_ms)
        self._i = 0

    def __call__(self) -> int:
        # Repeat the last tick if tests over-read; avoids IndexError noise.
        value = self._ticks[min(self._i, len(self._ticks) - 1)]
        self._i += 1
        return value


def test_topic_constant_is_stable_wire_name() -> None:
    """The topic the UI will subscribe to must stay stable."""
    assert LIVENESS_TOPIC == "liveness"


def test_heartbeat_serialization_matches_wire_format() -> None:
    hb = Heartbeat(seq=7, t_ms=12340)
    payload = hb.to_bytes()
    decoded = json.loads(payload.decode("utf-8"))
    assert decoded == {"seq": 7, "t_ms": 12340, "status": "alive"}


def test_heartbeat_source_seq_increments_monotonically() -> None:
    source = HeartbeatSource(now_ms=FakeClock([0, 100, 250, 400]))
    beats = [source.next() for _ in range(3)]
    assert [b.seq for b in beats] == [1, 2, 3]


def test_heartbeat_source_t_ms_is_non_decreasing_and_relative_to_start() -> None:
    # Start at t=1000 so that absolute wall-clock is clearly non-zero but
    # heartbeat t_ms (which is relative to start) begins at 0.
    source = HeartbeatSource(now_ms=FakeClock([1_000, 1_400, 2_500, 2_500]))
    beats = [source.next() for _ in range(3)]
    t = [b.t_ms for b in beats]
    assert t[0] == 400
    assert t[1] == 1500
    assert t[2] == 1500  # clock stalled: t_ms stays flat, never goes backward
    assert all(t[i + 1] >= t[i] for i in range(len(t) - 1))


def test_heartbeat_source_count_reflects_emitted_beats() -> None:
    source = HeartbeatSource(now_ms=FakeClock([0, 100, 200, 300, 400]))
    assert source.count == 0
    source.next()
    source.next()
    assert source.count == 2


def test_heartbeat_source_handles_clock_rewind_without_negative_t() -> None:
    """Even if the underlying clock rewinds, t_ms never goes negative."""
    source = HeartbeatSource(now_ms=FakeClock([1_000, 500, 1_200]))  # second tick is before start
    source.next()
    second = source.next()
    assert second.t_ms >= 0
