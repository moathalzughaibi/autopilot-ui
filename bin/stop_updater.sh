#!/usr/bin/env bash
set -euo pipefail
PID="/workspace/data/logs/updater.pid"
if [ -f "$PID" ]; then
  kill -9 "$(cat "$PID")" 2>/dev/null || true
  rm -f "$PID"
  echo "✅ updater stopped"
else
  echo "no updater pid file"
fi
