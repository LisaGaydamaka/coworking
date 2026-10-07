# EFA31: 3 vs 4 factors + longitudinal domain analysis

Independent experiment. Existing eNRI, PCA, and EFA folders are not modified.

The same cleaned processed 31-feature matrix is used. Domain definition uses only
week 0 (54 mice). Fixed k=3 and k=4 MINRES+oblimin solutions are compared using
the same 500 bootstrap resamples. Both frozen baseline solutions are projected to
retained week 16/24 states, and group trajectories are summarized for
PBS/LPS/run/MCC.

A predefined parsimony rule prefers k=3 only if the 4th parallel-analysis margin
is <0.10 and the 4th-factor bootstrap q10 congruence is <0.80. Both solutions
remain fully reported regardless of the decision.
