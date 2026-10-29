#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p comparison20/results/omnet
python3 comparison20/run_sweep.py --repetitions 10
cd src
opp_makemake -f -o ira_ra
make -j2
cd ..
# Nine generation probabilities x ten random seeds: 20 PT, 3000 symbols.
for seed in $(seq 1 10); do
  for i in $(seq 0 8); do
    ./src/ira_ra -u Cmdenv -n src -f src/omnetpp.ini -c Compare20PT -r "$i" \
      --seed-set="$seed" --cmdenv-express-mode=true \
      --output-scalar-file="comparison20/results/omnet/p${i}_s${seed}.sca" \
      > /dev/null
  done
done
python3 comparison20/compare_results.py
rm -rf comparison20/results/omnet
