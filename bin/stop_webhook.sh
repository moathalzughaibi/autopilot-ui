#!/usr/bin/env bash
PID=/workspace/data/logs/webhook_pull.pid
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
  echo "✅ webhook stopped"
else
  echo "webhook not running"
fi
