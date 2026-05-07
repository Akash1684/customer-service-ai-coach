# Research: Local ASR — `faster-whisper` embedded in the Python agent

**Scope:** How to run `faster-whisper` for real-time streaming STT **inside the Python agent process** (no separate STT service), integrated as a `livekit.agents.stt.STT` subclass, and meeting the `<500 ms` end-to-end budget on a consumer CPU.

**Date:** 2026-05-07

---

## 1. Why `faster-whisper` and why in-process

**`faster-whisper`** is a reimplementation of OpenAI's Whisper using `CTranslate2` — a fast, quantization-friendly inference engine. It is the de-facto open-source choice for running Whisper on CPU in real time.

Source: <https://github.com/SYSTRAN/faster-whisper>

**Why in-process (Option 2 from the SDK doc):**

- Removes the Docker container for the STT shim → one fewer dependency for developers.
- Removes HTTP serialization overhead (roughly 20–50 ms on each transcription call, depending on audio chunk size and payload).
- Gives us direct access to the model's streaming API and per-segment timestamps, which are needed for accurate dead-air and filler timing.
- Matches the P0-lean goal of running as few services as possible.

Tradeoff: we write a ~100–150 line `STT` plugin subclass rather than use the stock `openai.STT` client. This is the shape used by almost every in-tree LiveKit STT plugin.

---

## 2. Model choice on CPU

`faster-whisper` ships multiple model sizes. Approximate footprints and single-thread CPU real-time factor (RTF; <1.0 means faster than real time):

| Model | Parameters | Disk (int8 quant) | CPU RTF (Apple M-series / modern x86-64) | Notes |
|---|---|---|---|---|
| `tiny.en` | 39 M | ~75 MB | ~0.10–0.15 | Fast, noticeable accuracy drop for mumbled/fast speech |
| `base.en` | 74 M | ~145 MB | ~0.20–0.30 | **P0 default.** Good balance for clear rep audio reading a script |
| `small.en` | 244 M | ~480 MB | ~0.6–0.8 | Noticeably better accuracy, but thinner real-time headroom |
| `medium.en` | 769 M | ~1.4 GB | ~1.5–2.0 | Too slow for real-time on CPU |

Numbers vary by hardware; sources below. For P0 we ship **`base.en` + `int8` quantization**. If the user flags CPU-contention issues, we fall back to `tiny.en` (same code path, different model name).

Instantiation:

```python
from faster_whisper import WhisperModel

model = WhisperModel(
    model_size_or_path="base.en",
    device="cpu",
    compute_type="int8",   # best CPU perf; int8_float32 is slightly more accurate
    cpu_threads=4,         # tune to host
)
```

Models are downloaded from Hugging Face on first use and cached under `~/.cache/huggingface/`.

Sources:
- `faster-whisper` README — <https://github.com/SYSTRAN/faster-whisper>
- Benchmarks table — <https://github.com/SYSTRAN/faster-whisper#benchmark>

---

## 3. Streaming strategy

Whisper is fundamentally a non-streaming model — it wants a ~30 s context window. For real-time UI we use a **sliding-window** approach over short chunks, identical to the pattern used in `whisper_streaming` (Ufal) and `WhisperLiveKit`.

### Approach used in our `STT` subclass

1. **Audio ingest.** LiveKit delivers PCM frames at the track's sample rate (typically 48 kHz stereo). We resample to 16 kHz mono — Whisper's expected input.
2. **Chunk cadence.** Every **400 ms** we advance a buffer and run `model.transcribe(...)` on the **last ~2–3 s** window (overlapping with the previous call). `word_timestamps=True` gives us per-word offsets.
3. **Commit logic.** We emit a **partial transcript** every chunk (for UI streaming) and promote it to **final** once Silero VAD reports end-of-speech or enough trailing silence accumulates (~600 ms). Finals reset the buffer.
4. **Backpressure.** If a transcription takes longer than one chunk interval, we drop the oldest chunk rather than queueing; the goal is latency over completeness.

### End-to-end latency budget on CPU for a 400 ms spoken word

| Step | Budget |
|---|---|
| Browser → LiveKit audio capture & WebRTC | 40–80 ms |
| Resample + buffer copy | <5 ms |
| `faster-whisper` transcribe 2 s window (`base.en`, int8) | ~200–350 ms |
| Detector dispatch + data packet publish | <10 ms |
| LiveKit room → browser DataReceived | 40–80 ms |
| **Total p50** | **~300–500 ms** ✓ |

If the p95 on a specific machine is over budget, switch to `tiny.en` (halves transcribe time) or shrink the window to 1 s.

---

## 4. Mapping to `livekit.agents.stt.STT`

The SDK expects an `STT` implementation that produces `SpeechEvent`s: `INTERIM_TRANSCRIPT`, `FINAL_TRANSCRIPT`, `START_OF_SPEECH`, `END_OF_SPEECH`, each with `alternatives[]` and timing.

