#!/usr/bin/env bash
# Start all three local services in the background with logs in .run/.
#
# Processes are owned by your shell. Stop them with:
#   ./scripts/stop.sh
#
# Tail any log live:
#   tail -f .run/agent.log
#   tail -f .run/livekit.log
#   tail -f .run/ui.log

set -euo pipefail

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/.."
cd "$ROOT_DIR"

mkdir -p .run
rm -f .run/*.log .run/*.pid

say() { printf "\033[1;36m%s\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m%s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33m%s\033[0m\n" "$*"; }

# 1. LiveKit SFU
if lsof -i :7880 -sTCP:LISTEN >/dev/null 2>&1; then
  warn "livekit-server already on 7880 — leaving it alone"
else
  (nohup livekit-server --dev </dev/null >.run/livekit.log 2>&1 &
   echo $! > .run/livekit.pid
   disown) 2>/dev/null
  for i in {1..30}; do
    lsof -i :7880 -sTCP:LISTEN >/dev/null 2>&1 && break
    sleep 0.3
  done
  ok "✅ livekit on 7880"
fi

# 2. Python agent
(cd agent && nohup uv run src/coach_agent/main.py dev </dev/null >../.run/agent.log 2>&1 &
 echo $! > ../.run/agent.pid
 disown) 2>/dev/null
say "⏳ agent starting (pid=$(cat .run/agent.pid))..."

# 3. Vite UI
(nohup npm --prefix coach-ui run dev </dev/null >.run/ui.log 2>&1 &
 echo $! > .run/ui.pid
 disown) 2>/dev/null
for i in {1..40}; do
  lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1 && { ok "✅ ui on 5173"; break; }
  sleep 0.5
done

# Wait for the agent's LiveKit worker registration
for i in {1..40}; do
  grep -q "registered worker" .run/agent.log 2>/dev/null && { ok "✅ agent worker registered"; break; }
  sleep 0.5
done

echo
say "Open:   http://localhost:5173"
say "Tail:   tail -f .run/agent.log"
say "Stop:   ./scripts/stop.sh"
