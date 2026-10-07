# PCA31 experiment plan

## Input

Use the same 54-mouse analytic cohort and the same 31 MODEL_FEATURES as the
longitudinal-only GRIP31 eNRI analysis.

The processed matrix is reconstructed deterministically by the frozen
preprocessing code and immediately saved to this new experiment directory.
No alternative preprocessing is introduced.

## Important PCA choices

- Use only living rows (`status in {observed, imputed}`).
- Weeks: 0, 16, 24.
- No group labels enter PCA.
- No directional constraints enter PCA.
- No eNRI score enters PCA.
- No repeated standardization is performed.
- sklearn PCA's ordinary column centering is retained.
- All 31 processed features are included.

## Primary analysis: pooled PCA

Fit PCA to all living mouse×week observations from weeks 0/16/24.

Report:
- explained variance ratio for all PCs;
- cumulative explained variance;
- PC1 loadings;
- PC1 scores;
- group×week descriptive means after fitting;
- the six longitudinal comparisons as post-hoc descriptive checks.

## Sensitivity analysis: baseline PCA

Fit PCA only on the 54 week-0 rows and transform all living later rows with the
frozen baseline PCA basis.

This asks whether a latent axis defined before longitudinal deterioration can
track later states.

## Sign convention

The sign of a principal component is arbitrary. For presentation only, PC1 is
multiplied by -1 when necessary so that the overall mean PC1 at week 0 is not
below the overall mean at week 16. This changes neither explained variance nor
the PCA subspace.

No old experiment file is modified.
