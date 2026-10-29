# Matched random-access delay comparison

Two PT nodes, one FT, one channel, simulation horizon 3000 symbols.
Both use Bernoulli arrival probability per PT per symbol, cMin=1, cMax=16,
transTime=10, procTime=10, ackTime=5, lbtTime=2.

The Python copy changes only sim_delay(): first delivered event instead of
last packet journey event. The original contributor source remains in original/.
src/FT.cc additionally clears deniedWhileBusy for retransmission keys.

Run: bash run.sh (Docker OMNeT++ 6.3 plus Python/numpy/matplotlib).
Experiments: arrProb 0.01..0.09, ten seeds per model and setting.
Seed integers identify independent reproducible runs, NOT identical random
streams in Python vs OMNeT++.

Outputs: comparison/results/comparison.csv, comparison.png, python_runs.csv,
python_aggregate.csv, omnet_runs.csv.
Metrics are first unique delivery to the FT/root measured from packet creation.
Average is computed over runs with >=1 delivery, then across runs (not pooled).
Interpret remaining differences as not yet fully validated behavior, particularly
event ordering and collision/ACK handling.
