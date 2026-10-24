# Huber regression on PBS/LPS, Spearman rank-EFA 3 domains

Extends the earlier [Bayesian/Ridge experiment](../enri_mouse_neuroplasticity_forecast_rank3_bayesian_20261024/README.md). All prior results and components remain untouched.

**Source snapshots**: `input/clean133_k3_rank_frozen_scores.csv` (133 living visits from 54 baseline mice; full separately fitted k=3 Spearman MINRES-oblimin scores derived from 26 features) and `input/previous_bayesian_model_metrics.csv` (verified previous results). The script asserts Bayesian Ridge/Ridge/persistence/mean MAE match the prior report for all 12 tasks within 1e-8.

**Four intervals**: PBS 0→16 (9 pairs), PBS 16→24 (6), LPS 16→24 (11), PBS 0→24 (6); three domains D1 motor, D2 Learning/Endurance, D3 NOR1+NOR2; 12 separate scalar-to-scalar forecasts. No run or MCC and no post-baseline intervention predictors.

**Models**: HuberRegressor(epsilon=1.35,alpha=0.1) with fixed parameters; BayesianRidge(same weak Gamma priors as previous), Ridge(alpha=1), no-change baseline, mean-of-training-futures baseline. Each feature standardization is training-fold-only. Leave-one-mouse-out error estimates. No new parameter selection on held-out mice, no data synthesis.

**Results** (generated and committed by GitHub Actions in `results/`):
`model_metrics.csv` (MAE/RMSE/CV R²), `leave_one_mouse_out_predictions.csv`, `paired_mouse_scores.csv`, `REPORT.md`, `SUMMARY.json`, three numbered trajectory PNGs, `mean_trajectories.png`, `five_method_mae.png`, `winners.png`, `huber_actual_vs_prediction.png`, and the illustrated Russian Word report `Otchet_Huber_D1-D3_RANG_PBS_LPS_2026-10-24.docx`.

**Limitations**: fixed EFA/preprocessing originally fitted outside predictive LOOCV, so the full pipeline is NOT independently validated; results conditional on surviving paired mice; tiny n=6–11; no external test set.

**Run**: `bash run.sh`. Update this component's `.run` file to trigger the shared `.github/workflows/run-project.yml`, which commits generated outputs to this same folder.
