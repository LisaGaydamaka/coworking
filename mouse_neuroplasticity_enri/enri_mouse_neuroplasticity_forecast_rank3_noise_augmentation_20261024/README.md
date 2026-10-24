# Training-input noise augmentation · 3 Spearman rank-EFA domains · PBS/LPS

Independent component under `mouse_neuroplasticity_enri`. Earlier code/results unchanged.

**Input**: frozen k=3 rank-EFA scores for 133 living mouse visits (from 26 features, 54 baseline mice), copied from `enri_mouse_neuroplasticity_efa26_robust_validation_rank_scores/results/clean133_k3_rank_frozen_scores.csv`. D1 OFT, D2 Learning/Endurance, D3 NOR1+NOR2.

**Matched tasks** (12): PBS 0→16 n=9, PBS 16→24 n=6, LPS 16→24 n=11, PBS 0→24 n=6; no run/MCC forecasts. Per-domain univariate predictions. Same mice and fixed nonaugmented models as previous GitHub analyses.

**Prespecified primary augmentation**: Gaussian noise 0.10 × SD of the baseline current-domain input *estimated using training mice only*. For sensitivity, 0.05 and 0.20. Seed 20261024; 20 independent fits/repeat, with **one perturbed predictor per real training mouse per fit**, leaving each mouse's true target unchanged and averaging 20 held-out predictions. This is an input-jitter ensemble, **not creating 20 additional independent mice**. Validation mouse untouched and never involved in normalization. Compare against:
- Ridge(alpha=1) direct with and without noise;
- BayesianRidge (weak gamma hyperpriors) with and without noise;
- Huber(epsilon=1.35, alpha=0.1) with and without noise;
- Persistence / future training-mean. Total 8 methods in primary comparison.
Every method uses leave-one-mouse-out. No post hoc choice of noise per task; 5% and 20% results are descriptive sensitivity only. An assertion checks that all 12 historic unaugmented Ridge errors reproduce to <0.000001.

**GitHub Actions**: `bash run.sh` from this folder, triggered when `.run` changes using shared `.github/workflows/run-project.yml`. Results are committed under this component's `results/`. `results/Otchet_Shymovaya_Augmentaciya_D1-D3_RANG_PBS_LPS_2026-10-24.docx` is a 4-page illustrated Russian Word report; CSVs include per-mouse predictions and full 5%/10%/20% sensitivity. Plots show labeled trajectories, mean evolution, MAE comparisons, winning method and fact-vs-forecast.

**Limits**: only n=6–11 paired surviving animals per task; EFA and source imputation were pre-computed outside CV (not a leak-free prospective full pipeline); synthetic measurements are not independent animals. Very small changes in MAE should not be interpreted as validated predictive improvement.
