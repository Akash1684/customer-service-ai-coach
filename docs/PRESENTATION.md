# Customer Service AI Coach

## Slide 1 — Overview

**Customer Service AI Coach** is a browser-based practice environment that gives support representatives **real-time coaching feedback while they speak** — no scheduled reviews, no cloud, no recordings.

### Problem

- Reps today receive feedback **after** calls, via supervisor reviews or post-call transcripts. The feedback loop is slow and reactive.
- Cloud-based real-time alternatives require streaming customer audio to third parties — unacceptable for privacy-sensitive industries (healthcare, financial services, government).

### What the rep experiences

- Speak into the browser microphone.
- A live transcript appears in under half a second.
- Three coaching signals update continuously:
  - **Filler word count** (`um`, `uh`, `like`, `you know` …)
  - **Prohibited phrase hits** (`"I don't know"`, `"not my job"`, `"calm down"` …)
  - **Tone tracking** (positive / neutral / negative)

### Deployment properties

- **Fully local.** All audio and transcript data stay on the rep's laptop.
- **No cloud services, no per-session cost.**
- **CPU-only** — runs on a standard consumer laptop. One-time 2.2 GB model download.

---

## Slide 2 — How it works

```
   Rep's browser ────── WebRTC audio ──────► Local LiveKit server
         ▲                                          │
         │  live metrics + transcript (JSON)        ▼
         └──────────────────────────────── Python coaching agent
                                           (Whisper STT + detectors)
```

### Technical approach

- **Open-source Whisper** (`faster-whisper base.en`) for speech-to-text, running in-process on the rep's laptop. ~250 ms per transcription on CPU.
- **Rule-based detectors** for the three coaching signals. Low-latency, deterministic, no AI model drift.
- **WebRTC (LiveKit)** for the real-time audio transport. Industry-standard, open-source, self-hosted.

### End-to-end latency

| Step | Time |
|---|---|
| Speech → partial transcript on screen | ~500 ms |
| Speech → final transcript + metrics update | ~250 ms after a pause |
| Cold start (first utterance after launch) | 0 — model pre-warmed at agent startup |

---

## Slide 3 — Status

### Shipped and working end-to-end

- Browser microphone → local transcription → three live coaching tiles
- Pre-warmed model eliminates first-utterance cold start
- 72 automated tests passing, lint and type-check clean

### Scope

| Capability | Status |
|---|---|
| Real-time STT + live coaching metrics | **Shipped** |
| Filler, prohibited-phrase, and tone detectors | **Shipped** |
| AI-generated coaching suggestions (LLM nudges) | Scoped to v2 |
| Start/Stop session + practice script library | Scoped to v2 |
| In-browser settings editor (thresholds, phrase list) | Scoped to v2 |
| Downloadable session report | Scoped to v2 |

A 60-second recording-ready demo script is included in the repository.

---

## Slide 4 — Roadmap

### Near-term (v2)

1. **Session lifecycle.** Explicit Start / Stop controls, plus a small library of practice scripts covering the most common customer-service scenarios (billing disputes, cancellations, account inquiries).
2. **In-browser settings.** Let reps tune their filler list, prohibited phrases, and thresholds without a redeploy.
3. **AI coaching suggestions.** Layer a local LLM on top of the detector events to produce supportive, natural-language nudges. Local inference keeps the privacy posture intact.

### Longer-term

- End-of-session markdown report — transcript, metrics, and coaching summary, downloadable.
- Multi-language support (current build is English-only).
- Optional deployment for live customer calls (current build is practice-only).

### Links

- **Repository:** <https://github.com/Akash1684/customer-service-ai-coach>
- **Architecture reference:** `docs/AS-BUILT.md`
- **Demo script:** `docs/DEMO.md`
