#!/usr/bin/env bash
# Stop all three local services started by scripts/start.sh.

set -euo pipefail

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/.."
cd "$ROOT_DIR"

if [[ ! -d .run ]]; then
  echo "nothing to stop (.run/ missing)"
  exit 0
fi

for f in .run/agent.pid .run/ui.pid .run/livekit.pid; do
  [[ -f "$f" ]] || continue
  pid=$(cat "$f")
  if ps -p "$pid" >/dev/null 2>&1; then
    echo "stopping $(basename "$f" .pid) pid=$pid"
    kill "$pid" 2>/dev/null || true
  fi
done

# Give them a moment, then force-kill stragglers
sleep 1
for f in .run/agent.pid .run/ui.pid .run/livekit.pid; do
  [[ -f "$f" ]] || continue
  pid=$(cat "$f")
  if ps -p "$pid" >/dev/null 2>&1; then
    echo "force-killing pid=$pid"
    kill -9 "$pid" 2>/dev/null || true
  fi
done

rm -f .run/*.pid
echo "done"
