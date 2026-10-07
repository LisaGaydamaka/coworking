# PCA31 on the processed eNRI feature matrix

## Input

The experiment uses the exact 31-feature processed matrix produced by the
frozen GRIP31 preprocessing pipeline. No second standardization is applied.
PCA performs only its ordinary mean-centering.

Living rows: 137; week 0=54,
week 16=41, week 24=42.

## Pooled PCA

PC1 explained variance: **90.64%**.

Cumulative variance:
- PC1+PC2: 93.95%
- PC1+PC2+PC3: 95.73%
- components for 50%: 1
- components for 70%: 1
- components for 80%: 1
- components for 90%: 1

After the global sign convention, 4/6 specified
longitudinal group-mean directions are observed descriptively. These relations
were not used to fit PCA.

## Baseline PCA → later projection

PC1 explained variance within week 0: **33.11%**.

Cumulative variance:
- PC1+PC2: 52.36%
- PC1+PC2+PC3: 60.58%
- components for 50%: 2
- components for 70%: 5
- components for 80%: 8
- components for 90%: 12

Using the frozen week-0 PC1 direction, 3/6
longitudinal group-mean directions are observed descriptively.

## Relation between the two PC1 scores

Pearson correlation across the same living mouse×week rows:
**0.7590**.

Spearman correlation:
**0.7230**.

The sign convention is presentation-only. Multiplying any PC by -1 does not
change explained variance or the PCA solution.
