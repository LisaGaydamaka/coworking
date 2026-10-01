# eNRI pooled week-0 experiment

Standalone rerun of the full base eNRI pipeline under pooled week-0 normalization.

Normalization:
- all included week-0 mice are pooled;
- every mouse has equal weight;
- mean eNRI over the pooled week-0 mice is exactly 1.

The experiment reruns base stages through final validation, including
hyperparameter selection, final QP, robustness/sensitivity, and the final
validation checks. It does not import persisted results from the earlier model.
