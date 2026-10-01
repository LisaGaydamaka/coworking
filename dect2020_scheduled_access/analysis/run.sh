#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export MPLBACKEND=Agg
python3 -m pip install --quiet --disable-pip-version-check numpy matplotlib

RUN_MODE="$(cat .run 2>/dev/null || true)"
if [[ "$RUN_MODE" == phase6-variability-figure* ]]; then
  python3 phase6_service_variability.py
elif [[ "$RUN_MODE" == phase5-tail-figure* ]]; then
  python3 phase5_tail_latency.py
else
  python3 phase4_dimensioning.py
fi
