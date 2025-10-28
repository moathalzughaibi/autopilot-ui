#!/usr/bin/env bash
set -euo pipefail
PID="/workspace/data/logs/inbox.pid"
LOG="/workspace/data/logs/inbox.log"
INBOX="/mnt/data/inbox"
echo "Starting inbox watcher..."
setsid nohup bash -c '
  while true; do
    for f in "$INBOX"/*.task.json; do
      [ -e "$f" ] || { sleep 10; continue; }
      python - <<PY
from inbox_runner import apply_task, _log
import os, shutil
ok = apply_task("$f")
dst = "$INBOX"/"done"/(os.path.basename("$f").replace(".task.json",".done.json") if ok else os.path.basename("$f").replace(".task.json",".fail.json"))
shutil.move("$f", dst)
_log(f"MOVED: $f -> {dst}")
PY
    done
    sleep 10
  done
' >> "$LOG" 2>&1 &
echo $! > "$PID"
echo "✅ inbox watcher started. PID=$(cat "$PID"); LOG=$LOG"
