# Customer Service AI Coach — PDD Project Summary

**Project:** `customer-service-ai-coach`
**Generated:** 2026-05-07
**Repo target:** <https://github.com/Akash1684/customer-service-ai-coach>

---

## Overview

This document summarizes the Prompt-Driven Development planning output for the Customer Service AI Coach — a **fully local, browser-based, real-time practice tool** for customer service reps. Reps pick a prepared script, read the rep turns aloud, and receive live coaching feedback (filler words, pacing, dead air, prohibited phrases, sentiment) plus LLM-generated supportive-coach nudges and a downloadable narrative summary at session end.

Everything runs on the rep's laptop. No cloud calls, no authentication, no persistent storage beyond UI settings in `localStorage`. LiveKit transports audio and data packets; a Python agent runs the detectors and (locally) Ollama-backed LLM; a React + Vite UI renders the experience.

---

## Artifacts created

### Directory structure

```
.agents/planning/2026-05-06-customer-service-ai-coach/
├── rough-idea.md                          # Initial concept
├── idea-honing.md                         # 14-question requirements Q&A (~359 lines)
├── research/
│   ├── livekit-agents-sdk.md              # SDK deep dive (268 lines)
│   ├── livekit-local-setup.md             # Minimal local setup plan (288 lines)
│   ├── webrtc-stack-comparison.md         # LiveKit vs Pion/Pipecat/MediaSoup/Janus
│   ├── local-asr.md                       # faster-whisper in-process (195 lines)
│   ├── local-llm.md                       # Ollama for the relaxed lane (233 lines)
│   ├── detectors.md                       # Tight-lane signals (250 lines)
│   └── frontend.md                        # React + Vite + LiveKit UI (299 lines)
├── design/
│   └── detailed-design.md                 # Full design doc with 3 scripts drafted (725 lines)
├── implementation/
│   └── plan.md                            # 10-step implementation plan (455 lines)
└── summary.md                             # This document
```

**Total: ~2,800 lines across 10 markdown files.**

---

## Key design elements

### Product

- **Primary user:** customer service reps practicing scripted interactions.
- **Mode:** practice / rehearsal — rep reads a script aloud; no live customer; one-way audio only (rep mic).
- **Scripts (P0):** 3 pre-built scripts drafted during design — billing complaint, account inquiry with upgrade, cancellation with retention.
- **Live feedback signals:** filler words, pacing (WPM), dead air, prohibited phrases (user-configurable), text-level sentiment.
- **UI experience:** continuous visual/textual feedback — live metric counters + unified LLM-generated nudge stream (supportive coach tone, medium length, event-triggered + periodic sweep) + live transcript pane.
- **End of session:** downloadable markdown file containing full transcript, metrics, event timeline, all nudges, and an LLM-generated narrative summary.

### Technical

- **Transport:** local `livekit-server --dev` (WebRTC). Agent ↔ UI over data packets (`metrics`, `nudges`) and RPC (`start_session`, `stop_session`, `update_settings`).
- **Agent:** Python, `livekit-agents` SDK, follows the Transcriber recipe pattern — `AgentSession` with `stt` + `vad` only (no `llm` / `tts` wired into the voice pipeline).
- **ASR:** `faster-whisper base.en` (int8, 400 ms sliding window) embedded **in-process** in the agent — no STT container, no HTTP hop.
- **VAD:** Silero (via `livekit-plugins-silero`) drives dead-air detection and STT final-promotion.
- **Detectors (tight lane):** all in-process, event-driven on transcript + VAD events, aggregate into rate-limited `MetricsSnapshot` packets (≤ 4 Hz).
- **LLM (relaxed lane):** Ollama + `qwen2.5:3b-instruct-q4_K_M`, called from a separate `asyncio` worker with concurrency=1. **Never on the voice-pipeline critical path.**
- **Frontend:** React + Vite + `@livekit/components-react`. Static long-lived dev token in `.env.local`. Settings persisted in `localStorage`. Markdown download is pure client-side.

### Latency budget

- End-to-end tight-lane latency target **< 500 ms** from speech to UI, achievable on a consumer CPU with `base.en` / int8 / 400 ms window.
- LLM nudges arrive 1–5 s later (acceptable, not on the critical path).

### Footprint

- 3 services to run at dev time: LiveKit server, Python agent, Ollama.
- First-run download: ~2.2 GB (Whisper model + Silero VAD + Ollama 3B Q4).
- Peak session RAM: ~1.5–3 GB.
- No Docker required.
- macOS primary, Linux secondary; Windows via WSL2 untested in P0.

---

## P0 vs P1 scope

### In P0

