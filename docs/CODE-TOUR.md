# Code Tour

A 1-page walk through the agent code for someone who knows the product but not Python in depth. Read this alongside [`AS-BUILT.md`](./AS-BUILT.md) (which tells you *what* shipped; this tells you *where* to look).

---

## The one data flow

```
Mic (browser)                                           UI (browser)
    │                                                       ▲
    │  WebRTC audio                           metrics JSON  │
    ▼                                                       │
LiveKit server (local)                                      │
    │                                                       │
    ▼                                                       │
Python agent:                                               │
    ┌────────────────────────────────────────────────┐      │
    │  1. stt/local_whisper.py  (faster-whisper)     │      │
    │  2. detectors/*.py        (filler/pacing/…)    │      │
    │  3. pipeline/metrics.py   (rate-limit + emit)  │──────┘
    └────────────────────────────────────────────────┘
```

Follow the flow in that order and everything clicks.

## Walking the code

### 1. `main.py` — wiring

The agent entrypoint. Two things to understand here:

**a) The `@session.on("user_input_transcribed")` handler.** Every time Whisper emits a transcript (partial or final), this handler fires. Finals are fed into `metrics_builder.on_final(text, t_ms)`.

**b) The `@session.on("user_state_changed")` handler.** Silero VAD (voice activity detection) tells the session when the rep stops speaking. That's our cue to finalize the transcript — we call `stream.flush()`, which makes Whisper do one last pass and emit a `FINAL_TRANSCRIPT`.

Everything else in `main.py` is LiveKit SDK plumbing — you rarely need to touch it.

### 2. `stt/local_whisper.py` — the STT stream

Two classes:

- `LocalFasterWhisperSTT` — the plugin the LiveKit SDK mounts. Tells the SDK *"I can stream transcripts."*
- `LocalFasterWhisperStream` — the running stream. Holds a 3-second sliding buffer of audio, runs Whisper every 500 ms, emits `INTERIM_TRANSCRIPT` / `FINAL_TRANSCRIPT` events.

Two safety nets around Whisper:
- **RMS gate** — skip transcription when audio is near-silent (saves CPU + avoids hallucinations).
- **`_looks_hallucinated`** — drops the known silence-hallucinations (`"Okay."`, `"Thank you."`) without filtering legitimate fillers.

### 3. `detectors/` — the coaching signals

Four independent classes, each in its own file. All share the same shape by convention (no formal interface, see [the design doc](./planning/design/detailed-design.md) discussion):

```python
def on_final(self, text: str, t_ms: int) -> list[DetectorEvent]: ...
def reset(self) -> None: ...
```

Each detector also exposes state accessors specific to itself (`total`, `wpm_avg()`, `hits`, `tag()`).

| Detector | What it does |
|---|---|
| `filler.py` | Tokenizes text, matches against `DEFAULT_FILLER_WORDS` (uni- + bigram). |
| `pacing.py` | Rolling words-per-minute + cumulative average; emits band-transition events. |
| `prohibited.py` | Exact substring + `rapidfuzz` fuzzy fallback (threshold 88). |
| `sentiment.py` | VADER compound score on a 20 s rolling window; 3-tag output. |

### 4. `pipeline/metrics.py` — the composer

`MetricsSnapshotBuilder` owns all four detectors. Every final transcript:

1. Feeds every detector (`self._filler.on_final(...)` etc.).
2. Schedules a "trailing-edge publish" — a tiny async task that sleeps 250 ms, then sends one snapshot packet to the UI.

Bursts (N events inside 250 ms) coalesce into one packet. Quiet periods followed by a single event publish within 250 ms. This is the only non-trivial async pattern in the code.

### 5. UI

The UI is simpler than the agent and mostly React + hooks. Three files matter:

- `coach-ui/src/App.tsx` — mounts the LiveKit room.
- `coach-ui/src/metrics.ts` — parses the `metrics` JSON payload.
- `coach-ui/src/MetricsBar.tsx` — subscribes to the `metrics` topic via `useDataChannel`, renders four tiles.

## Python concepts you'll hit

- **`async def` / `await` / `asyncio`** — cooperative multitasking. Used in `main.py` entrypoint, the STT stream, and the metrics publisher. The detectors are all synchronous — no async needed.
- **`@dataclass(frozen=True)`** — an immutable value object. Like a Java `record`.
- **`@session.on("event_name")` decorators** — register a callback. Nothing magical; the SDK calls back when the event fires.
- **Type hints (`list[DetectorEvent]`, `str | None`)** — optional; the runtime ignores them, but they help readers.

## Where to make common changes

| I want to… | Touch… |
|---|---|
| Add / remove filler words | `agent/src/coach_agent/config.py` → `DEFAULT_FILLER_WORDS` |
| Change the WPM band | same file → `DEFAULT_WPM_LOW` / `DEFAULT_WPM_HIGH` |
| Add a prohibited phrase | same file → `DEFAULT_PROHIBITED_PHRASES` |
| Change metrics publish rate | same file → `metrics_publish_interval_s` |
| Add a 5th detector | new `detectors/foo.py` + register in `pipeline/metrics.py` (`__init__`, `reset`, `on_final`, `snapshot`) |
| Tweak the UI tile | `coach-ui/src/MetricsBar.tsx` |

## Lines-of-code at a glance

```
agent/src/coach_agent/
    main.py                ~180 lines   entrypoint + wiring
    config.py               ~55 lines   settings + defaults
    stt/local_whisper.py   ~320 lines   the streaming STT (longest file)
    stt/ring_buffer.py     ~100 lines   int16 → float32 sliding buffer
    detectors/{4 files}    ~300 lines   ~75 lines each
    pipeline/metrics.py    ~150 lines   async snapshot builder

coach-ui/src/
    App.tsx                 ~75 lines
    MetricsBar.tsx         ~140 lines
    TranscriptPane.tsx     ~100 lines
    metrics.ts              ~80 lines   parse + types
    transcript.ts           ~65 lines   parse + types
```

No file is over 320 lines. If you're lost, re-read this page, then jump to the file you care about.
