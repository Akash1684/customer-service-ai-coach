"""Metrics pipeline — snapshot composition, rate-limited publishing.

Collects signals from the four detectors and produces a single
``MetricsSnapshot`` packet. A trailing timer coalesces bursts of events so
the UI receives at most one update per ``metrics_publish_interval_s`` (default
250 ms).
"""

from .metrics import MetricsSnapshot, MetricsSnapshotBuilder

__all__ = ["MetricsSnapshot", "MetricsSnapshotBuilder"]
