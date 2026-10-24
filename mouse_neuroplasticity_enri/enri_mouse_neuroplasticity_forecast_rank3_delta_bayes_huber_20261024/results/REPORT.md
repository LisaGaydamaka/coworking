# Bayesian Ridge and Huber on ΔD versus previous direct forecasts

Baseline: 3 domains (Spearman rank EFA / 26 features), PBS and LPS only; 12 tasks on paired surviving mice.

Targets: ΔD = D_future - D_now. Final prediction D_future_hat = D_now + ΔD_hat. Same start-domain predictor, same parameters and same leave-one-mouse-out splits as direct models. No model hyperparameter tuning on held-out mice.

| Interval | Domain | n | Bayesian Δ | Huber Δ | Ridge Δ | Bayesian | Huber | Ridge | Unchanged | Mean | Best |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PBS 0→16 | D1 | 9 | 1.396 | 1.223 | 1.220 | 1.055 | 1.220 | 1.200 | 1.052 | 1.052 | Среднее |
| PBS 0→16 | D2 | 9 | 0.925 | 1.045 | 0.865 | 0.967 | 1.043 | 0.882 | 0.798 | 0.895 | Без изменений |
| PBS 0→16 | D3 | 9 | 1.093 | 1.055 | 1.058 | 0.908 | 1.046 | 1.010 | 1.354 | 0.877 | Среднее |
| PBS 16→24 | D1 | 6 | 0.273 | 0.259 | 0.296 | 0.256 | 0.265 | 0.271 | 1.645 | 0.226 | Среднее |
| PBS 16→24 | D2 | 6 | 0.828 | 1.080 | 0.940 | 1.069 | 1.084 | 0.957 | 0.585 | 0.644 | Без изменений |
| PBS 16→24 | D3 | 6 | 1.447 | 1.798 | 1.625 | 1.604 | 1.804 | 1.610 | 1.148 | 1.117 | Среднее |
| LPS 16→24 | D1 | 11 | 0.725 | 0.768 | 0.712 | 0.667 | 0.768 | 0.724 | 1.766 | 0.665 | Среднее |
| LPS 16→24 | D2 | 11 | 0.367 | 0.285 | 0.354 | 0.348 | 0.282 | 0.322 | 0.307 | 0.970 | Huber |
| LPS 16→24 | D3 | 11 | 1.094 | 1.077 | 1.103 | 1.328 | 1.083 | 1.152 | 1.003 | 1.352 | Без изменений |
| PBS 0→24 | D1 | 6 | 0.328 | 0.319 | 0.345 | 0.243 | 0.315 | 0.291 | 1.056 | 0.226 | Среднее |
| PBS 0→24 | D2 | 6 | 0.643 | 0.719 | 0.625 | 0.681 | 0.719 | 0.621 | 1.015 | 0.644 | Ridge |
| PBS 0→24 | D3 | 6 | 0.778 | 0.817 | 0.829 | 0.822 | 0.788 | 0.770 | 2.161 | 1.117 | Ridge |

Comparisons: {"Bayesian Δ beats direct": 6, "Huber Δ beats direct": 6, "Bayesian Δ beats both simple": 2, "Huber Δ beats both simple": 2, "Bayesian Δ best of 8": 0, "Huber Δ best of 8": 0, "Either new method best of 8": 0, "prior models verified": true}

Important: cross-validation only of regressions given fixed EFA scores. Upstream imputation can leak future data. Survivor selection. n=6–11. 12 tasks × many methods: individual wins can be accidental. No external dataset.

Word report: results/Otchet_Bayesian_Huber_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx. CSV tables and all plots are in results/.
