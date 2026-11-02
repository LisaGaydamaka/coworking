#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
mkdir -p figures
docker run --rm -v "$PWD:/work" -w /work "$IMAGE" bash -lc '
  set -e
  python3 -c "import matplotlib" || (apt-get update -qq && apt-get install -y -qq python3-matplotlib)
  python3 plot_metrics.py
'
