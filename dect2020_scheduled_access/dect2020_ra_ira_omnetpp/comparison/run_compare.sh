#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p comparison/results/omnet
python3 comparison/run_sweep.py --repetitions 10
cd src
opp_makemake -f -o ira_ra
make -j2
cd ..
# Nine probabilities x ten seeds. 1 OMNeT++ second = 1 protocol symbol.
for seed in $(seq 1 10); do
  for i in $(seq 0 8); do
    ./src/ira_ra -u Cmdenv -n src -f src/omnetpp.ini -c CompareWithPython -r "$i" \
      --seed-set="$seed" --cmdenv-express-mode=true \
      --output-scalar-file="comparison/results/omnet/p${i}_s${seed}.sca" \
      > /dev/null
  done
done
python3 comparison/compare_results.py
rm -rf comparison/results/omnet
