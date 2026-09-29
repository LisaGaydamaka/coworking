#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/src"

opp_makemake -f --deep -o dect2020_sa
make -j"${JOBS:-2}"

echo "Built: $ROOT/src/dect2020_sa"
