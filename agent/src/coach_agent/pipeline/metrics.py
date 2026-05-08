"""Rate-limited metrics snapshot composer.

`MetricsSnapshotBuilder` owns the detector instances and exposes two surfaces:

- ``on_final(text, t_ms)`` — called by the transcript pipeline after each
  final transcript. Feeds every detector and schedules a publish.
- ``snapshot()`` — produces a JSON-serializable dict matching the wire
  format the UI consumes.

Publishing is coalesced through an asyncio-based trailing timer. A burst of
N events within the window emits exactly one packet after the window
closes.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass

from ..config import CoachSettings
from ..detectors import (
    FillerDetector,
    ProhibitedDetector,
    SentimentDetector,
)

logger = logging.getLogger(__name__)

PublishCallback = Callable[[dict], Awaitable[None]]


@dataclass
class MetricsSnapshot:
    """Wire format for the ``metrics`` data-channel topic."""

    t_ms: int
    fillers_total: int
    fillers_last: str | None
    prohibited_hits: int
    prohibited_last: str | None
    sentiment_tag: str
    sentiment_score: float

    def to_dict(self) -> dict:
        return asdict(self)


class MetricsSnapshotBuilder:
    """Composes detector state into `MetricsSnapshot` and publishes it."""

    def __init__(
        self,
        settings: CoachSettings,
        publish: PublishCallback,
    ) -> None:
        self._settings = settings
        self._publish = publish

        self._filler = FillerDetector(settings.filler_words)
        self._prohibited = ProhibitedDetector(settings.prohibited_phrases)
        self._sentiment = SentimentDetector()

        self._pending: asyncio.Task | None = None

    def reset(self) -> None:
        """Clear all detector state. Call on session start."""
        self._filler.reset()
        self._prohibited.reset()
        self._sentiment.reset()
        if self._pending and not self._pending.done():
            self._pending.cancel()
        self._pending = None

    def on_final(self, text: str, t_ms: int) -> None:
        """Feed a final transcript through all detectors and schedule publish."""
        if not text.strip():
            return
        self._filler.on_final(text, t_ms)
        self._prohibited.on_final(text, t_ms)
        self._sentiment.on_final(text, t_ms)
        self._schedule_publish()

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            t_ms=int(time.time() * 1000),
            fillers_total=self._filler.total,
            fillers_last=self._filler.last_word,
            prohibited_hits=self._prohibited.hits,
            prohibited_last=self._prohibited.last_match,
            sentiment_tag=self._sentiment.tag(),
            sentiment_score=round(self._sentiment.compound(), 3),
        )

    def _schedule_publish(self) -> None:
        """Schedule a trailing-edge publish; coalesce bursts inside the window."""
        if self._pending is not None and not self._pending.done():
            return  # a publish is already pending — let it trail-fire
        loop = asyncio.get_running_loop()
        self._pending = loop.create_task(self._publish_trailing())

    async def _publish_trailing(self) -> None:
        try:
            await asyncio.sleep(self._settings.metrics_publish_interval_s)
            snap = self.snapshot()
            try:
                await self._publish(snap.to_dict())
            except Exception:
                logger.exception("metrics publish failed")
        except asyncio.CancelledError:
            pass
