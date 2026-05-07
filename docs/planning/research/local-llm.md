# Research: Local LLM — Ollama for the relaxed coaching lane

**Scope:** Model choice, prompting patterns, and runtime integration for the **relaxed-lane LLM** that generates supportive-coach nudges and the end-of-session narrative summary, running entirely on CPU via Ollama.

**Date:** 2026-05-07

---

## 1. Why Ollama

- **Single native binary** — install + `ollama serve`, no Docker required.
- **OpenAI-compatible endpoint** at `http://127.0.0.1:11434/v1`, which the LiveKit `openai` plugin explicitly supports. See plugin docs: <https://docs.livekit.io/python/livekit/plugins/openai/index.html>.
- **Automatic model pulling and caching** (`ollama pull ...`).
- **Active model library** of quantized instruct models that fit on CPU.

Alternative (rejected): `llama.cpp`'s `llama-server` exposes an equivalent OpenAI-compatible API (used by `ShayneP/local-voice-ai`), but requires the user to manage model files directly. Ollama is friendlier for first-run.

---

## 2. Model pick for P0

Constraints:

- CPU-only consumer laptop
- Must generate a **1–2 sentence nudge** in ~1–3 s wall clock (non-blocking, relaxed lane)
- Must generate a **~200–400 word markdown summary** at end-of-session in ~5–15 s (acceptable, not on critical path)
- Small disk/RAM footprint preferred

Candidates:

| Model | Params | Quant | Disk | CPU tokens/sec (approx) | Quality for short coaching prose |
|---|---|---|---|---|---|
| `qwen2.5:1.5b-instruct-q4_K_M` | 1.5 B | Q4_K_M | ~1.1 GB | ~25–40 | Decent, can be terse |
| **`qwen2.5:3b-instruct-q4_K_M`** | 3 B | Q4_K_M | ~2 GB | ~12–20 | **Good balance — P0 default** |
| `llama3.2:3b-instruct-q4_K_M` | 3 B | Q4_K_M | ~2 GB | ~12–18 | Comparable to Qwen; pick based on tone |
| `phi3.5:3.8b-mini-instruct-q4_K_M` | 3.8 B | Q4_K_M | ~2.3 GB | ~10–15 | Strong reasoning for its size |
| `qwen2.5:7b-instruct-q4_K_M` | 7 B | Q4_K_M | ~4.5 GB | ~5–8 | Better prose but too slow for near-realtime nudges |

**P0 default: `qwen2.5:3b-instruct-q4_K_M`.**
Reasoning: best speed/quality tradeoff at 3 B on CPU; Qwen 2.5 Instruct handles short, structured outputs well. Easy swap to Llama 3.2 or Phi-3.5 mini via env var.

Config envelope:

```python
# agent-side, relaxed lane
from livekit.plugins import openai

coach_llm = openai.LLM(
    base_url="http://127.0.0.1:11434/v1",
    api_key="ollama",                      # ignored by Ollama
    model="qwen2.5:3b-instruct-q4_K_M",
    temperature=0.4,
    # Ollama-specific keep-alive via request options (optional)
)
```

Generation parameters:
- `temperature=0.4` — enough variation to feel human, not unpredictable
- `max_tokens` bounded per call (~80 for nudges, ~600 for summary)

---

## 3. Prompt design — nudges

### System prompt (shared across nudge calls)

```
You are a supportive, concise customer-service coach listening to a rep practice
a scripted call. You give ONE short message (1–2 sentences, under 35 words).

Rules:
- Always encouraging, never scolding.
- Reference the specific event given (filler word, dead air, pacing, prohibited
  phrase, sentiment dip). Name what happened; suggest a concrete adjustment.
- Do not greet, do not preamble, do not close with a sign-off. Just the tip.
- Do not invent events that weren't given. If no salient event, acknowledge
  one positive signal (good pacing, clear articulation, etc.).
- Plain prose. No bullet points. No quotes around the rep's words.
```

### User prompt template (per nudge call)

Populated from detector state. Two shapes:

**Event-triggered:**

```
Event: filler_word
Detected: the rep said "um" twice in the last 10 seconds.
Current pacing: 175 words per minute (normal range 120–160).
Dead air events so far: 0.
Prohibited-phrase hits so far: 0.
Sentiment (last window): neutral.

Write the tip.
```

**Periodic sweep (no single dominating event):**

```
Event: periodic_sweep
Last 15 seconds of transcript:
"""
So I understand you're having trouble with your account. Let me uh pull that up
for you. Okay so I'm seeing here that your plan was changed last month.
"""
Metrics: fillers total 3, WPM avg 148, dead air events 1, prohibited hits 0,
sentiment neutral.

Write the tip.
```

