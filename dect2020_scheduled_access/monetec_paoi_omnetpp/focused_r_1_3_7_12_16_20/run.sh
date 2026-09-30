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

git -C "$REPO_ROOT" rev-parse HEAD > "$ROOT/SIMULATOR_SOURCE_COMMIT.txt"

rm -rf "$SCRATCH"
mkdir -p "$SCRATCH"
cp -a "$CORE/src" "$SCRATCH/src"
cp "$CORE/simulations/omnetpp.ini" "$SCRATCH/focused.ini"

RHO_LIST="$(python3 - <<'PY'
print(",".join(f"{0.005*i:.3f}" for i in range(1,61)))
PY
)"

{
cat <<'EOF'

# Isolated focused MONETEC sweep. Canonical simulator files remain untouched.
[Config MonetecFocusedSmallR]
result-dir = results_focused
repeat = 3
seed-set = ${repetition}
*.queue.D = 10
*.queue.r = ${r=1,3,7,12,16,20}
EOF
printf '*.queue.rho = ${rho=%s}\n' "$RHO_LIST"
cat <<'EOF'
*.queue.warmupCompletedPackets = 5000
*.queue.targetCompletedPackets = 30000
*.queue.recordVectors = false
EOF
} >> "$SCRATCH/focused.ini"

docker pull "$IMAGE"

docker run --rm   -v "$ROOT:/exp"   -w /exp/_scratch   "$IMAGE"   bash -lc '
    set -euo pipefail
    if ! command -v opp_makemake >/dev/null 2>&1; then
      for envfile in /root/omnetpp/setenv /root/omnetpp-*/setenv /opt/omnetpp/setenv /opt/omnetpp-*/setenv; do
        if [[ -f "$envfile" ]]; then
          source "$envfile"
          break
        fi
      done
    fi

    cd /exp/_scratch/src
    opp_makemake -f --deep -o dect2020_sa
    make -j2

    cd /exp/_scratch
    rm -rf results_focused
    mkdir -p results_focused

    echo "=== FOCUSED SMALL-r MONETEC PAoI SWEEP ==="
    ./src/dect2020_sa -u Cmdenv -n src -f focused.ini -c MonetecFocusedSmallR 2>&1 | tee /exp/run.log
    opp_scavetool x results_focused/*.sca -F CSV-R -o /exp/scalars.csv

    rm -rf /exp/_scratch
  '

python3 "$ROOT/analyze.py" "$ROOT/scalars.csv" "$ROOT"
printf "PASS\n" > "$ROOT/status.txt"

echo "Focused MONETEC sweep completed."
