#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p comparison20/horizon_study/results
cd src
opp_makemake -f -o ira_ra
make -j2
cd ..
for horizon in 10000 30000; do
  mkdir -p "comparison20/horizon_study/results/h${horizon}/omnet"
  python3 comparison20/horizon_study/run_python.py --horizon "$horizon" --repetitions 5
  for seed in $(seq 1 5); do
    for i in $(seq 0 8); do
      ./src/ira_ra -u Cmdenv -n src -f src/omnetpp.ini -c Compare20PT -r "$i" \
        --sim-time-limit="${horizon}s" --seed-set="$seed" --cmdenv-express-mode=true \
        --output-scalar-file="comparison20/horizon_study/results/h${horizon}/omnet/p${i}_s${seed}.sca" > /dev/null
    done
  done
  python3 comparison20/horizon_study/summarize_horizon.py --horizon "$horizon"
  rm -rf "comparison20/horizon_study/results/h${horizon}/omnet"
done
python3 comparison20/horizon_study/trend.py
