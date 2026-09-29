#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"

echo "Using OMNeT++ container: $IMAGE"
docker pull "$IMAGE"

rm -rf "$ROOT/ci_results"
mkdir -p "$ROOT/ci_results"

docker run --rm \
  -v "$ROOT:/workspace" \
  -w /workspace \
  "$IMAGE" \
  bash -lc '
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
    opp_run -h 2>&1 | tee ci_results/omnetpp_help.txt >/dev/null
    grep -m1 "^Version:" ci_results/omnetpp_help.txt | tee ci_results/omnetpp_version.txt

    echo "=== BUILD ==="
    bash build.sh
    test -x src/dect2020_sa
    echo "build=PASS" > ci_results/build_status.txt

    echo "=== BASELINE: D=10, r=30, rho=rho_sat, 10 repetitions ==="
    cd simulations
    rm -rf results
    mkdir -p results
    ../src/dect2020_sa -u Cmdenv -n ../src -f omnetpp.ini -c Baseline 2>&1 | tee ../ci_results/baseline_run.log

    opp_scavetool x results/*.sca -F CSV-R -o ../ci_results/baseline_scalars.csv
    awk -F, 'NR==1 || ($2=="scalar" && ($4=="D" || $4=="r" || $4=="L_effective" || $4=="rho" || $4=="rho_sat" || $4=="mean_delay_direct_ms" || $4=="mean_delay_little_ms" || $4=="little_vs_direct_relative_error" || $4=="blocking_probability" || $4=="mean_type1_number" || $4=="effective_throughput_departures_per_ms"))' ../ci_results/baseline_scalars.csv > ../ci_results/baseline_metrics.csv
    echo "baseline=PASS" > ../ci_results/baseline_status.txt

    echo "=== FULL PHASE-2 GRID ==="
    cd ..
    bash run_phase2_grid.sh 2>&1 | tee ci_results/phase2_grid_run.log

    cd simulations
    opp_scavetool x results/*.sca -F CSV-R -o ../ci_results/phase2_scalars.csv
    awk -F, 'NR==1 || ($2=="scalar" && ($4=="D" || $4=="r" || $4=="L_effective" || $4=="rho" || $4=="rho_sat" || $4=="mean_delay_direct_ms" || $4=="mean_delay_little_ms" || $4=="little_vs_direct_relative_error" || $4=="blocking_probability" || $4=="mean_type1_number" || $4=="effective_throughput_departures_per_ms"))' ../ci_results/phase2_scalars.csv > ../ci_results/phase2_metrics.csv
    echo "phase2_grid=PASS" > ../ci_results/phase2_grid_status.txt

    cd ..
    find ci_results -maxdepth 1 -type f -printf "%f %s bytes\n" | sort | tee ci_results/files.txt
  '

echo "OMNeT++ build, baseline, and full Phase-2 grid completed."
