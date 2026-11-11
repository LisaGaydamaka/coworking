#!/usr/bin/env bash
set -euo pipefail
TRIGGER="${1:-revision-smoke}"
# GitHub Actions .run triggers carry a unique date suffix; normalize to a
# stable experiment mode before selecting config and output file names.
case "$TRIGGER" in
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
  revision-smoke) configs=(Smoke) ;;
  revision-grid) configs=(Revision_D6 Revision_D10 Revision_D20) ;;
  revision-tail) configs=(Revision_Tail) ;;
  revision-geometry) configs=(Revision_Distributed Revision_Overhead) ;;
  revision-traffic) configs=(Revision_Traffic_Poisson Revision_Traffic_Periodic Revision_Traffic_Synchronized Revision_Traffic_Bursty) ;;
  revision-dimensioning) configs=(Revision_DimensioningD6 Revision_DimensioningD10 Revision_DimensioningD20 Revision_Trade) ;;
  revision-full) configs=(Revision_D6 Revision_D10 Revision_D20 Revision_Tail Revision_Distributed Revision_Overhead Revision_Traffic_Poisson Revision_Traffic_Periodic Revision_Traffic_Synchronized Revision_Traffic_Bursty Revision_DimensioningD6 Revision_DimensioningD10 Revision_DimensioningD20 Revision_Trade) ;;
  *) echo "Unknown revision mode: $MODE" >&2; exit 2 ;;
esac
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
