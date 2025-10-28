#!/usr/bin/env bash
PID="/workspace/data/logs/inbox.pid"
if [ -f "$PID" ] && ps -p "$(cat "$PID")" >/dev/null 2>&1; then
  echo "✅ inbox watcher running, PID=$(cat "$PID")"
else
  echo "❌ inbox watcher not running"
fi
echo "== LAST 20 LOG =="
tail -n 20 /workspace/data/logs/inbox.log 2>/dev/null || true
