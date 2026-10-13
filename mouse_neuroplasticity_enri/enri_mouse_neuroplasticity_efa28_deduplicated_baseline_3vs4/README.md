# EFA with exact baseline Learning mean/sum duplicates removed

Independent experiment. Source matrix is exactly the previous cleaned 31-feature,
133-state living matrix; historical 7 mouse-week exclusions are unchanged.

Remove exactly these three redundant columns from *the EFA input*:
- Learning_T1sum
- Learning_T2sum
- Learning_T3sum

This leaves 28 features and 54 week-0 mice for learning the domain structure.
The original 133 states remain for frozen score projection.
Parallel analysis: 1000 simulated independent 54x28 Gaussian matrices, Spearman correlation,
95th-percentile eigenvalue comparison. MINRES oblimin EFA with factor-count
selection by parallel analysis, plus fixed k=3 / k=4 sensitivity.
500 within-baseline-mouse bootstrap resamples for each model.
Hungarian matching and sign adjustment for factor permutation.
Compare loading vectors of old 31-feature EFA against new 28-feature EFA on
the 28 shared variables; compare domain scores after freezing the baseline projection.

Review results/REPORT.md, results/SUMMARY.json, results/parallel_old31_new28_comparison.csv,
results/k*_loadings_28.csv, results/k*_feature_stability.csv,
results/k*_scores_all_weeks.csv and result plots.
