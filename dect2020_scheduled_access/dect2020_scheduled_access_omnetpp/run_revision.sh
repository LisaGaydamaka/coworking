#!/usr/bin/env bash
set -euo pipefail
TRIGGER="${1:-revision-smoke}"
# GitHub Actions .run triggers carry a unique date suffix; normalize to a
# stable experiment mode before selecting config and output file names.
case "$TRIGGER" in
    revision-final-physical*) MODE=revision-final-physical ;;
    revision-final-saturation*) MODE=revision-final-saturation ;;
    revision-smoke*) MODE=revision-smoke ;;
    revision-grid*) MODE=revision-grid ;;
    revision-tail*) MODE=revision-tail ;;
    revision-geometry*) MODE=revision-geometry ;;
    revision-traffic*) MODE=revision-traffic ;;
    revision-dimensioning*) MODE=revision-dimensioning ;;
    revision-variability-aligned*) MODE=revision-variability-aligned ;;
    revision-full*) MODE=revision-full ;;
    *) echo "Unknown revision trigger: $TRIGGER" >&2; exit 2 ;;
esac
cd "$(dirname "$0")"
mkdir -p simulations/results_revision ci_results
cd simulations
case "$MODE" in
  revision-final-physical) configs=() ;;
  revision-final-saturation) configs=() ;;
  revision-smoke) configs=(Smoke) ;;
  revision-grid) configs=(Revision_D6 Revision_D10 Revision_D20) ;;
  revision-tail) configs=(Revision_Tail) ;;
  revision-geometry) configs=(Revision_Distributed Revision_Overhead) ;;
  revision-traffic) configs=(Revision_Traffic_Poisson Revision_Traffic_Periodic Revision_Traffic_Synchronized Revision_Traffic_Bursty) ;;
  revision-dimensioning) configs=(Revision_DimensioningD6 Revision_DimensioningD10 Revision_DimensioningD20 Revision_Trade) ;;
  revision-variability-aligned) configs=() ;;
  revision-full) configs=(Revision_D6 Revision_D10 Revision_D20 Revision_Tail Revision_Distributed Revision_Overhead Revision_Traffic_Poisson Revision_Traffic_Periodic Revision_Traffic_Synchronized Revision_Traffic_Bursty Revision_DimensioningD6 Revision_DimensioningD10 Revision_DimensioningD20 Revision_Trade) ;;
  *) echo "Unknown revision mode: $MODE" >&2; exit 2 ;;
esac
# Two final pre-writing checks; filenames and results are isolated from every
# previously published and major-revision experiment.
if [[ "$MODE" == "revision-final-physical" ]]; then
    rm -rf results_revision_final_physical
    mkdir -p results_revision_final_physical
    for cfg in FinalPhysical_D2 FinalPhysical_D13 FinalPhysical_D24; do
        echo "=== FINAL PHYSICAL DIMENSIONING CHECK: $cfg ==="
        ../src/dect2020_sa -u Cmdenv -n ../src -f revision_final_physical.ini -c "$cfg"
    done
    opp_scavetool x results_revision_final_physical/*.sca -F CSV-R -o ../ci_results/revision-final-physical_scalars.csv
    cd ..
    python3 revision_analysis.py revision-final-physical
    echo "revision-final-physical PASS" > ci_results/revision-final-physical_status.txt
    exit 0
fi
if [[ "$MODE" == "revision-final-saturation" ]]; then
    rm -rf results_revision_final_saturation
    mkdir -p results_revision_final_saturation
    for cfg in FinalSat_D10R20 FinalSat_D10R50 FinalSat_D20R5 FinalSat_D20R20 FinalSat_D20R50; do
        echo "=== FINAL LONG-RUN SATURATION CHECK: $cfg ==="
        ../src/dect2020_sa -u Cmdenv -n ../src -f revision_final_saturation.ini -c "$cfg"
    done
    opp_scavetool x results_revision_final_saturation/*.sca -F CSV-R -o ../ci_results/revision-final-saturation_scalars.csv
    cd ..
    python3 revision_final_post.py
    echo "revision-final-saturation PASS" > ci_results/revision-final-saturation_status.txt
    exit 0
fi
if [[ "$MODE" == "revision-variability-aligned" ]]; then
    rm -rf results_revision_variability
    mkdir -p results_revision_variability
    for cfg in RevisionVar_Deterministic RevisionVar_Exponential RevisionVar_Hyperexponential; do
        echo "=== OMNeT++ frame-aligned service variability: $cfg ==="
        ../src/dect2020_sa -u Cmdenv -n ../src -f revision_variability.ini -c "$cfg"
    done
    opp_scavetool x results_revision_variability/*.sca -F CSV-R -o ../ci_results/revision-variability-aligned_scalars.csv
    cd ..
    python3 revision_variability_post.py
    echo "revision-variability-aligned PASS" > ci_results/revision-variability-aligned_status.txt
    exit 0
fi
rm -f results_revision/*.sca results_revision/*.vec results_revision/*.vci
for cfg in "${configs[@]}"; do
    echo "=== OMNeT++ fixed-slot: $cfg ==="
    ../src/dect2020_sa -u Cmdenv -n ../src -f revision.ini -c "$cfg"
done
opp_scavetool x results_revision/*.sca -F CSV-R -o "../ci_results/${MODE}_scalars.csv"
echo "$MODE PASS" > "../ci_results/${MODE}_status.txt"
cd ..
if ! python3 -c "import numpy, matplotlib" >/dev/null 2>&1; then
    PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --quiet --disable-pip-version-check numpy matplotlib || true
fi
python3 revision_analysis.py "$MODE"
echo "$MODE complete"
