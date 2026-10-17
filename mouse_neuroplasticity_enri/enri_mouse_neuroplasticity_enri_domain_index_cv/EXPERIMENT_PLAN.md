# Prespecified benchmark plan
- Three models: historical 31-feature, 3-domain and 4-domain index.
- Same 31-feature train-only eNRI preprocessing across models to avoid unequal
  imputation; domains select fixed list of 26 variables afterward.
- Baseline EFA MINRES oblimin on Spearman, semantic factor anchors used only
  for labeling and orientation, with no group/outcome-specific selection.
- Train-only baseline midranks and regression factor scores, frozen to 16/24.
- QP identical to original longitudinal-only (6 within-group monotonicity rules,
  5 soft equalities, equal-weight 12-state covariance term, train positivity).
- Original eNRI and both domain eNRI fitted anew for every mouse-grouped split.
- Fixed beta=lambda=C=rho=0.1 from historical experiments.
- Evaluate heldout positivity violation, sign/margin, equality error, variance
  and relation to original eNRI; no external neuroplasticity target.
- Nine CV folds: three stratified 3-fold repeated seeds, not nested tuning because
  hyperparameters and feature list are fixed in advance.
- Sensitivity: exclude or retain seven known anomalous postbaseline mouse-weeks.
  Never conflate missing states with death score zero.
- Fit all models on full 54 mice only after validation for descriptive tables.
