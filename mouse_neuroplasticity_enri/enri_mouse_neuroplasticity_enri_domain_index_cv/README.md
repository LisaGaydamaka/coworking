# Domain-based eNRI vs original eNRI: leakage-controlled benchmark

**Independent project. No prior experiment directories modified.**

Workflow includes **user points 1–4**:
1. Fit baseline EFA domain structures k=3 and k=4 using **26 variables**,
   omitting three exact Learning sum duplicates and two almost-identical NOR speeds.
   Score 54 mice at weeks 0/16/24 with baseline-frozen Spearman midranks.
2. Optimize weight vectors to construct a domain eNRI for k=3 and k=4 using
   a single affine index normalized to mean=1 at train baseline, deaths=0,
   positivity constraints on training living mice.
3. Validate by **9 stratified mouse-grouped outer CV splits** (3 repeats of 3-fold).
   Entire preprocessing/IterativeImputer fits train-only, EFA baseline train-only,
   rank templates train-only, and QP weights train-only.
4. Compare on identical held-out mouse states to original 31-feature eNRI refit
   from scratch using the **same constrained QP** parameters and six **within-group**
   temporal order inequalities (with slack). Treatment superiority is NOT encoded.
   Parameters fixed beta=.1, lambda=.1, C=.1, rho=.1; no tuning on validation.

Sensitivity: two identical evaluation schedules:
- clean133: the 7 previous flagged postbaseline mouse-weeks are excluded as missing
  rather than death (state denominators exclude the missing state).
- full140: all seven extreme states retained unchanged.

CAVEATS:
- Counts 133/140 refer to living states; the full longitudinal includes death rows.
- k=3 and k=4 were examined *before* this CV; CV here is an evaluation, not
  a fresh unbiased method-selection test.
- No external true neuroplasticity reference. Compare predictions/constraint
  metrics, not claimed treatment effects or causal neuroplasticity.
- The baseline EFA fits n≈36 in 3-fold training and p=26; small sample.
- Baseline-frozen ranks saturate above/below observed train-baseline range.
- Preprocessor uses only train mouse IDs, but all train weeks can influence
  statistical imputation of missing train-baseline entries. This is not a
  prospective baseline-only imputation model.
- The clean strategy omits bad-looking full mouse-weeks but does not impute
  replacement visits or treat them as deaths.
- Do not compare CV normalized eNRI scores across folds as if their scale were
  calibrated by the same training mice; analyze paired fold metrics.

Files: results/SUMMARY.json, results/REPORT_RU.md,
results/paired_grouped_cv_metrics.csv, results/cv_summary.csv,
results/paired_cv_delta_summary.csv, results/out_of_fold_mouse_week_predictions.csv,
results/fullfit_*_scores.csv, results/fullfit_*_loadings.csv.
