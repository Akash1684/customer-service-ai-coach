# Customer Service AI Coach — Implementation Plan

**Project:** `customer-service-ai-coach`
**Design ref:** `design/detailed-design.md`
**Repo:** <https://github.com/Akash1684/customer-service-ai-coach>

> Conversion directive (PDD):
> Convert the design into a series of implementation steps that will build each component in a test-driven manner following agile best practices. Each step must result in a working, demoable increment of functionality. Prioritize best practices, incremental progress, and early testing, ensuring no big jumps in complexity at any stage. Make sure that each step builds on the previous steps, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step.

---

## Progress checklist

- [x] **Step 1** — Repository scaffolding, tooling, and local-services runbook — _committed as `72cbca5` on 2026-05-07_
- [ ] **Step 2** — Browser mic publishes to local LiveKit; agent echoes liveness to a data channel
- [ ] **Step 3** — In-process `faster-whisper` STT emits live transcripts to the UI
- [ ] **Step 4** — Session lifecycle (start/stop), 3-script library, and UI shell
- [ ] **Step 5** — Tight-lane text detectors (filler · pacing · prohibited · sentiment) wired to live metric counters
- [ ] **Step 6** — Silero VAD + dead-air detector + all P0 metrics live
- [ ] **Step 7** — UI settings panel persisted to `localStorage`, applied live via `update_settings` RPC
- [ ] **Step 8** — Ollama-backed nudge worker (relaxed lane) streaming LLM coaching to the UI
- [ ] **Step 9** — End-of-session LLM narrative summary + downloadable markdown report
- [ ] **Step 10** — Fault handling, status surface, README, and pre-release polish

---

## Sequencing principles

- **Get an end-to-end slice running as early as possible.** By Step 3 we have audio → transcript → UI; by Step 4 we have a real, demoable product (pick script, start, speak, see transcript, stop).
- **Tests ride along with the code they validate.** Each step lists tests that must be written as part of the step; there are no "add tests later" steps.
- **No orphaned modules.** Each module introduced in a step is wired into a UI-visible or CLI-visible behavior **in the same step**.
- **Complexity grows linearly.** Heavy dependencies (Ollama, LLM prompts, end-of-session flows) appear only after the core real-time loop is stable.

---

## Step 1 — Repository scaffolding, tooling, and local-services runbook

### Objective
Establish the monorepo layout, base tooling, and a documented way for anyone to start the local services (LiveKit server) and install agent + frontend deps. Provide a minimum "it boots" check — no audio, no STT, no LLM yet.

### Implementation guidance
- Initialize the Git repo locally and add the `origin` remote `git@github.com:Akash1684/customer-service-ai-coach.git`. Do not push until a reviewable commit is ready.
- Top-level layout:
  ```
  customer-service-ai-coach/
  ├── agent/                      # Python agent (uv project)
  │   ├── pyproject.toml
  │   ├── src/coach_agent/__init__.py
  │   └── tests/
  ├── coach-ui/                   # React + Vite app
  │   ├── package.json
  │   ├── index.html
  │   └── src/
  ├── scripts/
  │   ├── setup.sh                # install deps + pull models
  │   └── start.sh                # run livekit-server + agent + UI
  ├── docs/
  │   ├── design/detailed-design.md       # copied from planning
  │   └── research/*.md                   # copied from planning
  ├── .gitignore
  ├── README.md
  └── LICENSE                     # MIT or Apache-2.0
  ```
