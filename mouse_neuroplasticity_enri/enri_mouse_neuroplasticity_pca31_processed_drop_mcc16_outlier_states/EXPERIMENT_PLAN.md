# Sensitivity PCA31 after removing three full states

Use the same processed GRIP31 matrix as the prior PCA experiment, but exclude
the complete rows for 8.4@16, 8.2@16, and 8.3@16 before PCA.

This is row exclusion, not feature-wise trimming or winsorization.

Expected living rows after exclusion:
- week 0: 54
- week 16: 41
- week 24: 42
- total: 137

Run both:
1. pooled PCA on all 137 retained living states;
2. baseline PCA fit on week 0 and frozen projection to retained week16/week24.

No group labels, eNRI, or longitudinal constraints enter the PCA fit.
