# Research: LiveKit Minimal Local Setup

**Scope:** Determine the leanest working local setup — LiveKit server + Python agent + React frontend — satisfying our "local-only, minimal, fully open-source, no cloud" constraints.

**Date:** 2026-05-07

---

## 1. What we need running locally

| Component | Role |
|-----------|------|
| **LiveKit server** | WebRTC SFU: terminates browser WebRTC, forwards audio track to the agent. |
| **Python agent** | Connects to the LiveKit server, consumes the rep's audio track, runs STT + detectors + LLM, publishes nudges/metrics back to the room. |
| **React (Vite) frontend** | Browser UI. Publishes mic audio, subscribes to data packets from the agent, renders script + nudges + metrics + download button. |
| **Local STT service** | `faster-whisper` exposed via an OpenAI-compatible HTTP shim (bound to `127.0.0.1`). |
| **Local LLM service** | **Ollama** (`ollama serve`) with a small instruct model. |
| **Local embedding model** | For prohibited-phrase semantic match; can run in-process via `sentence-transformers` in the agent, no separate service needed. |

No external cloud services are called for P0. Every process binds to `localhost`.

---

## 2. LiveKit server: `livekit-server --dev`

LiveKit ships a **dev mode** that is explicitly designed for local development. Per the official "Running LiveKit locally" guide (<https://docs.livekit.io/home/self-hosting/local/>):

```bash
# macOS
brew update && brew install livekit

# Linux
curl -sSL https://get.livekit.io | bash

# Start in dev mode
livekit-server --dev
```

Dev mode pre-bakes a known API key pair:

- `API key:   devkey`
- `API secret: secret`

It binds the signal server to `127.0.0.1:7880` by default (add `--bind 0.0.0.0` only if we need LAN access from another device; for our P0 `127.0.0.1` is fine).

### Why not Docker for LiveKit server?

`ShayneP/local-voice-ai` and many production templates use Docker Compose. For our **minimal testing** goal a native `livekit-server --dev` binary is simpler — single process, easy logs, no Docker dependency, and LiveKit itself recommends this for local dev. We can always containerize later.

---

## 3. Python agent: LiveKit CLI starter or hand-rolled

Two viable starting points:

### Option A: `lk agent init` with the Python starter template

From the Voice AI quickstart:

```bash
# Install LiveKit CLI
brew install livekit-cli        # macOS
# curl -sSL https://get.livekit.io/cli | bash   # Linux

lk agent init my-agent --template agent-starter-python
cd my-agent
uv sync
uv run src/agent.py download-files   # Silero VAD + turn detector
uv run src/agent.py dev
```

This produces a ready-to-run agent scaffold using `uv`. It's optimized for **LiveKit Cloud** (assumes `LIVEKIT_URL=wss://...livekit.cloud`) but we override via `.env.local`:

```
LIVEKIT_URL=ws://127.0.0.1:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

We then strip out the TTS / LLM / noise-cancellation plugins that target LiveKit Inference and replace with our local stack.

### Option B: Start from scratch with `livekit-agents`

Equivalent dependencies; gives us full control without stripping the template:

```bash
uv init customer-service-ai-coach-agent
uv add "livekit-agents[silero]" python-dotenv faster-whisper sentence-transformers httpx
```

**Recommendation:** **Option A** — the starter includes a useful project structure (`src/agent.py`, `.env.local`, `agent.py download-files` hook), and we just swap plugins. Saves setup time.

### Minimal Python agent skeleton (illustrative)

```python
from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, Agent, JobContext, cli
from livekit.plugins import silero, openai as oai_plugin

load_dotenv(".env.local")
server = AgentServer()

@server.rtc_session(agent_name="coach")
async def entry(ctx: JobContext):
    # Local STT via OpenAI-compatible shim around faster-whisper
    stt = oai_plugin.STT(
        base_url="http://127.0.0.1:8001/v1",
        api_key="local",
        model="Systran/faster-whisper-base.en",
        language="en",
    )

    session = AgentSession(stt=stt, vad=silero.VAD.load())

    @session.on("user_input_transcribed")
    def on_transcript(t):
        # Dispatch to tight-lane detectors (separate module)
        ...

    await session.start(
        agent=Agent(instructions="Coaching-only agent; do not speak."),
        room=ctx.room,
    )
    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(server)
```

Run with `uv run src/agent.py dev`.

---

## 4. Local STT shim

We need an OpenAI-compatible `/v1/audio/transcriptions` endpoint backed by `faster-whisper`. Open-source options:

| Project | Notes |
|---------|-------|
| **`speaches-ai/speaches`** (formerly `faster-whisper-server`) | Purpose-built OpenAI-compatible API over `faster-whisper`; supports streaming. Active. |
| **`ahmetoner/whisper-asr-webservice`** | Popular but less focused on OpenAI-API compatibility for streaming. |
| **`vox-box`** (from `ShayneP/local-voice-ai`) | Works, simpler, also supports Nemotron backend. |
| **Hand-rolled FastAPI wrapper** | ~100 lines; full control. Recommended as a fallback if the above don't fit the streaming shape LiveKit wants. |

**Tentative pick for P0:** `speaches` (single container, OpenAI-compatible). To be validated in a prototype step. Details to be deepened in `research/local-asr.md`.

Run with something like:

```bash
# placeholder — exact command from upstream README
docker run --rm -p 8001:8000 fedirz/faster-whisper-server:latest-cpu
# or the speaches image
```

*Note: this is the one place where Docker may make the minimal setup easier, because building `ctranslate2` and `faster-whisper` wheels from source on every dev machine is painful. Running a single Docker container for STT keeps things self-contained without forcing a full Compose stack.*

---

## 5. Local LLM: Ollama

Ollama is the simplest path (single binary, native macOS + Linux + Windows, exposes OpenAI-compatible API at `http://localhost:11434/v1`).

```bash
# macOS
brew install ollama           # or download from ollama.com
ollama serve                  # runs the daemon

# pull a small instruct model
ollama pull qwen2.5:3b-instruct-q4_K_M   # ~2 GB, CPU-friendly
# alternatives: llama3.2:3b-instruct-q4_K_M, phi3.5:3.8b-mini-instruct-q4_K_M
```

The agent's relaxed-lane worker talks to Ollama via `openai.LLM(base_url="http://127.0.0.1:11434/v1", ...)`.

---

## 6. Frontend: React + Vite + LiveKit React SDK

Smallest-possible real frontend:

```bash
npm create vite@latest coach-ui -- --template react-ts
cd coach-ui
npm i @livekit/components-react @livekit/components-styles livekit-client
npm run dev
```

Minimal `App.tsx` connects to the local LiveKit room:

```tsx
import { LiveKitRoom, useDataChannel } from "@livekit/components-react";
import "@livekit/components-styles";

export default function App() {
  const token = /* fetched from a tiny token endpoint — see §7 */;
  return (
    <LiveKitRoom token={token} serverUrl="ws://127.0.0.1:7880" audio video={false}>
      <CoachUI />
    </LiveKitRoom>
  );
}
```

We consume nudge + metric data packets with `useDataChannel("nudges")` / `useDataChannel("metrics")` and render them. The download button serializes in-memory state to a markdown string and triggers a blob download — pure client-side, no server involvement.

---

## 7. Token generation

LiveKit clients authenticate with a JWT signed by the API key/secret. Two approaches:

| Approach | Pros | Cons |
|---------|------|------|
| **Static long-lived token** generated once with `lk token create ...` and hard-coded in the frontend **for local dev only** | No server code at all. One less thing to run. | Only acceptable in local dev; never for anything shared. |
| **Tiny Python token endpoint** (e.g., a `/api/token` route on the same agent server or a 30-line FastAPI app) that signs tokens with `livekit-api`'s `AccessToken` | Clean pattern; mirrors what we'd deploy. | One more process / endpoint. |

**Recommendation for P0:** Ship a **tiny token endpoint in the same Python process as the agent** using FastAPI + `livekit-api.AccessToken`. Maybe 25 lines. Keeps the minimum-moving-parts spirit.

---

## 8. Putting it together — the minimal runbook

In four terminals (or a tmux script):

```bash
# 1. LiveKit server
livekit-server --dev

# 2. Local STT (e.g., speaches in Docker)
docker run --rm -p 8001:8000 fedirz/faster-whisper-server:latest-cpu
# or a local Python process — tbd in local-asr.md

# 3. Ollama (daemon + model pulled once)
ollama serve

# 4. Python agent (includes token endpoint)
uv run src/agent.py dev

# 5. Frontend dev server
npm --prefix coach-ui run dev
```

Open <http://localhost:5173> → grant mic → pick a script → Start → speak. Nudges and metrics stream live.

---

## 9. Dependency footprint (actual, realistic)

| Component | Install size | First-run download | Steady-state RAM |
|---|---|---|---|
| `livekit-server` binary | ~50 MB | 0 | ~50 MB |
| Python agent + `livekit-agents[silero]` | ~400 MB site-packages | Silero VAD model ~20 MB | ~300 MB |
| `faster-whisper base.en` model | — | ~145 MB | ~500 MB during ASR |
| Embedding model (`all-MiniLM-L6-v2`) | — | ~90 MB | ~150 MB |
| Ollama daemon | ~500 MB | — | ~100 MB idle |
| Ollama model (Qwen 2.5 3B Q4_K_M) | — | ~2 GB | ~3 GB when generating |
| Node + frontend | ~250 MB `node_modules` | 0 | ~100 MB browser tab |
| **Total** | **~1.2 GB** | **~2.3 GB one-time** | **~4 GB peak during a session** |

This fits comfortably on a modern laptop with 8 GB RAM free. No GPU required.

---

## 10. Target OS

Everything above works natively on **macOS and Linux** and via WSL2 on Windows. The reference project `ShayneP/local-voice-ai` already provides macOS + Linux + Windows variants of Compose; for our simpler binary + `uv` setup, native macOS and Linux are straightforward. **Tentative P0 target: macOS (primary), Linux (secondary).** Windows via WSL2 should work but will not be explicitly tested in P0.

---

## 11. Risks and open questions

1. **faster-whisper OpenAI-compatible shim streaming behavior.** The LiveKit `openai.STT` client expects the upstream to accept streamed audio and emit partial results. Not every shim supports this cleanly. We may need to write ~100 lines of our own shim. **Action:** verify in the prototype step (Step 1 or 2 of the implementation plan).
2. **LiveKit agent dispatch model for single-user.** Agents are designed around "one agent process per room". For a single-user local app that's fine — one browser tab = one room. Multi-tab would spawn multiple agent jobs, which on a 1-CPU machine would be bad. **Action:** document as a single-session constraint in the design.
3. **CLI vs manual token generation.** The LiveKit CLI adds a small dependency; the token endpoint approach avoids it. **Decision pending** — default to the token endpoint approach.

---

## 12. References

- Running LiveKit locally — <https://docs.livekit.io/home/self-hosting/local/>
- Self-host overview — <https://docs.livekit.io/transport/self-hosting/>
- Voice AI quickstart — <https://docs.livekit.io/agents/start/voice-ai/>
- Python agent starter — <https://github.com/livekit-examples/agent-starter-python>
- Local reference stack (Docker Compose, heavier than what we need) — <https://github.com/ShayneP/local-voice-ai>
- `faster-whisper` — <https://github.com/SYSTRAN/faster-whisper>
- `speaches` (OpenAI-compatible `faster-whisper` server) — <https://github.com/speaches-ai/speaches>
- Ollama — <https://ollama.com>
- `@livekit/components-react` — <https://docs.livekit.io/reference/components/react/>