- `agent/` uses `uv` with `python >= 3.10`. Initial deps: `livekit-agents`, `livekit-plugins-silero`, `python-dotenv`, plus dev deps `pytest`, `ruff`. Place these in `pyproject.toml`; other deps will be added in later steps.
- `coach-ui/` uses Vite + React + TypeScript. Initial deps: React, `livekit-client`, `@livekit/components-react`, `@livekit/components-styles`. Dev deps: `vitest`, `@testing-library/react`, `typescript`, `vite`, `@vitejs/plugin-react`.
- `.gitignore` must include: `.env.local`, `__pycache__/`, `.pytest_cache/`, `node_modules/`, `dist/`, `.venv/`, and model-cache dirs if they ever leak into repo.
- `.env.local.example` for both `agent/` and `coach-ui/` with placeholders.
- `scripts/setup.sh` installs `uv` deps in `agent/`, runs `npm install` in `coach-ui/`. (Model downloads arrive in later steps.)
- `scripts/start.sh` starts `livekit-server --dev` in the background, then prints instructions for the other two panes. Keep it intentionally simple.
- `README.md` lists: prereqs (Python 3.10+, Node 20+, `livekit-cli`, `livekit-server`), how to install, how to run, and a link to the design doc. No product marketing yet.
- Repo artifacts from planning: copy `.agents/planning/2026-05-06-customer-service-ai-coach/design/` and `research/` into `docs/` so the repo is self-contained for reviewers.

### Tests for this step
- **Python:** one smoke test `tests/test_imports.py` asserting `import coach_agent` works and `livekit-agents` is importable. Fails clearly if the virtual environment isn't bootstrapped.
- **TypeScript:** one smoke test verifying Vite dev server boots and the root component renders "Customer Service AI Coach".
- CI is not required in P0 but add a single Makefile / justfile target `make test` that runs both.

### Integration with prior work
First step — establishes the substrate everything else builds on.

### Demo
Clone the repo, run `./scripts/setup.sh`, run `./scripts/start.sh` (LiveKit server running), then `npm --prefix coach-ui run dev`. Visit <http://localhost:5173> and see a bare page titled "Customer Service AI Coach — v0". `curl http://127.0.0.1:7880` responds. Smoke tests pass.

---

## Step 2 — Browser mic publishes to local LiveKit; agent echoes liveness to a data channel

### Objective
Prove the bidirectional real-time plumbing end-to-end: the browser publishes the rep's microphone into a LiveKit room, and a Python agent participant reads a heartbeat on the room and publishes periodic liveness packets the browser renders.

### Implementation guidance
- **Dev token:** generate once with `lk token create --api-key devkey --api-secret secret --join --room coach-room --identity rep-local --valid-for 720h`. Place in `coach-ui/.env.local`:
  ```
  VITE_LIVEKIT_URL=ws://127.0.0.1:7880
  VITE_LIVEKIT_TOKEN=<jwt>
  VITE_LIVEKIT_ROOM=coach-room
  ```
- **Frontend (`coach-ui/src`):**
  - `App.tsx` wraps the app in `<LiveKitRoom token={} serverUrl={} audio={true} video={false} connect>`.
  - A small `DebugPane` component uses `useDataChannel("liveness")` to display the last 5 agent heartbeat messages with timestamps.
  - `@livekit/components-styles` imported for default styling.
- **Python agent (`agent/src/coach_agent`):**
  - `main.py` creates `AgentServer`, registers a minimal `rtc_session` entrypoint.
  - Entrypoint: `await ctx.connect()`, then a background `asyncio` task publishes `{"t_ms": ..., "status": "alive"}` on topic `liveness` every 2 s via `ctx.room.local_participant.publish_data(payload, topic="liveness")`.
  - `.env.local` for agent mirrors the same `LIVEKIT_URL/API_KEY/API_SECRET` with `devkey`/`secret`.
- Agent runs with `uv run src/coach_agent/main.py dev`. Use `agent_name="coach"` so the CLI dispatch finds it.
- Explicitly **do not** wire `stt`/`vad` yet. The `AgentSession` is not needed this step; we're just proving the data-channel loop.

### Tests for this step
- **Agent:** unit test for a small `Heartbeat` helper that yields monotonically increasing `t_ms` values.
- **Frontend (`vitest`):** `DebugPane` renders heartbeat items in reverse-chronological order; handles empty state.
- **Manual E2E check:** microphone permission prompt appears, once granted the browser's Network tab shows ICE + DTLS succeeding, and the `DebugPane` shows a new heartbeat every 2 s.

### Integration with prior work
Builds on the scaffolding from Step 1: fills `main.py` (agent) and `App.tsx` (UI).

### Demo
Run LiveKit server, the agent, and the UI. Open the browser, grant mic. In the DebugPane, see a new `{"t_ms": …, "status":"alive"}` line every 2 s. Kill the agent; DebugPane stops updating, proving the packets originate server-side.

