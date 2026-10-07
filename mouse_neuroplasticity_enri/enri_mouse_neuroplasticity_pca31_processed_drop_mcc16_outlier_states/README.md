# PCA31 on processed data, excluding three MCC week-16 states

Independent sensitivity PCA. No previous PCA/eNRI files are modified.

Entire mouse×week states excluded from PCA and from all projections:
- mouse 8.4, week 16
- mouse 8.2, week 16
- mouse 8.3, week 16

All 31 feature values for each excluded state are removed as one row.

No repeated standardization is performed. PCA only mean-centers the already
processed 31-feature matrix.

Outputs include pooled PCA and baseline-week0 PCA projected to later weeks.
