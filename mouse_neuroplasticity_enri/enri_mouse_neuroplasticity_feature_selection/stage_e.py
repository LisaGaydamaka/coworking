#!/usr/bin/env python3
"""
Stage E: paired feature and correlation-block ablation.

Development analysis at the Stage-B development lambda1*.

For each Stage-C core/candidate feature and each Stage-A correlation block:
- use the exact same 22 accepted mouse-level CV splits as the reference model;
- force the target weighted coefficient(s) to zero;
- refit the entire constrained Elastic-Net QP;
- evaluate the same validation metrics;
- compute paired delta = ablated - reference.

All validation metrics are losses, so delta > 0 means ablation worsened
out-of-sample performance.

Important: this stage tests weighted-model contribution while keeping the same
30-feature train-only preprocessing/imputation used by the reference model.
The autonomous reduced-preprocessing test is a later stage.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parent / "enri_mouse_neuroplasticity"
BASE_SOLVE = BASE_DIR / "solve.py"
STAGE_B_PY = ROOT / "stage_b.py"
STAGE_B_SUMMARY = ROOT / "stage_b" / "stage_b_summary.json"
STAGE_B_FOLDS = ROOT / "stage_b" / "elastic_net_fold_metrics.csv"
STAGE_C_STABILITY = ROOT / "stage_c" / "stability_selection.csv"
STAGE_D_BLOCKS = ROOT / "stage_a" / "correlation_blocks.csv"
OUT_DIR = ROOT / "stage_e"

METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w")
PRIORITY_METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var")
REFERENCE_TOL = 1e-8


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_lambda1_star():
    summary = json.loads(STAGE_B_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("status") != "READY":
        raise RuntimeError("Stage B is not READY.")
    return float(summary["development_selection"]["lambda1_star"])


def evaluate_fit(base, sparse, split, lambda1_star, forced_zero_features):
    train_ids = set(split["train_ids"])
    train_df = split["final_std"][
        split["final_std"]["mouse_id"].isin(train_ids)
    ].copy()

    solution, meta = sparse.solve_sparse_qp(
        base,
        train_df,
        split["train_states"],
        split["xbar_train"],
        lambda1=lambda1_star,
        forced_zero_features=forced_zero_features,
    )
    if solution is None or meta.get("errors"):
        return None, {
            "status": meta.get("status"),
            "errors": meta.get("errors", []),
        }

    metrics = base.evaluate_validation_metrics(
        split["final_std"],
        split["val_ids"],
        split["val_states"],
        split["xbar_train"],
        solution["w"],
        rho=sparse.RHO,
    )
    rec = {
        **{m: float(metrics[m]) for m in METRICS},
        "active_count": int(solution["active_count"]),
        "slack_sum": float(solution["slack_sum"]),
        "slack_max": float(solution["slack_max"]),
        "min_live_enri": float(solution["min_live_enri"]),
        "solver_status": str(solution["solver_status"]),
        "solver_used": str(solution.get("solver_used", "")),
    }
    return rec, None


def summarize_ablation(fold_df: pd.DataFrame, key_cols: list[str]):
    rows = []
    group_key = key_cols[0] if len(key_cols) == 1 else key_cols
    for keys, sub in fold_df.groupby(group_key, sort=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row = {col: val for col, val in zip(key_cols, keys)}
        row["folds"] = int(len(sub))
        row["forced_zero_count"] = int(sub["forced_zero_count"].iloc[0])
        row["forced_zero_features"] = str(sub["forced_zero_features"].iloc[0])

        for metric in METRICS:
            d = sub[f"delta_{metric}"].astype(float)
            row[f"delta_{metric}_mean"] = float(d.mean())
            row[f"delta_{metric}_median"] = float(d.median())
            row[f"delta_{metric}_q10"] = float(d.quantile(0.10))
            row[f"delta_{metric}_q90"] = float(d.quantile(0.90))
            row[f"p_{metric}_worse"] = float(np.mean(d > 0))
            row[f"p_{metric}_better"] = float(np.mean(d < 0))
            row[f"p_{metric}_equal"] = float(np.mean(np.isclose(d, 0.0, atol=1e-12, rtol=0)))

        da = sub["delta_active_count"].astype(float)
        ds = sub["delta_slack_sum"].astype(float)
        row["delta_active_count_median"] = float(da.median())
        row["delta_active_count_q10"] = float(da.quantile(0.10))
        row["delta_active_count_q90"] = float(da.quantile(0.90))
        row["delta_slack_sum_median"] = float(ds.median())
        row["delta_slack_sum_q10"] = float(ds.quantile(0.10))
        row["delta_slack_sum_q90"] = float(ds.quantile(0.90))

        # Descriptive lexicographic signature, not a PASS/FAIL rule.
        # It records the first priority metric with any positive median
        # deterioration and its paired worsening probability.
        first = ""
        first_p = np.nan
        first_median = np.nan
        for metric in PRIORITY_METRICS:
            med = row[f"delta_{metric}_median"]
            if med > 0:
                first = metric
                first_p = row[f"p_{metric}_worse"]
                first_median = med
                break
        row["first_positive_median_metric"] = first
        row["first_positive_median_p_worse"] = first_p
        row["first_positive_median_delta"] = first_median
        rows.append(row)

    return pd.DataFrame(rows)


def check_reference_against_stage_b(reference_df, lambda1_star):
    persisted = pd.read_csv(STAGE_B_FOLDS)
    persisted = persisted[
        np.isclose(
            persisted["lambda1"].astype(float).to_numpy(),
            lambda1_star,
            rtol=0,
            atol=1e-15,
        )
    ].copy()

    keys = ["seed", "fold"]
    if len(persisted) != len(reference_df):
        raise RuntimeError(
            f"Reference split count mismatch: recomputed={len(reference_df)}, "
            f"Stage-B={len(persisted)}."
        )

    merged = reference_df.merge(
        persisted[keys + list(METRICS)],
        on=keys,
        how="inner",
        validate="one_to_one",
        suffixes=("_recomputed", "_stage_b"),
    )
    if len(merged) != len(reference_df):
        raise RuntimeError("Reference split keys do not exactly match Stage B.")

    max_diffs = {}
    for metric in METRICS:
        diff = np.abs(
            merged[f"{metric}_recomputed"].astype(float).to_numpy()
            - merged[f"{metric}_stage_b"].astype(float).to_numpy()
        )
        max_diffs[metric] = float(diff.max())
        if max_diffs[metric] > REFERENCE_TOL:
            raise RuntimeError(
                f"Reference {metric} differs from Stage B by "
                f"{max_diffs[metric]} > {REFERENCE_TOL}."
            )
    return max_diffs


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    needed = [
        BASE_SOLVE,
        STAGE_B_PY,
        STAGE_B_SUMMARY,
        STAGE_B_FOLDS,
        STAGE_C_STABILITY,
        STAGE_D_BLOCKS,
    ]
    for path in needed:
        if not path.exists():
            raise FileNotFoundError(path)

    base = load_module(BASE_SOLVE, "enri_base_model_e")
    sparse = load_module(STAGE_B_PY, "enri_stage_b_e")
    lambda1_star = load_lambda1_star()

    stability = pd.read_csv(STAGE_C_STABILITY)
    feature_targets = (
        stability[stability["category"].isin(["core", "candidate"])]
        .sort_values(["category", "stability_rank"])
        ["feature"]
        .astype(str)
        .tolist()
    )
    if len(feature_targets) != 13:
        raise RuntimeError(
            f"Expected 13 core/candidate feature targets from Stage C, got {len(feature_targets)}."
        )

    blocks = pd.read_csv(STAGE_D_BLOCKS)
    is_block = blocks["is_correlation_block"]
    if is_block.dtype != bool:
        is_block = is_block.astype(str).str.lower().eq("true")
    block_defs = blocks[is_block].copy()
    block_targets = []
    for block_id, sub in block_defs.groupby("block_id", sort=False):
        sub = sub.sort_values("feature_order")
        block_targets.append(
            (str(block_id), sub["feature"].astype(str).tolist())
        )
    if len(block_targets) != 6:
        raise RuntimeError(
            f"Expected 6 correlation blocks from Stage A, got {len(block_targets)}."
        )

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    accepted_splits, rejected_splits = base.prepare_cv_splits(long_raw, source)
    if len(accepted_splits) != 22:
        raise RuntimeError(
            f"Expected 22 accepted splits, got {len(accepted_splits)}."
        )

    reference_rows = []
    failures = []

    for split in accepted_splits:
        ref, err = evaluate_fit(
            base, sparse, split, lambda1_star, forced_zero_features=[]
        )
        if err:
            failures.append({
                "kind": "reference",
                "target": "reference",
                "seed": int(split["seed"]),
                "fold": int(split["fold"]),
                "status": err["status"],
                "errors": " | ".join(err["errors"]),
            })
            continue
        reference_rows.append({
            "seed": int(split["seed"]),
            "fold": int(split["fold"]),
            **ref,
        })

    if failures:
        pd.DataFrame(failures).to_csv(OUT_DIR / "ablation_failures.csv", index=False)
        raise RuntimeError(f"{len(failures)} reference fits failed.")

    reference_df = pd.DataFrame(reference_rows)
    reference_max_diffs = check_reference_against_stage_b(reference_df, lambda1_star)
    reference_df.to_csv(OUT_DIR / "reference_fold_metrics.csv", index=False)

    reference_map = {
        (int(r["seed"]), int(r["fold"])): r
        for r in reference_rows
    }

    feature_fold_rows = []
    for feature in feature_targets:
        for split in accepted_splits:
            key = (int(split["seed"]), int(split["fold"]))
            ref = reference_map[key]
            abl, err = evaluate_fit(
                base, sparse, split, lambda1_star,
                forced_zero_features=[feature],
            )
            if err:
                failures.append({
                    "kind": "feature",
                    "target": feature,
                    "seed": key[0],
                    "fold": key[1],
                    "status": err["status"],
                    "errors": " | ".join(err["errors"]),
                })
                continue

            row = {
                "feature": feature,
                "seed": key[0],
                "fold": key[1],
                "forced_zero_count": 1,
                "forced_zero_features": feature,
                "reference_active_count": int(ref["active_count"]),
                "ablated_active_count": int(abl["active_count"]),
                "delta_active_count": int(abl["active_count"] - ref["active_count"]),
                "reference_slack_sum": float(ref["slack_sum"]),
                "ablated_slack_sum": float(abl["slack_sum"]),
                "delta_slack_sum": float(abl["slack_sum"] - ref["slack_sum"]),
                "solver_used": abl["solver_used"],
            }
            for metric in METRICS:
                row[f"reference_{metric}"] = float(ref[metric])
                row[f"ablated_{metric}"] = float(abl[metric])
                row[f"delta_{metric}"] = float(abl[metric] - ref[metric])
            feature_fold_rows.append(row)

    block_fold_rows = []
    for block_id, members in block_targets:
        for split in accepted_splits:
            key = (int(split["seed"]), int(split["fold"]))
            ref = reference_map[key]
            abl, err = evaluate_fit(
                base, sparse, split, lambda1_star,
                forced_zero_features=members,
            )
            if err:
                failures.append({
                    "kind": "block",
                    "target": block_id,
                    "seed": key[0],
                    "fold": key[1],
                    "status": err["status"],
                    "errors": " | ".join(err["errors"]),
                })
                continue

            row = {
                "block_id": block_id,
                "seed": key[0],
                "fold": key[1],
                "forced_zero_count": len(members),
                "forced_zero_features": "|".join(members),
                "reference_active_count": int(ref["active_count"]),
                "ablated_active_count": int(abl["active_count"]),
                "delta_active_count": int(abl["active_count"] - ref["active_count"]),
                "reference_slack_sum": float(ref["slack_sum"]),
                "ablated_slack_sum": float(abl["slack_sum"]),
                "delta_slack_sum": float(abl["slack_sum"] - ref["slack_sum"]),
                "solver_used": abl["solver_used"],
            }
            for metric in METRICS:
                row[f"reference_{metric}"] = float(ref[metric])
                row[f"ablated_{metric}"] = float(abl[metric])
                row[f"delta_{metric}"] = float(abl[metric] - ref[metric])
            block_fold_rows.append(row)

    if failures:
        pd.DataFrame(failures).to_csv(OUT_DIR / "ablation_failures.csv", index=False)
        raise RuntimeError(f"{len(failures)} ablation fits failed.")

    feature_folds = pd.DataFrame(feature_fold_rows)
    block_folds = pd.DataFrame(block_fold_rows)

    expected_feature_rows = len(feature_targets) * len(accepted_splits)
    expected_block_rows = len(block_targets) * len(accepted_splits)
    if len(feature_folds) != expected_feature_rows:
        raise RuntimeError(
            f"Expected {expected_feature_rows} feature-ablation rows, got {len(feature_folds)}."
        )
    if len(block_folds) != expected_block_rows:
        raise RuntimeError(
            f"Expected {expected_block_rows} block-ablation rows, got {len(block_folds)}."
        )

    feature_summary = summarize_ablation(feature_folds, ["feature"])
    block_summary = summarize_ablation(block_folds, ["block_id"])

    # Carry Stage-C stability information into the feature summary.
    stability_cols = [
        "feature", "pi_selection", "sign_consistency", "category",
        "stability_rank", "gamma_median_selected",
        "abs_gamma_median_selected",
    ]
    feature_summary = feature_summary.merge(
        stability[stability_cols],
        on="feature",
        how="left",
        validate="one_to_one",
    )

    # Carry Stage-D block stability into the block summary when available.
    block_stability_path = ROOT / "stage_d" / "block_stability.csv"
    if block_stability_path.exists():
        bstab = pd.read_csv(block_stability_path)
        keep = [
            "block_id", "members", "pi_block_any_selected",
            "p_exactly_one_selected", "p_multiple_selected",
            "primary_member_by_pi", "primary_member_pi",
        ]
        block_summary = block_summary.merge(
            bstab[keep],
            on="block_id",
            how="left",
            validate="one_to_one",
            suffixes=("", "_stage_d"),
        )

    # Descriptive ordering only: probability and magnitude of worsening in the
    # predeclared metric priority. No hard PASS/FAIL classification is created.
    feature_summary = feature_summary.sort_values(
        [
            "p_V_sign_worse", "delta_V_sign_median",
            "p_V_margin_worse", "delta_V_margin_median",
            "p_V_eq_worse", "delta_V_eq_median",
            "stability_rank",
        ],
        ascending=[False, False, False, False, False, False, True],
    ).reset_index(drop=True)
    feature_summary["ablation_descriptive_rank"] = np.arange(
        1, len(feature_summary) + 1
    )

    block_summary = block_summary.sort_values(
        [
            "p_V_sign_worse", "delta_V_sign_median",
            "p_V_margin_worse", "delta_V_margin_median",
            "p_V_eq_worse", "delta_V_eq_median",
        ],
        ascending=[False, False, False, False, False, False],
    ).reset_index(drop=True)
    block_summary["ablation_descriptive_rank"] = np.arange(
        1, len(block_summary) + 1
    )

    feature_folds.to_csv(OUT_DIR / "feature_ablation_folds.csv", index=False)
    feature_summary.to_csv(OUT_DIR / "feature_ablation.csv", index=False)
    block_folds.to_csv(OUT_DIR / "block_ablation_folds.csv", index=False)
    block_summary.to_csv(OUT_DIR / "block_ablation.csv", index=False)

    def compact_feature_row(row):
        return {
            "feature": str(row["feature"]),
            "category": str(row["category"]),
            "pi_selection": float(row["pi_selection"]),
            "sign_consistency": float(row["sign_consistency"]),
            "p_V_sign_worse": float(row["p_V_sign_worse"]),
            "delta_V_sign_median": float(row["delta_V_sign_median"]),
            "p_V_margin_worse": float(row["p_V_margin_worse"]),
            "delta_V_margin_median": float(row["delta_V_margin_median"]),
            "p_V_eq_worse": float(row["p_V_eq_worse"]),
            "delta_V_eq_median": float(row["delta_V_eq_median"]),
            "delta_slack_sum_median": float(row["delta_slack_sum_median"]),
        }

    def compact_block_row(row):
        return {
            "block_id": str(row["block_id"]),
            "forced_zero_features": str(row["forced_zero_features"]).split("|"),
            "p_V_sign_worse": float(row["p_V_sign_worse"]),
            "delta_V_sign_median": float(row["delta_V_sign_median"]),
            "p_V_margin_worse": float(row["p_V_margin_worse"]),
            "delta_V_margin_median": float(row["delta_V_margin_median"]),
            "p_V_eq_worse": float(row["p_V_eq_worse"]),
            "delta_V_eq_median": float(row["delta_V_eq_median"]),
            "delta_slack_sum_median": float(row["delta_slack_sum_median"]),
        }

    summary = {
        "stage": "E",
        "status": "READY",
        "purpose": "development_paired_feature_and_block_ablation",
        "lambda1_star": float(lambda1_star),
        "reference": {
            "accepted_splits": int(len(accepted_splits)),
            "rejected_splits": int(len(rejected_splits)),
            "max_metric_diff_vs_stage_b": reference_max_diffs,
        },
        "interpretation": {
            "delta_definition": "ablated_metric - reference_metric",
            "positive_delta": "worse out-of-sample metric",
            "p_worse": "fraction of the same paired splits with delta > 0",
            "no_pass_fail_rule": True,
            "preprocessing_scope": (
                "All-30 train-only preprocessing/imputation retained; target "
                "weighted coefficients are forced to zero. Autonomous reduced "
                "preprocessing is tested later."
            ),
        },
        "fits": {
            "feature_targets": int(len(feature_targets)),
            "feature_ablation_fits": int(len(feature_folds)),
            "block_targets": int(len(block_targets)),
            "block_ablation_fits": int(len(block_folds)),
            "solver_failures": 0,
        },
        "feature_ablation_descriptive_order": [
            compact_feature_row(row)
            for _, row in feature_summary.iterrows()
        ],
        "block_ablation_descriptive_order": [
            compact_block_row(row)
            for _, row in block_summary.iterrows()
        ],
        "outputs": {
            "reference_fold_metrics": "stage_e/reference_fold_metrics.csv",
            "feature_ablation": "stage_e/feature_ablation.csv",
            "feature_ablation_folds": "stage_e/feature_ablation_folds.csv",
            "block_ablation": "stage_e/block_ablation.csv",
            "block_ablation_folds": "stage_e/block_ablation_folds.csv",
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_e_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STAGE_E_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
