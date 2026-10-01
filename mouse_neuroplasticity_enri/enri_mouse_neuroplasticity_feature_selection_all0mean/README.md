# eNRI feature selection — ALL0MEAN

Independent rerun of the latest feature-selection pipeline.

The only intentional model change is normalization:
the value 1 is anchored to the pooled arithmetic mean eNRI of all included
mice at week 0. Each mouse has equal weight; week-0 group means are not
averaged first.

Pipeline:
Stage 0 -> A -> B -> C -> D -> E -> F -> G -> H production -> K.

See EXPERIMENT_PLAN.md for the frozen definition.
