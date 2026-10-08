# PC1 loading similarity across weeks in end-surviving mice

Each group×week PCA was fit independently on 31 baseline-standardized processed variables,
without restandardization; PC1 loadings are sklearn PCA unit eigenvector coefficients.

Similarity is absolute cosine (sign-invariant); its arccos gives principal angle in degrees.

## Similarity table

| group   |   0_vs_16 |   0_vs_24 |   16_vs_24 |
|:--------|----------:|----------:|-----------:|
| PBS     |     0.699 |     0.599 |      0.824 |
| LPS     |     0.648 |     0.664 |      0.899 |
| run     |     0.537 |     0.382 |      0.346 |
| MCC     |     0.812 |     0.733 |      0.739 |

## Paired-bootstrap diagnostics

- PBS 0→16: cos=0.699, angle=45.7°, bootstrap median=0.504, q2.5–q97.5=0.031–0.772.
- PBS 0→24: cos=0.599, angle=53.2°, bootstrap median=0.418, q2.5–q97.5=0.026–0.699.
- PBS 16→24: cos=0.824, angle=34.5°, bootstrap median=0.708, q2.5–q97.5=0.083–0.864.
- LPS 0→16: cos=0.648, angle=49.6°, bootstrap median=0.589, q2.5–q97.5=0.033–0.740.
- LPS 0→24: cos=0.664, angle=48.4°, bootstrap median=0.589, q2.5–q97.5=0.081–0.787.
- LPS 16→24: cos=0.899, angle=26.0°, bootstrap median=0.779, q2.5–q97.5=0.130–0.898.
- run 0→16: cos=0.537, angle=57.5°, bootstrap median=0.520, q2.5–q97.5=0.029–0.821.
- run 0→24: cos=0.382, angle=67.5°, bootstrap median=0.353, q2.5–q97.5=0.068–0.745.
- run 16→24: cos=0.346, angle=69.7°, bootstrap median=0.352, q2.5–q97.5=0.036–0.824.
- MCC 0→16: cos=0.812, angle=35.7°, bootstrap median=0.518, q2.5–q97.5=0.101–0.868.
- MCC 0→24: cos=0.733, angle=42.9°, bootstrap median=0.626, q2.5–q97.5=0.096–0.831.
- MCC 16→24: cos=0.739, angle=42.3°, bootstrap median=0.684, q2.5–q97.5=0.058–0.834.

## Interpretation caveats

Independent PCA at each week can change direction. High PC1% does not itself show persistent PC1 loadings.
Very small n relative to 31 features makes each PC1 loading vector noisy.
Bootstrap distributions are descriptive and may be unstable with this sample size.
Matched complete-case sensitivity recomputes every weekly PCA on exactly the same survivor mice with all 3 retained visits; see CSV.
Only animals alive at week 24 enter the analysis. This conditions on survival and is not a population-wide aging estimate.
