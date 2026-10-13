# Plan

1. Assert the old cleaned dataset still has 133 living states, with week0=54, week16=41, week24=38.
2. Assert Learning T1/T2/T3 mean and sum are exact duplicates among 54 baseline mice.
3. Remove three sum columns only in this new analysis, leaving 28 features.
4. Recompute Spearman correlation and 1000-simulation parallel analysis.
5. Fit MINRES oblimin EFA at parallel-retained k, and separately at k=3 and k=4.
6. Bootstrap each solution 500 times on resampled baseline mice; align factor order/sign.
7. Record loadings, strong membership |loading|>=0.40, stable core probability >=0.70.
8. Compare old 31-feature domain loadings/score correlations on the shared 28 features.
9. Freeze baseline scores and project to all 133 old-cleaned living states.
10. Do not alter old files or infer longitudinal treatment significance.
