#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
PROJECT_PARENT="$(cd .. && pwd)"
mkdir -p omnet_new/results figures
# Mount the common DECT project root: the OMNeT++ source is the sibling Ira simulator.
# All generated build files and scalar outputs remain inside THIS comparison component.
docker run --rm -v "$PROJECT_PARENT:/project" \
  -w /project/dect2020_ra_metrics_comparison "$IMAGE" bash -lc '
    set -euo pipefail
    if ! command -v opp_makemake >/dev/null 2>&1; then source /root/omnetpp/setenv; fi
    mkdir -p omnet_new/src omnet_new/results figures
    cp ../dect2020_ra_ira_omnetpp/src/* omnet_new/src/
    cd omnet_new/src
    opp_makemake -f -o ra_collision_compare
    make -j2
    cd ../..
    rm -f omnet_new/results/*.sca
    for seed in $(seq 1 10); do
      for i in $(seq 0 8); do
        ./omnet_new/src/ra_collision_compare -u Cmdenv -n omnet_new/src \
          -f omnet_new/src/omnetpp.ini -c CompareWithPython -r "$i" \
          --sim-time-limit=3000s --seed-set="$seed" --cmdenv-express-mode=true \
          --output-scalar-file="omnet_new/results/p${i}_s${seed}.sca" > /dev/null
      done
    done
    python3 -c "import numpy, matplotlib" || (apt-get update -qq && apt-get install -y -qq python3-numpy python3-matplotlib)
    python3 regression_ack_lbt.py
    for scenario in DeterministicParity DeterministicOnePT DeterministicPhase; do
      ./omnet_new/src/ra_collision_compare -u Cmdenv -n omnet_new/src \
        -f omnet_new/src/omnetpp.ini -c "$scenario" \
        --output-scalar-file="omnet_new/${scenario}.sca" > /dev/null
    done
    python3 deterministic_parity.py
    ./omnet_new/src/ra_collision_compare -u Cmdenv -n omnet_new/src \
      -f omnet_new/src/omnetpp.ini -c SharedRandomParity \
      --output-scalar-file="omnet_new/SharedRandomParity.sca" > /dev/null
    python3 shared_rng_replay.py
    python3 compare_metrics.py
    python3 plot_metrics.py
  '
