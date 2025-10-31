#!/usr/bin/env bash
set -euo pipefail
LOG="/workspace/data/logs/notion_watcher.log"
PID="/workspace/data/logs/notion_watcher.pid"
INTERVAL="${1:-120}"   # seconds (default 120)

if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "notion-watcher already running with PID $(cat "$PID")"; exit 0
fi

setsid nohup bash -lc '
  source /workspace/data/.venv/bin/activate || true
  while true; do
    SR=$(ls -1t /workspace/data/Session_Report_*.md 2>/dev/null | head -n 1)
    if [ -n "$SR" ]; then
      python /workspace/data/bin/notion_push.py --push-session "$SR" >> "'"$LOG"'" 2>&1 || true
    fi
    python /workspace/data/bin/notion_push.py --scan-logs >> "'"$LOG"'" 2>&1 || true
    sleep '"$INTERVAL"'
  done
' </dev/null >/dev/null 2>&1 &

echo $! > "$PID"
echo "✅ notion-watcher started. PID=$(cat "$PID"); LOG=$LOG"
