# New eNRI experiment: only living mice contribute to functional score

Independent rerun using the old train-only grouped CV implementation as a reference,
but with a different scientific estimand.

**Dead mouse eNRI is blank/NaN (NEVER 0).** Postmortem domain scores are also NaN.
Group×week means, within-group directional QP constraints, variance/covariance and
out-of-fold validation are calculated only from observed/imputed living mice.
Conditional state affine mean intercept is 1, NOT alive/all-count.

For 31 original feature, 3-factor domain, and 4-factor domain index:
- Refit preprocessing on train mice only, factor solutions on train baseline only.
- Compute Spearman-consistent baseline-frozen rank factor scores for living at
  W0/W16/W24; optimize weights with longitudinal-only 6 soft directional constraints.
- Parameters fixed beta=lambda=C=rho=.1, positive eNRI for train living mice.
- Mouse-stratified 3x3-fold CV: 36 training / 18 validation mice.
- Alternative handling of seven extreme late observations: clean133 vs full140.
- Constant-living=1 negative control, with zero after death NEVER used.
- Evaluate functional agreement of domain and 31-feature indices on living only.

Data accounting: 54 mice × 3 weeks = 162 rows; 140 living, 22 death.
On clean133: 133 living + 22 death rows (7 extreme living states omitted).
Postmortem CSV cells are blank as NaN, not imputed or set to 0.

Cautions: survivor bias across late weeks; no independent neuroplasticity ground truth;
regularization and constraints favor flatter scores; fixed feature set has prior data
exploration; 9 repeated folds are not 9 independent cohorts.
