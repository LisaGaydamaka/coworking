#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export MPLBACKEND=Agg
python3 - <<'PY'
try:
    import numpy  # noqa: F401
    import matplotlib  # noqa: F401
except Exception:
    raise SystemExit(1)
PY
python3 phase4_dimensioning.py
