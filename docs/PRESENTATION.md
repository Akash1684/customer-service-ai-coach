# Customer Service AI Coach

## Slide 1: Overview

**Customer Service AI Coach** is a browser-based practice environment
that gives support representatives **real-time coaching feedback while
they speak**. No scheduled reviews, no cloud, no recordings.

### The cost customer service operations already carry

**Poor rep performance drives revenue out the door.**

- US call center agent attrition runs 30 to 45 percent annually, 2 to 5
  times the rate for other US occupations. Some sectors hit 55 to 60
  percent. [BLS data, RethinkCX 2026 playbook]
- Companies with below-average customer experience scores show -2.3
  percent annual revenue growth. Above-average CX companies grow 8.1
  percent. [Forrester CX Index, cited by Blippr CX Research]
- Industry average annual customer churn is 20 to 30 percent, with poor
  service the leading driver. [Ringly Customer Churn Statistics, 2026]
- Retaining an existing customer costs 5 to 25 times less than acquiring
  a new one. A 5 percent retention improvement increases profit 25 to 95
  percent. [Bain classic retention research]

**Training a rep is expensive and slow.**

- Replacing one call center agent costs $10,000 to $25,000 in direct
  hiring, onboarding, and ramp expenses. Total impact, including lost
  productivity, reaches $46,000 per agent. [SHRM 2025 Benchmarking,
  Insignia Resource 2026]
- New-agent training costs $3,000 to $10,000 per rep before the first
  live call. [HiveDesk Call Center Labor Cost Management]
- Average ramp time to full productivity is 90 days. Companies pay
  full salary during this window against limited call output.
  [Symtrain, HiveDesk]
- Corporate training delivery costs $123 per instructor hour, at 17.4
  hours per employee per year. [ATD 2024 State of the Industry Report]

### What reps get today, and why it is not enough

- Feedback arrives **after** the call, from supervisor reviews or
  post-call transcripts. The gap between mistake and correction is
  hours to days.
- Cloud-based real-time coaching tools stream customer audio to
  third-party servers. That rules them out for healthcare, financial
  services, and government deployments.

### What the rep sees in this product

- Speaks into the browser microphone.
- Live transcript appears in under 500 ms.
- Three coaching signals update continuously:
  - Filler word count (`um`, `uh`, `like`, `you know`).
  - Prohibited phrase hits (`I don't know`, `not my job`, `calm down`).
  - Tone (positive, neutral, negative).

### Deployment properties

- Fully local. Audio and transcript data stay on the rep's laptop.
- No cloud services. No per-session cost.
- CPU only. Runs on a standard consumer laptop. One-time 2.2 GB model
  download.

---

## Slide 2: How it works

```
   Rep's browser ────── WebRTC audio ──────► Local LiveKit server
         ▲                                          │
         │  live metrics + transcript (JSON)        ▼
         └──────────────────────────────── Python coaching agent
                                           (Whisper STT + detectors)
```

### Technical approach

- **Open-source Whisper** (`faster-whisper base.en`) for speech-to-text,
  running in-process on the rep's laptop. ~250 ms per transcription on
  CPU.
- **Rule-based detectors** for the three coaching signals. Low latency,
  deterministic, no AI model drift.
- **WebRTC (LiveKit)** for real-time audio transport. Open source,
  self-hosted.

### End-to-end latency

| Step | Time |
|---|---|
| Speech to partial transcript on screen | ~500 ms |
| Speech to final transcript plus metrics update | ~250 ms after a pause |
| Cold start (first utterance after launch) | ~4 s first time, then hot |

---

## Slide 3: Status

### Shipped and working end-to-end

- Browser microphone to local transcription to three live coaching tiles.
- 72 automated tests passing. Lint and type-check clean.
- Demo video included in the repository (60 seconds, narrated).

### Scope

| Capability | Status |
|---|---|
| Real-time STT plus live coaching metrics | Shipped |
| Filler, prohibited-phrase, and tone detectors | Shipped |
| AI-generated coaching suggestions (LLM nudges) | Scoped to v2 |
| Start / Stop session plus practice script library | Scoped to v2 |
| In-browser settings editor (thresholds, phrase list) | Scoped to v2 |
| Downloadable session report | Scoped to v2 |

---

## Slide 4: Roadmap and impact

### What this product changes for a customer service operation

- **Practice loop measured in seconds, not days.** Reps rehearse in the
  browser against the same three detectors, so corrections land before
  the habit reaches a live customer.
- **Coaching load per supervisor decreases.** Post-call review shifts
  from spotting every filler word to reviewing patterns the rep already
  sees.
- **Reduced ramp exposure.** New hires practice on their own machine
  between scheduled training blocks. Classroom hours stay focused on
  judgement calls and scenario work.
- **Compliance-safe by construction.** No audio or transcript leaves the
  laptop, so the tool deploys in regulated industries where cloud
  coaching tools are blocked.

### Near-term (v2)

1. **Session lifecycle.** Explicit Start / Stop controls, plus a
   library of practice scripts covering billing disputes, cancellations,
   and account inquiries.
2. **In-browser settings.** Let reps and supervisors tune filler lists,
   prohibited phrases, and thresholds without a redeploy.
3. **AI coaching suggestions.** Layer a local LLM on detector events to
   produce natural-language nudges. Local inference keeps the privacy
   posture intact.

### Longer-term

- End-of-session markdown report with transcript, metrics, and coaching
  summary.
- Multi-language support. Current build is English only.
- Optional deployment for live customer calls. Current build is
  practice-only.

### Links

- Repository: https://github.com/Akash1684/customer-service-ai-coach
- Architecture reference: `docs/AS-BUILT.md`
- Demo script: `docs/DEMO.md`
- Demo video: `docs/demo/DemoCoach.mov`
