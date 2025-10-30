#!/usr/bin/env bash
set -euo pipefail
LOG="/workspace/data/logs/backup_daily.log"
PID="/workspace/data/logs/backup_daily.pid"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "backup-daily already running, PID=$(cat "$PID")"; exit 0
fi
setsid nohup bash -c '
  while true; do
    /workspace/data/bin/backup_now.sh >> "'"$LOG"'" 2>&1 || true
    sleep 86400
  done
' </dev/null >/dev/null 2>&1 &
echo $! > "$PID"
echo "✅ backup-daily started. PID=$(cat "$PID"); LOG=$LOG"
