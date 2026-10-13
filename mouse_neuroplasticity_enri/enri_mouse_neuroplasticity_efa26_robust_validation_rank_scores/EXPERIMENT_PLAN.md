# Predeclared analysis and sensitivity checks

1. Verify clean 133 rows, original 140 rows, baseline 54, observed-only baseline 52;
   excluded 7 states all at weeks 16/24.
2. Remove Learning T1/T2/T3 sum and Average_speed_NOR1/NOR2 to prevent duplicate influence.
3. Re-run parallel analysis with 1000 Gaussian and 1000 permutation nulls;
   ordinary Spearman eigenvalues and SMC-reduced eigenvalues for common-factor PA.
4. Repeat the same on 52 observed-only baseline mice using 500 null replicates.
5. Run k=3/k=4 EFA by MINRES+oblimin; report factor fit residuals and correlations,
   cross-loading patterns, 500 bootstrap replicates on 54 and 250 on 52.
6. Compare loadings of 28- and 26-feature solutions in same common feature space.
7. Compute regression factor scores from *baseline-frozen Spearman midranks* so
   Pearson of transformed baseline columns exactly matches Spearman R.
   W=pinv(R)@L@Phi, factor scores normalized on baseline.
8. Project rank scores to 133 cleaned states and all 140 pre-exclusion states;
   quantify sensitivity to excluded rows without treating those measurements as reliable.
9. Show score differences from original linear-standardized scoring formula.
10. Keep all historic source and outputs unchanged; make no causal treatment claims.
11. Explicitly disclose unsolved original-Excel raw outlier QC and all-week
    model preprocessing/impputation leakage limitations.
