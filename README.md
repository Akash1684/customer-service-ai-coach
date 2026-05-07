# Customer Service AI Coach

> A fully local, browser-based, real-time practice tool for customer service reps.
> v0.1.0 (P0) — Step 1 scaffold.

Pick a prepared script, click Start, read the rep turns aloud, and receive live coaching feedback (filler words, pacing, dead air, prohibited phrases, sentiment) plus LLM-generated supportive-coach nudges and a downloadable narrative summary — all running locally on your laptop. No cloud, no accounts, no data leaves your machine.

## Status

This is **Step 1** of a 10-step implementation plan. The scaffolding is in place; no real-time audio, STT, or LLM features yet. See [`docs/planning/implementation/plan.md`](./docs/planning/implementation/plan.md) for the full plan and [`docs/planning/design/detailed-design.md`](./docs/planning/design/detailed-design.md) for the design.

## Prerequisites

| Tool | Used in | Required for Step 1? |
|---|---|:---:|
| Python ≥ 3.10 | Agent | ✅ |
| Node ≥ 20 | Frontend | ✅ |
| `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/)) | Python package manager for the agent | Recommended — plain `pip` + `venv` also works |
| `livekit-server` ([install](https://docs.livekit.io/home/self-hosting/local/)) | Local WebRTC SFU | Step 2+ |
| `lk` ([LiveKit CLI](https://docs.livekit.io/reference/developer-tools/livekit-cli/)) | Dev-token generation | Step 2+ |
| Ollama ([install](https://ollama.com)) | Local LLM | Step 8+ |

**Install the post-Step-1 tools (macOS):**

```bash
brew install livekit livekit-cli ollama
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: pip install --user uv
```

## Layout

```
customer-service-ai-coach/
├── agent/                  # Python agent (LiveKit Agents SDK)
│   ├── pyproject.toml
│   ├── src/coach_agent/    # Source package
│   └── tests/              # pytest
├── coach-ui/               # React + Vite frontend
│   ├── package.json
│   └── src/
├── scripts/
│   ├── setup.sh            # Install deps (Python + Node)
│   └── start.sh            # Print run instructions for LiveKit + agent + UI
├── docs/planning/          # PDD planning artifacts (rough idea, Q&A, research, design, plan)
├── Makefile                # `make test` runs Python + TS smoke tests
└── README.md
```

## Install

```bash
./scripts/setup.sh
```

This installs agent deps (via `uv` if available, else `pip` + `venv`) and runs `npm install` for the UI. It does not pull the Whisper / Ollama / Silero models — those arrive in later steps.

## Run (Step 1 smoke check)

```bash
make test                            # runs Python + TS smoke tests
npm --prefix coach-ui run dev        # serves the bare UI at http://localhost:5173
```

Visit <http://localhost:5173> → you should see a page titled *"Customer Service AI Coach — v0"*. That's the entirety of the Step 1 deliverable. Real-time audio + STT + UI wire-up arrives in Step 2 and beyond.

## Where to look next

- [Design](./docs/planning/design/detailed-design.md) — single source of truth for behavior, components, data models, errors, testing.
- [Implementation plan](./docs/planning/implementation/plan.md) — 10 incremental, demoable steps.
- [Research notes](./docs/planning/research/) — six deep-dive docs (LiveKit Agents SDK, local ASR, local LLM, detectors, frontend, minimal setup).

## License

MIT — see [`LICENSE`](./LICENSE).
