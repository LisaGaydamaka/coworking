# PCA31 sensitivity analysis excluding seven full mouse×week states

Independent experiment. Previous PCA and eNRI folders are not modified.

Excluded entire states:
- 8.4 @ week 16
- 8.2 @ week 16
- 8.3 @ week 16
- 9.2 @ week 24
- 17.1 @ week 24
- 21.4 @ week 24
- 16.1 @ week 24

For each excluded state, all 31 processed feature values are removed together.

No repeated standardization is performed. PCA only mean-centers the already
processed 31-feature matrix.

Expected retained living rows:
- week 0: 54
- week 16: 41
- week 24: 38
- total: 133

Both pooled PCA and baseline-week0 PCA with frozen projection are produced.
