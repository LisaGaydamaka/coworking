# PCA31 on the already processed eNRI matrix

Independent PCA experiment. Existing eNRI experiment folders are read-only.

The experiment reconstructs the exact final 31-feature processed matrix used by
the longitudinal-only GRIP31 analysis, then performs PCA without any additional
feature scaling.

Two analyses are produced:

1. **Pooled PCA** — PCA fitted to all living mouse×week rows from weeks 0, 16,
   and 24.
2. **Baseline PCA** — PCA fitted only to the 54 week-0 mice, then the frozen
   baseline PCA basis is used to project living week-16 and week-24 rows.

Dead rows are excluded from PCA because eNRI=0 for death is a scale rule, not a
31-dimensional functional measurement.

Run:

```bash
bash run.sh
```
