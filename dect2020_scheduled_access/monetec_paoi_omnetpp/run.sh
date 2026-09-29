#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$ROOT" rev-parse --show-toplevel)"
CORE="$REPO_ROOT/dect2020_scheduled_access/dect2020_scheduled_access_omnetpp"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
SCRATCH="$ROOT/_scratch"

if [[ ! -f "$CORE/src/ScheduledAccessQueue.cc" || ! -f "$CORE/simulations/omnetpp.ini" ]]; then
  echo "Canonical OMNeT++ simulator not found at $CORE" >&2
  exit 1
fi

# Record the exact repository state used. The canonical simulator is read-only
# for this experiment: all build/run work happens in this component's scratch.
git -C "$REPO_ROOT" rev-parse HEAD > "$ROOT/SIMULATOR_SOURCE_COMMIT.txt"

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
cp -a "$CORE/src" "$SCRATCH/src"
cp "$CORE/simulations/omnetpp.ini" "$SCRATCH/paper_plot.ini"

cat >> "$SCRATCH/paper_plot.ini" <<'EOF'

# ---------------------------------------------------------------------------
# Isolated MONETEC PAoI plot reproduction. This block is generated in scratch;
# the canonical simulator configuration is not modified.
# ---------------------------------------------------------------------------
[Config MonetecPaperPlot]
result-dir = results_monetec
repeat = 3
seed-set = ${repetition}
*.queue.D = 10
*.queue.r = ${r=5,10,20,30,40,50}
*.queue.rho = ${rho=0.010,0.093,0.176,0.259,0.342,0.425,0.508,0.591,0.674,0.757,0.840,0.923,1.006,1.089,1.172,1.255,1.338,1.421,1.504,1.587,1.670,1.753,1.836,1.919,2.002,2.085,2.168,2.251,2.334,2.417,2.500,2.583}
*.queue.warmupCompletedPackets = 5000
*.queue.targetCompletedPackets = 20000
*.queue.recordVectors = false
EOF

docker pull "$IMAGE"

docker run --rm   -v "$ROOT:/exp"   -w /exp/_scratch   "$IMAGE"   bash -lc '
    set -euo pipefail

    if ! command -v opp_makemake >/dev/null 2>&1; then
      for envfile in /root/omnetpp/setenv /root/omnetpp-*/setenv /opt/omnetpp/setenv /opt/omnetpp-*/setenv; do
        if [[ -f "$envfile" ]]; then
          # shellcheck disable=SC1090
          source "$envfile"
          break
        fi
      done
    fi

    echo "opp_makemake=$(command -v opp_makemake)"
    echo "opp_scavetool=$(command -v opp_scavetool)"
    opp_run -h 2>&1 | grep -m1 "^Version:" || true

    cd /exp/_scratch/src
    opp_makemake -f --deep -o dect2020_sa
    make -j2

    cd /exp/_scratch
    rm -rf results_monetec
    mkdir -p results_monetec

    echo "=== MONETEC PAPER PLOT SWEEP ==="
    ./src/dect2020_sa -u Cmdenv -n src -f paper_plot.ini -c MonetecPaperPlot 2>&1 | tee /exp/run.log

    opp_scavetool x results_monetec/*.sca -F CSV-R -o /exp/scalars.csv
  '

python3 "$ROOT/analyze.py" "$ROOT/scalars.csv" "$ROOT"

rm -rf "$SCRATCH"
printf "PASS\n" > "$ROOT/status.txt"

echo "MONETEC PAoI OMNeT++ reproduction completed."
echo "Outputs:"
ls -lh "$ROOT/paper_plot_data.csv" "$ROOT/paper_plot_runs.csv" "$ROOT/paper_plot.svg" "$ROOT/summary.txt" "$ROOT/scalars.csv" "$ROOT/status.txt"
