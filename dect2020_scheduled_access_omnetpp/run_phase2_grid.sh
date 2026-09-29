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
rm -rf results
mkdir -p results

for cfg in Phase2_D6 Phase2_D10 Phase2_D20; do
  "$BIN" -u Cmdenv -n "$NED" -f "$INI" -c "$cfg"
done

echo "Phase-2 OMNeT++ runs completed. Results are under simulations/results/."
