# Bayesian Ridge versus prior Ridge / PBS, LPS / 3 frozen rank-EFA domains

**Inputs**: baseline-frozen Spearman EFA k=3 full 26 features; 54 baseline mice, 133 living states. Only PBS/LPS used for predictions.

**Evaluation**: 4 intervals, 12 tasks, one scalar starting domain as sole predictor, LOOCV by mouse. BayesianRidge defaults for gamma priors, no hyperparameter search; Ridge(alpha=1.0) baseline from previous report. Both standardize only the training x in each fold.

| Interval | Domain | n | Bayes MAE | Ridge MAE | Unchanged MAE | Train-mean MAE | Winner |
|---|---|---:|---:|---:|---:|---:|---|
| PBS 0→16 | D1 | 9 | 1.055 | 1.200 | 1.052 | 1.052 | Среднее |
| PBS 0→16 | D2 | 9 | 0.967 | 0.882 | 0.798 | 0.895 | Без изменений |
| PBS 0→16 | D3 | 9 | 0.908 | 1.010 | 1.354 | 0.877 | Среднее |
| PBS 16→24 | D1 | 6 | 0.256 | 0.271 | 1.645 | 0.226 | Среднее |
| PBS 16→24 | D2 | 6 | 1.069 | 0.957 | 0.585 | 0.644 | Без изменений |
| PBS 16→24 | D3 | 6 | 1.604 | 1.610 | 1.148 | 1.117 | Среднее |
| LPS 16→24 | D1 | 11 | 0.667 | 0.724 | 1.766 | 0.665 | Среднее |
| LPS 16→24 | D2 | 11 | 0.348 | 0.322 | 0.307 | 0.970 | Без изменений |
| LPS 16→24 | D3 | 11 | 1.328 | 1.152 | 1.003 | 1.352 | Без изменений |
| PBS 0→24 | D1 | 6 | 0.243 | 0.291 | 1.056 | 0.226 | Среднее |
| PBS 0→24 | D2 | 6 | 0.681 | 0.621 | 1.015 | 0.644 | Ridge |
| PBS 0→24 | D3 | 6 | 0.822 | 0.770 | 2.161 | 1.117 | Ridge |

Bayesian Ridge beats Ridge: 6/12; best of 4: 0/12.

**Caveats**: EFA and original imputations fit prior to LOOCV and not re-estimated within training folds. No independent holdout; complete-case survivor pairs only. Differences between conditions are not modeled; run/MCC excluded. No augmentation/synthetic mice.

See results/Otchet_Bayesian_Ridge_D1-D3_RANG_PBS_LPS_2026-10-24.docx for four-page illustrated report; full paired data and LOOCV predictions in CSV.