Skeleton (illustrative, not final code):

```python
from livekit import rtc
from livekit.agents import stt
from faster_whisper import WhisperModel
import asyncio, collections

class LocalFasterWhisperSTT(stt.STT):
    def __init__(self, model_size: str = "base.en"):
        super().__init__(capabilities=stt.STTCapabilities(streaming=True, interim_results=True))
        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")

    def stream(self, *, language=None) -> "LocalFasterWhisperStream":
        return LocalFasterWhisperStream(self._model)


class LocalFasterWhisperStream(stt.SpeechStream):
    def __init__(self, model):
        super().__init__()
        self._model = model
        self._buf = collections.deque(maxlen=...)   # ~3 s of 16kHz mono int16
        self._task = asyncio.create_task(self._run())

    def push_frame(self, frame: rtc.AudioFrame) -> None:
        # Resample 48kHz stereo → 16kHz mono, append to _buf
        ...

    async def _run(self):
        while True:
            await asyncio.sleep(0.4)                       # 400 ms cadence
            if len(self._buf) < MIN_SAMPLES: continue
            pcm16 = np.frombuffer(bytes(self._buf), dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = self._model.transcribe(
                pcm16, language="en", word_timestamps=True,
                beam_size=1, vad_filter=False, condition_on_previous_text=False,
            )
            text = " ".join(s.text.strip() for s in segments).strip()
            if text:
                self._event_ch.send_nowait(
                    stt.SpeechEvent(
                        type=stt.SpeechEventType.INTERIM_TRANSCRIPT,
                        alternatives=[stt.SpeechData(language="en", text=text)],
                    )
                )
```

Key detail: we **do not** rely on Whisper's `vad_filter`. Silero VAD (from `livekit-plugins-silero`) is what drives dead-air detection and speech boundaries. We let Whisper transcribe continuously; Silero tells us when to promote to `FINAL_TRANSCRIPT`.

---

## 5. Dependency list for P0

Added to the agent's `pyproject.toml`:

```
faster-whisper >= 1.0.3      # wraps CTranslate2
ctranslate2 >= 4.3           # transitive, but pin for macOS wheel clarity
numpy                        # already transitive via livekit-agents
scipy                        # for resampling (or use `soxr` for speed)
```

Platform notes:
- **macOS (Apple Silicon and Intel):** `ctranslate2` wheels available on PyPI; `pip install faster-whisper` works out of the box.
- **Linux x86-64:** same; wheels on PyPI.
- **Windows native:** wheels exist but less well-tested; WSL2 recommended.

No `ffmpeg` subprocess is required because we feed raw PCM, not decoded files.

---

## 6. Alternatives considered and why rejected

| Alternative | Why rejected for P0 |
|---|---|
| `openai.STT` against a containerized `speaches` server | Adds Docker dep and an HTTP hop; violates P0-lean goal. |
| `whisper.cpp` via Python bindings (`whispercpp-py`, `pywhispercpp`) | Comparable speed to `faster-whisper`; weaker streaming ergonomics and smaller ecosystem in Python. |
| Hugging Face `transformers` Whisper pipeline | Much slower on CPU than CTranslate2. |
| Cloud APIs (Deepgram, OpenAI Whisper API, AssemblyAI) | Rules out by "fully local" constraint (Q6). |
| `QuentinFuxa/WhisperLiveKit` | Interesting project; overlaps with what we'd build. Worth monitoring for P1 but integrating it now would add more dependencies than we'd write from scratch. |

---

## 7. Risks

1. **CPU contention with Ollama.** When the relaxed-lane LLM worker is generating a nudge, it will peg 1–2 cores. `faster-whisper` on `int8` is lean but not free. Mitigation:
   - Ollama model capped at 3B-Q4.
   - LLM worker concurrency strictly 1.
   - `cpu_threads=4` on `WhisperModel` leaves headroom on an 8-core machine.
   - If users report missed transcripts during nudge generation, switch Whisper to `tiny.en`.

2. **First-run download.** ~145 MB on first session start. Mitigation: download at `download-files` step (`uv run src/agent.py download-files`) before first use. The LiveKit Python starter already provides this hook.

3. **Punctuation drift in long dictations.** Whisper can hallucinate on long silence or very fast speech. For P0 practice mode the rep is reading prepared text, which is the best-case input for Whisper. We accept this risk.

---

## 8. References

- `faster-whisper` — <https://github.com/SYSTRAN/faster-whisper>
- `CTranslate2` — <https://github.com/OpenNMT/CTranslate2>
- Whisper streaming reference — <https://github.com/ufal/whisper_streaming>
- Example integration — <https://github.com/atyenoria/livekit-whisper-transcribe>
- Related project — <https://github.com/QuentinFuxa/WhisperLiveKit>
- LiveKit STT interface — <https://docs.livekit.io/python/livekit/agents/stt/index.html>
- Silero VAD plugin — <https://docs.livekit.io/python/livekit/plugins/silero/index.html>