- Practice mode, rep reading a script, one-way audio.
- 3 pre-built scripts.
- All five P0 detectors (fillers, pacing, dead air, prohibited phrases exact+fuzzy, sentiment via VADER).
- LLM-generated nudges and narrative summary via local Ollama.
- Configurable settings in UI (dead air, prohibited phrases, pacing band), persisted in `localStorage`.
- Downloadable markdown report on Stop.
- Error handling for Ollama offline, mic denied, LiveKit disconnect, `localStorage` unavailable.

### Explicitly deferred to P1 (architecture supports without rework)

- Customer-leg analysis (second audio track; interruption/cross-talk signals).
- Live calls with real customers.
- User-provided / admin-curated / AI-generated scripts.
- Per-script prohibited-phrase overrides.
- Audio-based prosody sentiment.
- Semantic prohibited-phrase matching (embeddings) — gated by `COACH_EMBEDDINGS_MODEL` env var.
- Session history, replay, audio recording.
- TTS / speech-to-speech (voice role-play).

---

## Implementation approach (10 steps)

The implementation plan breaks the design into **10 incremental, demoable, test-driven steps**, each producing working functionality:

| Step | Deliverable |
|---|---|
| 1 | Repository scaffolding, `scripts/setup.sh`, `scripts/start.sh`, smoke tests |
| 2 | Browser mic publishes to local LiveKit; agent echoes liveness packets (proves the transport end-to-end) |
| 3 | In-process `faster-whisper` STT emits live transcripts to the UI |
| 4 | Session lifecycle + 3-script library + UI shell (first real, demoable product slice) |
| 5 | Tight-lane text detectors (filler · pacing · prohibited · sentiment) + live metric counters |
| 6 | Silero VAD + dead-air detector → all five P0 metrics live |
| 7 | UI settings panel, `localStorage` persistence, `update_settings` RPC |
| 8 | Ollama-backed nudge worker streaming LLM coaching to the UI |
| 9 | End-of-session LLM narrative summary + downloadable markdown report |
| 10 | Fault handling, status badges, README, and pre-release polish |

Core end-to-end functionality (speak → see transcript → see metrics) is reachable by **Step 5**. Product-defining LLM coaching lands in **Step 8**. A shippable v0.1.0-p0 is ready after **Step 10**.

Tests are written **alongside** each step — no "add tests later" steps.

---

## Areas likely to need iteration during implementation

These are flagged in the design (Appendix E) and implementation plan. They are all in-scope for P0 and won't require rearchitecture, but will benefit from empirical tuning:

1. **`faster-whisper` streaming shape.** The design's 400 ms sliding-window + interim/final promotion strategy is reasonable but best tuned against real recordings in Step 3. Fallback to `tiny.en` is built in.
2. **LLM nudge prompts.** The system + user prompts in `research/local-llm.md` are v1 drafts. Expect 1–2 rounds of prompt refinement after recordings in Step 8 to get tone and length right.
3. **Script content.** The three P0 scripts (design Appendix C) are first drafts; minor editing may be warranted after practice runs.
4. **CPU contention between Whisper + Silero + Ollama on lower-end hardware.** Mitigations are designed in (bounded LLM concurrency, small model default, auto-downgrade Whisper). Needs validation on the actual target laptop.

---

## Next steps for the user

1. **Review the design document** — `design/detailed-design.md`. It's the single source of truth for behavior, components, data models, error handling, testing, and the script content.
2. **Review the implementation plan** — `implementation/plan.md`. If you want to reshape the sequence (e.g., surface Ollama earlier, push settings later), this is the time.
3. **Start Step 1** — create the GitHub repository scaffold, copy planning docs under `docs/`, set up the `agent/` and `coach-ui/` packages. Each subsequent step ends with a working demo, so reviewing progress incrementally is easy.
4. **Copy this planning folder into the repo under `docs/planning/`** so reviewers can see the full PDD trace.

---

## Open decisions (non-blocking)

- **Whether to build the `status` data channel + UI badges in Step 10** or defer. Marked optional in the plan.
- **Auto-downgrade Whisper to `tiny.en`** on sustained dropped chunks — designed in, behind a config flag, default off.
- **CI / GH Actions** for unit tests — not in P0 scope but straightforward to add.

---

## Reference documents

- `rough-idea.md` — original concept
- `idea-honing.md` — 14 questions, full Q&A record, including the P0-lean decisions
- `research/livekit-agents-sdk.md`, `research/livekit-local-setup.md`, `research/local-asr.md`, `research/local-llm.md`, `research/detectors.md`, `research/frontend.md`
- `design/detailed-design.md`
- `implementation/plan.md`
