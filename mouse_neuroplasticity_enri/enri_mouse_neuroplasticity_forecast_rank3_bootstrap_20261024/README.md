# Bootstrap aggregation / 3 rank-EFA domains / PBS and LPS

Independent mouse eNRI forecast experiment. All prior experiments preserved.

## Data and tasks

- Versioned input: `input/clean133_k3_rank_frozen_scores.csv`, copied from the 26-feature Spearman MINRES-oblimin EFA3 baseline-frozen scores. 54 baseline mice, 133 living mouse-week rows. Baseline EFA not refit here.
- Forecast cohorts: PBS 0→16 (9 paired mice), PBS 16→24 (6), LPS 16→24 (11), PBS 0→24 (6). D1 motor/OFT, D2 Learning/Endurance, D3 joint NOR1/NOR2: 12 scalar forecast tasks.
- No run/MCC prediction tasks, no interventions included as predictors.

## Experiment

- Compare direct Ridge(alpha=1.0), BayesianRidge(weak Gamma priors 1e-6), HuberRegressor(epsilon=1.35, alpha=0.1), with and without bootstrap aggregation. Also compare no-change and mean-of-training-future benchmarks, eight alternatives total.
- Leave-one-mouse-out: first exclude one real mouse entirely; learn x-centering/scaling only from remaining mice.
- For each fold, draw **100 bootstrap samples**, each of size n_train, **with replacement among real training mouse-pairs**. Fit the same estimator on each sample and average the 100 forecasts for the untouched real mouse. Duplicated mice in one resample are **not new independent observations**. Sampled indices are shared across algorithms within a fold.
- Prespecified 100 repetitions, fixed seed 20261024; partial ensembles at 25 and 50 repetitions are only for convergence sensitivity, not to select a preferred count using the holdout results.
- Prior 12-task direct Ridge MAE values reproduced within 1e-6 by assertion.

## Outputs / GitHub Actions

`run.sh` installs dependencies and executes `run_forecasts.py`; modifying only `.run` triggers the shared workflow `.github/workflows/run-project.yml`. All outputs are committed to `results/`:

- `model_metrics.csv`: per task MAE, RMSE for all algorithms and bootstrap counts;
- `leave_one_mouse_out_predictions.csv`: each excluded mouse's true and predicted values;
- `paired_mouse_scores.csv`: paired visits;
- `SUMMARY.json`, `REPORT.md`;
- `Отчет_Bootstrap.docx` (four-page illustrated Russian Word report; same style as previous reports), PNG graphs: 3 labeled trajectories, mean trends, MAE, best-method heatmap, Ridge bootstrap scatter, and bootstrap-count sensitivity.

## Methodological limits

Only n=6–11 paired surviving mice per task. Existing EFA and the upstream imputations were prepared outside cross-validation; this validates the downstream regression **conditional on frozen scores**, not an end-to-end leakage-free prospective pipeline. Bootstrapping a tiny training sample does not create new information. The standard deviation of bootstrap predictions is *not* an externally calibrated prediction interval. No independent holdout dataset and no claim of biological generalization; multiple methods were tested on the same small validation sets.
