# ALL0MEAN GRIP31: longitudinal-only directional constraints

This is a new, independent experiment. Historical experiment folders and
their source/results are not modified.

## Only scientific change

The historical ten directional inequalities are replaced by six longitudinal
inequalities comparing the same experimental branch over time:

1. PBS^0 > PBS^16
2. LPS^0 > LPS^16
3. run^0 > run^16
4. MCC^0 > MCC^16
5. PBS^16 > PBS^24
6. LPS^16 > LPS^24

No between-group directional inequality is used. In particular, the model is
not told that PBS must exceed LPS at weeks 16/24, nor that run/MCC must exceed
LPS at week 24. No direction is imposed for run or MCC between weeks 16 and 24.

## Frozen parts of the analysis

- Historical data/source code are imported read-only.
- Exclude mice 3.2 and 4.2; n=54.
- 31 weighted functional features: historical 30 + Grip.
- Grip mapping: model week 0 = Grip_0; week 16 = Grip_16; week 24 = Grip_22.
- CFI is excluded from the weighted feature vector.
- Pooled week-0 mouse-mean normalization: mean eNRI across all included
  baseline mice is exactly 1.
- Death eNRI = 0; living positivity epsilon = 0.001.
- Five soft equalities are unchanged.
- rho = 0.1.
- Base beta/lambda2/C are re-selected from scratch by the original Stage-6
  repeated stratified mouse-level CV grid under the six-constraint model.
- Stages A-G use the same correlation, L1, stability, ablation,
  block-compression and sequential one-SE rules.
- Stage H uses the same production nested validation: 30 outer x 20 inner x
  100 stability resamples.
- Stage K uses the same pre-specified stopping rule.
- No threshold or selection rule is changed after seeing the new results.

The purpose is to isolate the effect of removing all between-group directional
inequalities from the GRIP31 eNRI construction.
