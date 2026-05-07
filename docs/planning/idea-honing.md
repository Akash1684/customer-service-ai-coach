# Idea Honing: Customer Service AI Coach

This document captures the requirements clarification Q&A for the project.

## Q1: Target users and primary use case

The rough idea quotes a sales rep persona, but the project name says "Customer Service AI Coach". These two contexts have meaningfully different dynamics:

- **Sales reps (outbound/inbound sales)** — goals include driving conversions, handling objections, discovery questions. Calls are often longer, more strategic.
- **Customer service reps (support/CX)** — goals include empathy, resolution time, clarity, de-escalation. Calls are often shorter, higher volume, can be emotionally charged.
- **Both** — a more generic coach with persona-specific modes.

Who is the primary target user for this tool, and what is the main problem you're trying to solve for them? Any secondary users we should keep in mind?

**Answer:** Customer Service reps are the primary consumers.

## Q2: Coaching signals / metrics

The rough idea mentions three signals: filler words, pacing, and talk-time ratio. For customer service specifically, there are other commonly-used signals. Which are in scope?

Core signals from rough idea:
- **Filler words** — "um", "uh", "like", "you know", etc.
- **Pacing / speech rate** — words per minute, too fast / too slow
- **Talk-time ratio** — rep vs customer speaking time

Additional customer-service-relevant signals to consider:
- **Sentiment / tone** — customer frustration, rep empathy level
- **Silence / dead air** — long pauses that feel awkward on calls
- **Interruptions / cross-talk** — rep talking over the customer
- **Volume / energy level** — too quiet, monotone, or excessively loud
- **Key phrase usage** — empathy phrases, required disclosures, brand scripts
- **Prohibited phrases** — things the rep shouldn't say / promise
- **Question balance** — discovery / clarifying questions asked

Which signals are must-have for v1 (MVP), which are nice-to-have, and are there any other signals specific to your context?

**Answer:**

**P0 (MVP) signals:**
- Core signals: filler words, pacing, talk-time ratio
- Sentiment
- Dead air
- Prohibited phrases

**P1 signals:**
- Customer leg analysis (second party audio and derived signals like interruptions, customer sentiment, etc.)

**Important scope clarification:** This project is focused on **one-way audio only** — the customer service rep will read out a transcript and the AI agent needs to provide live feedback on the rep's audio. The customer leg is out of scope for v1.

## Q3: Use case scenario — rehearsal vs. live call

You mentioned the rep will "read out a transcript" with only their audio analyzed. Clarifying the exact scenario:

- **Option A: Rehearsal / practice mode** — Rep practices reading scripts before real calls.
- **Option B: Live call, rep-only audio** — Rep on a real call with a customer, but only rep's mic is captured.
- **Option C: Outbound scripted call** — Rep reads a prepared script to a real customer (only rep audio analyzed).
- **Option D: Something else** — please describe.

Follow-ups given one-way audio:
- **"Talk-time ratio" reinterpretation** — Redefine as "speaking vs silent ratio", or drop and rely on dead air?
- **"Dead air" interpretation** — Rep silent for X seconds between sentences, or something else?

**Answer:**

**Scenario:** Option A — **Practice / rehearsal mode** is P0. Options B, C (live calls with customers) are P1.

**3a. Talk-time ratio:** Dropped. System will rely on **dead air** as the silence-related signal.

**3b. Dead air definition:** Default threshold of **3 seconds** of rep silence. Threshold must be **configurable from the UI**.

## Q4: Transcript / script source

In practice mode, where do the scripts the rep reads come from?

Options:
- **A. User-provided** — upload/paste their own scripts.
- **B. Pre-built library** — system ships with curated practice scripts.
- **C. Admin/manager-curated** — admin creates and assigns scripts to reps.
- **D. AI-generated** — system generates scripts dynamically.
- **E. Mix of the above** — e.g., P0 is user-provided + pre-built library, admin-curated is P1.

For v1/MVP, where do scripts come from, and are there any constraints on script format (plain text only, markdown, structured with speaker turns, expected cue points, etc.)?

**Answer:**

**P0:** Pre-built library — system ships with a curated set of practice scripts.

**P1:** User-provided, admin-curated, and AI-generated sources.

Script format constraints deferred to design phase (library is system-controlled).

## Q5: Real-time feedback UX / delivery

How does feedback reach the rep during a practice session?

**Feedback modality:**
- **A. Visual cues on a side panel** — live counters, color indicators, toast notifications.
- **B. Inline script annotations** — flag exact word/phrase on the scrolling script.
- **C. Audio cues** — tones/beeps (likely disruptive).
- **D. Post-session report only** — no real-time feedback.
- **E. Combination** — visual side panel + inline annotations + post-session summary.

