#!/usr/bin/env bash
set -euo pipefail
LOG="/workspace/data/logs/git_sync.log"
PID="/workspace/data/logs/git_sync.pid"
INTERVAL="${1:-120}"   # ثواني (افتراضي 120s)

# إن كان شغال لا تكرّر
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "git-sync already running with PID $(cat "$PID")"; exit 0
fi

setsid nohup bash -c '
  while true; do
    /workspace/data/bin/git_sync.sh >> "'"$LOG"'" 2>&1 || true
    sleep '"$INTERVAL"'
  done
' </dev/null >/dev/null 2>&1 &

echo $! > "$PID"
echo "✅ git-sync started. PID=$(cat "$PID"); LOG=$LOG"
