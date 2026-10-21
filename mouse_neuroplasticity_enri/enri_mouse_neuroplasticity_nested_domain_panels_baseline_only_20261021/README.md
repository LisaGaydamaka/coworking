# End-to-end nested baseline-only EFA panel selection

Independent experiment; old files untouched. Runs 2x5 outer stratified CV and 150 bootstrap re-fits with training-mouse-only original Excel preprocessing, Spearman EFA (k=3/4), rank scores, inner forward Ridge selection. Inner panel sizes 1-5. The 26-feature full scores are the reconstruction target. This is an internal reduction study, not independent mouse validation or survival prediction.

Run `bash run.sh`. Results in results/.
