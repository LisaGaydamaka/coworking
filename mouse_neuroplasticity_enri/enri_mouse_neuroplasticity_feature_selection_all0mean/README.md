# eNRI feature selection — ALL0MEAN

Independent rerun of the latest feature-selection pipeline.

The only intentional model change is normalization:
the value 1 is anchored to the equal arithmetic mean of the four experimental
states at week 0 (PBS^0, LPS^0, run^0, MCC^0), rather than PBS^0 alone.

Pipeline:
Stage 0 -> A -> B -> C -> D -> E -> F -> G -> H production -> K.

See EXPERIMENT_PLAN.md for the frozen definition.
