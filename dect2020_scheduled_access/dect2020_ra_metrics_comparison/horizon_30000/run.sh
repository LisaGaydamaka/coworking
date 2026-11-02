#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
ROOT="$(cd ../.. && pwd)"
mkdir -p src results figures
docker run --rm -v "$ROOT:/project" -w /project/dect2020_ra_metrics_comparison/horizon_30000 "$IMAGE" bash -lc '
  set -euo pipefail
  if ! command -v opp_makemake >/dev/null 2>&1; then source /root/omnetpp/setenv; fi
  cp ../../dect2020_ra_ira_omnetpp/src/* src/
  cd src
  opp_makemake -f -o ra_30000
  make -j2
  cd ..
  rm -f results/*.sca
  for seed in $(seq 1 10); do
    for i in $(seq 0 8); do
      ./src/ra_30000 -u Cmdenv -n src -f src/omnetpp.ini \
        -c CompareWithPython -r "$i" \
        --sim-time-limit=30000s --seed-set="$seed" \
        --cmdenv-express-mode=true \
        --output-scalar-file="results/p${i}_s${seed}.sca" > /dev/null
    done
  done
  python3 -c "import numpy,matplotlib" || (apt-get update -qq && apt-get install -y -qq python3-numpy python3-matplotlib)
  python3 compare_30000.py
  python3 plot_30000.py
  python3 compare_horizons.py
'
