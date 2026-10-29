#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
docker run --rm -v "$PWD:/work" -w /work "$IMAGE" bash -lc '
  set -euo pipefail
  if ! command -v opp_makemake >/dev/null 2>&1; then source /root/omnetpp/setenv; fi
  bash comparison/run_compare.sh
'
