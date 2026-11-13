#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export MPLBACKEND=Agg
python3 -m pip install --quiet --disable-pip-version-check numpy matplotlib

RUN_MODE="$(cat .run 2>/dev/null || true)"
if [[ "$RUN_MODE" == revision-relayout-all* ]]; then
  export OPENBLAS_NUM_THREADS=1
  # Regenerate already-measured plots without changing OMNeT++ data or LaTeX.
  python3 revision_validation.py
  python3 revision_final_analysis.py
  python3 revision_corrected_figures.py
elif [[ "$RUN_MODE" == revision-corrected-figures* ]]; then
  export OPENBLAS_NUM_THREADS=1
  python3 revision_corrected_figures.py
elif [[ "$RUN_MODE" == revision-final-publication* ]]; then
  export OPENBLAS_NUM_THREADS=1
  python3 revision_final_analysis.py
elif [[ "$RUN_MODE" == revision-analytics* ]]; then
  export OPENBLAS_NUM_THREADS=1
  python3 revision_validation.py
elif [[ "$RUN_MODE" == phase6-variability-figure* ]]; then
  python3 phase6_service_variability.py
elif [[ "$RUN_MODE" == phase5-tail-figure* ]]; then
  python3 phase5_tail_latency.py
else
  python3 phase4_dimensioning.py
fi
