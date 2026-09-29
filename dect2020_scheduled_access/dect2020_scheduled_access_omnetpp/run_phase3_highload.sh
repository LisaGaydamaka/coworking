#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="$ROOT/src/dect2020_sa"
INI="$ROOT/simulations/omnetpp.ini"
NED="$ROOT/src"

if [[ ! -x "$BIN" ]]; then
  echo "Executable not found. Run: bash $ROOT/build.sh" >&2
  exit 1
fi

cd "$ROOT/simulations"
rm -rf results_phase3
mkdir -p results_phase3

configs=(
  Phase3_D6
  Phase3_D10
  Phase3_D20
  Phase3_CorR
  Phase3_CorL1
  Phase3_CorL2
  Phase3_CorL3
  Phase3_CorL4
)

for cfg in "${configs[@]}"; do
  echo "=== $cfg ==="
  "$BIN" -u Cmdenv -n "$NED" -f "$INI" -c "$cfg"
done

echo "Phase-3 OMNeT++ high-load audit completed."
