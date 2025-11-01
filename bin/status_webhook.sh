#!/usr/bin/env bash
PID="/workspace/data/logs/webhook_pull.pid"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "✅ webhook running, PID=$(cat "$PID")"
  echo "== TAIL LOG =="
  tail -n 30 /workspace/data/logs/webhook_pull.log || true
else
  echo "webhook not running"
fi
