#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8891}"
echo "== LISTENERS =="; ss -ltnp | grep ":$PORT" || echo "no listener on $PORT"
echo -n "HEALTH: "; curl -sS "http://127.0.0.1:${PORT}/_stcore/health" || true; echo
LOG="/workspace/data/logs/streamlit_${PORT}.log"
echo "== LAST LOG ($LOG) =="; tail -n 60 "$LOG" 2>/dev/null || echo "no log"
