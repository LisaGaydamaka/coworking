# Ridge direct versus Ridge for target ΔD

Ridge direct: yhat = a + bx. Ridge for change: delta_hat = a + bx, yhat=x+delta_hat. Both alpha=1 and input standardized only on training mice.

All 12 matched PBS/LPS tasks; baseline-frozen separate rank Spearman 3-factor EFA on 26 features. Same folds. No synthetic data.

| Transition | Domain | n | ΔD Ridge MAE | Direct Ridge MAE | Unchanged MAE | Mean MAE | Best |
|---|---|---:|---:|---:|---:|---:|---|
| PBS 0→16 | D1 | 9 | 1.220 | 1.200 | 1.052 | 1.052 | Среднее |
| PBS 0→16 | D2 | 9 | 0.865 | 0.882 | 0.798 | 0.895 | Без изменений |
| PBS 0→16 | D3 | 9 | 1.058 | 1.010 | 1.354 | 0.877 | Среднее |
| PBS 16→24 | D1 | 6 | 0.296 | 0.271 | 1.645 | 0.226 | Среднее |
| PBS 16→24 | D2 | 6 | 0.940 | 0.957 | 0.585 | 0.644 | Без изменений |
| PBS 16→24 | D3 | 6 | 1.625 | 1.610 | 1.148 | 1.117 | Среднее |
| LPS 16→24 | D1 | 11 | 0.712 | 0.724 | 1.766 | 0.665 | Среднее |
| LPS 16→24 | D2 | 11 | 0.354 | 0.322 | 0.307 | 0.970 | Без изменений |
| LPS 16→24 | D3 | 11 | 1.103 | 1.152 | 1.003 | 1.352 | Без изменений |
| PBS 0→24 | D1 | 6 | 0.345 | 0.291 | 1.056 | 0.226 | Среднее |
| PBS 0→24 | D2 | 6 | 0.625 | 0.621 | 1.015 | 0.644 | Ridge |
| PBS 0→24 | D3 | 6 | 0.829 | 0.770 | 2.161 | 1.117 | Ridge |

ΔD beats direct Ridge: 4/12; best of all four: 0/12.

**Limitations**: preprocessing and EFA learned before CV; no test independent of EFA. Paired survivors only, n=6–11, no intervention claims.

Word report: results/Otchet_Ridge_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx. Other result CSVs and PNGs in same directory.
