# PCA31 after excluding seven complete outlier states

Use the same processed GRIP31 matrix as the prior PCA experiments.

Exclude complete mouse×week rows:
8.4@16, 8.2@16, 8.3@16, 9.2@24, 17.1@24, 21.4@24, 16.1@24.

This is row-level exclusion. No feature-wise clipping, winsorization, or
re-scaling is introduced.

Run:
1. pooled PCA on all retained living states;
2. baseline PCA fit only on week 0 and frozen projection to retained later rows.

No group labels, eNRI values, or longitudinal constraints enter the PCA fit.
