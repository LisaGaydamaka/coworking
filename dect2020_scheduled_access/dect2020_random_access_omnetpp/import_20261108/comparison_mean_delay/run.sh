#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Restore exact uploaded Python bytes; do not alter either simulation algorithm.
base64 -d 4_random_access_my_parameters.py.xz.b64 | xz -d > 4_random_access_my_parameters.py
echo '0f1f9cef3c8b7b0e8e71487d70e5caa0d33605d89406ebfc4da723688c488034  4_random_access_my_parameters.py' | sha256sum -c -
mkdir -p build results
cp ../dect-ra/RandomAccessModel.cc ../dect-ra/DectRandomAccess.ned build/
IMAGE="${OMNETPP_IMAGE:-ghcr.io/omnetpp/omnetpp:u24.04-6.3.0}"
ROOT="$(pwd)"
docker run --rm -v "$ROOT:/project" -w /project "$IMAGE" bash -lc '
set -euo pipefail
if ! command -v opp_makemake >/dev/null 2>&1; then source /root/omnetpp/setenv; fi
python3 -c "import numpy,matplotlib" || (apt-get update -qq && apt-get install -y -qq python3-numpy python3-matplotlib)
cd build
opp_makemake -f -o ra_compare
make -j2
cd ..
python3 -m py_compile 4_random_access_corrected.py
python3 compare_fixed.py
'