---

## Step 3 — In-process `faster-whisper` STT emits live transcripts to the UI

### Objective
Deliver the first slice of real value: speak into the mic, see live transcript text in the UI, produced by `faster-whisper` running in-process on the agent.

### Implementation guidance
- **Add deps:** `agent/pyproject.toml` — `faster-whisper`, `ctranslate2`, `numpy`, `scipy` (for resampling) or `soxr`.
- **New module** `agent/src/coach_agent/stt/local_whisper.py`:
  - `LocalFasterWhisperSTT(stt.STT)` loads `WhisperModel(model_size_or_path="base.en", device="cpu", compute_type="int8", cpu_threads=4)`.
  - `LocalFasterWhisperStream(stt.SpeechStream)` maintains a resampled 16 kHz mono buffer of the last ~3 s. A timer coroutine runs every 400 ms, calls `model.transcribe(buffer_fp32, language="en", word_timestamps=True, beam_size=1, vad_filter=False, condition_on_previous_text=False)`, and emits an `INTERIM_TRANSCRIPT` event with joined segment text.
  - Promote to `FINAL_TRANSCRIPT` on a simple heuristic for Step 3: ~600 ms of no new audio (we'll replace this with VAD in Step 6).
- **Wire into `AgentSession`:** in `main.py`, create `session = AgentSession(stt=LocalFasterWhisperSTT())`. Register `@session.on("user_input_transcribed")` that calls `ctx.room.local_participant.publish_data(json({"partial": t.transcript, "is_final": t.is_final}), topic="transcript")`. Replace the old liveness echo with transcript publishing; liveness moves to a lower-cadence debug log.
- **Frontend:** new `useTranscript()` hook subscribes to `"transcript"` topic. A `TranscriptPane` component renders the current partial + last N finals. Replace the DebugPane with TranscriptPane.
- **Model download hook:** add `agent/src/coach_agent/download_files.py` and wire `uv run src/coach_agent/main.py download-files` per the LiveKit starter pattern so the Whisper weights are fetched once ahead of first run.

### Tests for this step
- **Unit (Python):**
  - Resampling helper: assert a 48 kHz stereo chunk of 4800 samples is resampled to ~1600 mono int16 samples.
  - `LocalFasterWhisperStream` state machine: mock the `WhisperModel` to return a canned transcript and assert `SpeechEvent`s are produced at the expected cadence.
- **Integration (Python):** feed a short canned WAV (e.g., a 5-second "the quick brown fox…" sample included in `tests/fixtures/`) through the stream and assert the final transcript contains a minimum hit rate of expected words (case-insensitive substring check, not exact equality).
- **Frontend:** `TranscriptPane` renders partial and final segments distinctly.
- **Manual E2E:** speak a sentence; within ~0.5 s see partial text appear; within ~1 s final text lands and a new partial line begins for the next utterance.

### Integration with prior work
Replaces Step 2's liveness data packet with real transcript events. Reuses the data-channel publish pattern.

### Demo
Open the UI, grant mic, and speak. Live text streams into the TranscriptPane. Logs show per-chunk STT latency under 500 ms p95.

---

## Step 4 — Session lifecycle (start/stop), 3-script library, and UI shell

### Objective
Turn the prototype into a real product: the rep picks one of three practice scripts, clicks Start, reads the rep turns aloud, clicks Stop, and returns to idle. Transcript only updates during active sessions. Establishes the persistent UI layout used for the rest of the project.

### Implementation guidance
- **Agent:**
  - `scripts/library.py` with the three P0 scripts from `design/detailed-design.md` §11 (complaint-billing, inquiry-account, cancellation-retention), each as `Script(id, title, category, turns: list[Turn])`.
  - `transport/rpc.py` registers `start_session(script_id)`, `stop_session()`, and `list_scripts()` on the agent participant via `ctx.room.local_participant.register_rpc_method(...)`.
  - `start_session` sets an internal `session_active` flag (per-room state), records `session_started_at`, and validates the `script_id` exists. Returns `{ok: true}` or `{ok: false, error}`.
  - `stop_session` clears the flag.
  - Transcript publisher only emits when `session_active` is true. Outside a session, no transcript packets are sent.
- **Frontend:**
  - Introduce the single-screen layout from `design/detailed-design.md` §4.3: header (script selector, Start/Stop, Download placeholder), left `ScriptPanel`, right column containing `MetricsBar` (placeholder, empty) and `TranscriptPane`.
  - `ScriptPanel` renders turns as alternating `[Customer]` / `[Rep]` blocks. Rep turns are visually prominent.
  - `useCoachSession()` hook centralizes: `status`, `scriptId`, `startedAt`, and dispatches RPC calls on button clicks.
  - Start button is enabled only when a script is selected and `status === "idle"`. Stop button enabled when `status === "running"`.
  - The `DownloadButton` is rendered but disabled; it lights up after Step 9.
- **Script selector** fetches scripts from the agent via `list_scripts()` RPC on first connect.

### Tests for this step
- **Agent:**
  - Unit: `library.list_scripts()` returns three scripts with the exact IDs from the design.
  - Unit: RPC handlers — `start_session` rejects unknown IDs; rejects a double-start; `stop_session` on an idle session is a no-op returning `{ok: true}`.
- **Frontend:**
  - `ScriptPanel` renders speaker turns with correct visual treatment.
  - `useCoachSession` transitions: idle → running on start; running → idle on stop; handles RPC failures.
  - Transcript packets are ignored when `status !== "running"`.

### Integration with prior work
The transcript pipeline from Step 3 now has a lifecycle around it. The data-channel plumbing (Step 2) carries new RPC and transcript messages.

### Demo
Open UI, pick "Billing dispute on a monthly plan", click Start, read the rep turns, observe the transcript updating only during the session. Click Stop; transcript freezes; Start button re-enables.

---

## Step 5 — Tight-lane text detectors wired to live metric counters

### Objective
Deliver the first coaching signals. On every transcript event, run filler, pacing, prohibited-phrase, and sentiment detectors in-process. Publish a `metrics` snapshot to the UI and render live counters.

### Implementation guidance
- **Add deps:** `rapidfuzz`, `vaderSentiment`.
- **New modules under `agent/src/coach_agent/detectors/`:**
  - `base.py` — `DetectorEvent` dataclass and `Detector` protocol (per `design/detailed-design.md` §4.2).
  - `filler.py` — `FillerDetector` with the default word set, case-insensitive membership on final transcripts (interim transcripts advance a cursor but don't double-count). Normalization strips punctuation.
  - `pacing.py` — `PacingDetector` tracks rolling 10-s-of-speech WPM and cumulative average. Emits `pace_fast` / `pace_slow` events per design §3.
  - `prohibited.py` — `ProhibitedDetector` uses exact substring first, then `rapidfuzz.fuzz.partial_ratio >= 88` as fallback. Default list from `config.CoachSettings`.
  - `sentiment.py` — `SentimentDetector` with `vaderSentiment.SentimentIntensityAnalyzer`, rolling ~20 s window, tag transitions emit events.
- **`pipeline/metrics.py`:** `MetricsSnapshotBuilder` holds detector state contributions, composes the `MetricsSnapshot` dataclass (matching design §5.1), and rate-limits publication to one packet per 250 ms via a trailing timer.
- **`pipeline/event_bus.py`:** thin `asyncio.Queue` wrapper (used now for metrics rate-limiting; the nudge worker in Step 8 consumes from the same bus).
- **`main.py` wiring:** on `user_input_transcribed`, call `detector.on_transcript(ev)` for each detector, enqueue their `DetectorEvent`s, and let `MetricsSnapshotBuilder` drive publication on topic `metrics`.
- **Frontend:**
  - `useMetrics()` hook subscribes to `"metrics"` topic and holds the latest `MetricsSnapshot`.
  - `MetricsBar` component renders: fillers total (+ small chip showing the last word heard), current + average WPM with band coloring, prohibited hits count with the last matched phrase as a subtitle, and a `SentimentPill` (Positive / Neutral / Flat / Negative).
  - Use default threshold values from `CoachSettings` (Step 7 adds configurability).

### Tests for this step
- **Detectors (Python):**
  - `FillerDetector`: given synthetic `user_input_transcribed` events, emits one event per filler, doesn't double-count interim→final.
  - `PacingDetector`: fabricated event sequences produce expected `wpm_current` and `wpm_avg`; pause correctly ages windows out.
  - `ProhibitedDetector`: exact match; fuzzy match ("dont know" ≈ "I don't know"); unrelated string doesn't match; user-overridden list is applied.
  - `SentimentDetector`: positive/negative lexical samples yield expected tags; transitions emit `sentiment_dip` only on downgrades.
- **`MetricsSnapshotBuilder`:**
  - Burst of 10 events in 50 ms produces exactly one data packet after the 250 ms window closes.
  - Quiet periods followed by a single event produce a packet within 250 ms.
- **Frontend:**
  - `MetricsBar` renders each field with correct band/tag colors.
  - `useMetrics` replaces state atomically on each packet.
- **Integration (Python):** feed the canned WAV from Step 3 into the full pipeline and assert the snapshots contain expected approximate counts (fillers within ±1 of ground truth, WPM within ±15%).

### Integration with prior work
Event-binds detectors to the STT events wired in Step 3 and the session lifecycle wired in Step 4. The `MetricsBar` takes its intended place in the UI shell.

### Demo
Start a session and read a script. Live counters update: filler count ticks up on "um", WPM changes with pace, prohibited hits tick if a forbidden phrase is read (e.g., scripts contain "I understand" — non-matching — so trigger one intentionally by saying "I can't help you" during practice). Sentiment pill reflects recent tone.

---

## Step 6 — Silero VAD + dead-air detector + all P0 metrics live

### Objective
Add the last missing tight-lane signal. Use Silero VAD (first-class LiveKit plugin) to provide reliable speech boundaries, drive the dead-air detector, and improve the STT final-promotion logic from Step 3.

### Implementation guidance
- **Agent:**
  - Add `vad=silero.VAD.load()` when constructing `AgentSession` in `main.py`.
  - `download_files` includes the Silero model so it's pre-fetched.
  - `detectors/dead_air.py` — `DeadAirDetector`:
    - Subscribes to session VAD events (start/end of speech). Uses `session.on("speech_started"/"speech_stopped")` or equivalent; verify the exact event names during implementation and stick with the design contract.
    - On end-of-speech, records `silence_start`. On start-of-speech, computes `silence_duration`. If `>= settings.dead_air_threshold_s`, emits a `dead_air` event and increments the count.
    - Pre-session silence (before the first `speech_started` after `start_session`) is ignored.
  - Upgrade `LocalFasterWhisperStream` final-promotion: instead of the timer-based heuristic from Step 3, promote the partial to `FINAL_TRANSCRIPT` on `speech_stopped`. This reduces finalization latency and aligns dead-air boundaries with transcript boundaries.
  - Extend `MetricsSnapshot` with `dead_air_count` and `dead_air_total_s` populated from the new detector.
- **Frontend:** extend `MetricsBar` with a Dead-air tile (e.g., `2 events · 6.4s`).

### Tests for this step
- **Python:**
  - `DeadAirDetector`: synthetic VAD event sequences — ignore pre-session silence, fire at threshold, respect live-updated threshold, account for consecutive silences.
  - Updated `LocalFasterWhisperStream`: on a simulated `speech_stopped`, the pending interim transcript is promoted to final exactly once.
- **Frontend:** `MetricsBar` dead-air tile renders zeroes initially and updates on snapshot changes.
- **Integration:** extend the canned-WAV fixture to include a ~4 s silence; assert one `dead_air` event with duration close to 4 s.

### Integration with prior work
Plugs into the same snapshot/publish path from Step 5. All P0 detectors are now producing live metrics.

### Demo
Start a session. Intentionally pause 4 s mid-script. See Dead-air tile increment to `1 event · 4.0s`. Pacing and fillers continue to behave.

---

## Step 7 — UI settings panel persisted to `localStorage`, applied live via `update_settings` RPC

### Objective
Let the rep customize dead-air threshold, pacing band, and the prohibited-phrase list from the UI. Persist these in `localStorage`. Settings take effect live — no restart needed.

### Implementation guidance
- **Agent:**
  - `transport/rpc.py` adds `update_settings(patch)` RPC. It merges the patch into an in-memory `CoachSettings` owned by the session and pushes the updated settings into each detector's reconfigurable surface (e.g., `DeadAirDetector.set_threshold(s)`, `ProhibitedDetector.set_phrases(list)`, `PacingDetector.set_band(low, high)`).
  - `start_session` clears any custom per-session overrides and begins with the current global settings (so settings persist across sessions on the agent side too, until a restart).
  - `list_settings()` RPC returns the current effective settings so the UI can sync on reconnect.
- **Frontend:**
  - New `SettingsAccordion` component with three subsections:
    - **Dead-air threshold** — number input (seconds).
    - **Prohibited phrases** — multi-line editor (one phrase per line, with the default list pre-populated).
    - **Pacing band** — two number inputs (low / high WPM).
  - `useSettings()` hook:
    - On load, reads `localStorage.getItem("coach.settings")`; falls back to defaults from the design when empty or invalid JSON.
    - On every change, writes to `localStorage` and calls `room.localParticipant.performRpc({ method: "update_settings", payload })`.
  - Settings survive page refresh; the hook fires one reconciliation `update_settings` RPC on room connect to resync the agent.

### Tests for this step
- **Agent:**
  - `update_settings` merges a partial patch without clobbering unspecified fields.
  - Detectors honor updated values on the very next event (e.g., lowering dead-air threshold from 3 s to 2 s fires on a 2.5 s silence).
  - Invalid settings (e.g., wpm_band low > high, negative thresholds) return `{ok: false, error}` and leave current state unchanged.
- **Frontend:**
  - `useSettings` reads + writes `localStorage` correctly; private-mode (writing throws) falls back to defaults without breaking the app.
  - `SettingsAccordion` edits trigger debounced RPC calls (one per 300 ms of inactivity) to avoid spamming the agent on each keystroke.

### Integration with prior work
Builds on the detector reconfiguration paths sketched in Step 5/6. No new transport primitives are introduced.

### Demo
Open Settings, set dead-air to 2 s, click a prohibited-phrase into the list. Read a script with a 2.5 s pause and one of those phrases. Both trigger metric updates. Refresh the page — the settings persist; session data does not.

---

## Step 8 — Ollama-backed nudge worker streaming LLM coaching to the UI

### Objective
Deliver the defining product feature: **supportive-coach nudges** generated by a local LLM (Ollama), streaming into the UI as the rep speaks. Event-triggered + periodic sweep cadence per design §4.

### Implementation guidance
- **Prereq (one-time user step, document in README):**
  ```
  brew install ollama     # or equivalent
  ollama serve &
  ollama pull qwen2.5:3b-instruct-q4_K_M
  ```
- **Agent:**
  - Add `livekit-plugins-openai` to deps. Instantiate `coach_llm = openai.LLM(base_url="http://127.0.0.1:11434/v1", api_key="ollama", model=<model_from_env_or_default>, temperature=0.4)` where `<model_from_env_or_default>` defaults to `qwen2.5:3b-instruct-q4_K_M` and can be overridden with `COACH_LLM_MODEL`.
  - `pipeline/nudger.py` — `NudgeWorker`:
    - Holds a rolling detector-event log and the last ~20 s of final transcripts.
    - On every detector event posted to the event bus, decides whether to respond (rate-limited to `nudge_min_interval_s`, default 5 s; prioritizes higher-impact events).
    - Every `sweep_interval_s` (default 12 s), if no event-triggered nudge has fired recently, emits a periodic-sweep nudge based on recent state.
    - Builds the system + user prompts from `research/local-llm.md` §3.
    - Calls `coach_llm.chat([...])` with `max_tokens=80` for nudges. Post-processes the output (strip preamble/sign-off, enforce ≤35 words).
    - Publishes on `nudges` topic with `Nudge{id, t_ms, text_markdown, event_type}`.
    - Concurrency strictly 1. If a call takes > 8 s, log a warning and allow the next event to kick a new request only after the current one finishes.
  - On `start_session`, send a warmup request (`max_tokens=1`) to load the model into RAM.
- **Frontend:**
  - New `useNudges()` hook subscribes to `"nudges"` topic and keeps an append-only list.
  - `NudgeStream` component renders nudges as a vertical feed, newest on top, rendering `text_markdown` with `marked`. Virtualize if the list exceeds 50 entries.
  - Replaces the placeholder area in the right column from Step 4.

### Tests for this step
- **Agent:**
  - Unit: `NudgeWorker` with a mocked `LLM.chat` asserts:
    - Event triggers a call within rate limit; bursts coalesce.
    - Periodic sweep fires only when quiet.
    - Malformed model output (leading greeting / trailing sign-off / >35 words) is post-processed correctly.
    - If the mock LLM raises, the worker logs and continues (does not crash the session).
  - Prompt-shape assertion: the constructed messages match the documented structure (no free-form LLM content in tests; shape only).
- **Frontend:**
  - `NudgeStream` renders markdown safely (no raw HTML injection).
  - `useNudges` appends and does not de-duplicate across refresh (each session starts fresh).
- **Manual E2E:** with Ollama running locally and the model pulled, start a session and say "um um um". Within ~5 s a nudge appears acknowledging the fillers. Say nothing for 12 s; a periodic nudge arrives commenting on pacing or silence.

### Integration with prior work
Connects the detector event bus (Step 5) to a new consumer. Reuses `publish_data` on a new topic. UI fills the previously empty nudge column from Step 4.

### Demo
Full session with LLM coaching: speak a script, receive 3–5 supportive-coach nudges tied to detected events over ~1–2 minutes.

---

## Step 9 — End-of-session narrative summary + downloadable markdown report

### Objective
Close the session loop. On Stop, generate an LLM narrative summary and enable the client-side markdown download with everything from the session.

### Implementation guidance
- **Agent:**
  - `pipeline/summary.py` — `SummaryWorker.generate(session_state) -> str`:
    - Collects aggregated metrics, top-N events by impact, script title, and duration.
    - Calls `coach_llm.chat(...)` with the system + user prompts from `research/local-llm.md` §4, `max_tokens=600`.
    - Post-processes to ensure the required markdown section structure is present.
  - On `stop_session`:
    - Stop emitting metrics.
    - Run `SummaryWorker.generate(...)`.
    - Publish the result on `nudges` topic as `Nudge{event_type: "final_summary", text_markdown: <summary>, ...}`.
    - Return `{ok: true}` only after publishing.
  - Timeout: cap summary generation at 20 s. If exceeded, publish a rule-based fallback summary (totals + counts) so the user always gets something downloadable.
- **Frontend:**
  - `useCoachSession` captures the `final_summary` nudge and stashes it separately from the regular nudge list.
  - `DownloadButton` becomes enabled once a session has ended and a `final_summary` is available (or the 20 s timeout has elapsed with the fallback).
  - Build the markdown per design §5.4, then trigger a Blob download: filename `coach-session-<ISO timestamp>-<scriptId>.md`.
  - Client-side only — no server roundtrip.

### Tests for this step
- **Agent:**
  - `SummaryWorker` with a mocked LLM asserts prompt construction and output post-processing.
  - Timeout path: slow mock returns after 25 s → fallback is invoked within 20 s, and the session returns to idle.
- **Frontend:**
  - Markdown builder produces the exact section structure from design §5.4 given a representative `SessionState`.
  - `DownloadButton` is disabled while running, enabled after `final_summary` (or fallback) arrives, and triggers a `Blob` download of the right MIME type and filename pattern.

### Integration with prior work
Reuses the nudge channel for the final summary; reuses the detector totals accumulated in Step 5/6. The `DownloadButton` placeholder from Step 4 now has real behavior.

### Demo
Complete a 60–90 second practice session. Click Stop; within a few seconds the summary appears as the final nudge card. Click Download; a markdown file saves locally. Open it and verify the structure matches design §5.4.

---

## Step 10 — Fault handling, status surface, README, and pre-release polish

### Objective
Make the system friendly when something goes wrong, finalize the first-time-run experience, and land a clean repo state ready to push to `Akash1684/customer-service-ai-coach`.

### Implementation guidance
- **Agent fault handling** (walk the design §6.1 fault matrix):
  - Ollama unreachable at `start_session`: log warning, emit a fallback nudge `{event_type: "llm_offline_notice"}`, and thereafter have `NudgeWorker` emit **event-headline** nudges (`"Filler 'um' at 00:22"`) directly from the detector event without calling the LLM.
  - Ollama slow: bounded timeout per call, skip on timeout.
  - LLM malformed output: strict post-processor; drop if still invalid.
  - Whisper model missing at boot: fatal with clear message to run `download-files`.
  - Dropped audio chunks: log and optionally auto-downgrade to `tiny.en` after sustained drop > 30% for 10 s (behind a config flag; default off).
- **Status surface (optional but recommended):**
  - Agent publishes `{"stt": "streaming" | "degraded", "coach": "ready" | "slow" | "offline", "room": "connected"}` on topic `status` every 2 s while a session is running.
  - `StatusFooter` component in the UI renders three badges consuming `useDataChannel("status")`.
- **Frontend fault UX:**
  - Mic-permission denied overlay with instructions.
  - LiveKit server unreachable banner on initial connect failure.
  - `localStorage` unavailable notice.
- **Developer experience:**
  - `scripts/setup.sh` now runs `uv run src/coach_agent/main.py download-files` (Whisper + Silero) and instructs the user to run `ollama pull qwen2.5:3b-instruct-q4_K_M` if not already present.
  - `scripts/start.sh` prints three-pane run instructions and tails the agent log.
  - `README.md` final version: prereqs, five-step quickstart, screenshot placeholder, link to the design doc, license, contribution note.
- **Repo push:** create a first release tag `v0.1.0-p0` on `main` after a final full manual E2E walkthrough passes.

### Tests for this step
- **Agent:**
  - Ollama-offline mode: mock `coach_llm.chat` to raise at `start_session`; worker switches to event-headline mode; subsequent transcript events emit nudges that match a fixed template without any LLM call.
  - Timeout path (if implemented): LLM call exceeds 8 s → skipped with a warning log assertion.
  - Dropped-chunk metric increments correctly under simulated backpressure.
- **Frontend:**
  - Mic-denied overlay renders when `getUserMedia` rejects.
  - LiveKit disconnect banner toggles on `Room` state changes.
  - Status badges render ready/degraded/offline states from canned `status` packets.
- **Manual E2E (checklist in `docs/E2E-checklist.md`):** run the full steps from design §7.4 and confirm all pass.

### Integration with prior work
Final wire-up pass — every prior module gets its failure modes tested and surfaced. The UI gets its informational surface completed.

### Demo
Start the full stack. Mid-session, kill Ollama (`pkill ollama`); UI banner turns yellow ("Coach offline"), but metrics and transcript continue. Re-start Ollama, re-start the session, full experience returns. Download the final report.

---

## Exit criteria for P0

Before marking the whole project done:

1. All 10 checklist items ticked.
2. Unit tests pass (`make test`).
3. Integration tests pass against the bundled fixture audio.
4. Manual E2E checklist (§7.4 of design) is green.
5. `README.md` instructions reproduce a working demo on a clean machine.
6. Repository published to `https://github.com/Akash1684/customer-service-ai-coach` with the planning docs included under `docs/` and a `v0.1.0-p0` tag.

---

## Post-P0 upgrade path (reference only, not in scope here)

Items already designed for but explicitly deferred:

- **Semantic prohibited-phrase matching** — flip `COACH_EMBEDDINGS_MODEL=all-MiniLM-L6-v2`; add `sentence-transformers` dep.
- **Session history, replay, audio recording** — would require adding a local storage layer; no impact on agent architecture.
- **Customer-leg audio / two-party analysis** — add a second audio track; extend detectors for interruption + cross-talk signals.
- **Voice role-play** — wire `tts` and/or a speech-to-speech model into `AgentSession`.
- **CI / lint / format** — GH Actions covering the `make test` target and publishing per-PR coverage.