### Why structured inputs over raw transcripts

The tight lane has *already* done the work of detecting what's noteworthy. Handing the LLM the structured event + minimal context prevents hallucinated detections and lets a 3B model perform reliably. This is the same pattern as `ShayneP/local-voice-ai` uses for routing decisions.

### Expected output

- 1–2 sentences, 15–35 words, plain prose
- Example: `"You said 'um' twice — slowing your pace from 175 WPM down to ~140 usually gives you room to breathe. Try a deliberate pause instead of a filler next time."`

---

## 4. Prompt design — end-of-session summary

### Flow

1. On `stop_session`, the agent collects:
   - Full transcript
   - All events with timestamps
   - Aggregated metrics (totals, averages)
   - All nudges produced during the session
2. Agent calls Ollama with a single "summary" prompt, `max_tokens ~600`.
3. Markdown output is combined with the raw data and offered to the UI as a download.

### System prompt

```
You are a supportive customer-service coach writing a short post-practice
feedback report in Markdown. The report must follow this exact structure:

# Session summary
<2–3 sentences of overall impression>

## Highlights
- <bullet, what went well, keyed to specific metrics>
- <bullet>
- <bullet>

## Top improvement areas
1. <area>: <what to do next time, 1–2 sentences>
2. <area>: <...>
3. <area>: <...>

## Next practice session
<One suggestion for what to focus on>

Rules:
- Ground every claim in the metrics you are given. Never invent numbers.
- Tone: warm, specific, forward-looking. No pep talk clichés.
```

### User prompt template

```
Session duration: {duration}
Script: {script_title}

Metrics:
- Total filler words: {filler_total}  (breakdown: {filler_breakdown})
- Average pacing: {wpm_avg} WPM  (target 120–160)
- Dead air events: {dead_air_count}, total silent time: {dead_air_seconds}s
- Prohibited-phrase hits: {prohibited_count}  (phrases: {prohibited_list})
- Sentiment profile: {sentiment_profile}

Top 3 events by impact:
1. {event_1}
2. {event_2}
3. {event_3}

Write the report.
```

---

## 5. Runtime integration

### Relaxed-lane worker

Detectors emit events on an internal `asyncio.Queue`. A single worker task consumes this queue, bounded concurrency = 1. It:

1. Decides whether this event warrants a nudge (rate-limiting: no more than 1 nudge per ~5 s, plus one periodic sweep every ~12 s).
2. Builds the prompt from detector state.
3. Calls `coach_llm.chat(...)` and awaits the response.
4. Publishes the nudge to the LiveKit room as a data packet on channel `nudges`.

### Why bounded concurrency

A 3B model on CPU generating at ~15 tokens/s means an 80-token nudge takes ~5 s. If we allowed parallel generations we would queue up stale nudges that arrive seconds after they're relevant. One-at-a-time keeps nudges fresh; stale events are coalesced into the next periodic sweep.

### Keep-alive

Ollama unloads models from RAM after an idle period. We set keep-alive to session-duration by sending a warmup request on `start_session` and periodically during idle gaps:

```python
# warm the model on start
await coach_llm.chat([{"role": "user", "content": "ok"}], max_tokens=1)
```

---

## 6. Failure modes

- **Ollama not running** at session start → tight lane works normally; relaxed lane logs the error and the UI shows a small banner: `"Live coaching tips are unavailable (LLM offline). Metrics and transcript still work."` Deterministic fallback: the agent can still send *event headlines* (e.g., `"Filler: 'um'"`) to the `nudges` channel so the UI stream isn't empty.
- **Model too slow on this hardware** → the rate-limit naturally absorbs slowness. We log per-call latency so the user can see if they should switch to a smaller model.
- **LLM produces malformed output** (e.g., preamble, sign-off) → system prompt is strict; we also run a light post-processor that strips leading/trailing meta-text and truncates to ~35 words for nudges.

---

## 7. Security / privacy note

All calls are `127.0.0.1` → `127.0.0.1`. No audio, transcript, or metric data leaves the machine. The downloadable report is generated locally and delivered to the browser only.

---

## 8. References

- Ollama — <https://ollama.com> · <https://github.com/ollama/ollama>
- Ollama OpenAI-compatibility — <https://ollama.com/blog/openai-compatibility>
- Qwen 2.5 Instruct — <https://huggingface.co/Qwen/Qwen2.5-3B-Instruct>
- Llama 3.2 Instruct — <https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct>
- Phi-3.5 mini — <https://huggingface.co/microsoft/Phi-3.5-mini-instruct>
- LiveKit `openai` plugin (Ollama-compatible) — <https://docs.livekit.io/python/livekit/plugins/openai/index.html>
