# Plan

1. Read the cleaned 31-feature matrix after the seven full state exclusions.
2. Define latent structure using only the 54 week-0 mice.
3. Recompute the baseline Spearman correlation and 1000-run parallel analysis.
4. Fit fixed k=3 and fixed k=4 MINRES EFA solutions with oblimin rotation.
5. Use the same 500 bootstrap mouse resamples for both solutions.
6. Report factor congruence and stable-core feature membership.
7. Compare off-diagonal correlation reconstruction error.
8. Map the k=3 factors to their closest k=4 factors by loading congruence.
9. Freeze each baseline solution and compute factor scores for all retained states.
10. Report PBS/LPS/run/MCC means at weeks 0,16,24 and changes 0→16,16→24,0→24.
11. Apply the predefined parsimony rule; do not hide the non-preferred solution.
