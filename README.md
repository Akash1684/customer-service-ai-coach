# Customer Service AI Coach

> A fully local, browser-based, real-time practice tool for customer service reps.
> Current build: `main` — Steps 1, 2, 3, and 5 shipped. Ollama/LLM work (Step 8) deferred out of P0.

Speak into your microphone and receive **live coaching feedback** as you talk: a rolling transcript plus four real-time metric tiles (filler words, pacing WPM, prohibited-phrase hits, sentiment) — all running on your laptop. No cloud calls, no accounts, no data leaves your machine.

![status badge](https://img.shields.io/badge/status-active%20development-yellow)

## What works today

| Capability | Status |
|---|---|
| Browser mic → local LiveKit room → Python agent | ✅ |
| In-process `faster-whisper` STT (`base.en`, int8) | ✅ |
| Silero-VAD-driven finalization (no custom turn detection) | ✅ |
| Live partial + final transcripts on the UI | ✅ |
| Filler / Pacing / Prohibited / Sentiment detectors | ✅ |
| MetricsBar UI (four live tiles) | ✅ |
| Whisper-hallucination guard | ✅ |
| Start/Stop session lifecycle + script library | ⏭ Step 4 |
| In-session settings UI (thresholds, phrase list) | ⏭ Step 7 |
| LLM-generated nudges (Ollama) | ⏭ Step 8 (out of P0) |
| Markdown session report | ⏭ Step 9 |
| Dead-air detection + endpoint polish | ⏭ Step 6 / 10 |

See [`docs/AS-BUILT.md`](./docs/AS-BUILT.md) for the **implemented** architecture (what's actually in the code), and [`docs/planning/`](./docs/planning/) for the original planning record (rough idea → Q&A → research → design → plan).

## Prerequisites

| Tool | Purpose |
|---|---|
| Python ≥ 3.10 | Agent runtime |
| Node ≥ 20 | UI build (Vite) |
| `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/)) | Fast Python package manager (fallback: `pip` + `venv`) |
| `livekit-server` ([install](https://docs.livekit.io/home/self-hosting/local/)) | Local WebRTC SFU |
| `lk` ([LiveKit CLI](https://docs.livekit.io/reference/developer-tools/livekit-cli/)) | Dev-token generation |

**One-time install on macOS:**

```bash
brew install livekit livekit-cli
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: pip install --user uv
```

Ollama is **not** required — P0 runs entirely without an LLM. It becomes a prerequisite when Step 8 (LLM nudges) lands.

## Install

```bash
./scripts/setup.sh
```

This installs agent deps (via `uv`, with a `pip` + `venv` fallback) and runs `npm install` for the UI. The `faster-whisper base.en` model (~140 MB) downloads lazily on first agent session into `~/.cache/huggingface/`.

## Run

You need three panes:

```bash
# Pane 1 — LiveKit SFU
livekit-server --dev

# Pane 2 — Python agent
cd agent
uv run src/coach_agent/main.py dev

# Pane 3 — UI
npm --prefix coach-ui run dev
```

Generate a dev token once (long-lived, 30 days) and drop it in `coach-ui/.env.local`:

```bash
lk token create \
  --api-key devkey --api-secret secret \
  --join --room coach-room --identity rep-local \
  --valid-for 720h --token-only
```

```
# coach-ui/.env.local
VITE_LIVEKIT_URL=ws://127.0.0.1:7880
VITE_LIVEKIT_TOKEN=<paste jwt here>
VITE_LIVEKIT_ROOM=coach-room
```

Visit <http://localhost:5173>, grant mic permission, and start talking.

## Layout

```
customer-service-ai-coach/
├── agent/                              # Python agent (LiveKit Agents SDK)
│   ├── pyproject.toml
│   ├── src/coach_agent/
│   │   ├── main.py                     # Entry point, CoachAgent subclass
│   │   ├── config.py                   # CoachSettings (defaults)
│   │   ├── stt/local_whisper.py        # In-process faster-whisper STT
│   │   ├── detectors/                  # filler · pacing · prohibited · sentiment
│   │   ├── pipeline/metrics.py         # MetricsSnapshotBuilder (rate-limited)
│   │   └── transport/liveness.py       # Agent heartbeat (debug channel)
│   └── tests/                          # 57 unit tests, 2 manual E2E scripts
├── coach-ui/                           # React + Vite frontend
│   └── src/
│       ├── App.tsx                     # Mount LiveKitRoom + panes
│       ├── TranscriptPane.tsx          # Live partial + final transcripts
│       ├── MetricsBar.tsx              # Four-tile live metrics
│       └── DebugPane.tsx               # Agent heartbeat (debug)
├── scripts/                            # setup.sh, start.sh
├── docs/
│   ├── AS-BUILT.md                     # Current architecture (what shipped)
│   └── planning/                       # PDD planning record (historical)
├── Makefile                            # make test = Python + TS tests
└── README.md
```

## Tests

```bash
make test            # Python (57) + TypeScript (42)
make test-agent      # Python only
make test-ui         # TypeScript only
```

Manual end-to-end (publishes a WAV + listens for transcripts on the same LiveKit session):

```bash
cd agent
uv run tests/e2e_speaker_listener.py /path/to/sample.wav
```

## Where to look next

- [`docs/AS-BUILT.md`](./docs/AS-BUILT.md) — implemented architecture, data flows, and key deviations from the original plan.
- [`docs/planning/design/detailed-design.md`](./docs/planning/design/detailed-design.md) — original design doc (historical; some sections superseded by AS-BUILT).
- [`docs/planning/implementation/plan.md`](./docs/planning/implementation/plan.md) — the 10-step plan with a progress checklist at the top.

## License

MIT — see [`LICENSE`](./LICENSE).
