# eNRI GRIP31 — longitudinal-only rerun

Independent experiment derived from the existing ALL0MEAN GRIP31 pipeline.

The old experiment folders are read-only inputs. This directory contains all
new code copies, generated outputs, nested-validation results and summaries.

Run entry point:

```bash
bash run.sh
```

Model change: only six within-group longitudinal order inequalities are active;
all between-group directional inequalities are removed.
