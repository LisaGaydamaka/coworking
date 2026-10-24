# Ridge for change ΔD versus direct Ridge · rank-EFA3 · PBS/LPS

Independent comparison of **two Ridge targets** on exactly the same three Spearman rank-EFA domains and matched mice. Original experiments are untouched.

- Input: frozen three-factor MINRES/oblimin scores built from all 26 features on 54 baseline mice, projected to 133 living mouse–week states. A snapshot is versioned in `input/clean133_k3_rank_frozen_scores.csv`.
- Tasks: PBS 0→16 (n=9), PBS 16→24 (n=6), LPS 16→24 (n=11), PBS 0→24 (n=6), each D1 motor/OFT, D2 learning/endurance, D3 NOR1+NOR2 = **12 tasks**. No run/MCC, no future intervention features.
- Direct Ridge baseline: `Ridge(alpha=1)` predicts y = future domain score from x = current score.
- Change Ridge experiment: **same** `Ridge(alpha=1)` predicts Δ=y−x from x, then final forecast `x + predicted_delta`.
- Other baselines: unchanged (`yhat=x`) and training-fold future mean.
- Outer leave-one-mouse-out CV; both Ridge variants standardize the input predictor on training mice *within* each fold; no hyperparameter search.
- Historical direct Ridge MAE for all 12 cells are **asserted** (absolute tolerance 0.000003); outputs are computed from the versioned input, not typed-in results.
- Outputs under `results/`: `model_metrics.csv`, `leave_one_mouse_out_predictions.csv`, `paired_mouse_scores.csv`, `REPORT.md`, `SUMMARY.json`, figures, and `Otchet_Ridge_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx` (four-page illustrated Word report, same earlier style).

**Why it can differ from direct Ridge**: with an intercept and fixed regularization, learning Δ shrinks the resulting slope for predicting y toward **1** (unchanged score), while direct Ridge shrinks it toward **0** (mean predicted score). Unregularized OLS would be equivalent under this reparameterization.

**Important limits**: EFA and source imputation were fit before forecast CV, so this is validation of regressions *conditional on precomputed domain scores*, not fully leakage-free end-to-end CV. Small n and survivor selection; no external validation or new synthetic mice.

Launch: `bash run.sh`; for GitHub Actions change `.run` only. The existing shared `.github/workflows/run-project.yml` runs and commits outputs into this same component.
