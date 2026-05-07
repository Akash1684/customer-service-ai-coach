"""Customer Service AI Coach — Python agent package.

Package layout:

- ``config.py``    — :class:`CoachSettings` dataclass (detector defaults)
- ``stt/``         — in-process :class:`LocalFasterWhisperSTT` (faster-whisper)
- ``detectors/``   — filler, pacing, prohibited, and sentiment detectors
- ``pipeline/``    — :class:`MetricsSnapshotBuilder` (rate-limited publisher)
- ``transport/``   — data-channel helpers (liveness heartbeat)
- ``main.py``      — :class:`CoachAgent` + :func:`entrypoint` wiring everything
                     into a LiveKit ``AgentSession``

Turn detection is delegated entirely to the session-level Silero VAD — there
is no custom voice-activity or silence-gap logic inside the STT stream. See
``docs/AS-BUILT.md`` at the repo root for the full architecture.
"""

__version__ = "0.1.0"
