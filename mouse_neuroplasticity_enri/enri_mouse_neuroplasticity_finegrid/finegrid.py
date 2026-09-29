from pathlib import Path
import importlib.util
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "enri_mouse_neuroplasticity"

spec = importlib.util.spec_from_file_location("enri_solve", BASE / "solve.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

GRID = (0.03, 0.05, 0.1, 0.2, 0.3, 0.5)
m.CV_GRID = GRID

source = m.load_included_source()
long_raw = m.build_long_table(source)
accepted, rejected = m.prepare_cv_splits(long_raw, source)

fold_rows, failures = m.run_cv_grid(accepted)
aggregates = m.aggregate_cv_grid(fold_rows, accepted_split_count=len(accepted))

if not aggregates:
    raise RuntimeError("No complete fine-grid aggregate rows.")

selected, trace = m.lexicographic_select(aggregates, tol=m.CV_SELECTION_TOL)

agg = pd.DataFrame(aggregates).sort_values(
    ["V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w",
     "beta", "lambda", "C"],
    kind="mergesort"
).reset_index(drop=True)
agg.to_csv(ROOT / "fine_grid_results.csv", index=False)

pd.DataFrame(fold_rows).to_csv(ROOT / "fine_grid_fold_metrics.csv", index=False)

baseline = next(
    (r for r in aggregates
     if r["beta"] == 0.1 and r["lambda"] == 0.1 and r["C"] == 0.1),
    None,
)

summary = {
    "grid_values": list(GRID),
    "grid_combinations": len(GRID) ** 3,
    "accepted_splits": len(accepted),
    "rejected_splits": len(rejected),
    "fold_fits_expected": len(accepted) * (len(GRID) ** 3),
    "fold_metric_rows": len(fold_rows),
    "solver_failures": len(failures),
    "selection_tolerance": m.CV_SELECTION_TOL,
    "selection_trace": trace,
    "baseline_0.1_0.1_0.1": baseline,
    "selected": selected,
    "top10_lexicographic": agg.head(10).to_dict(orient="records"),
}

(ROOT / "fine_grid_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("FINEGRID_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
