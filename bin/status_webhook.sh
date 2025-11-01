#!/usr/bin/env bash
PID="/workspace/data/logs/webhook_pull.pid"
LOG="/workspace/data/logs/webhook_pull.log"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "✅ webhook running, PID=$(cat "$PID")"
else
  echo "webhook not running"
fi
echo "== TAIL LOG =="
tail -n 50 "$LOG" 2>/dev/null || true
