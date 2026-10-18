#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Starter entry point: compile the unfinished project, do not run experiments.
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
docker run --rm -v "$PWD:/work" -w /work "$IMAGE" bash -lc '
  set -e
  if ! command -v opp_makemake >/dev/null 2>&1; then
    source /root/omnetpp/setenv
  fi
  cd src
  opp_makemake -f -o ra
  make -j2
  echo "Starter builds; TODO: add a smoke test, parameter sweeps and plots."
'
