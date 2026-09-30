#!/usr/bin/env python3
"""
Stage B: constrained Elastic-Net path for eNRI feature selection.

Development-stage calculation:
- keep beta=lambda2=C=rho=0.1 from the original model;
- add lambda1 * ||w||_1;
- reuse the original model's fixed mouse-level repeated stratified CV splits;
- evaluate the same validation metrics as the original model;
- choose a development lambda1* with the frozen sequential one-SE rule;
- fit the full-data path for diagnostics only.

This is not the final nested-CV estimate. Final selection must be repeated
inside outer-train as specified in FEATURE_SELECTION_PLAN.md.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parent / "enri_mouse_neuroplasticity"
BASE_SOLVE = BASE_DIR / "solve.py"
OUT_DIR = ROOT / "stage_b"

BETA = 0.1
LAMBDA2 = 0.1
C_SLACK = 0.1
RHO = 0.1
ACTIVE_TOL = 1e-6

BASE_LAMBDA1_GRID = (
    0.0,
    1e-5,
    3e-5,
    1e-4,
    3e-4,
    1e-3,
    3e-3,
    1e-2,
    3e-2,
    1e-1,
    3e-1,
)
EXTENDED_LAMBDA1 = (1.0, 3.0)
METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w")


def load_base_module():
    if not BASE_SOLVE.exists():
        raise FileNotFoundError(BASE_SOLVE)
    spec = importlib.util.spec_from_file_location("enri_base_model_b", BASE_SOLVE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import base model from {BASE_SOLVE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def solve_sparse_qp(base, final_std, states, xbar, lambda1):
    errors = []

    Q_var, q_stats = base.assemble_qvar(states)
    if not q_stats["finite"]:
        errors.append("Q_var contains non-finite values.")
    if q_stats["min_eigenvalue"] < -1e-8:
        errors.append(
            f"Q_var minimum eigenvalue {q_stats['min_eigenvalue']} < -1e-8."
        )

    living = final_std["status"].isin(["observed", "imputed"])
    X_live = final_std.loc[living, base.MODEL_FEATURES].to_numpy(dtype=float)
    xbar = np.asarray(xbar, dtype=float)

    if xbar.shape != (len(base.MODEL_FEATURES),):
        errors.append(f"Invalid xbar shape: {xbar.shape}.")
    if not np.isfinite(X_live).all():
        errors.append("Non-finite living MODEL_FEATURES.")

    if errors:
        return None, {"status": "NOT_SOLVED", "errors": errors}

    p = len(base.MODEL_FEATURES)
    m = len(base.ORDER_PAIRS)
    w = cp.Variable(p, name="w")
    eta = cp.Variable(m, nonneg=True, name="eta")

    equality_exprs = []
    for A, B in base.EQUALITY_PAIRS:
        c_ab, d_ab = base.pair_affine_components(states, A, B)
        equality_exprs.append(c_ab + d_ab @ w)

    objective = (
        cp.quad_form(w, cp.psd_wrap(Q_var))
        + BETA * cp.sum_squares(cp.hstack(equality_exprs))
        + LAMBDA2 * cp.sum_squares(w)
        + C_SLACK * cp.sum(eta)
        + float(lambda1) * cp.norm1(w)
    )

    constraints = []
    for k, (A, B) in enumerate(base.ORDER_PAIRS):
        c_ab, d_ab = base.pair_affine_components(states, A, B)
        constraints.append(c_ab + d_ab @ w >= RHO - eta[k])

    centered_live = X_live - xbar
    constraints.append(
        1.0 + centered_live @ w >= base.POSITIVITY_EPSILON
    )

    problem = cp.Problem(cp.Minimize(objective), constraints)
    try:
        objective_value = problem.solve(
            solver=cp.OSQP,
            eps_abs=1e-8,
            eps_rel=1e-8,
            max_iter=100000,
            verbose=False,
        )
    except Exception as exc:
        return None, {
            "status": "SOLVER_EXCEPTION",
            "errors": [f"{type(exc).__name__}: {exc}"],
        }

    status = str(problem.status)
    if status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
        errors.append(f"Unexpected solver status: {status}")
    if w.value is None or eta.value is None:
        errors.append("Solver returned no primal solution.")
        return None, {"status": status, "errors": errors}

    wv = np.asarray(w.value, dtype=float).reshape(-1)
    etav = np.asarray(eta.value, dtype=float).reshape(-1)
    if not np.isfinite(wv).all() or not np.isfinite(etav).all():
        errors.append("Non-finite primal solution.")

    active = np.abs(wv) > ACTIVE_TOL
    live_enri = 1.0 + centered_live @ wv

    order_results = {}
    max_order_violation = 0.0
    for k, (A, B) in enumerate(base.ORDER_PAIRS):
        c_ab, d_ab = base.pair_affine_components(states, A, B)
        delta = float(c_ab + d_ab @ wv)
        residual = float(delta - RHO + etav[k])
        violation = max(0.0, -residual)
        max_order_violation = max(max_order_violation, violation)
        order_results[f"{A}>{B}"] = {
            "delta": delta,
            "slack": float(etav[k]),
            "residual": residual,
            "violation": violation,
        }

    equality_deltas = {}
    for A, B in base.EQUALITY_PAIRS:
        c_ab, d_ab = base.pair_affine_components(states, A, B)
        equality_deltas[f"{A}>{B}"] = float(c_ab + d_ab @ wv)

    group_means = {}
    for group in base.STATE_GROUPS:
        for week in base.STATE_WEEKS:
            label = base.state_label(group, week)
            s = states[label]
            group_means[label] = float(s["a"] + s["b"] @ wv)

    variance_term = float(wv @ Q_var @ wv)
    equality_term = float(
        BETA * sum(v * v for v in equality_deltas.values())
    )
    ridge_term = float(LAMBDA2 * np.dot(wv, wv))
    slack_term = float(C_SLACK * np.sum(etav))
    l1_term = float(float(lambda1) * np.sum(np.abs(wv)))
    recomputed = variance_term + equality_term + ridge_term + slack_term + l1_term

    positivity_violation = max(
        0.0,
        float(base.POSITIVITY_EPSILON - np.min(live_enri)),
    )

    if max_order_violation > base.QP_TOLERANCE:
        errors.append(f"Order violation {max_order_violation}.")
    if positivity_violation > base.QP_TOLERANCE:
        errors.append(f"Positivity violation {positivity_violation}.")
    if float(np.min(etav)) < -base.QP_TOLERANCE:
        errors.append(f"Negative eta {float(np.min(etav))}.")

    return {
        "w": wv,
        "eta": etav,
        "solver_status": status,
        "objective": float(objective_value),
        "objective_recomputed": recomputed,
        "objective_gap": abs(float(objective_value) - recomputed),
        "objective_components": {
            "variance": variance_term,
            "equality": equality_term,
            "ridge": ridge_term,
            "slack": slack_term,
            "l1": l1_term,
        },
        "active_count": int(active.sum()),
        "active_mask": active,
        "active_features": [
            feature
            for feature, is_active in zip(base.MODEL_FEATURES, active)
            if bool(is_active)
        ],
        "weight_l1_norm": float(np.sum(np.abs(wv))),
        "weight_l2_norm": float(np.linalg.norm(wv)),
        "weight_max_abs": float(np.max(np.abs(wv))),
        "slack_sum": float(np.sum(etav)),
        "slack_max": float(np.max(etav)),
        "min_live_enri": float(np.min(live_enri)),
        "max_order_violation": float(max_order_violation),
        "max_positivity_violation": float(positivity_violation),
        "equality_deltas": equality_deltas,
        "order_results": order_results,
        "group_means": group_means,
        "errors": errors,
    }, {"status": status, "errors": errors}


def fit_full_data(base, long_raw, lambda1_grid):
    final_std, prep_stats = base.fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=base.IMPUTATION_SEED,
        sample_posterior=False,
    )
    errors = list(prep_stats.get("errors", []))
    states, xbar, state_stats = base.build_experimental_states(final_std)
    errors.extend(base.validate_full_stage4(states, xbar, state_stats))
    if errors:
        raise RuntimeError("Full-data preprocessing/state errors: " + " | ".join(errors))

    rows = []
    weight_rows = []
    solutions = {}

    for lambda1 in lambda1_grid:
        solution, meta = solve_sparse_qp(
            base, final_std, states, xbar, lambda1=lambda1
        )
        if solution is None or meta.get("errors"):
            raise RuntimeError(
                f"Full-data sparse QP failed for lambda1={lambda1}: "
                + " | ".join(meta.get("errors", []))
            )
        solutions[float(lambda1)] = solution
        rows.append({
            "lambda1": float(lambda1),
            "active_count": int(solution["active_count"]),
            "weight_l1_norm": float(solution["weight_l1_norm"]),
            "weight_l2_norm": float(solution["weight_l2_norm"]),
            "weight_max_abs": float(solution["weight_max_abs"]),
            "slack_sum": float(solution["slack_sum"]),
            "slack_max": float(solution["slack_max"]),
            "min_live_enri": float(solution["min_live_enri"]),
            "objective": float(solution["objective"]),
            "objective_variance": float(solution["objective_components"]["variance"]),
            "objective_equality": float(solution["objective_components"]["equality"]),
            "objective_ridge": float(solution["objective_components"]["ridge"]),
            "objective_slack": float(solution["objective_components"]["slack"]),
            "objective_l1": float(solution["objective_components"]["l1"]),
            "active_features": "|".join(solution["active_features"]),
        })
        for feature, weight in zip(base.MODEL_FEATURES, solution["w"]):
            weight_rows.append({
                "lambda1": float(lambda1),
                "feature": feature,
                "weight": float(weight),
                "active": bool(abs(float(weight)) > ACTIVE_TOL),
            })

    return pd.DataFrame(rows), pd.DataFrame(weight_rows), solutions


def run_cv_path(base, accepted_splits, lambda1_grid):
    fold_rows = []
    failures = []

    for lambda1 in lambda1_grid:
        for split in accepted_splits:
            train_ids = set(split["train_ids"])
            train_df = split["final_std"][
                split["final_std"]["mouse_id"].isin(train_ids)
            ].copy()

            solution, meta = solve_sparse_qp(
                base,
                train_df,
                split["train_states"],
                split["xbar_train"],
                lambda1=lambda1,
            )
            if solution is None or meta.get("errors"):
                failures.append({
                    "lambda1": float(lambda1),
                    "seed": int(split["seed"]),
                    "fold": int(split["fold"]),
                    "status": meta.get("status"),
                    "errors": " | ".join(meta.get("errors", [])),
                })
                continue

            metrics = base.evaluate_validation_metrics(
                split["final_std"],
                split["val_ids"],
                split["val_states"],
                split["xbar_train"],
                solution["w"],
                rho=RHO,
            )

            fold_rows.append({
                "lambda1": float(lambda1),
                "seed": int(split["seed"]),
                "fold": int(split["fold"]),
                "active_count": int(solution["active_count"]),
                "V_pos": float(metrics["V_pos"]),
                "V_sign": float(metrics["V_sign"]),
                "V_margin": float(metrics["V_margin"]),
                "V_eq": float(metrics["V_eq"]),
                "V_var": float(metrics["V_var"]),
                "V_w": float(metrics["V_w"]),
                "train_slack_sum": float(solution["slack_sum"]),
                "train_slack_max": float(solution["slack_max"]),
                "train_min_live_enri": float(solution["min_live_enri"]),
                "validation_min_enri": float(metrics["validation_min_enri"]),
                "solver_status": str(solution["solver_status"]),
            })

    return pd.DataFrame(fold_rows), pd.DataFrame(failures)


def aggregate_path(fold_df, expected_splits):
    rows = []
    for lambda1 in sorted(fold_df["lambda1"].unique()):
        sub = fold_df[fold_df["lambda1"].eq(lambda1)]
        if len(sub) != expected_splits:
            continue
        row = {
            "lambda1": float(lambda1),
            "folds": int(len(sub)),
            "active_count_mean": float(sub["active_count"].mean()),
            "active_count_median": float(sub["active_count"].median()),
            "active_count_min": int(sub["active_count"].min()),
            "active_count_max": int(sub["active_count"].max()),
            "slack_sum_mean": float(sub["train_slack_sum"].mean()),
        }
        for metric in METRICS:
            vals = sub[metric].astype(float)
            sd = float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0
            se = float(sd / math.sqrt(len(vals))) if len(vals) else float("nan")
            row[f"{metric}_mean"] = float(vals.mean())
            row[f"{metric}_sd"] = sd
            row[f"{metric}_se"] = se
        rows.append(row)
    return pd.DataFrame(rows)


def one_se_select(aggregate_df):
    survivors = aggregate_df.copy()
    trace = []

    for metric in METRICS:
        mean_col = f"{metric}_mean"
        se_col = f"{metric}_se"
        best_mean = float(survivors[mean_col].min())
        best_candidates = survivors[np.isclose(
            survivors[mean_col].to_numpy(dtype=float),
            best_mean,
            rtol=0,
            atol=1e-15,
        )]
        # Deterministic choice of the reference best row: strongest sparsity
        # among exact mean ties.
        best_row = best_candidates.sort_values("lambda1").iloc[-1]
        best_se = float(best_row[se_col])
        threshold = best_mean + best_se

        survivors = survivors[
            survivors[mean_col] <= threshold + 1e-15
        ].copy()

        trace.append({
            "metric": metric,
            "best_mean": best_mean,
            "best_se": best_se,
            "threshold": threshold,
            "survivors": int(len(survivors)),
            "survivor_lambda1": [
                float(x) for x in sorted(survivors["lambda1"].tolist())
            ],
        })

    selected = survivors.sort_values("lambda1").iloc[-1].to_dict()
    return selected, trace


def lambda_grid_with_extension(full_base_path):
    row = full_base_path[
        np.isclose(full_base_path["lambda1"], 0.3, rtol=0, atol=1e-15)
    ]
    if len(row) != 1:
        raise RuntimeError("lambda1=0.3 full-data row missing.")
    active_at_03 = int(row.iloc[0]["active_count"])

    # The plan later evaluates S_3...S_15. If lambda1=0.3 still leaves
    # more than 15 active features, extend the pre-authorized grid to 1 and 3.
    needs_extension = active_at_03 > 15
    grid = list(BASE_LAMBDA1_GRID)
    if needs_extension:
        grid.extend(EXTENDED_LAMBDA1)
    return tuple(grid), needs_extension, active_at_03


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = load_base_module()

    # Guard against accidental drift from the specified first model.
    if set(base.ORDER_PAIRS) != {
        ("PBS^16", "LPS^16"),
        ("PBS^24", "LPS^24"),
        ("run^24", "LPS^24"),
        ("MCC^24", "LPS^24"),
        ("PBS^0", "PBS^16"),
        ("LPS^0", "LPS^16"),
        ("run^0", "run^16"),
        ("MCC^0", "MCC^16"),
        ("PBS^16", "PBS^24"),
        ("LPS^16", "LPS^24"),
    }:
        raise RuntimeError("Base ORDER_PAIRS are not the required 10-condition model.")

    source = base.load_included_source()
    long_raw = base.build_long_table(source)

    # First calculate the predeclared base lambda1 grid on full data only to
    # determine whether the authorized 1,3 extension is necessary.
    full_base_path, full_base_weights, _ = fit_full_data(
        base, long_raw, BASE_LAMBDA1_GRID
    )
    lambda1_grid, extended, active_at_03 = lambda_grid_with_extension(full_base_path)

    if extended:
        full_ext_path, full_ext_weights, _ = fit_full_data(
            base, long_raw, EXTENDED_LAMBDA1
        )
        full_path = pd.concat(
            [full_base_path, full_ext_path], ignore_index=True
        ).sort_values("lambda1").reset_index(drop=True)
        full_weights = pd.concat(
            [full_base_weights, full_ext_weights], ignore_index=True
        ).sort_values(["lambda1", "feature"]).reset_index(drop=True)
    else:
        full_path = full_base_path.sort_values("lambda1").reset_index(drop=True)
        full_weights = full_base_weights.sort_values(
            ["lambda1", "feature"]
        ).reset_index(drop=True)

    # lambda1=0 must reproduce the original beta=lambda2=C=0.1 model.
    original_weights = pd.read_csv(BASE_DIR / "results" / "weights.csv")
    expected_order = list(base.MODEL_FEATURES)
    if original_weights["feature"].tolist() != expected_order:
        raise RuntimeError("Original weights.csv feature order does not match MODEL_FEATURES.")
    w_original = original_weights["weight"].to_numpy(dtype=float)
    w_zero = (
        full_weights[
            np.isclose(full_weights["lambda1"], 0.0, rtol=0, atol=1e-15)
        ]
        .set_index("feature")
        .loc[expected_order, "weight"]
        .to_numpy(dtype=float)
    )
    lambda0_max_abs_weight_diff = float(np.max(np.abs(w_original - w_zero)))
    if lambda0_max_abs_weight_diff > 1e-6:
        raise RuntimeError(
            "lambda1=0 sparse solver does not reproduce original model: "
            f"max abs weight diff={lambda0_max_abs_weight_diff}"
        )

    # Development CV: exactly the original fixed repeated stratified splits.
    accepted_splits, rejected_splits = base.prepare_cv_splits(long_raw, source)
    if len(accepted_splits) != 22:
        raise RuntimeError(
            f"Expected 22 accepted original CV splits, got {len(accepted_splits)}."
        )

    fold_df, failures_df = run_cv_path(base, accepted_splits, lambda1_grid)
    if not failures_df.empty:
        failures_df.to_csv(OUT_DIR / "elastic_net_failures.csv", index=False)
        raise RuntimeError(
            f"{len(failures_df)} sparse QP fits failed; see elastic_net_failures.csv"
        )

    expected_rows = len(accepted_splits) * len(lambda1_grid)
    if len(fold_df) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} CV fold rows, got {len(fold_df)}."
        )

    aggregate_df = aggregate_path(fold_df, expected_splits=len(accepted_splits))
    if len(aggregate_df) != len(lambda1_grid):
        raise RuntimeError(
            f"Expected {len(lambda1_grid)} aggregate rows, got {len(aggregate_df)}."
        )

    selected, trace = one_se_select(aggregate_df)
    lambda1_star = float(selected["lambda1"])

    # Merge CV and full-data diagnostics into the primary path table.
    path_df = aggregate_df.merge(
        full_path,
        on="lambda1",
        how="left",
        validate="one_to_one",
        suffixes=("_cv", "_full"),
    )
    path_df["selected_development_lambda1"] = np.isclose(
        path_df["lambda1"].to_numpy(dtype=float),
        lambda1_star,
        rtol=0,
        atol=1e-15,
    )

    path_df.to_csv(OUT_DIR / "elastic_net_path.csv", index=False)
    fold_df.to_csv(OUT_DIR / "elastic_net_fold_metrics.csv", index=False)
    full_weights.to_csv(OUT_DIR / "elastic_net_weights.csv", index=False)

    trace_rows = []
    for step, rec in enumerate(trace, start=1):
        trace_rows.append({
            "step": step,
            "metric": rec["metric"],
            "best_mean": rec["best_mean"],
            "best_se": rec["best_se"],
            "threshold": rec["threshold"],
            "survivors": rec["survivors"],
            "survivor_lambda1": "|".join(
                f"{x:.12g}" for x in rec["survivor_lambda1"]
            ),
        })
    selection_df = pd.DataFrame(trace_rows)
    selection_df["selected_lambda1"] = lambda1_star
    selection_df.to_csv(OUT_DIR / "lambda1_selection.csv", index=False)

    selected_full = full_path[
        np.isclose(full_path["lambda1"], lambda1_star, rtol=0, atol=1e-15)
    ].iloc[0]

    summary = {
        "stage": "B",
        "status": "READY",
        "purpose": "development_constrained_elastic_net_path",
        "warning": (
            "Development lambda1* is not a final estimate. In nested validation "
            "lambda1 must be selected again inside each outer-train."
        ),
        "fixed_hyperparameters": {
            "beta": BETA,
            "lambda2": LAMBDA2,
            "C": C_SLACK,
            "rho": RHO,
        },
        "lambda1_grid": [float(x) for x in lambda1_grid],
        "grid_extended": bool(extended),
        "extension_rule": (
            "append lambda1=1,3 if full-data lambda1=0.3 leaves more than "
            "15 active features"
        ),
        "active_at_lambda1_0_3": int(active_at_03),
        "active_threshold": ACTIVE_TOL,
        "cv": {
            "scheme": "original repeated stratified 3-fold mouse-level CV",
            "accepted_splits": int(len(accepted_splits)),
            "rejected_splits": int(len(rejected_splits)),
            "expected_fit_count": int(expected_rows),
            "solver_failures": 0,
        },
        "lambda1_zero_reproduction": {
            "max_abs_weight_diff_vs_original": lambda0_max_abs_weight_diff,
            "pass": True,
        },
        "development_selection": {
            "rule": (
                "sequential one-SE filtering over "
                "V_pos,V_sign,V_margin,V_eq,V_var,V_w; choose largest lambda1 "
                "among final survivors"
            ),
            "lambda1_star": lambda1_star,
            "selected_cv_metrics": {
                metric: float(selected[f"{metric}_mean"])
                for metric in METRICS
            },
            "selected_cv_active_count_mean": float(selected["active_count_mean"]),
            "selected_cv_active_count_median": float(selected["active_count_median"]),
            "selected_full_active_count": int(selected_full["active_count"]),
            "selected_full_active_features": str(selected_full["active_features"]).split("|")
            if str(selected_full["active_features"])
            else [],
            "selected_full_slack_sum": float(selected_full["slack_sum"]),
        },
        "outputs": {
            "path": "stage_b/elastic_net_path.csv",
            "fold_metrics": "stage_b/elastic_net_fold_metrics.csv",
            "weights": "stage_b/elastic_net_weights.csv",
            "selection_trace": "stage_b/lambda1_selection.csv",
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_b_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STAGE_B_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
