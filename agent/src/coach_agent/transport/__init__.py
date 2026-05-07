"""Transport — data-channel publishing, RPC, and wire-format helpers.

Step 2 introduces the `liveness` module (heartbeat payloads).
Later steps will add:
  - `publisher.py` — typed wrappers around `publish_data` (Step 5+)
  - `rpc.py`       — RPC handler registration (Step 4+)
  - `nudge_types.py` — shared dataclasses for nudges, metrics (Step 5/8)
"""
