#!/usr/bin/env bash
set -euo pipefail
cd /workspace/data
# تأكد أن الفرع متعقّب للـremote
git branch --set-upstream-to=origin/main main >/dev/null 2>&1 || true
git pull --rebase --autostash --allow-unrelated-histories origin main || true
git add -A || true
if ! git diff --cached --quiet; then
  git commit -m "Runpod auto-sync: $(date -u +%FT%TZ)"
  git push origin main || true
fi
