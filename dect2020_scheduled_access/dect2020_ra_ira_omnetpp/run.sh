#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Reproduce the supplied OMNeT++ model in the same image as the related project.
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
docker run --rm -v "$PWD:/work" -w /work "$IMAGE" bash -lc '
  set -euo pipefail
  if ! command -v opp_makemake >/dev/null 2>&1; then
    source /root/omnetpp/setenv
  fi
  cd src
  opp_makemake -f -o ira_ra
  make -j2
  cd ..
  mkdir -p results
  ./src/ira_ra -u Cmdenv -n src -f src/omnetpp.ini \
    --cmdenv-express-mode=false --output-scalar-file=results/ira.sca \
    > results/console_full.log 2>&1
  python3 summarize.py results/ira.sca results/console_full.log
  echo "--- Simulation results ---"
  cat results/summary.txt
  echo "--- Console excerpt ---"
  sed -n "1,28p" results/console_excerpt.txt
'
