#!/usr/bin/env bash
# Start all three local services in the background with logs in .run/.
# Stop them with: ./scripts/stop.sh
#
# No `set -e` — we want a single bad step to NOT take down the whole
# script. Each step reports its own success or failure.

ROOT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/.."
cd "$ROOT_DIR" || { echo "❌ can't cd to $ROOT_DIR"; exit 1; }

mkdir -p .run
rm -f .run/*.log .run/*.pid

say() { printf "\033[1;36m%s\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m%s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33m%s\033[0m\n" "$*"; }
err() { printf "\033[1;31m%s\033[0m\n" "$*"; }

# -------- 1. LiveKit SFU --------
if lsof -i :7880 -sTCP:LISTEN >/dev/null 2>&1; then
  warn "livekit-server already on 7880 — leaving it alone"
else
  nohup livekit-server --dev </dev/null >.run/livekit.log 2>&1 &
  LK_PID=$!
  echo "$LK_PID" > .run/livekit.pid
  disown "$LK_PID" 2>/dev/null
  for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
    lsof -i :7880 -sTCP:LISTEN >/dev/null 2>&1 && break
    sleep 0.3
  done
  if lsof -i :7880 -sTCP:LISTEN >/dev/null 2>&1; then
    ok "✅ livekit on 7880 (pid $LK_PID)"
  else
    err "❌ livekit failed to bind 7880; see .run/livekit.log"
    tail .run/livekit.log | sed 's/^/  /'
    exit 1
  fi
fi

# -------- 2. Python agent --------
# Background from the current shell (not a subshell) so PID capture is reliable.
pushd agent >/dev/null || { err "❌ can't cd agent"; exit 1; }
nohup uv run src/coach_agent/main.py dev </dev/null >../.run/agent.log 2>&1 &
AGENT_PID=$!
popd >/dev/null
echo "$AGENT_PID" > .run/agent.pid
disown "$AGENT_PID" 2>/dev/null
say "⏳ agent starting (pid=$AGENT_PID) — tail .run/agent.log to watch"

# -------- 3. Vite UI --------
nohup npm --prefix coach-ui run dev </dev/null >.run/ui.log 2>&1 &
UI_PID=$!
echo "$UI_PID" > .run/ui.pid
disown "$UI_PID" 2>/dev/null
say "⏳ ui starting (pid=$UI_PID)"

# -------- Wait for readiness --------
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40; do
  lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1 && { ok "✅ ui on 5173"; break; }
  sleep 0.5
done
if ! lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1; then
  err "❌ ui did not bind 5173; last 10 lines of .run/ui.log:"
  tail .run/ui.log 2>/dev/null | sed 's/^/  /'
fi

for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40; do
  grep -q "registered worker" .run/agent.log 2>/dev/null && { ok "✅ agent worker registered"; break; }
  # Bail early if the process died
  if ! ps -p "$AGENT_PID" >/dev/null 2>&1; then
    err "❌ agent process exited; last 20 lines of .run/agent.log:"
    tail -20 .run/agent.log 2>/dev/null | sed 's/^/  /'
    break
  fi
  sleep 0.5
done

echo
say "Open:  http://localhost:5173"
say "Logs:  tail -f .run/{agent,livekit,ui}.log"
say "Stop:  ./scripts/stop.sh"
