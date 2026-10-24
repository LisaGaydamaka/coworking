# Bootstrap aggregation on 3 rank-EFA domains / PBS and LPS

Within each LOOCV training fold, 100 bootstrap resamples of real training mouse-pairs (n−1 each, with replacement). Independent models fit per draw; predictions averaged. NO synthetic mice. Original heldout mouse never used in fitting/scaling.

| Transition | Domain | n | Ridge | Ridge boot | Bayes | Bayes boot | Huber | Huber boot | Persistence | Training mean | Best of 8 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PBS 0→16 | D1 | 9 | 1.200 | 1.194 | 1.055 | 1.155 | 1.220 | 1.221 | 1.052 | 1.052 | Среднее |
| PBS 0→16 | D2 | 9 | 0.882 | 0.912 | 0.967 | 0.948 | 1.043 | 0.964 | 0.798 | 0.895 | Без изменений |
| PBS 0→16 | D3 | 9 | 1.010 | 0.978 | 0.908 | 0.953 | 1.046 | 1.008 | 1.354 | 0.877 | Среднее |
| PBS 16→24 | D1 | 6 | 0.271 | 0.271 | 0.256 | 0.339 | 0.265 | 0.291 | 1.645 | 0.226 | Среднее |
| PBS 16→24 | D2 | 6 | 0.957 | 0.906 | 1.069 | 0.921 | 1.084 | 0.966 | 0.585 | 0.644 | Без изменений |
| PBS 16→24 | D3 | 6 | 1.610 | 1.557 | 1.604 | 1.744 | 1.804 | 1.704 | 1.148 | 1.117 | Среднее |
| LPS 16→24 | D1 | 11 | 0.724 | 0.721 | 0.667 | 0.701 | 0.768 | 0.749 | 1.766 | 0.665 | Среднее |
| LPS 16→24 | D2 | 11 | 0.322 | 0.318 | 0.348 | 0.359 | 0.282 | 0.358 | 0.307 | 0.970 | Huber|direct |
| LPS 16→24 | D3 | 11 | 1.152 | 1.154 | 1.328 | 1.240 | 1.083 | 1.106 | 1.003 | 1.352 | Без изменений |
| PBS 0→24 | D1 | 6 | 0.291 | 0.301 | 0.243 | 0.454 | 0.315 | 0.375 | 1.056 | 0.226 | Среднее |
| PBS 0→24 | D2 | 6 | 0.621 | 0.658 | 0.681 | 0.635 | 0.719 | 0.580 | 1.015 | 0.644 | Huber|bootstrap100 |
| PBS 0→24 | D3 | 6 | 0.770 | 0.773 | 0.822 | 0.754 | 0.788 | 0.759 | 2.161 | 1.117 | Bayesian Ridge|bootstrap100 |

Bootstrap beats direct in {'Ridge': 6, 'Bayesian Ridge': 5, 'Huber': 7}; bootstrap best of eight in 2/12.
Mean MAE: {'Ridge': {'plain': 0.8174780944177078, 'bootstrap100': 0.8119269616874399}, 'Bayesian Ridge': {'plain': 0.829014212185805, 'bootstrap100': 0.850160706684007}, 'Huber': {'plain': 0.868082451020275, 'bootstrap100': 0.8402187068807071}}. Mean number unique training mice in a bootstrap draw: 4.63.
Sensitivity 25/50/100 bootstraps is only a Monte Carlo convergence check, not hyperparameter optimization. No claims of reliable uncertainty intervals.
Input EFA/imputation precomputed outside outer LOOCV. Survivors-only paired samples; n=6–11, no external test.

Word report: results/Отчет_Bootstrap.docx
