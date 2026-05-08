"""Speech-to-text — local `faster-whisper` in-process implementation.

Exposes the two classes the agent needs: the `STT` subclass
(:class:`LocalFasterWhisperSTT`) and its streaming recognizer
(:class:`LocalFasterWhisperStream`). The ring buffer and per-module
constants live in submodules and are imported directly when needed.
"""

from .local_whisper import LocalFasterWhisperStream, LocalFasterWhisperSTT

__all__ = ["LocalFasterWhisperSTT", "LocalFasterWhisperStream"]
