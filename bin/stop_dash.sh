#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8891}"
PID="/workspace/data/logs/streamlit_${PORT}.pid"
[ -f "$PID" ] && kill -9 "$(cat "$PID")" 2>/dev/null || true
fuser -k ${PORT}/tcp 2>/dev/null || true
rm -f "$PID"
echo "✅ stopped port ${PORT}"
