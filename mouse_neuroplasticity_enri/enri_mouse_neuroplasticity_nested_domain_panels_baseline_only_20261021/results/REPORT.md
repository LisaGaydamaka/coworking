# Fully nested baseline-only EFA panel validation

Baseline 54 mice, 26 predictors. All preprocessing refit using outer-training mouse IDs; no future visits used. 2x5 outer stratified folds. Full EFA MINRES oblimin refit separately for k=3/4 in every outer fold. Rank transformations and regression score weights learned from training mice, forward Ridge alpha=.03, inner 3-fold CV choosing 1-5 predictors, r>=.90 and RMSE <=110% min. Holdout tested exactly once per repetition. 150 bootstrap repeats refit whole procedure on resampled mice.

## Results

| k | Domain | Out-of-fold r | RMSE | Median selected predictors | Accepted inner size rule |
|--:|---|---:|---:|---:|---:|
| 3 | D1 | 0.871 | 0.594 | 3.0 | 100% |
| 3 | D2 | 0.810 | 0.641 | 4.0 | 100% |
| 3 | D3 | 0.867 | 0.558 | 4.0 | 100% |
| 4 | D1 | 0.893 | 0.531 | 3.0 | 100% |
| 4 | D2 | 0.916 | 0.451 | 4.0 | 100% |
| 4 | D3 | 0.852 | 0.594 | 4.0 | 100% |
| 4 | D4 | 0.432 | 1.118 | 5.0 | 20% |

## Limitations

Factor labeling uses prior full-data EFA for orientation only; earlier feature-list engineering from these mice remains a source of exploratory optimism.
Reference full scores for heldout mice use all 26 observed predictors as ground truth; this tests reduction, not prospective biological validity.
Repeated folds share mice, hence pooled heldout correlation is not an independent-sample confidence interval.
No longitudinal prediction, intervention contrasts, survival prediction or independent external cohort validation has been performed.
See SUMMARY.csv, feature_frequencies.csv and fold/bootstrap CSVs for details.
