"""`faster-whisper`-backed LiveKit STT plugin — runs in-process.

Wires a custom `STT` / `RecognizeStream` pair into the LiveKit Agents SDK so
the session consumes transcripts directly from a local Whisper model. This
eliminates the need for an out-of-process STT container and an HTTP hop.

Design summary (see `docs/planning/research/local-asr.md`):

- SDK auto-resamples pushed frames to 16 kHz mono int16 (we set
  `sample_rate=16000` on the stream).
- We keep the most recent ``WINDOW_SECONDS`` of audio in a ring buffer (a
  sliding window, not an accumulator). Every ``CHUNK_INTERVAL_S`` we run
  Whisper on a snapshot of the window and emit an INTERIM event with the
  joined text. This bounds the per-call CPU cost regardless of how long
  the user speaks — a growing-buffer design causes interim latency to
  balloon as utterances lengthen.
- Finalization is driven by the SDK's `_FlushSentinel`. The sentinel is
  sent from outside this class — `main.py` subscribes to the AgentSession's
  `user_state_changed` event (Silero-VAD-powered) and calls
  `stream.flush()` the moment the user stops speaking. This class itself
  does NOT do any voice-activity detection; Silero (loaded by the
  AgentSession) is the sole VAD.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import TYPE_CHECKING

import numpy as np
from livekit import rtc
from livekit.agents import stt
from livekit.agents.types import (
    DEFAULT_API_CONNECT_OPTIONS,
    NOT_GIVEN,
    APIConnectOptions,
    NotGivenOr,
)

from .ring_buffer import AudioRingBuffer

if TYPE_CHECKING:  # pragma: no cover
    from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

DEFAULT_MODEL_SIZE = "base.en"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_DEVICE = "cpu"
DEFAULT_CPU_THREADS = 4

# Streaming knobs
TARGET_SAMPLE_RATE = 16_000  # Hz — Whisper's expected input
# Sliding-window size. The ring buffer auto-evicts older samples past this
# point, so every transcribe call sees a bounded amount of audio regardless
# of how long the user speaks. Keeps interim latency flat as the utterance
# grows. Tuned for base.en on a laptop CPU: 3 s transcribes in ~150–250 ms,
# leaving headroom within the ``CHUNK_INTERVAL_S`` cadence so calls don't
# queue up. Utterances longer than this will drop their earliest words
# from the final transcript — acceptable because Silero-driven flushing
# means this only happens on very long single-breath utterances.
WINDOW_SECONDS = 3.0
CHUNK_INTERVAL_S = 0.5
MIN_TRANSCRIBE_SAMPLES = int(TARGET_SAMPLE_RATE * 0.3)  # skip if < 300 ms of audio

# Audio-energy pre-check used as a cheap gate on Whisper calls (we skip
# transcription on pure silence to avoid wasting CPU and producing
# "Okay. Okay." hallucinations). RMS on the float32 [-1, 1] scale.
SILENCE_RMS_THRESHOLD = 0.002


def _transcribe_snapshot(model: WhisperModel, audio_fp32: np.ndarray) -> str:
    """Synchronous transcribe — single-pass Whisper over the current window.

    The two-pass (VAD-filter + fallback) strategy was discarded: with Silero
    VAD driving turn detection at the session level and our RMS gate
    skipping transcription on silent buffers, the extra pass just doubled
    CPU cost with no accuracy gain. The downstream string-based
    hallucination guard catches the rare junk that slips through.
    """
    if audio_fp32.size == 0:
        return ""
    segments, _ = model.transcribe(
        audio_fp32,
        language="en",
        beam_size=1,
        vad_filter=False,
        condition_on_previous_text=False,
        temperature=0.0,
        no_speech_threshold=0.7,
        compression_ratio_threshold=2.4,
    )
    parts = [seg.text.strip() for seg in segments if seg.text.strip()]
    return " ".join(parts).strip()


# Known Whisper hallucinations on silence / room tone. When the filter
# returns one of these (or a trivial repeat of any single word), we drop
# the transcript instead of publishing it to the UI.
_HALLUCINATION_EXACT = {
    "okay.",
    "okay",
    "you",
    "you.",
    "thank you.",
    "thanks for watching.",
    "thanks for watching!",
    "bye.",
    "bye",
    ".",
    "..",
    "...",
    "i'm sorry.",
    "i'm sorry",
}

# Tokens that Whisper parrots on near-silent audio. A sentence consisting
# purely of repetitions of one of these counts as a hallucination.
#
# IMPORTANT: This set must NOT contain legitimate filler words ("um", "uh",
# "ah", "oh", "huh") because the downstream `FillerDetector` needs to see
# them. Room-tone hallucinations are specifically the YouTube-caption-style
# artifacts from Whisper's training data ("okay", "thank you", "bye",
# "sorry"), which are unlikely to be the sole content of a real rep
# utterance in a coaching session.
_HALLUCINATION_REPEAT_TOKENS = {
    "okay",
    "you",
    "bye",
    "sorry",
    "mm",
}

_TOKEN_PUNCT_RE = re.compile(r"[^\w']")


def _strip_token_punct(tok: str) -> str:
    """Remove punctuation from a token; keeps letters, digits, apostrophes."""
    return _TOKEN_PUNCT_RE.sub("", tok)


def _looks_hallucinated(text: str) -> bool:
    """Return True if ``text`` looks like a classic Whisper silence hallucination.

    Catches:
    1. The entire output is one of the well-known silence phrases.
    2. Every token (punctuation-stripped) collapses to a single word that
       appears in the known-hallucinated set — covers "okay", "Okay.",
       "Okay. Okay.", "okay okay okay", etc.
    3. Generic repeat detection: ≥3 tokens where one token dominates ≥75%.
    """
    normalized = text.strip().lower()
    if not normalized:
        return True
    if normalized in _HALLUCINATION_EXACT:
        return True

    # Punctuation-stripped tokens for shape analysis.
    tokens = [_strip_token_punct(t) for t in normalized.split()]
    tokens = [t for t in tokens if t]
    if not tokens:
        return True

    # If the whole utterance is repetitions of a single known-hallucinated
    # token (any count ≥ 1), drop. This catches "okay.", "okay okay",
    # "Okay. Okay. Okay." and the long 29-token variants alike.
    unique = set(tokens)
    if len(unique) == 1 and next(iter(unique)) in _HALLUCINATION_REPEAT_TOKENS:
        return True

    # Generic repeat detection — protects against unseen-but-clearly-
    # degenerate outputs (long all-same-token bursts) without clipping
    # natural stutters (3 "um"s can be legit).
    if len(tokens) >= 4:
        most_common = max(unique, key=tokens.count)
        if tokens.count(most_common) / len(tokens) >= 0.8:
            return True
    return False


class LocalFasterWhisperSTT(stt.STT):
    """LiveKit STT that runs `faster-whisper` in-process.

    The model is loaded lazily on first `stream()` call so importing the
    module is cheap (useful for unit tests that don't need the model).
    """

    def __init__(
        self,
        *,
        model_size: str = DEFAULT_MODEL_SIZE,
        compute_type: str = DEFAULT_COMPUTE_TYPE,
        device: str = DEFAULT_DEVICE,
        cpu_threads: int = DEFAULT_CPU_THREADS,
    ) -> None:
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=True,
                interim_results=True,
                offline_recognize=False,
            )
        )
        self._model_size = model_size
        self._compute_type = compute_type
        self._device = device
        self._cpu_threads = cpu_threads
        self._model: WhisperModel | None = None

    @property
    def model(self) -> str:  # used by the SDK for metrics / logging
        return self._model_size

    @property
    def provider(self) -> str:
        return "local-faster-whisper"

    def _ensure_model(self) -> WhisperModel:
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info(
                "loading faster-whisper model size=%s compute=%s device=%s threads=%d",
                self._model_size,
                self._compute_type,
                self._device,
                self._cpu_threads,
            )
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
                cpu_threads=self._cpu_threads,
            )
        return self._model

    def prewarm(self) -> None:
        self._ensure_model()

    async def _recognize_impl(
        self,
        buffer: stt.AudioBuffer,  # type: ignore[name-defined]
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> stt.SpeechEvent:  # pragma: no cover — not used by streaming sessions
        raise NotImplementedError("LocalFasterWhisperSTT only supports streaming")

    def stream(
        self,
        *,
        language: NotGivenOr[str] = NOT_GIVEN,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> LocalFasterWhisperStream:
        model = self._ensure_model()
        return LocalFasterWhisperStream(
            stt=self,
            model=model,
            language="en" if not language else language,
            conn_options=conn_options,
        )


class LocalFasterWhisperStream(stt.RecognizeStream):
    """Sliding-window streaming recognizer over a local Whisper model."""

    def __init__(
        self,
        *,
        stt: LocalFasterWhisperSTT,
        model: WhisperModel,
        language: str,
        conn_options: APIConnectOptions,
    ) -> None:
        super().__init__(
            stt=stt, conn_options=conn_options, sample_rate=TARGET_SAMPLE_RATE
        )
        self._model = model
        self._language = language
        self._buffer = AudioRingBuffer(
            sample_rate=TARGET_SAMPLE_RATE, window_seconds=WINDOW_SECONDS
        )
        self._last_transcribe_t = 0.0
        self._current_text: str = ""

    async def _run(self) -> None:
        """Consume audio frames, transcribe periodically, emit events."""
        logger.info("LocalFasterWhisperStream started (sr=%d)", TARGET_SAMPLE_RATE)
        loop = asyncio.get_running_loop()

        async for item in self._input_ch:
            # Flush sentinel = end of current utterance; promote to FINAL.
            # The sentinel is always driven externally — `main.py`'s
            # `user_state_changed` handler calls `stream.flush()` the moment
            # Silero VAD reports end-of-speech at the session level. This
            # class does no silence detection of its own.
            if isinstance(item, self._FlushSentinel):
                await self._maybe_transcribe(loop, force=True)
                emitted = self._emit_final()
                if not emitted:
                    # Whisper produced no text for this utterance (too short,
                    # too quiet, or dropped by the hallucination filter). We
                    # still need to reset state so the next utterance starts
                    # on a clean buffer — otherwise silence + fragments
                    # accumulate across many VAD triggers and Whisper only
                    # produces output once the buffer grows large enough.
                    logger.debug(
                        "flush with no transcribable text; resetting buffer "
                        "(size=%d)",
                        self._buffer.size,
                    )
                    self._reset_after_utterance()
                continue

            # Otherwise it's an rtc.AudioFrame (already resampled to 16 kHz).
            frame: rtc.AudioFrame = item
            self._ingest_frame(frame)
            await self._maybe_transcribe(loop, force=False)

        # Input channel closed — flush what we have.
        await self._maybe_transcribe(loop, force=True)
        self._emit_final()

    def _ingest_frame(self, frame: rtc.AudioFrame) -> None:
        # AudioFrame.data is a bytes-like buffer of int16 PCM samples.
        arr = np.frombuffer(frame.data, dtype=np.int16)
        if frame.num_channels and frame.num_channels > 1:
            # Downmix to mono by averaging channels.
            arr = arr.reshape(-1, frame.num_channels).mean(axis=1).astype(np.int16)
        self._buffer.append(arr)

        # Very-low-frequency diagnostics: every 50 frames (~1 s at 20 ms each),
        # log frame shape + RMS at DEBUG so we can enable it when tuning
        # without it spamming the default INFO stream.
        self._frames_ingested = getattr(self, "_frames_ingested", 0) + 1
        if self._frames_ingested % 50 == 0 and logger.isEnabledFor(logging.DEBUG):
            rms = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2)))
            logger.debug(
                "[STT_INGEST] n=%d sr=%d ch=%d samples=%d rms=%.1f buf_size=%d",
                self._frames_ingested,
                frame.sample_rate,
                frame.num_channels,
                len(arr),
                rms,
                self._buffer.size,
            )

    async def _maybe_transcribe(
        self, loop: asyncio.AbstractEventLoop, *, force: bool
    ) -> None:
        now = time.monotonic()
        if not force and (now - self._last_transcribe_t) < CHUNK_INTERVAL_S:
            return
        if self._buffer.size < MIN_TRANSCRIBE_SAMPLES:
            return
        self._last_transcribe_t = now

        snapshot = self._buffer.snapshot_float32()

        # Audio-energy pre-check: avoid Whisper hallucinations on silence.
        # RMS on float32 [-1, 1]; anything below the threshold is treated as
        # room tone / background noise and skipped entirely.
        rms = float(np.sqrt(np.mean(snapshot**2)))
        if rms < SILENCE_RMS_THRESHOLD:
            return

        try:
            text = await loop.run_in_executor(
                None, _transcribe_snapshot, self._model, snapshot
            )
        except Exception:
            logger.exception("faster-whisper transcribe failed")
            return

        if not text:
            return
        if _looks_hallucinated(text):
            logger.debug("dropped likely hallucination: %r", text)
            return

        self._current_text = text
        self._emit_interim(text)

    def _emit_interim(self, text: str) -> None:
        ev = stt.SpeechEvent(
            type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=self._language, text=text)],
        )
        self._event_ch.send_nowait(ev)

    def _emit_final(self) -> bool:
        """Emit FINAL_TRANSCRIPT if we have text; returns True iff emitted.

        Clears buffer + interim state on success. On failure (no text),
        returns False and leaves state untouched — the `_FlushSentinel`
        branch of `_run()` is responsible for calling
        :meth:`_reset_after_utterance` to keep the buffer clean.
        """
        text = self._current_text
        if not text:
            return False
        ev = stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language=self._language, text=text)],
        )
        self._event_ch.send_nowait(ev)
        logger.info("FINAL emitted: %r", text[:80])
        self._reset_after_utterance()
        return True

    def _reset_after_utterance(self) -> None:
        """Clear per-utterance state. Call after every flush regardless of outcome."""
        self._current_text = ""
        self._buffer.clear()
