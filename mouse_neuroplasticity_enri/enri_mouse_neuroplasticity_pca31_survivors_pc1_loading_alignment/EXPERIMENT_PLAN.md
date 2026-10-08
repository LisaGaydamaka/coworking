# Analysis plan

1. Determine end survivors using the pre-exclusion week-24 living state.
2. Filter the cleaned 31-feature matrix; do not restore seven previously excluded states.
3. Fit separate group×week PCA exactly as prior survivor analysis and verify n.
4. Extract unit PC1 coefficient vectors and align their sign relative to week 0 for display.
5. Calculate |dot(u,v)| and arccos absolute dot as principal angle.
6. Report top 10 contributors by absolute PC1 coefficient for each group×week.
7. Paired mouse bootstrap within each group, 1000 draws; resample the same mouse IDs
   at all visits, retaining the historical excluded-state mask; record similarity
   distributions and PC1 loading stability.
8. Repeat PCA on a fixed complete-case set of survivors with all three cleaned visits
   to assess the effect of changing n due to outlier-state exclusions.
9. Interpret descriptive comparisons cautiously because p=31 and n=6–12.
