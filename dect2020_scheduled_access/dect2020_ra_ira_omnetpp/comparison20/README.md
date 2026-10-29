# 20-PT comparison (Python versus Ira OMNeT++)

Matched settings: 1 cluster, 20 PT, cMin=1, cMax=16, transTime=10,
procTime=10, ackTime=5, lbtTime=2, 3000 protocol symbols.
arrProb: 0.01 through 0.09, 10 independent seeds per probability and model.
End-to-end delay: generation to first unique delivery; model results are
mean delay per successful packet, then equally averaged across runs.
Runs are repeatable individually, but Python and OMNeT++ random streams differ.
The original 2-PT comparison remains in ../comparison/results/.

GitHub Actions runs this directory via run.sh. For the 2-PT experiment
use "bash comparison/run_compare.sh" in the same Docker environment.

Files generated: results/{python_aggregate.csv,python_runs.csv,
omnet_runs.csv,comparison.csv,comparison.png}.
Results do not imply complete algorithmic equivalence.