**Cadence / intrusiveness:**
- Continuous updates (every second) vs event-driven?
- Peripheral/ambient vs interruptive warnings?

**Post-session:**
- Full metrics report + transcript replay?

What's the v1 design here? P0 vs P1 split.

**Answer:**

**Real-time feedback (P0):**
- **Visual textual feedback** on the UI
- **Streaming continuously** with detailed feedback (non-intrusive, peripheral)

**Post-session (P0):**
- Option to **download the entire feedback** (transcript + detected events)
- **Overall summary** of the session

Audio cues are out of scope. Inline script annotations are not explicitly required for P0 (primary feedback lives in a side/dedicated UI area).

## Q6: Platform, form factor, and tech stack constraints

**6a. Form factor:** Web / Desktop / Mobile / more than one?

**6b. Deployment context:** Cloud-hosted SaaS / Self-hosted / Local-only?

**6c. Tech stack preferences or constraints:**
- LiveKit — firm requirement or open?
- Preferred backend language / runtime?
- Preferred frontend framework?
- Preferred LLM/ASR providers (OpenAI, AWS Transcribe, Bedrock, Deepgram, AssemblyAI, Whisper, etc.)?
- Existing organizational stack to fit into?

**Answer:**

- **6a. Form factor:** **Web app** (browser)
- **6b. Deployment:** **Local-only** (runs entirely on user's machine, no cloud infra)
- **6c. Tech stack:**
  - **LiveKit is a must** (firm requirement for the real-time audio pipeline, likely self-hosted locally)
  - **Backend:** **Python**
  - **Frontend:** Recommend — easiest for LiveKit with minimal UI. **Recommendation: React + Vite + LiveKit React SDK (`@livekit/components-react`)** — smallest footprint, official LiveKit starter exists, no meta-framework overhead (vs. Next.js, which is heavier than needed for a local-only web app).
  - **ASR, Reasoning, TTS/Speech2Speech:** **Fully local stack** — no external/cloud API calls. Examples:
    - ASR: `whisper.cpp` or `faster-whisper` (local)
    - Reasoning: local LLM via Ollama (Llama, Mistral, Qwen, etc.)
    - TTS: Piper / Kokoro / similar (local)
    - Speech2Speech (optional, future): e.g., Moshi
  - **TTS / Speech2Speech scope:** **Option C** — stack availability only, **not a P0 feature**. P0 feedback remains visual/textual. TTS/S2S reserved for future features (e.g., voice coaching, P1 customer role-play).
  - **Deliverable / repo:** All project resources, including the PDD planning notes, must be pushed to **https://github.com/Akash1684/customer-service-ai-coach**

## Q7: Latency and real-time quality targets

**7a. End-to-end feedback latency:**
- Tight (<500 ms)
- Moderate (500 ms – 2 s)
- Relaxed (2–5 s)
- Mixed (by signal type)

**7b. Hardware assumptions (target for P0):**
- Consumer laptop (CPU only)
- Developer workstation (CPU + GPU)
- Apple Silicon Mac
- Specific target

**7c. ASR accuracy vs speed tradeoff:**
- Whisper model preference (tiny / base / small / medium / large) or recommend based on 7a + 7b?

**Answer:**

- **7a. Latency target:** **<500 ms end-to-end** from speech to UI cue.
- **7b. Hardware:** **CPU-only** (consumer laptop).
- **7c. ASR recommendation (based on 7a + 7b):**
  - **`faster-whisper` with `base.en` model** as the primary choice (74M params, English-only, int8 quantization on CPU → real-time factor well below 1.0 on modern CPUs, typical chunk latency ~150–300 ms).
  - Fallback to **`tiny.en`** (~39M params) if `base.en` is too slow on target hardware.
  - Use **streaming mode** with ~500 ms audio windows to emit partial transcripts continuously.
  - Language locked to English for P0 (smaller/faster `.en` models).

### Derived architectural implication (important)

A strict **<500 ms** budget on **CPU-only** means we cannot run a local LLM on the critical path. The system will use a **two-lane architecture**:

- **Tight lane (<500 ms, real-time):** Rule-based and lightweight ML detectors on streaming ASR output — filler words, dead air, pacing, prohibited phrases (keyword + embedding similarity), lightweight sentiment (small local classifier, e.g., distilled model or VADER-style). These power the continuous streaming UI.
- **Relaxed lane (async, seconds to post-session):** Local LLM (Ollama) for richer narrative feedback, nuanced sentiment commentary, and the downloadable overall summary. Not on the UI's per-event critical path.

This will be revisited in design.

## Q8: Session lifecycle and data persistence

**8a. Session flow:**
- A. Start/Stop buttons (manual)
- B. Auto-detect start (voice) / auto-end (silence or script complete)
- C. Script-locked (cannot end early without confirmation)

**8b. Persistence (local storage only):**
- Transcripts stored?
- Detected events timeline stored?
- Session metadata stored?
- Audio recordings — stored or discarded?
- Storage format (SQLite / JSON / other)?

**8c. History / review UI:**
- Past sessions list + drill-in, or ephemeral (download-only, session-gone after)?

**Answer:**

- **8a. Session flow:** **Start/Stop buttons (manual)** for P0. Rep picks a script, clicks Start, speaks, clicks Stop.
- **8b. Persistence:** **No persistent storage** in P0. Everything lives in-memory for the session. A **download button** in the UI exports the entire feedback as a **text file** from the browser. No DB, no audio recordings, no session files on disk.
- **8c. History / review UI:** **Not in P0** — ephemeral sessions, download-only. Past-sessions list + drill-in deferred to P1.

## Q9: Feedback content — UI stream and download contents

**9a. Real-time streaming UI feedback:**
- Live metric counters (fillers, WPM, dead-air count)?
- Rolling event log with timestamps?
- Running sentiment indicator?
- Live transcript pane?
- Coaching hints — rule-based strings only, or LLM-generated nudges from the relaxed lane?

**9b. Downloadable feedback (text file):**
- Full transcript?
- Full event timeline with timestamps?
- Per-signal metrics (totals, averages)?
- LLM-generated narrative summary?
- Format — plain text / markdown / user-selectable?

P0 vs P1 split for each.

**Answer (partial — direct input from user):**

- **9a Real-time UI feedback (P0):** Includes **LLM-generated coaching nudges from the relaxed lane** (in addition to rule-based detections).
- **9b Downloadable feedback (P0):** Includes an **LLM-generated narrative summary** of the session.

(Follow-up needed to confirm which standard UI elements accompany this — see 9a-follow-up and 9b-follow-up below.)

### Consolidated answer (after follow-up)

**9a. Real-time streaming UI feedback (P0):**
- **Live metric counters** — fillers, WPM, dead-air count, prohibited-phrase hits, current sentiment tag.
- **Live transcript pane** — partial transcript as the rep speaks.
- **Unified LLM-nudge stream** — the single primary feedback feed. The LLM **incorporates detected events into natural-language nudges**, so the "rolling event log" is **not a separate UI element**; events are woven into the nudge stream (e.g., "You just said 'um' — try a brief pause instead"; "Dead air at 00:34 (3.2s) — keep momentum"). This is a cleaner UX than parallel raw-event + nudge panels.

**9b. Downloadable feedback (P0):**
- **Format:** **Markdown**.
- Contents: full transcript, per-signal totals/averages (fillers, avg WPM, dead-air time, prohibited-phrase hits, sentiment profile), **LLM-generated narrative summary**, and the full nudge stream from the session.

## Q10: Prohibited phrases — source and configuration

**10a. Source:**
- A. Global default list
- B. Per-script list
- C. Global default + per-script overrides
- D. User-configurable in the UI
- E. Combination

**10b. Match type:**
- Exact string (case-insensitive)
- Fuzzy / token-based
- Embedding similarity (semantic match)
- Combination

P0 vs P1 for each.

**Answer:**

- **10a. Source:** **Option D — User-configurable in the UI** for P0. The app ships with a sensible default list that users can view, add to, or remove from directly in the UI at any time. Per-script overrides deferred to P1.
- **10b. Match type:** **Combination** — exact (case-insensitive) + fuzzy (token-based) + **embedding similarity** for semantic matches (e.g., "I'm not able to help" ≈ "I can't help you"). A small local embedding model (e.g., MiniLM / nomic-embed-text via Ollama) fits well within the <500 ms budget.

## Q11: Pre-built script library scope

**11a. Script count and categories:**
- A. Minimal (3–5)
- B. Moderate (10–15)
- C. Larger (20+)

**11b. Script structure:**
- Plain prose
- Speaker-turn format (rep reads only their turns)
- Speaker-turn with visible customer lines

**11c. Per-script metadata:**
- Context/notes, expected key phrases, learning objectives — any of these for P0?

**Answer:**

- **11a. Script count:** **Minimal — 3–5 scripts** for P0, covering core customer-service scenarios.
- **11b. Structure:** **Speaker-turn format with visible customer lines** — rep sees both sides on screen; reads only the rep turns aloud.
- **11c. Per-script metadata:** **Not P0.** Context notes, expected key phrases, and learning objectives deferred to P1. (Minimum per-script metadata in P0: title, maybe category tag, and the speaker-turn text.)

## Q12: LLM nudge cadence, style, and sentiment scope

**12a. Nudge cadence:**
- A. Event-triggered only
- B. Periodic sweep (every N seconds)
- C. Combined

**12b. Nudge style / tone:**
- Length: short / medium / variable
- Tone: supportive coach / neutral analyst / strict reviewer

**12c. Sentiment signal (given rep is reading a script):**
- Rep's tone/delivery (prosody, audio-based)
- Text-level sentiment of transcript
- Hybrid
- Drop sentiment for P0 (defer to P1 with customer leg)

**Answer:**

- **12a. Cadence:** **Combined** — LLM emits nudges on events (filler, dead air, prohibited phrase, sentiment swing) **and** on a periodic sweep of the rolling transcript.
- **12b. Style / tone:** **Medium length** (1–2 sentences), **supportive coach** tone.
- **12c. Sentiment scope (P0):** **Text-level sentiment of the transcript only**. Lightweight local classifier or VADER-style approach (no audio prosody in P0). Audio-based prosody deferred to P1 alongside customer-leg analysis.

## Q13: Install / first-run / setup experience

**13a. Who runs what?**
- A. Fully self-contained bundle (e.g., Docker Compose / launcher)
- B. Guided setup script (e.g., `./setup.sh`)
- C. Developer-style README with manual steps

**13b. Dependency footprint (multi-GB initial downloads):**
- LiveKit server, Whisper model (~150 MB), Ollama + LLM (~2–5 GB), embedding model (~100 MB). Acceptable or push for lighter footprint?

**13c. Target OS:**
- macOS only / macOS + Linux / macOS + Linux + Windows

**Answer:**

**Direction:** This is a **local testing project** — keep setup and dependencies **minimal**. After research on the LiveKit Agents SDK, we settled on a **P0-lean stack**:

### P0-lean decisions

| Decision | Rationale |
|---|---|
| **LLM (Ollama) stays in P0** | LLM-generated nudges and narrative summary are product-defining per Q9 and Q12; we accept the ~2–3 GB Ollama footprint. |
| **Drop the embedding model from P0** | Prohibited-phrase matching uses **exact + fuzzy (`rapidfuzz`)** only in P0. Semantic/embedding match becomes a P0.5 config-flag upgrade. |
| **Embed `faster-whisper` directly in the Python agent** | No separate STT Docker container. Custom thin `STT` subclass wraps `faster-whisper` in-process for lower latency and one fewer service. |
| **Static long-lived LiveKit dev token** | Generate once with `lk token create`, hardcode in `coach-ui/.env.local`. No token endpoint / FastAPI service needed for local dev. |
| **LiveKit server runs as the native binary** | `livekit-server --dev` on `127.0.0.1:7880`. No Docker for LiveKit. |
| **Frontend: React + Vite** | Leanest option with `@livekit/components-react`. |
| **OS target** | macOS primary, Linux secondary. Windows via WSL2 not explicitly tested in P0. |

### Services to run at dev time (3)

1. `livekit-server --dev` (native binary)
2. `ollama serve` (native daemon, once per machine, plus `ollama pull <model>` once)
3. Python agent (`uv run src/agent.py dev`) + Vite dev server (`npm run dev`) — these two may share a terminal pair

### First-run footprint

- Whisper `base.en` model (~145 MB)
- Silero VAD (~20 MB)
- Ollama small instruct model (~2 GB, e.g., `qwen2.5:3b-instruct-q4_K_M`)
- Total: ~2.2 GB one-time; ~1.5–3 GB peak RAM during a session; **no Docker required**.

### P0.5 upgrade path (no rearchitecture)

- Turn on semantic prohibited-phrase matching by setting `COACH_EMBEDDINGS_MODEL=all-MiniLM-L6-v2` (adds ~90 MB model and `sentence-transformers` dep).


## Q14: Pending decisions after research (locked in)

**Q14a. `localStorage` for UI settings:** **Yes.** Persist dead-air threshold, prohibited-phrase list, and pacing band across refreshes via `localStorage`. Session data (transcript, metrics, nudges) remains ephemeral per Q8.

**Q14b. Script library content:** **Draft during design.** Scripts will be authored during the design step; domains: complaint handling, account/billing inquiry, cancellation/retention (standard customer-service scenarios).

**Q14c. Default prohibited-phrase list:** **OK to use the researched defaults.** Initial list:

- "I can't help you"
- "That's not my problem"
- "I don't know"
- "We never"
- "Always works"
- "Guaranteed"

User can edit / extend from the UI; the edited list is persisted via `localStorage`.
