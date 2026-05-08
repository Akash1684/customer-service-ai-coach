# Customer Service AI Coach — Project Presentation

> Draft deck, 4 slides. Edit freely. Each slide ends with speaker notes in
> *italics* — delete before showing.

---

## Slide 1 — What & Why

### Customer Service AI Coach

A **fully-local, browser-based, real-time practice tool** for customer
service reps. Speak into your laptop mic, get live coaching feedback —
three metric tiles + live transcript, all within ~500 ms.

**Hard constraints (chosen, not accidental):**

- **No cloud.** Nothing leaves the machine. No accounts. No session history.
- **CPU-only** consumer laptop. No GPU assumption.
- **< 500 ms** end-to-end for tight-lane feedback.
- **~2.2 GB one-time** model download. No Docker.

**Stack:** LiveKit (WebRTC) + Python agent (`faster-whisper base.en int8`,
Silero VAD, rule-based detectors) + React/Vite UI.

*Speaker note: These constraints forced a 2-lane architecture — fast
signals in-process, LLM-heavy work async. We ultimately deferred the LLM
entirely out of P0 (slide 3).*

---

## Slide 2 — Architecture

```
   Browser (React/Vite)                           Browser UI
        │                                             ▲
        │ WebRTC audio                 metrics JSON   │
        ▼                                             │
   LiveKit server (--dev mode, local)                 │
        │                                             │
        ▼                                             │
   Python agent:                                      │
   ┌──────────────────────────────────────────────┐   │
   │  1. faster-whisper STT (3 s sliding window)  │   │
   │  2. Silero VAD drives finalization           │   │
   │  3. Three detectors (filler/prohibited/sent) │   │
   │  4. 250 ms trailing metrics publish          │───┘
   └──────────────────────────────────────────────┘
```

**Three design calls worth calling out:**

- **Silero-driven finalization.** No custom timer heuristic. Whisper
  transcribes on a rolling 3 s window; Silero flips a flag on speech-stop;
  we flush. Eliminated ~40 lines of handcrafted VAD.
- **Hallucination guard.** Whisper outputs `"Okay. Okay. Okay."` on room
  tone. RMS gate + string filter drop these *without* swallowing real
  fillers like `"um"` / `"uh"`.
- **State-replacement `metrics` topic.** UI keeps only the latest packet.
  No event ordering bugs, no delta reducers.

*Speaker note: The in-process STT replaced a separately-planned Docker
container. Silero-driven flush replaced a planned timer heuristic. Both
changed during implementation — documented in `AS-BUILT.md`.*

---

## Slide 3 — Process: Scope Discipline + Simplification

**Planned vs Shipped — explicit deferrals**

| Planned | Shipped |
|---|---|
| 4 detectors (Filler, Pacing, Prohibited, Sentiment) | 3 — dropped pacing post-launch |
| Ollama-backed LLM nudges | **Deferred out of P0** |
| End-of-session LLM narrative summary | Deferred |
| Start/Stop lifecycle + 3-script library | Implicit session (connected = running) |
| Settings UI + `localStorage` | Defaults in `config.py` |

**Three simplification passes — net –500 LOC, zero regressions**

1. Dropped `DebugPane`/liveness scaffold (~370 LOC) — a Step-2 debug aid
   with no product value.
2. Linearized the audio ring buffer (4 code paths → 1), unified two
   publish helpers, dropped dead state fields.
3. Removed step-history narration ("Step 8 will add…") that made the code
   read like it had missing pieces.

**Testing posture.** 72 tests green (44 Python + 28 TypeScript).
`ruff` clean. `tsc --noEmit` clean.

*Speaker note: The willingness to defer the LLM is the most important
decision. Keeping P0 free of the LLM worker + prompt engineering meant we
could actually ship something comprehensible and testable. Every
simplification pass was a conscious "can we cut this without losing
value" call.*

---

## Slide 4 — Status, Demo, Next

### Today

- Speak → partial transcript in ~500 ms, final in ~250 ms after VAD
- Fillers / Prohibited / Sentiment tiles update live (250 ms cadence)
- Prohibited-phrase hits highlight red; sentiment pill goes green/red
- Model pre-warmed at agent startup — **no cold-start on first utterance**

### Demo

**`docs/DEMO.md`** — a 4-act, ~60 s script that exercises all three
detectors with a sentiment dip + recovery. Recording-ready.

### Natural next steps (ordered by user value)

1. **Session lifecycle + 3-script library** — currently implicit; add
   explicit Start/Stop and a minimal practice-script library.
2. **Settings UI + `localStorage`** — let reps edit the prohibited list,
   filler list, thresholds from the browser.
3. **LLM nudges (Ollama + `qwen2.5:3b`)** — supportive coaching
   suggestions. Only after (1) and (2) land.
4. **End-of-session markdown report** — transcript + metrics + nudges +
   narrative summary, downloadable.

### Repo

<https://github.com/Akash1684/customer-service-ai-coach>

- [`AS-BUILT.md`](./AS-BUILT.md) — shipping architecture
- [`CODE-TOUR.md`](./CODE-TOUR.md) — 1-page code tour
- [`DEMO.md`](./DEMO.md) — recording-ready script

*Speaker note: Ordering intentionally puts LLM last. User-facing scope
(sessions, settings) is bigger bang-for-buck than deeper AI integration
at this stage. The LLM adds the biggest footprint (~2 GB model + prompt
engineering + concurrency control) — worth doing only when the core UX
has room to use it.*
