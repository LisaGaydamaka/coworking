#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/simulations"

if ! command -v opp_scavetool >/dev/null 2>&1; then
  echo "opp_scavetool is not on PATH. Source the OMNeT++ environment first." >&2
  exit 1
fi

mkdir -p exported
opp_scavetool x results/*.sca \
  -f 'name =~ "mean_delay_direct_ms" OR name =~ "mean_delay_little_ms" OR name =~ "blocking_probability" OR name =~ "mean_type1_number" OR name =~ "effective_throughput_departures_per_ms" OR name =~ "rho" OR name =~ "rho_sat" OR name =~ "D" OR name =~ "r" OR name =~ "L_effective"' \
  -F CSV-R -o exported/phase2_scalars.csv

echo "Wrote simulations/exported/phase2_scalars.csv"
