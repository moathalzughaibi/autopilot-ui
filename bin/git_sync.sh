#!/usr/bin/env bash
set -euo pipefail
cd /workspace/data
# اسحب آخر تغييرات مع حفظ تعديلاتك تلقائياً
git pull --rebase --autostash --allow-unrelated-histories || true
# ادفع أي تغييرات محلية (إن وجدت)
git add -A || true
if ! git diff --cached --quiet; then
  git commit -m "Runpod auto-sync: $(date -u +%FT%TZ)"
  git push origin main || true
fi
