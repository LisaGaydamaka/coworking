#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r ../enri_mouse_neuroplasticity/requirements.txt
python stage7_finegrid.py

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add stage7_new
if ! git diff --cached --quiet; then
  git commit -m "Save fine-grid Stage 7 outputs"
  git pull --rebase origin main
  git push origin HEAD:main
fi
