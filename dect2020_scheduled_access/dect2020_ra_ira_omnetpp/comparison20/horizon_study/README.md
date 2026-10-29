# 20-PT simulation-horizon study

Question: does increasing the observation horizon reduce the mismatch
between the two independently implemented DECT-2020 RA models?

Keep 20 PT, 1 FT, cMin=1, cMax=16, arrProb=0.01..0.09,
transTime=10, procTime=10, ackTime=5, lbtTime=2.
Compare horizon=3000 (earlier results under ../results/) with 10000 and 30000.
For new horizons, 5 independent seeds are used in each model per arrProb.
This is a resource-limited diagnostic, not proof of equivalence.
A run includes only first-delivered unique packets in the mean; unfinished
and undelivered packets are excluded, leading to potential censoring bias.

Outputs: results/h{10000,30000}/comparison.csv, *.png, python_runs.csv,
omnet_runs.csv, summary.txt, plus results/horizon_trend.csv.

Don't increase horizon merely to force equality. Evaluate per-p load and
delivered-count selection; a 20-PT source rate greatly exceeds the
effective single FT channel service capacity for most arrProb values.
Convergence criterion: all nine relative differences <=5%; otherwise
report mismatch rather than claim convergence.
