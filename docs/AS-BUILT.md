# As-Built Architecture

> Current implementation reference for `main` at SHA `4cfd847` (2026-05-07).
> Complements [`docs/planning/design/detailed-design.md`](./planning/design/detailed-design.md) — the design doc is the original plan; this file captures **what actually shipped** and the decisions that diverged during implementation.

---

## Process architecture

Three long-running services on the rep's laptop. Nothing else.

```
┌──────────────┐          WebRTC audio + data         ┌──────────────────┐
│  Browser UI  │ ───────────────────────────────────► │  LiveKit server  │
│  (Vite/React)│ ◄─────── data packets ─────────────  │   (--dev mode)   │
└──────────────┘                                      └──────────────────┘
                                                                │
                                                                │ SFU routes
                                                                ▼
                                                        ┌──────────────────┐
                                                        │  Python agent    │
                                                        │  (livekit-agents │
                                                        │   + Whisper +    │
                                                        │   Silero VAD +   │
                                                        │   detectors)     │
                                                        └──────────────────┘
```

- **LiveKit server** — stock `livekit-server --dev`. Port 7880 signaling, 7881 TCP RTC, 7882 UDP RTC. Placeholder devkey/secret ("devkey" / "secret").
- **Python agent** — single process, child `WhisperModel` loaded lazily. Silero VAD at the `AgentSession` level. No LLM, no TTS.
- **UI** — Vite dev server on port 5173. Uses `@livekit/components-react` for the room connection and `useDataChannel` hooks for transcript/metrics subscriptions.

All traffic is loopback. No outbound network calls during a session.

## Data-channel topics

Agent → UI:

