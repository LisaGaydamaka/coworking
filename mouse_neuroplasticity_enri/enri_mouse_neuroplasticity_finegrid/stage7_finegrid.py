from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "enri_mouse_neuroplasticity"
OUT = ROOT / "stage7_new"
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("enri_solve", BASE / "solve.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

fine = json.loads((ROOT / "fine_grid_summary.json").read_text(encoding="utf-8"))
sel = fine["selected"]
beta = float(sel["beta"])
lam = float(sel["lambda"])
C = float(sel["C"])

source = m.load_included_source()
long_raw = m.build_long_table(source)
final_std, stage3_stats = m.fit_transform_stage3(
    long_raw,
    fit_mouse_ids=None,
    random_state=m.IMPUTATION_SEED,
)
errors = list(stage3_stats.get("errors", []))

states, xbar, state_stats = m.build_experimental_states(final_std)
errors.extend(m.validate_full_stage4(states, xbar, state_stats))

solution, qp_meta = m.solve_qp_smoke(
    final_std,
    states,
    xbar,
    rho=m.SMOKE_RHO,
    beta=beta,
    ridge_lambda=lam,
    C=C,
)
errors.extend(qp_meta.get("errors", []))
if solution is None:
    raise RuntimeError("New Stage 7 QP failed: " + " | ".join(errors or ["unknown"]))

weights = np.asarray(solution["w"], dtype=float)
enri = m.build_final_enri_table(final_std, xbar, weights)
validation_errors, output_stats = m.validate_stage7_outputs(
    enri, weights, solution, states
)
errors.extend(validation_errors)

pd.DataFrame({
    "feature": m.MODEL_FEATURES,
    "weight": weights,
}).to_csv(OUT / "weights.csv", index=False)
enri.to_csv(OUT / "enri.csv", index=False)

scaling = stage3_stats["scaling"]
censor_maxima = stage3_stats["deterministic"]["censor_maxima"]
model = {
    "source": "fine-grid Stage 7 recalculation",
    "excluded_mouse_ids": sorted(m.EXCLUDED_MOUSE_IDS),
    "group_map": m.GROUP_MAP,
    "features": list(m.MODEL_FEATURES),
    "derived_features": list(m.DERIVED_FEATURES),
    "censored_latency_rule": "train_feature_max",
    "censored_latency_final_maxima": {
        k: None if v is None else float(v) for k, v in censor_maxima.items()
    },
    "max_missing_per_visit": int(m.MAX_MISSING_PER_VISIT),
    "mean": [float(scaling["mean"][f]) for f in m.MODEL_FEATURES],
    "std": [float(scaling["std"][f]) for f in m.MODEL_FEATURES],
    "xbar_pbs0": [float(x) for x in np.asarray(xbar, dtype=float)],
    "weights": [float(x) for x in weights],
    "rho": float(m.SMOKE_RHO),
    "beta": beta,
    "lambda": lam,
    "C": C,
    "epsilon": float(m.POSITIVITY_EPSILON),
    "imputation_method": "IterativeImputer(BayesianRidge)",
    "imputation_sample_posterior": False,
    "imputation_seed": int(m.IMPUTATION_SEED),
    "solver_status": str(solution["solver_status"]),
    "solver_name": str(solution["solver_name"]),
    "stage": 7,
}
(OUT / "model.json").write_text(
    json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

new_group = pd.DataFrame([
    {
        "state": label,
        "group": states[label]["group"],
        "week": states[label]["week"],
        "mean_eNRI": float(mu),
        "N": int(states[label]["N"]),
        "O": int(states[label]["O"]),
        "D": int(states[label]["D"]),
        "I": int(states[label]["I"]),
    }
    for label, mu in sorted(solution["group_means"].items())
])
new_group.to_csv(OUT / "group_means.csv", index=False)

# Compare against current official Stage 7 artifacts without changing them.
old_weights = pd.read_csv(BASE / "results" / "weights.csv")
weight_cmp = old_weights.rename(columns={"weight": "old_weight"}).merge(
    pd.DataFrame({"feature": m.MODEL_FEATURES, "new_weight": weights}),
    on="feature", how="inner"
)
weight_cmp["delta"] = weight_cmp["new_weight"] - weight_cmp["old_weight"]
weight_cmp["abs_delta"] = weight_cmp["delta"].abs()
weight_cmp.to_csv(OUT / "weight_comparison.csv", index=False)

old_enri = pd.read_csv(BASE / "results" / "enri.csv")
old_group = (
    old_enri.groupby(["group", "week"], as_index=False)["eNRI"].mean()
    .rename(columns={"eNRI": "old_mean_eNRI"})
)
group_cmp = new_group.merge(old_group, on=["group", "week"], how="left")
group_cmp["delta"] = group_cmp["mean_eNRI"] - group_cmp["old_mean_eNRI"]
group_cmp.to_csv(OUT / "group_mean_comparison.csv", index=False)

summary = {
    "stage": 7,
    "status": "READY" if not errors else "FATAL",
    "validation_errors": errors,
    "beta": beta,
    "lambda": lam,
    "C": C,
    "rho": float(m.SMOKE_RHO),
    "solver_status": str(solution["solver_status"]),
    "solver_name": str(solution["solver_name"]),
    "solver_num_iters": int(solution["solver_num_iters"]),
    "objective": float(solution["objective"]),
    "objective_components": {
        k: float(v) for k, v in solution["objective_components"].items()
    },
    "weight_l2_norm": float(solution["weight_l2_norm"]),
    "weight_max_abs": float(solution["weight_max_abs"]),
    "slack_sum": float(solution["slack_sum"]),
    "slack_max": float(solution["slack_max"]),
    "max_order_violation": float(solution["max_order_violation"]),
    "max_positivity_violation": float(solution["max_positivity_violation"]),
    "eta_nonneg_violation": float(solution["eta_nonneg_violation"]),
    "living_rows": int(output_stats["living_rows"]),
    "death_rows": int(output_stats["death_rows"]),
    "imputed_rows": int(output_stats["imputed_rows"]),
    "missing_visit_rows": int(output_stats["missing_visit_rows"]),
    "min_live_enri": float(output_stats["min_live_enri"]),
    "max_live_enri": float(output_stats["max_live_enri"]),
    "pbs0_mean": float(output_stats["pbs0_mean"]),
    "group_means": {k: float(v) for k, v in solution["group_means"].items()},
    "equality_deltas": {k: float(v) for k, v in solution["equality_deltas"].items()},
    "order_results": solution["order_results"],
    "largest_weight_changes": (
        weight_cmp.sort_values("abs_delta", ascending=False)
        .head(10)[["feature","old_weight","new_weight","delta"]]
        .to_dict(orient="records")
    ),
}
(OUT / "stage7_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print("STAGE7_FINEGRID_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
if errors:
    raise RuntimeError("Stage 7 validation failed: " + " | ".join(errors))
