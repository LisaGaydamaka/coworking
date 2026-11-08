#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p results
python3 prepare.py
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
PROJECT_PARENT="$(cd .. && pwd)"
docker run --rm -v "$PROJECT_PARENT:/project" \
    -w /project/parity_backoff_test "$IMAGE" bash -lc '
    set -euo pipefail
    if ! command -v opp_makemake >/dev/null 2>&1; then source /root/omnetpp/setenv; fi
    python3 -c "import numpy,matplotlib" || (apt-get update -qq && apt-get install -y -qq python3-numpy python3-matplotlib)
    cd build
    opp_makemake -f -o ra_parity
    make -j2
    cd ..
    python3 compare.py
'
