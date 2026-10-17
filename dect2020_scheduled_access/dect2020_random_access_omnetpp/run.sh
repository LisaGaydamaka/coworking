#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
mkdir -p results figures
docker run --rm -e RUN_MODE="$(cat .run)" -v "$PWD:/work" -w /work "$IMAGE" bash -lc '
  set -euo pipefail
  for f in /root/omnetpp/setenv /root/omnetpp-*/setenv /opt/omnetpp/setenv /opt/omnetpp-*/setenv; do
    if [ -f "$f" ]; then source "$f"; break; fi
  done
  cd src
  opp_makemake -f -o ra
  make -j2
  cd ..
  if [ "$RUN_MODE" = full ]; then CFGS="Fig31a Fig31b Fig32 Fig33"; else CFGS=Smoke; fi
  for cfg in $CFGS; do src/ra -u Cmdenv -n src -f omnetpp.ini -c "$cfg"; done
  if [ "$RUN_MODE" = full ]; then
    python3 -c "import matplotlib" || (apt-get update -qq && apt-get install -y -qq python3-matplotlib)
    python3 plot.py
  fi
'
