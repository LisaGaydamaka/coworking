#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
ROOT="$(cd .. && pwd)"
mkdir -p src results
docker run --rm -v "$ROOT:/project" -w /project/diagnose_colleague_timeout "$IMAGE" bash -lc '
  set -euo pipefail
  if ! command -v opp_makemake >/dev/null 2>&1; then source /root/omnetpp/setenv; fi
  cp ../dect2020_ra_ira_omnetpp/src/* src/
  cd src
  opp_makemake -f -o check_timeout
  make -j2
  cd ..
  rm -f results/*.sca
  for seed in $(seq 1 10); do
    for suffix in exact offset; do
      timeout=25s
      if [ "$suffix" = offset ]; then timeout=25.000001s; fi
      ./src/check_timeout -u Cmdenv -n src -f src/omnetpp.ini \
        -c CompareWithPython -r 1 --sim-time-limit=30000s \
        --seed-set="$seed" --Cluster.ackTimeout="$timeout" \
        --output-scalar-file="results/${suffix}_seed_${seed}.sca" >/dev/null
    done
  done
  python3 evaluate.py
'
