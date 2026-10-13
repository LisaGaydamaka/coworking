# Independent EFA26 robustness and Spearman rank-score correction

**Previous experiments untouched.** Builds on original full and cleaned processed matrices.

Core changes:
- Remove 3 exact baseline Learning sum duplicates and 2 nearly redundant NOR average-speed
  columns; retain NOR1/NOR2 total distance. p=26.
- Compare 26-feature parallel analysis with 28-feature old one.
- Main 1000-simulation PA with Gaussian null and independently permuted baseline columns
  (preserves ties and marginal distributions), and both ordinary correlation-matrix and
  reduced-correlation (SMC) common-factor eigenvalue tests.
- 52 observed-only baseline mice sensitivity (two imputed baseline states omitted),
  with 500 null simulations for its own thresholds.
- EFA MINRES+oblimin k=3 vs k=4, 500 bootstrap replicates on all 54 baseline mice
  and 250 on the 52 observed-only; Hungarian factor alignment.
- Quantitative correlation-model fit / residuals and mapping to old 28-feature domains.
- Correct **Spearman-rank-consistent frozen domain score projection** to weeks 16 and 24.
- Compare old raw-score formula against consistent rank-derived scores.
- Audit impact of restoring all 7 previously excluded postbaseline rows on rank domain scores.
  This sensitivity DOES NOT correct or validate extreme original raw readings.
- No changes to any source file or previous result.

Run: bash run.sh; browse results/REPORT.md and results/SUMMARY.json.
