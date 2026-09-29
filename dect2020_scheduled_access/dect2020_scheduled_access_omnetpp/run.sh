#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
RUN_MODE="$(cat "$ROOT/.run" 2>/dev/null || true)"

echo "Using OMNeT++ container: $IMAGE"
echo "Run mode: $RUN_MODE"
docker pull "$IMAGE"

mkdir -p "$ROOT/ci_results"

docker run --rm \
  -e RUN_MODE="$RUN_MODE" \
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

    if [[ "$RUN_MODE" == phase4-crosscheck* ]]; then
      echo "=== PHASE 4 DIMENSIONING CROSS-CHECK ==="
      rm -f ci_results/phase4_*.csv ci_results/phase4_*.log ci_results/phase4_crosscheck_status.txt
      cd simulations
      rm -rf results_phase4
      mkdir -p results_phase4
      for cfg in Phase4_D2 Phase4_D6 Phase4_D10 Phase4_D13 Phase4_D20 Phase4_D24 Phase4_Trade; do
        echo "=== $cfg ==="
        ../src/dect2020_sa -u Cmdenv -n ../src -f omnetpp.ini -c "$cfg"
      done 2>&1 | tee ../ci_results/phase4_crosscheck_run.log
      opp_scavetool x results_phase4/*.sca -F CSV-R -o ../ci_results/phase4_scalars.csv
      {
        head -n 1 ../ci_results/phase4_scalars.csv
        grep -E ",scalar,DectScheduledAccessNetwork\\.queue,(D|r|L_effective|rho|rho_sat|lambda_per_ms|lambda_sat_per_ms|mean_delay_direct_ms|mean_delay_little_ms|little_vs_direct_relative_error|blocking_probability|mean_type1_number|effective_throughput_departures_per_ms),,," ../ci_results/phase4_scalars.csv
      } > ../ci_results/phase4_metrics.csv
      echo "phase4_crosscheck=PASS" > ../ci_results/phase4_crosscheck_status.txt
      cd ..
      find ci_results -maxdepth 1 -type f -printf "%f %s bytes\\n" | sort | tee ci_results/files.txt
      echo "OMNeT++ Phase-4 dimensioning cross-check completed."
      exit 0
    fi

    if [[ "$RUN_MODE" == article-representative* ]]; then
      echo "=== ARTICLE REPRESENTATIVE OMNET++ RUNS ==="
      rm -f ci_results/article_representative_*.csv ci_results/article_representative_*.log ci_results/article_representative_status.txt
      cd simulations
      rm -rf results_article
      mkdir -p results_article
      ../src/dect2020_sa -u Cmdenv -n ../src -f omnetpp.ini -c ArticleRepresentative 2>&1 | tee ../ci_results/article_representative_run.log
      opp_scavetool x results_article/*.sca -F CSV-R -o ../ci_results/article_representative_scalars.csv
      {
        head -n 1 ../ci_results/article_representative_scalars.csv
        grep -E ",scalar,DectScheduledAccessNetwork\\.queue,(D|r|L_effective|rho|rho_sat|lambda_per_ms|lambda_sat_per_ms|mean_delay_direct_ms|mean_delay_little_ms|little_vs_direct_relative_error|blocking_probability|mean_type1_number|effective_throughput_departures_per_ms),,," ../ci_results/article_representative_scalars.csv
      } > ../ci_results/article_representative_metrics.csv
      echo "article_representative=PASS" > ../ci_results/article_representative_status.txt
      cd ..
      find ci_results -maxdepth 1 -type f -printf "%f %s bytes\\n" | sort | tee ci_results/files.txt
      echo "OMNeT++ article representative runs completed."
      exit 0
    fi

    if [[ "$RUN_MODE" == phase3-highload* ]]; then
      echo "=== PHASE 3 HIGH-LOAD AUDIT ==="
      rm -f ci_results/phase3_highload_*.csv ci_results/phase3_highload_*.log ci_results/phase3_highload_status.txt
      bash run_phase3_highload.sh 2>&1 | tee ci_results/phase3_highload_run.log

      cd simulations
      opp_scavetool x results_phase3/*.sca -F CSV-R -o ../ci_results/phase3_highload_scalars.csv
      {
        head -n 1 ../ci_results/phase3_highload_scalars.csv
        grep -E ",scalar,DectScheduledAccessNetwork\\.queue,(D|r|L_effective|rho|rho_sat|lambda_per_ms|lambda_sat_per_ms|load_factor_rho_over_rho_sat|mean_delay_direct_ms|mean_delay_little_ms|little_vs_direct_relative_error|blocking_probability|mean_type1_number|effective_throughput_departures_per_ms|type1_service_fraction|type2_service_fraction|full_type1_fraction|full_type2_fraction|nonfull_state_fraction|saturated_full_state_fraction|full_type1_phase_[0-9]+_fraction),,," ../ci_results/phase3_highload_scalars.csv
      } > ../ci_results/phase3_highload_metrics.csv
      echo "phase3_highload=PASS" > ../ci_results/phase3_highload_status.txt
      cd ..
      find ci_results -maxdepth 1 -type f -printf "%f %s bytes\n" | sort | tee ci_results/files.txt
      echo "OMNeT++ Phase-3 high-load audit completed."
      exit 0
    fi

    echo "=== BASELINE: D=10, r=30, rho=rho_sat, 10 repetitions ==="
    cd simulations
    rm -rf results
    mkdir -p results
    ../src/dect2020_sa -u Cmdenv -n ../src -f omnetpp.ini -c Baseline 2>&1 | tee ../ci_results/baseline_run.log

    opp_scavetool x results/*.sca -F CSV-R -o ../ci_results/baseline_scalars.csv
    { head -n 1 ../ci_results/baseline_scalars.csv; grep -E ",scalar,DectScheduledAccessNetwork\\.queue,(D|r|L_effective|rho|rho_sat|mean_delay_direct_ms|mean_delay_little_ms|little_vs_direct_relative_error|blocking_probability|mean_type1_number|effective_throughput_departures_per_ms),,," ../ci_results/baseline_scalars.csv; } > ../ci_results/baseline_metrics.csv
    echo "baseline=PASS" > ../ci_results/baseline_status.txt

    echo "=== FULL PHASE-2 GRID ==="
    cd ..
    bash run_phase2_grid.sh 2>&1 | tee ci_results/phase2_grid_run.log

    cd simulations
    opp_scavetool x results/*.sca -F CSV-R -o ../ci_results/phase2_scalars.csv
    { head -n 1 ../ci_results/phase2_scalars.csv; grep -E ",scalar,DectScheduledAccessNetwork\\.queue,(D|r|L_effective|rho|rho_sat|mean_delay_direct_ms|mean_delay_little_ms|little_vs_direct_relative_error|blocking_probability|mean_type1_number|effective_throughput_departures_per_ms),,," ../ci_results/phase2_scalars.csv; } > ../ci_results/phase2_metrics.csv
    echo "phase2_grid=PASS" > ../ci_results/phase2_grid_status.txt

    cd ..
    find ci_results -maxdepth 1 -type f -printf "%f %s bytes\n" | sort | tee ci_results/files.txt
  '

echo "OMNeT++ validation run completed."