| Topic | Shape | Cadence |
|---|---|---|
| `transcript` | `{ text: string, is_final: bool }` | One per interim (~500 ms) + one final per utterance |
| `metrics` | [`MetricsSnapshot`](#metricssnapshot) | Trailing-edge ≤ 250 ms after each final transcript |

UI → agent: **none yet**. The Settings RPC (`update_settings`) is a Step 7 item.

### MetricsSnapshot

```jsonc
{
  "t_ms": 1715125000,
  "fillers_total": 3,
  "fillers_last": "um",
  "wpm_current": 148,
  "wpm_avg": 152,
  "pacing_band": "ok",          // "slow" | "ok" | "fast"
  "prohibited_hits": 1,
  "prohibited_last": "calm down",
  "sentiment_tag": "Neutral",   // "Positive" | "Neutral" | "Negative"
  "sentiment_score": 0.12
}
```

## STT pipeline

`agent/src/coach_agent/stt/local_whisper.py` implements a custom `stt.STT` + `stt.RecognizeStream` pair.

- **Model**: `faster-whisper base.en` (int8, CPU, 4 threads). ~140 MB cached in `~/.cache/huggingface/`.
- **Buffer**: `AudioRingBuffer` — fixed 3-second sliding window at 16 kHz mono. Older samples auto-evicted.
- **Interim cadence**: every 500 ms, transcribe the current window, emit `INTERIM_TRANSCRIPT` event.
- **Finalization trigger**: external. The session-level `user_state_changed` event (fired by Silero VAD) calls `stream.flush()`, which pushes a `_FlushSentinel` into the stream's input channel. `_run()` responds by transcribing once more and emitting `FINAL_TRANSCRIPT`.
- **No voice activity detection in the stream itself** — Silero is the sole VAD in the system.
- **No growing buffer** — per-utterance latency stays bounded regardless of how long the user speaks. Utterances longer than 3 s lose their earliest words in the final; acceptable tradeoff for coaching speech patterns.

### Whisper call knobs

```python
model.transcribe(
    audio_fp32,
    language="en",
    beam_size=1,
    vad_filter=False,              # single-pass; our RMS gate + hallucination guard handle silence
    condition_on_previous_text=False,
    temperature=0.0,
    no_speech_threshold=0.7,
    compression_ratio_threshold=2.4,
)
```

Two safety nets around Whisper output:

1. **RMS gate** (in `_maybe_transcribe`): skip transcription entirely when the window's float32 RMS falls below `0.002`. Saves CPU and avoids most silence hallucinations at the source.
2. **Hallucination filter** (`_looks_hallucinated`): drops known silence artefacts (`"Okay. Okay."`, `"Thank you."`, `"Thanks for watching!"`, `". . ."`) without swallowing legitimate filler words (`"um"`, `"uh"`, `"ah"`).

## Turn detection (Silero-driven)

```
Mic audio ─► LiveKit ─► AgentSession
                         │
                         ├── Silero VAD ── detects end-of-speech
                         │                       │
                         │                       ▼
                         │                session.emit("user_state_changed",
                         │                               old="speaking",
                         │                               new="listening")
                         │                       │
                         │                       ▼
                         │           main.py handler → CoachAgent.active_stream.flush()
                         │                       │
                         │                       ▼
                         │            LocalFasterWhisperStream._run()
                         │              sees _FlushSentinel
                         │              → transcribes current window
                         │              → emits FINAL_TRANSCRIPT
                         └── STT stream ◄──── forwards frames
```

The `CoachAgent` class (in `main.py`) subclasses `livekit.agents.Agent` and overrides `stt_node` for the sole purpose of stashing a reference to the active stream on `self.active_stream`. The session-level `user_state_changed` handler then has a concrete object to flush.

This eliminates all custom VAD / silence-heuristic code from the STT stream. The original plan (Step 3) used a timer-based "~600 ms of no new audio" heuristic that we **do not implement** — it's superseded here.

## Detectors

`agent/src/coach_agent/detectors/` — four independent detectors, each consuming final transcripts only (interim events are ignored to prevent double-counting).

- **`FillerDetector`** — tokenizes final text, matches against a unigram + bigram filler list, tracks cumulative count + last word.
- **`PacingDetector`** — rolling 10-s WPM and cumulative avg WPM; emits `pace_fast` / `pace_slow` events on band transitions.
- **`ProhibitedDetector`** — exact substring first, `rapidfuzz.fuzz.partial_ratio >= 88` as fallback (catches missing apostrophes, minor Whisper errors).
- **`SentimentDetector`** — VADER compound score on a rolling 20-s window; emits `sentiment_dip` only on downgrades.

### MetricsSnapshotBuilder

`agent/src/coach_agent/pipeline/metrics.py`

- Owns the four detector instances.
- On each final transcript, feeds all detectors and schedules a trailing-edge publish (250 ms window).
- Coalesces bursts — N events inside the window produce exactly one snapshot.
- Snapshot shape matches the [`MetricsSnapshot`](#metricssnapshot) wire format above.

## UI (React + Vite)

`coach-ui/src/`:

- **`App.tsx`** — mounts `<LiveKitRoom>` with the dev token from `.env.local`, renders the panes.
- **`TranscriptPane.tsx`** — subscribes to the `transcript` topic. Shows finals as solid lines, the current partial as italicized draft text, and a pulsing "● Listening…" badge while a partial is active.
- **`MetricsBar.tsx`** — subscribes to `metrics`. Four tiles: fillers, pacing, prohibited, sentiment. Accent colors flag fast/slow pacing, prohibited hits, and negative sentiment.

All text-level UI state lives in React components; **nothing** is persisted to `localStorage` yet (Step 7 item).

## Error handling currently implemented

- **Room disconnect during publish** — the metrics publisher checks `ctx.room.isconnected()` before each `publish_data` call and swallows `PublishDataError` on the race. The entrypoint's idle loop exits cleanly on disconnect so the SDK doesn't force-cancel the job.
- **Whisper hallucinations on silence** — RMS gate skips transcription; string filter catches what slips through.
- **Silero over-triggering on short pauses** — handled: the `_FlushSentinel` branch of `_run()` clears the buffer even when Whisper produced no text for that utterance, preventing silence accumulation across many VAD triggers.

Not yet implemented (Step 10 items):
- Mic-permission denied overlay
- LiveKit server unreachable banner
- `localStorage` unavailable notice
- Status data-channel + badges

## Dependencies as of `main`

### Agent (`agent/pyproject.toml`)

```
python-dotenv >= 1.0
livekit-agents >= 0.11
livekit-plugins-silero >= 0.6
faster-whisper >= 1.0
numpy >= 1.26
rapidfuzz >= 3.0
vaderSentiment >= 3.3
# dev: pytest, pytest-asyncio, ruff
```

No `livekit-plugins-openai`, no `ollama`, no LLM client.

### Frontend (`coach-ui/package.json`)

```
@livekit/components-react ^2.8.2
@livekit/components-styles ^1.1.5
livekit-client ^2.7.5
react ^18.3.1
# dev: vitest, @testing-library/react, typescript, vite, @vitejs/plugin-react
```

## Testing

- **Python**: unit tests covering ring buffer, Whisper stream (with fake model), hallucination guard, four detectors, and the metrics builder.
- **TypeScript**: unit tests covering parse helpers, panes, and the App shell.
- **Manual E2E**: `agent/tests/e2e_listener.py` (listens for data-channel events) and `agent/tests/e2e_speaker_listener.py` (publishes a WAV + listens, single-participant sanity runner).

```bash
make test          # all
make test-agent    # Python only
make test-ui       # TypeScript only
```

## Key deviations from the original design

| Design doc says | We implemented |
|---|---|
| 3 s sliding window for interims, SDK-flush for finals (Step 3 as stopgap timer heuristic, Step 6 to add VAD-driven flush) | 3 s sliding window, **Silero-driven flush via `user_state_changed` event** — lands in the Step 3 commit; no timer heuristic ever shipped |
| Custom RMS voice-activity detection in the stream to drive finalization | **Removed entirely** — SDK's Silero is the sole VAD |
| P0 includes Ollama-backed LLM nudges (Step 8) and narrative summary (Step 9) | **Deferred out of P0** — runtime is LLM-free. The `nudges` data-channel topic doesn't exist yet |
| Dead-air detector (Step 6) | **Not yet implemented** — Silero VAD is there but not wired to an event emitter |
| Session lifecycle (Start / Stop) + 3-script library (Step 4) | **Not yet implemented** — session is implicit (as long as the browser is connected) |
| Settings UI + `localStorage` + `update_settings` RPC (Step 7) | **Not yet implemented** — defaults are hard-coded in `config.py`, change by editing and restarting |
| Model: `base.en` / int8 | Matches |
| Whisper's own `vad_filter=True` with Silero internally | Tried, backed off — we're single-pass `vad_filter=False`. Whisper VAD was over-aggressive and doubled CPU cost |

## Quick operational facts

- **First-run model download**: ~140 MB (`base.en`). Silero VAD is much smaller and loads with the plugin.
- **Steady-state RAM**: ~0.6 GB per agent worker.
- **Interim latency** (voice → visible text): ~500–700 ms.
- **Final latency** (pause → crisp line): ~150–300 ms after Silero detects speech stop.
- **No audio recording**. No transcript storage. No persistence.
