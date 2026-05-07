#!/usr/bin/env bash
# Start — print instructions to run the three local services.
#
# The three services you need:
#   1. livekit-server --dev    (WebRTC SFU, ws://127.0.0.1:7880)
#   2. Python agent            (STT + detectors)
#   3. Vite dev server         (UI at http://localhost:5173)

set -euo pipefail

say() { printf "\033[1;36m%s\033[0m\n" "$*"; }
dim() { printf "\033[2m%s\033[0m\n" "$*"; }

say "Customer Service AI Coach — local run checklist"
echo

say "Prereqs:"
dim "  brew install livekit livekit-cli"
dim "  curl -LsSf https://astral.sh/uv/install.sh | sh"
dim "  (Ollama is NOT required for the current build — Step 8 work only.)"
echo

say "Three-pane setup:"
echo "  Pane 1:   livekit-server --dev"
dim "            (LiveKit WebRTC server on ws://127.0.0.1:7880)"
echo
echo "  Pane 2:   cd agent && uv run src/coach_agent/main.py dev"
dim "            (Python agent — loads faster-whisper base.en lazily on first session)"
echo
echo "  Pane 3:   npm --prefix coach-ui run dev"
dim "            (UI at http://localhost:5173 — needs coach-ui/.env.local with a dev token)"
echo

say "Dev token (once, valid 30 days):"
dim "  lk token create --api-key devkey --api-secret secret \\"
dim "      --join --room coach-room --identity rep-local \\"
dim "      --valid-for 720h --token-only"
echo
dim "Drop the JWT into coach-ui/.env.local under VITE_LIVEKIT_TOKEN."
echo

say "Open http://localhost:5173, grant mic, start speaking."
