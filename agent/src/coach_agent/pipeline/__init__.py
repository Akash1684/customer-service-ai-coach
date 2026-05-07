"""Metrics pipeline — snapshot composition, rate-limited publishing.

Collects signals from the four P0 detectors and produces a single
``MetricsSnapshot`` packet. A trailing timer coalesces bursts of events so
the UI receives at most one update per ``metrics_publish_interval_s`` (default
250 ms).

Step 8 will add a second consumer (the nudge worker) that subscribes to the
raw detector events — for Step 5 we only wire the snapshot publisher.
"""

from .metrics import MetricsSnapshot, MetricsSnapshotBuilder

__all__ = ["MetricsSnapshot", "MetricsSnapshotBuilder"]
