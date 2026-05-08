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

### One-sentence version *(~15 s — fastest end-to-end proof)*

If you just need to show all three detectors firing in a single breath,
read this one sentence and stop. It exercises every detector category
without needing the 4-act structure.

> "Honestly, um, actually this is ridiculous, like, I don't know why
> this is happening, basically I don't care what the policy says, it's
> not my job, whatever, you should have checked this yourself, uh, I
> hate having to deal with this."

**Expected after this sentence** (scored against VADER, compound ≈ −0.52):

| Tile | Value |
|---|---|
| Fillers | **5** (`um`, `actually`, `like`, `basically`, `uh`) |
| Prohibited | **5** (red, last: `"you should have"`) — hits: `i don't know`, `i don't care`, `not my job`, `whatever`, `you should have` |
| Sentiment | **Negative** (red pill) |

> **Why the extra `"ridiculous"` / `"hate"`?** VADER measures word-level
> valence, not stance. Phrases like `"not my fault"` and `"that's not my
> problem"` actually score *positive* in VADER (the `not` negates `fault`
> / `problem`). The demo needs genuinely negative words — `"ridiculous"`,
> `"hate"`, `"frustrating"` — to land the Sentiment tile in Negative.

If you want a longer demo that also shows **sentiment flipping back to
Positive over time**, use the four-act version below instead.

---

### Four-act version *(~60 s — fuller demo with sentiment recovery)*

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

> "Honestly this is ridiculous. I don't care what the policy says.
> Whatever. That's not my problem. You should have checked before
> calling. It's not my job. I hate these pointless excuses."

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
| Sentiment stays Neutral throughout | Dismissive prohibited phrases (`"not my fault"`, `"whatever"`, etc.) are lexically Neutral or even Positive to VADER. You need explicit negative words like `"ridiculous"`, `"hate"`, `"frustrating"`, `"awful"` — the revised script includes these |
| Prohibited doesn't trip | Whisper transcribed something different; check agent log for the actual transcribed text |
