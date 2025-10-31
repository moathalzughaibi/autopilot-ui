#!/usr/bin/env bash
set -euo pipefail
LOG="/workspace/data/logs/timeline_watcher.log"
PID="/workspace/data/logs/timeline_watcher.pid"
INTERVAL="${1:-21600}" # 6 ساعات = 21600 ثانية

# إن كان شغّال لا تكرر
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "timeline-watcher already running with PID $(cat "$PID")"; exit 0
fi

setsid nohup bash -c '
  while true; do
    /workspace/data/bin/run_timeline_once.sh >> "'"$LOG"'" 2>&1 || true
    sleep '"$INTERVAL"'
  done
' </dev/null >/dev/null 2>&1 &

echo $! > "$PID"
echo "✅ timeline-watcher started. PID=$(cat "$PID"); LOG=$LOG"
