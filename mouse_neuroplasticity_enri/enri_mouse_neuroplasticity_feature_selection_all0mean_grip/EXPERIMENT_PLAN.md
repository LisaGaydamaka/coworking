# Pooled week-0 eNRI + Grip: full feature-selection experiment

This is an independent rerun of the same frozen analysis procedure.

## Only data/model-definition change
- CFI is excluded.
- Grip is added as weighted feature 31.
- model week 0 uses `Grip_0`.
- model week 16 uses `Grip_16`.
- model week 24 uses `Grip_22` by pre-specified equivalence of the 22-week grip measurement to the 24-week model visit.

## Normalization
The arithmetic mean eNRI across all included mice at model week 0 is exactly 1; every mouse has equal weight.

## Frozen procedure
- Exclude mice 3.2 and 4.2; n=54.
- Repeat QC and train-only preprocessing from scratch.
- Re-select base QP hyperparameters by the original Stage-6 CV grid before feature selection.
- Keep 5 soft equalities, 10 directional constraints, rho=0.1, death eNRI=0 and positivity epsilon=0.001.
- Stage A: Spearman and group-centered correlation blocks.
- Stage B: constrained L1 path and sequential one-SE lambda1 selection.
- Stage C: 200 mouse-level stability resamples.
- Stage D: block stability.
- Stage E: paired feature/block ablation.
- Stage F: block-aware ranking/compression and S3..S15.
- Stage G: sequential one-SE development k.
- Stage H: production nested validation, 30 outer x 20 inner x 100 stability.
- Stage K: the same pre-specified stopping rule for one fixed reduced subset.

No threshold or selection rule is changed after seeing the Grip results.
