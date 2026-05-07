"""Customer Service AI Coach — Python agent package.

This package will host:
- `stt/`          — local `faster-whisper` STT subclass (Step 3)
- `detectors/`    — filler, pacing, dead-air, prohibited, sentiment (Steps 5–6)
- `pipeline/`     — event bus, metrics snapshot builder, nudge worker, summary (Steps 5, 8, 9)
- `transport/`    — data-channel publisher, RPC registration (Step 2+)
- `scripts/`      — pre-built script library (Step 4)
- `config.py`     — CoachSettings dataclass (Step 5)
- `main.py`       — AgentServer entrypoint (Step 2)

Step 1 keeps the package intentionally empty beyond this version marker so the
scaffolding import check passes without requiring the full runtime stack.
"""

__version__ = "0.1.0"
