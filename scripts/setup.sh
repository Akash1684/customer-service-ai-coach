#!/usr/bin/env bash
# Setup — install agent + UI dependencies.
#
# Uses `uv` if available (faster, LiveKit-starter-recommended). Falls back to
# plain venv + pip otherwise.
#
# Later steps will extend this to also fetch Whisper + Silero model weights and
# remind the user to `ollama pull <model>`. For Step 1 this is strictly about
# making the smoke tests runnable.

set -euo pipefail

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/.."
cd "$ROOT_DIR"

say() { printf "\033[1;36m%s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m%s\033[0m\n" "$*"; }

say "=== 1/2  Installing Python agent deps ==="
cd "$ROOT_DIR/agent"

if command -v uv >/dev/null 2>&1; then
  say "Using uv..."
  uv sync --extra dev
else
  warn "uv not installed — falling back to venv + pip."
  warn "(For faster installs later: curl -LsSf https://astral.sh/uv/install.sh | sh)"

  if [[ ! -d .venv ]]; then
    python3 -m venv .venv
  fi
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip >/dev/null
  pip install -e ".[dev]"
  deactivate
fi

say ""
say "=== 2/2  Installing UI deps (npm) ==="
cd "$ROOT_DIR/coach-ui"
npm install --no-audit --no-fund

say ""
say "Setup complete. Next:"
say "  make test                              # smoke tests"
say "  npm --prefix coach-ui run dev          # UI at http://localhost:5173"
