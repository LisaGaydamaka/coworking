# Huber vs Bayesian Ridge vs Ridge / 3 rank-EFA domains / PBS+LPS

**Inputs**: k=3 baseline-frozen Spearman EFA on full 26 features. 54 baseline mice and 133 living visits. PBS and LPS only. Four transitions: PBS 0→16, PBS 16→24, LPS 16→24, PBS 0→24.

**Models**: HuberRegressor(epsilon=1.35, alpha=0.1) fixed beforehand, BayesianRidge(Gamma priors 1e-6), Ridge(alpha=1), persistence, training-only future mean. One starting domain predictor, x scaled within training fold; leave-one-mouse-out. Historical Bayesian and Ridge errors checked to 1e-8.

| Interval | Domain | n | Huber MAE | Bayes MAE | Ridge MAE | Persistence MAE | Train-mean MAE | Winner |
|---|---|---:|---:|---:|---:|---:|---:|---|
| PBS 0→16 | D1 | 9 | 1.220 | 1.055 | 1.200 | 1.052 | 1.052 | Среднее |
| PBS 0→16 | D2 | 9 | 1.043 | 0.967 | 0.882 | 0.798 | 0.895 | Без изменений |
| PBS 0→16 | D3 | 9 | 1.046 | 0.908 | 1.010 | 1.354 | 0.877 | Среднее |
| PBS 16→24 | D1 | 6 | 0.265 | 0.256 | 0.271 | 1.645 | 0.226 | Среднее |
| PBS 16→24 | D2 | 6 | 1.084 | 1.069 | 0.957 | 0.585 | 0.644 | Без изменений |
| PBS 16→24 | D3 | 6 | 1.804 | 1.604 | 1.610 | 1.148 | 1.117 | Среднее |
| LPS 16→24 | D1 | 11 | 0.768 | 0.667 | 0.724 | 1.766 | 0.665 | Среднее |
| LPS 16→24 | D2 | 11 | 0.282 | 0.348 | 0.322 | 0.307 | 0.970 | Huber |
| LPS 16→24 | D3 | 11 | 1.083 | 1.328 | 1.152 | 1.003 | 1.352 | Без изменений |
| PBS 0→24 | D1 | 6 | 0.315 | 0.243 | 0.291 | 1.056 | 0.226 | Среднее |
| PBS 0→24 | D2 | 6 | 0.719 | 0.681 | 0.621 | 1.015 | 0.644 | Ridge |
| PBS 0→24 | D3 | 6 | 0.788 | 0.822 | 0.770 | 2.161 | 1.117 | Ridge |

Huber < Ridge: 3/12; Huber < Bayesian: 3/12; Huber < both simple baselines: 2/12; Huber best out of five: 1/12.

**Caveats**: n=6–11. LOOCV only on fixed precomputed EFA scores, not end-to-end leakage-free baseline preprocessing. Only surviving paired mice; no external validation; no synthetic augmentation. Pooled interpretation across different experimental exposures is not supported.

Report: results/Otchet_Huber_D1-D3_RANG_PBS_LPS_2026-10-24.docx.
