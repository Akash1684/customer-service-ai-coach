"""Tests for `MetricsSnapshotBuilder` — rate-limited publishing + snapshot shape."""

from __future__ import annotations

import asyncio

import pytest

from coach_agent.config import CoachSettings
from coach_agent.pipeline import MetricsSnapshotBuilder


def _settings(interval_s: float = 0.05) -> CoachSettings:
    # Short interval keeps tests fast.
    return CoachSettings(metrics_publish_interval_s=interval_s)


@pytest.mark.asyncio
async def test_snapshot_has_expected_fields():
    builder = MetricsSnapshotBuilder(_settings(), publish=_noop_publish)
    builder.on_final("um so like yeah", t_ms=1_000)
    snap = builder.snapshot().to_dict()
    for key in (
        "t_ms",
        "fillers_total",
        "fillers_last",
        "wpm_current",
        "wpm_avg",
        "pacing_band",
        "prohibited_hits",
        "prohibited_last",
        "sentiment_tag",
        "sentiment_score",
    ):
        assert key in snap, f"missing key {key!r} in snapshot"


@pytest.mark.asyncio
async def test_burst_of_events_coalesces_into_one_publish():
    published: list[dict] = []

    async def publish(snap: dict) -> None:
        published.append(snap)

    settings = _settings(interval_s=0.05)
    builder = MetricsSnapshotBuilder(settings, publish=publish)

    # Burst 10 events in < 5 ms — must coalesce into a single publish after
    # the trailing window (50 ms) closes.
    for i in range(10):
        builder.on_final(f"word{i}", t_ms=i)
    assert published == []  # nothing yet

    await asyncio.sleep(0.12)
    assert len(published) == 1, f"expected 1 publish, got {len(published)}"


@pytest.mark.asyncio
async def test_two_separated_bursts_produce_two_publishes():
    published: list[dict] = []

    async def publish(snap: dict) -> None:
        published.append(snap)

    settings = _settings(interval_s=0.05)
    builder = MetricsSnapshotBuilder(settings, publish=publish)

    builder.on_final("um um um", t_ms=1)
    await asyncio.sleep(0.1)
    builder.on_final("uh like like", t_ms=2_000)
    await asyncio.sleep(0.1)

    assert len(published) == 2
    # Counters should be cumulative: fillers_total rose between snapshots.
    assert published[1]["fillers_total"] >= published[0]["fillers_total"]


@pytest.mark.asyncio
async def test_empty_text_does_not_schedule_publish():
    published: list[dict] = []

    async def publish(snap: dict) -> None:
        published.append(snap)

    builder = MetricsSnapshotBuilder(_settings(), publish=publish)
    builder.on_final("   ", t_ms=1)
    await asyncio.sleep(0.1)
    assert published == []


@pytest.mark.asyncio
async def test_reset_clears_detector_state():
    builder = MetricsSnapshotBuilder(_settings(), publish=_noop_publish)
    builder.on_final("um um so so", t_ms=1)
    assert builder.snapshot().fillers_total > 0
    builder.reset()
    snap = builder.snapshot()
    assert snap.fillers_total == 0
    assert snap.fillers_last is None
    assert snap.prohibited_hits == 0


async def _noop_publish(snap: dict) -> None:
    pass
