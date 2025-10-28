#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8891}"
APP="${2:-/workspace/data/app_dashboard.py}"
LOG="/workspace/data/logs/streamlit_${PORT}.log"
PID="/workspace/data/logs/streamlit_${PORT}.pid"
source /workspace/data/.venv/bin/activate
export PYTHONPATH=/workspace/data:$PYTHONPATH
mkdir -p /workspace/data/logs
fuser -k ${PORT}/tcp 2>/dev/null || true
: > "$LOG"
setsid nohup env STREAMLIT_SERVER_HEADLESS=true   STREAMLIT_SERVER_ENABLECORS=false   STREAMLIT_SERVER_ENABLEXSRFPROTECTION=false   STREAMLIT_SERVER_ENABLEWEBSOCKETCOMPRESSION=false   streamlit run "$APP" --server.port "$PORT" --server.address 0.0.0.0   --logger.level info >> "$LOG" 2>&1 < /dev/null &
echo $! > "$PID"
sleep 2
echo "== CHECK =="
ss -ltnp | grep ":$PORT" || echo "❌ ${PORT} not listening"
echo -n "HEALTH: "; curl -sS "http://127.0.0.1:${PORT}/_stcore/health" || true; echo
echo "LOG: $LOG"
tail -n 40 "$LOG" || true
