#!/usr/bin/env bash
PID="/workspace/data/logs/backup_daily.pid"
LOG="/workspace/data/logs/backup_daily.log"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "✅ backup-daily running, PID=$(cat "$PID")"
else
  echo "backup-daily not running"
fi
echo "== LAST 20 LINES =="
tail -n 20 "$LOG" 2>/dev/null || true
