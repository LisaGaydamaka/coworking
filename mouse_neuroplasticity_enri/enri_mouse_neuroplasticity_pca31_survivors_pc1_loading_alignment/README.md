# PC1 loading similarity: end-of-experiment survivors

Independent GitHub experiment; previous experiments are read-only.

End survivors: 42 mice identified by a living week-24 row before outlier-state exclusions.
The seven states excluded by the previous PCA cleaning remain excluded. Use exactly
the 31 processed features from that experiment. Fit PCA independently per group×week,
with no new standardization. Compare absolute cosine of 31-dimensional unit PC1
vectors for 0↔16, 0↔24, 16↔24 in each group; report principal angles, top loadings,
1000 paired mouse-bootstrap resamples, and a complete-case sensitivity analysis.
