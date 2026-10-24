# Bayesian Ridge & Huber for domain changes ΔD · rank-EFA3 PBS/LPS

Independent experimental component. Prior projects and GitHub workflows remain untouched.

**Data**: immutable `input/clean133_k3_rank_frozen_scores.csv` snapshot from `enri_mouse_neuroplasticity_efa26_robust_validation_rank_scores`: separately fitted 3-factor Spearman MINRES-oblimin scores from 26 features, 54 baseline mice, 133 living mouse-week states.

**12 tasks**: D1 motor/OFT, D2 learning/endurance, D3 NOR1+NOR2 each on PBS 0→16 (9 paired mice), PBS 16→24 (6), LPS 16→24 (11), PBS 0→24 (6). No run/MCC prediction tasks, no new interventions.

**Targets and models**: direct future score versus ΔD=future−current and reconstructed future=current+predicted ΔD. Compare 8 fixed methods: BayesianRidge on direct/Δ (Gamma prior hyperparameters 1e-6), HuberRegressor on direct/Δ (epsilon=1.35, alpha=0.1, max_iter=1500), Ridge on direct/Δ (alpha=1), persistence and mean of training future scores. Same initial domain predictor for all, training-fold-only feature scaling, one-mouse-out CV; no hyperparameter optimization on held-out mice. Frozen prior results are verified through exact MAE checks (tolerance 1e-7) for previously published direct Huber/Bayesian/Ridge and Δ Ridge models.

**Outputs**: `results/model_metrics.csv`, `results/leave_one_mouse_out_predictions.csv`, `results/paired_mouse_scores.csv`, `results/REPORT.md`, `results/SUMMARY.json`, charts and the illustrated Russian `results/Otchet_Bayesian_Huber_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx`.

**Limits**: domain scores and original imputations fitted outside predictive CV; only downstream regressions are checked, not a leakage-free full pipeline. Survivors-only paired samples n=6–11, no external validation, multiple model comparisons, no synthetic data.

**Run**: `bash run.sh`; the shared `.github/workflows/run-project.yml` is triggered when **only** this component's `.run` changes and commits generated results within this component.
