#!/usr/bin/env bash
# Start — print instructions to run the three local services.
#
# Step 1 doesn't wire an agent to LiveKit yet, so this script keeps things
# strictly informational. Later steps will actually boot `livekit-server` and
# the agent here.

set -euo pipefail

say() { printf "\033[1;36m%s\033[0m\n" "$*"; }
dim() { printf "\033[2m%s\033[0m\n" "$*"; }

say "Customer Service AI Coach — local run checklist"
echo

say "Prereqs for Step 2+:"
dim "  brew install livekit livekit-cli ollama"
dim "  curl -LsSf https://astral.sh/uv/install.sh | sh   # (optional) faster Python installs"
echo

say "Recommended three-pane setup:"
echo "  Pane 1:   livekit-server --dev"
dim "            (LiveKit WebRTC server on ws://127.0.0.1:7880)"
echo
echo "  Pane 2:   ollama serve"
dim "            (Local LLM daemon on http://127.0.0.1:11434 — Step 8+)"
echo
echo "  Pane 3:   cd agent && uv run src/coach_agent/main.py dev"
dim "            (Python agent — lands in Step 2)"
echo
echo "  Pane 4:   npm --prefix coach-ui run dev"
dim "            (UI at http://localhost:5173)"
echo

say "Step 1 does not require panes 1–3 — only the UI."
