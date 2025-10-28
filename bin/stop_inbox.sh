#!/usr/bin/env bash
set -euo pipefail
PID="/workspace/data/logs/inbox.pid"
[ -f "$PID" ] && kill -9 "$(cat "$PID")" 2>/dev/null || true
rm -f "$PID"
echo "✅ inbox watcher stopped"
