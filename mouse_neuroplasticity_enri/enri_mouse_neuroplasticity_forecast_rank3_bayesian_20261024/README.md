# Rank-EFA3 PBS/LPS longitudinal forecasting: prior Ridge and Bayesian Ridge

This is the GitHub home for the prior 3-domain forecast (not previously committed) and the Bayesian Ridge comparison. Original EFA, raw/preprocessing, and other experiments are **not modified**.

**Input**: versioned copy of `enri_mouse_neuroplasticity_efa26_robust_validation_rank_scores/results/clean133_k3_rank_frozen_scores.csv` (133 living visits; 54 baseline mice; k=3 separate MINRES/oblimin Spearman EFA; 26 original features).

**Tasks** (3 domains each, 12 in total): PBS 0→16 (9 matched mice), PBS 16→24 (6), LPS 16→24 (11), PBS 0→24 (6). Same subject at both visits; exclude run/MCC. D3 is joint NOR1/NOR2.

**Models**:
1. Prior Ridge(alpha=1), one current-domain predictor, training-fold x standardization — exact reproduction of the previously delivered report (checked MAE within 0.000003).
2. BayesianRidge(default weak Gamma hyperpriors, max_iter=300), also one current-domain predictor, training-fold x standardization.
3. Persistence: future score = current score.
4. Training-only future mean.

All evaluated leave-one-mouse-out. No synthetic mice or new treatments. Results saved under `results/`:
- `previous_ridge_reproduced.csv` = historical three-domain Ridge benchmark for all 12 tasks
- `model_metrics.csv`, `leave_one_mouse_out_predictions.csv`, `paired_mouse_scores.csv`
- `REPORT.md`, `SUMMARY.json`
- `Otchet_Bayesian_Ridge_D1-D3_RANG_PBS_LPS_2026-10-24.docx` = illustrated four-page report in the original visual style
- PNG figures for trajectories and CV.

**Caveats**: scores and imputation were previously learned from the full baseline data (and upstream preprocessing may use follow-up visits). Thus CV validates only the forecasting regression conditional on already computed factors, not the full pipeline. Only paired surviving mice are modeled. Bayesian nominal predictive uncertainty may be poorly calibrated at n=6–11.

Run: `bash run.sh`. To launch through GitHub Actions, update **only** this component's `.run` file; shared `.github/workflows/run-project.yml` runs and commits the results.
