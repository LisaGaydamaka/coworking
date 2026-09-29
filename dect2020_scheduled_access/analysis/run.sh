#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export MPLBACKEND=Agg
python3 -m pip install --quiet --disable-pip-version-check numpy matplotlib
python3 phase4_dimensioning.py
