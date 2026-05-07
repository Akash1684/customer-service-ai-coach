"""Tests for `PacingDetector`."""

from __future__ import annotations

import pytest

from coach_agent.detectors import PacingDetector


def test_rejects_invalid_config():
    with pytest.raises(ValueError):
        PacingDetector(wpm_low=200, wpm_high=100)
    with pytest.raises(ValueError):
        PacingDetector(window_s=0)


def test_empty_state_returns_zero_wpm():
    p = PacingDetector()
    assert p.wpm_current() == 0.0
    assert p.wpm_avg() == 0.0
    assert p.band() == "ok"


def test_average_wpm_over_two_seconds_of_speech():
    p = PacingDetector(wpm_low=80, wpm_high=200, window_s=10)
    # 4 words at t=0s, then 6 words at t=2s  →  10 words in 2 s = 300 wpm
    p.on_final("one two three four", t_ms=0)
    p.on_final("five six seven eight nine ten", t_ms=2_000)
    assert p.wpm_avg() == pytest.approx(300.0, abs=1.0)


def test_window_ages_out_older_segments():
    p = PacingDetector(wpm_low=0, wpm_high=1000, window_s=10)
    p.on_final("old words here", t_ms=0)  # 3 words @ t=0
    p.on_final("fresh words now", t_ms=15_000)  # 3 words @ t=15 s
    # t=0 is outside the 10 s window as of t=15 s, so current WPM reflects
    # only the recent 3 words spread across the effective window.
    assert p.wpm_current(now_ms=15_000) > 0.0
    # And the old segment has been evicted from the deque.
    assert len(p._segments) == 1  # type: ignore[attr-defined]


def test_band_transitions_emit_events_once():
    p = PacingDetector(wpm_low=110, wpm_high=165, window_s=10)
    # ~250 wpm: 25 words over 6 s → 250 wpm avg
    words = " ".join([f"w{i}" for i in range(25)])
    events = p.on_final(words, t_ms=6_000)
    assert p.band() == "fast"
    kinds = [e.kind for e in events]
    assert "pace_fast" in kinds

    # Same pace — no new transition event
    events2 = p.on_final("w25 w26 w27", t_ms=7_000)
    assert not any(e.kind == "pace_fast" for e in events2)


def test_reset_clears_state():
    p = PacingDetector()
    p.on_final("one two three", t_ms=1_000)
    p.reset()
    assert p.wpm_avg() == 0.0
    assert p.band() == "ok"
