#!/usr/bin/env bash
set -euo pipefail
PID="/workspace/data/logs/webhook_pull.pid"
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
fi
echo "✅ webhook stopped"
