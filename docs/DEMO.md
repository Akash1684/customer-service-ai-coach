# Demo Script

A ~60-second read-aloud session designed to exercise all three detectors
(Fillers, Prohibited, Sentiment) and include a sentiment dip + recovery so
the MetricsBar tiles visibly change during the recording.

## Pre-flight

1. Three terminals running:
   ```bash
   livekit-server --dev
   cd agent && uv run src/coach_agent/main.py dev
   npm --prefix coach-ui run dev
   ```
2. Visit <http://localhost:5173>, grant mic permission, **keep the tab focused**
   (background tabs throttle WebRTC).
3. Wait for the agent terminal to print `agent ready` (it pre-loads
   `faster-whisper` at startup — ~4 s one-time, then all sessions are hot).
4. Start your screen recorder. On macOS: `⌘5` → Record Entire Screen →
   Options → Microphone: Built-in.

## The script

Read each act as one natural-sounding sentence. **Pause ~2 seconds between
acts** so Silero VAD finalizes each utterance into its own transcript.

---

### Act 1 — cheerful opening *(~10 s)*

> "Hi, thank you for calling. Um, I'm really happy to help. So let me, uh,
> pull up your account real quick."

**Expected after Act 1**

| Tile | Value |
|---|---|
| Fillers | ~3 (last: `"uh"`) |
| Prohibited | 0 |
| Sentiment | **Positive** (green) |

---

### Act 2 — frustration creeps in *(~10 s)*

> "Well, actually, I don't know why the system did that. You know, it's
> not my fault — basically, the records aren't matching."

**Expected after Act 2**

| Tile | Value |
|---|---|
| Fillers | ~6 |
| Prohibited | **2** (red, last: `"not my fault"`) |
| Sentiment | Positive or Neutral |

---

### Act 3 — dismissive meltdown *(~15 s)*

> "Honestly, I don't care what the policy says. Whatever. That's not my
> problem. You should have checked before calling. It's not my job to fix
> this."

**Expected after Act 3**

| Tile | Value |
|---|---|
| Fillers | ~6 (little change) |
| Prohibited | **~6** (last: `"not my job"`) |
| Sentiment | **Negative** (red pill) |

---

### Act 4 — recovery *(pause ~5 seconds first, then ~10 s)*

The 5-second pause lets the rolling 20-second sentiment window start aging
Act 3 out before Act 4 lands.

> "You're absolutely right — I'm happy to help you. Thank you so much for
> your patience. You're wonderful."

**Expected after Act 4**

| Tile | Value |
|---|---|
| Fillers | ~6 (no change) |
| Prohibited | 6 (no change, still red) |
| Sentiment | **Neutral** or **Positive** (recovered) |

## Final dashboard (rough target)

| Tile | Target |
|---|---|
| **Fillers** | 8-10 (last: probably `"uh"` / `"actually"`) |
| **Prohibited** | **6** (red, last: `"not my job"`) |
| **Sentiment** | **Neutral** or **Positive** |

## Recording tips

- **Don't switch tabs mid-demo.** Chrome/Safari throttle WebRTC in
  background tabs; the UI will freeze and the agent will think you
  disconnected.
- **Short pauses between acts.** 1-2 seconds lets Silero VAD trigger the
  stream flush so each act becomes its own final transcript.
- **Fuzzy matcher has your back.** If Whisper mis-hears `"i don't know"`
  as `"i dont know"` or `"I don know"`, `rapidfuzz.partial_ratio ≥ 88`
  still fires the prohibited detector.
- **Want a longer demo?** Repeat each act, or improvise customer-service
  dialogue between them. Watch the Fillers subtitle update live.

## Troubleshooting during recording

| Symptom | Likely cause |
|---|---|
| Nothing appears for >6 s | Tab not focused, or the agent hasn't printed `agent ready` yet |
| Transcripts stop mid-session | Tab went to background, or the LiveKit WS dropped (DevTools → Network → WS) |
| Sentiment stays Neutral throughout | Rolling 20 s window still averaging out the negatives — add a longer Act 3 |
| Prohibited doesn't trip | Whisper transcribed something different; check agent log for the actual transcribed text |
