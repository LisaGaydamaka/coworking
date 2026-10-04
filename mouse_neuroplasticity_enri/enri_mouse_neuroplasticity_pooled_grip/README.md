# eNRI pooled week-0 experiment with Grip

Independent full rerun.

Changes relative to the 30-feature pooled experiment:
- CFI is not used.
- Grip is added as the 31st weighted feature.
- Grip_0 is model week 0.
- Grip_16 is model week 16.
- Grip_22 is treated as model week 24.
- Baseline normalization remains the equal-mouse arithmetic mean across all included week-0 mice = 1.

Everything else is rerun from scratch: QC/preprocessing, hyperparameter CV, final constrained QP, robustness/sensitivity, 25 final checks, and the full feature-selection pipeline in the companion Grip project.
