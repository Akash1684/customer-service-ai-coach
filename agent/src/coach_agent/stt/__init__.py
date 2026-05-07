"""Speech-to-text — local `faster-whisper` in-process implementation.

Step 3: `LocalFasterWhisperSTT` subclasses the LiveKit Agents `STT` so the
SDK's auto-resampling feeds the stream 16 kHz mono PCM, and
`LocalFasterWhisperStream` runs `faster-whisper` on a rolling window to emit
interim transcripts about every 400 ms. Finalization is driven by the
LiveKit flush sentinel (Step 6 will drive finalization from Silero VAD).
"""

from .local_whisper import (
    DEFAULT_MODEL_SIZE,
    LocalFasterWhisperSTT,
    LocalFasterWhisperStream,
)
from .ring_buffer import AudioRingBuffer

__all__ = [
    "DEFAULT_MODEL_SIZE",
    "LocalFasterWhisperSTT",
    "LocalFasterWhisperStream",
    "AudioRingBuffer",
]
