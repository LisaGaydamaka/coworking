# ALL0MEAN eNRI feature-selection experiment

## Frozen normalization change

This rerun changes only the eNRI scale origin.

At week 0 there are four experimental states:
- PBS^0
- LPS^0
- run^0
- MCC^0

Within every training context, compute the mean feature vector separately for
each state and then average the FOUR state means with equal weight:

xbar_all0 = (xbar_PBS0 + xbar_LPS0 + xbar_run0 + xbar_MCC0) / 4.

Then:

eNRI_i = 1 + w^T (x_i - xbar_all0).

Therefore the arithmetic mean of the four training week-0 STATE means is 1.
This is deliberately an equal-state mean, not a pooled mouse-count-weighted
week-0 mean. Validation reuses the train-derived xbar_all0 exactly.

## Everything else remains frozen

- 54 mice after excluding 3.2 and 4.2.
- 30 weighted MODEL_FEATURES.
- Original 10 directional constraints, including run^24>LPS^24 and
  MCC^24>LPS^24.
- Five soft equalities.
- Death eNRI=0.
- Positivity epsilon=0.001.
- beta=0.1, lambda2=0.1, C=0.1, rho=0.1.
- IterativeImputer(BayesianRidge), deterministic, seed 20260928.
- Bounded autonomous reduced imputation.
- Stage A: correlation graph.
- Stage B: constrained Elastic-Net lambda1 path.
- Stage C: 200-resample stability selection.
- Stage D: block stability.
- Stage E: feature/block ablation.
- Stage F: block-aware ranking/compression and S3..S15.
- Stage G: sequential one-SE development k.
- Stage H: production nested validation, 30 outer x 20 inner x 100 stability.
- Stage K: the same fixed-subset stopping rule used in the previous experiment.

No selection rule is changed after inspecting Stage-H outer results.
