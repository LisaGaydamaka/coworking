#!/usr/bin/env python3
"""
Stage H: nested mouse-level validation for eNRI feature selection.

Default production design:
- 30 valid stratified 80/20 outer mouse-level splits, seeds from 1000;
- 20 valid stratified 80/20 inner splits inside each outer-train;
- complete train-only feature-selection machinery inside each outer-train:
  correlations -> lambda1* -> stability selection -> block stability ->
  feature/block ablation -> block-aware ranking/compression -> S_k -> k*;
- 100 valid stability resamples per outer-train (minimum specified by plan);
- autonomous reduced preprocessing and reduced QP refit on the complete
  outer-train;
- outer-validation is used only once for final evaluation.

Environment overrides exist only for smoke testing:
NESTED_OUTER_TARGET, NESTED_INNER_TARGET, NESTED_STABILITY_TARGET.
The committed production result must use 30 / 20 / 100.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parent / "enri_mouse_neuroplasticity"
BASE_SOLVE = BASE_DIR / "solve_all0mean_grip.py"
STAGE_A_PY = ROOT / "stage_a.py"
STAGE_B_PY = ROOT / "stage_b.py"
STAGE_C_PY = ROOT / "stage_c.py"
STAGE_E_PY = ROOT / "stage_e.py"
STAGE_F_PY = ROOT / "stage_f.py"
FULLDATA_BLOCKS = ROOT / "stage_a" / "correlation_blocks.csv"
OUT_DIR = ROOT / "stage_h"

OUTER_TARGET = int(os.environ.get("NESTED_OUTER_TARGET", "30"))
INNER_TARGET = int(os.environ.get("NESTED_INNER_TARGET", "20"))
STABILITY_TARGET = int(os.environ.get("NESTED_STABILITY_TARGET", "100"))

PRODUCTION_OUTER = 30
PRODUCTION_INNER = 20
PRODUCTION_STABILITY = 100

OUTER_TRAIN_FRACTION = 0.80
INNER_TRAIN_FRACTION = 0.80
STABILITY_TRAIN_FRACTION = 0.80

OUTER_SEED_START = 1000
MAX_OUTER_CANDIDATES = int(os.environ.get("NESTED_MAX_OUTER_CANDIDATES", "1000"))
MAX_INNER_CANDIDATES = int(os.environ.get("NESTED_MAX_INNER_CANDIDATES", "500"))
MAX_STABILITY_CANDIDATES = int(os.environ.get("NESTED_MAX_STABILITY_CANDIDATES", "1000"))
STABILITY_SEED_BASE = 50000

ACTIVE_TOL = 1e-6
OUTER_MIN_TRAIN_O = 5
OUTER_MIN_VAL_O = 2
INNER_MIN_TRAIN_O = 4
INNER_MIN_VAL_O = 2
MIN_K = 3
MAX_K = 15

METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w")
PRIORITY_METRICS = METRICS


class OuterSelectionFailure(RuntimeError):
    pass


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stratified_split(mouse_df: pd.DataFrame, train_fraction: float, seed: int):
    X = np.zeros((len(mouse_df), 1), dtype=float)
    y = mouse_df["group"].to_numpy()
    splitter = StratifiedShuffleSplit(
        n_splits=1,
        train_size=train_fraction,
        random_state=int(seed),
    )
    train_idx, val_idx = next(splitter.split(X, y))
    train_ids = mouse_df.iloc[train_idx]["mouse_id"].tolist()
    val_ids = mouse_df.iloc[val_idx]["mouse_id"].tolist()
    return train_ids, val_ids


def quick_state_count_precheck(
    long_raw,
    train_ids,
    val_ids,
    required_min_train_o,
    required_min_val_o,
):
    """
    Cheap split feasibility filter based only on fixed group/week/death structure.

    O_A after preprocessing equals the number of living rows in the state,
    because stage-3 imputes admissible missing feature values rather than
    dropping living rows. Therefore impossible train/validation state counts
    can be rejected before the expensive IterativeImputer fit.
    """
    train_ids = set(train_ids)
    val_ids = set(val_ids)
    train_min = math.inf
    val_min = math.inf
    counts = {}

    for group in ("PBS", "LPS", "run", "MCC"):
        for week in (0, 16, 24):
            label = f"{group}^{week}"
            rows = long_raw[
                long_raw["group"].eq(group)
                & long_raw["week"].eq(week)
            ]
            train_o = int(
                (
                    rows["mouse_id"].isin(train_ids)
                    & ~rows["death"].astype(bool)
                ).sum()
            )
            val_o = int(
                (
                    rows["mouse_id"].isin(val_ids)
                    & ~rows["death"].astype(bool)
                ).sum()
            )
            counts[label] = {
                "train_O": train_o,
                "validation_O": val_o,
            }
            train_min = min(train_min, train_o)
            val_min = min(val_min, val_o)

    train_min = int(train_min if math.isfinite(train_min) else 0)
    val_min = int(val_min if math.isfinite(val_min) else 0)
    ok = (
        train_min >= int(required_min_train_o)
        and val_min >= int(required_min_val_o)
    )
    return ok, {
        "min_train_O": train_min,
        "min_validation_O": val_min,
        "state_counts": counts,
    }


def prepare_full_feature_split(
    base, long_raw, train_ids, val_ids, seed, split_index,
    required_min_train_o, required_min_val_o,
):
    final_std, prep = base.fit_transform_stage3(
        long_raw,
        fit_mouse_ids=train_ids,
        random_state=base.IMPUTATION_SEED,
        sample_posterior=False,
    )
    errors = list(prep.get("errors", []))

    train_states, xbar_train, train_stats = base.build_experimental_states(
        final_std,
        state_mouse_ids=train_ids,
        reference_xbar=None,
    )
    val_states, xbar_val, val_stats = base.build_experimental_states(
        final_std,
        state_mouse_ids=val_ids,
        reference_xbar=xbar_train,
    )
    errors.extend(train_stats.get("errors", []))
    errors.extend(val_stats.get("errors", []))

    train_o = {k: int(v["O"]) for k, v in train_states.items()} if train_states else {}
    val_o = {k: int(v["O"]) for k, v in val_states.items()} if val_states else {}
    min_train_o = min(train_o.values()) if train_o else 0
    min_val_o = min(val_o.values()) if val_o else 0
    if min_train_o < int(required_min_train_o):
        errors.append(
            f"train min O={min_train_o} < {int(required_min_train_o)}"
        )
    if min_val_o < int(required_min_val_o):
        errors.append(
            f"validation min O={min_val_o} < {int(required_min_val_o)}"
        )

    if xbar_train is None or xbar_val is None:
        errors.append("Missing train/validation xbar.")
    elif not np.allclose(
        np.asarray(xbar_train, dtype=float),
        np.asarray(xbar_val, dtype=float),
        rtol=0,
        atol=0,
    ):
        errors.append("Validation did not reuse training xbar exactly.")

    if errors:
        return None, {
            "seed": int(seed),
            "split_index": int(split_index),
            "min_train_O": int(min_train_o),
            "min_val_O": int(min_val_o),
            "errors": errors,
        }

    return {
        "seed": int(seed),
        "split_index": int(split_index),
        "train_ids": list(train_ids),
        "val_ids": list(val_ids),
        "final_std": final_std,
        "train_states": train_states,
        "val_states": val_states,
        "xbar_train": np.asarray(xbar_train, dtype=float),
        "prep_stats": prep,
        "min_train_O": int(min_train_o),
        "min_val_O": int(min_val_o),
    }, None


def collect_outer_splits(base, long_raw, mouse_df):
    accepted = []
    rejected = []
    for candidate_index in range(MAX_OUTER_CANDIDATES):
        if len(accepted) >= OUTER_TARGET:
            break
        seed = OUTER_SEED_START + candidate_index
        train_ids, val_ids = stratified_split(
            mouse_df, OUTER_TRAIN_FRACTION, seed
        )
        split, reject = prepare_full_feature_split(
            base,
            long_raw,
            train_ids,
            val_ids,
            seed=seed,
            split_index=len(accepted),
            required_min_train_o=OUTER_MIN_TRAIN_O,
            required_min_val_o=OUTER_MIN_VAL_O,
        )
        if split is None:
            rejected.append(reject)
        else:
            split["outer_candidate_index"] = int(candidate_index)
            accepted.append(split)

    if len(accepted) < OUTER_TARGET:
        raise RuntimeError(
            f"Only {len(accepted)} valid outer splits; target={OUTER_TARGET}."
        )
    return accepted, rejected


def collect_inner_splits(base, outer_index, outer_train_raw, outer_train_mouse_df):
    accepted = []
    rejected = []
    for candidate_index in range(MAX_INNER_CANDIDATES):
        if len(accepted) >= INNER_TARGET:
            break
        seed = 10000 + 100 * int(outer_index) + candidate_index
        train_ids, val_ids = stratified_split(
            outer_train_mouse_df, INNER_TRAIN_FRACTION, seed
        )
        quick_ok, quick_stats = quick_state_count_precheck(
            outer_train_raw,
            train_ids,
            val_ids,
            required_min_train_o=INNER_MIN_TRAIN_O,
            required_min_val_o=INNER_MIN_VAL_O,
        )
        if not quick_ok:
            rejected.append({
                "seed": int(seed),
                "split_index": int(len(accepted)),
                "phase": "cheap_state_count_precheck",
                **quick_stats,
                "errors": [
                    f"cheap precheck min train O={quick_stats['min_train_O']} "
                    f"or min validation O={quick_stats['min_validation_O']} "
                    "below nested inner threshold"
                ],
            })
            continue

        split, reject = prepare_full_feature_split(
            base,
            outer_train_raw,
            train_ids,
            val_ids,
            seed=seed,
            split_index=len(accepted),
            required_min_train_o=INNER_MIN_TRAIN_O,
            required_min_val_o=INNER_MIN_VAL_O,
        )
        if split is None:
            rejected.append(reject)
        else:
            split["inner_candidate_index"] = int(candidate_index)
            accepted.append(split)
            if (
                len(accepted) == 1
                or len(accepted) % 5 == 0
                or len(accepted) == INNER_TARGET
            ):
                print(
                    f"STAGE_H_INNER_PROGRESS outer={outer_index} "
                    f"valid={len(accepted)}/{INNER_TARGET} "
                    f"candidate_index={candidate_index}",
                    flush=True,
                )

    if len(accepted) < INNER_TARGET:
        raise OuterSelectionFailure(
            f"outer {outer_index}: only {len(accepted)} valid inner splits; "
            f"target={INNER_TARGET}"
        )
    return accepted, rejected


def compute_outer_correlation_blocks(base, stage_a, outer_final_std, outer_train_ids):
    train_set = set(outer_train_ids)
    living = outer_final_std[
        outer_final_std["mouse_id"].isin(train_set)
        & outer_final_std["status"].isin(["observed", "imputed"])
    ].copy()
    features = list(base.MODEL_FEATURES)
    pooled, centered = stage_a.spearman_matrices(living, features)
    pair_table = stage_a.build_pair_table(
        living, features, pooled, centered
    )
    blocks, components = stage_a.connected_components(
        features, pair_table
    )
    return pair_table, blocks, components


def solve_sparse_on_split(base, sparse, split, lambda1, forced=None):
    train_ids = set(split["train_ids"])
    train_df = split["final_std"][
        split["final_std"]["mouse_id"].isin(train_ids)
    ].copy()
    solution, meta = sparse.solve_sparse_qp(
        base,
        train_df,
        split["train_states"],
        split["xbar_train"],
        lambda1=float(lambda1),
        forced_zero_features=[] if forced is None else list(forced),
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
    return {
        "solution": solution,
        "metrics": {m: float(metrics[m]) for m in METRICS},
    }, None


def aggregate_metric_rows(rows, group_key):
    df = pd.DataFrame(rows)
    out = []
    for key, sub in df.groupby(group_key, sort=False):
        row = {group_key: key, "folds": int(len(sub))}
        for metric in METRICS:
            vals = sub[metric].astype(float)
            sd = float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0
            row[f"{metric}_mean"] = float(vals.mean())
            row[f"{metric}_sd"] = sd
            row[f"{metric}_se"] = float(sd / math.sqrt(len(vals)))
            row[f"{metric}_median"] = float(vals.median())
        out.append(row)
    return pd.DataFrame(out)


def choose_lambda1(base, sparse, outer_split, inner_splits):
    train_ids = set(outer_split["train_ids"])
    outer_train_df = outer_split["final_std"][
        outer_split["final_std"]["mouse_id"].isin(train_ids)
    ].copy()

    sol03, meta03 = sparse.solve_sparse_qp(
        base,
        outer_train_df,
        outer_split["train_states"],
        outer_split["xbar_train"],
        lambda1=0.3,
        forced_zero_features=[],
    )
    if sol03 is None or meta03.get("errors"):
        raise OuterSelectionFailure(
            "lambda1=0.3 outer-train diagnostic failed: "
            + " | ".join(meta03.get("errors", []))
        )

    grid = list(sparse.BASE_LAMBDA1_GRID)
    extended = int(sol03["active_count"]) > 15
    if extended:
        grid.extend(sparse.EXTENDED_LAMBDA1)

    fold_rows = []
    for lambda1 in grid:
        for split in inner_splits:
            fit, err = solve_sparse_on_split(
                base, sparse, split, lambda1=lambda1
            )
            if err:
                raise OuterSelectionFailure(
                    f"lambda1={lambda1}, inner seed={split['seed']}: "
                    + " | ".join(err["errors"])
                )
            fold_rows.append({
                "lambda1": float(lambda1),
                "seed": int(split["seed"]),
                **fit["metrics"],
                "active_count": int(fit["solution"]["active_count"]),
            })

    agg_rows = []
    fold_df = pd.DataFrame(fold_rows)
    for lambda1 in grid:
        sub = fold_df[np.isclose(
            fold_df["lambda1"].astype(float).to_numpy(),
            float(lambda1),
            rtol=0,
            atol=1e-15,
        )]
        if len(sub) != INNER_TARGET:
            raise OuterSelectionFailure(
                f"lambda1={lambda1}: {len(sub)}/{INNER_TARGET} inner fits."
            )
        row = {
            "lambda1": float(lambda1),
            "folds": int(len(sub)),
            "active_count_mean": float(sub["active_count"].mean()),
            "active_count_median": float(sub["active_count"].median()),
        }
        for metric in METRICS:
            vals = sub[metric].astype(float)
            sd = float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0
            row[f"{metric}_mean"] = float(vals.mean())
            row[f"{metric}_sd"] = sd
            row[f"{metric}_se"] = float(sd / math.sqrt(len(vals)))
        agg_rows.append(row)
    aggregate_df = pd.DataFrame(agg_rows)
    selected, trace = sparse.one_se_select(aggregate_df)
    return {
        "lambda1_star": float(selected["lambda1"]),
        "grid": [float(x) for x in grid],
        "grid_extended": bool(extended),
        "active_at_0_3": int(sol03["active_count"]),
        "folds": fold_df,
        "aggregate": aggregate_df,
        "trace": trace,
    }


def stability_selection(
    base, sparse, stage_c, outer_index, outer_train_raw,
    outer_train_mouse_df, lambda1_star
):
    valid_records = []
    rejected = []
    for candidate_index in range(MAX_STABILITY_CANDIDATES):
        if len(valid_records) >= STABILITY_TARGET:
            break
        seed = (
            STABILITY_SEED_BASE
            + 1000 * int(outer_index)
            + candidate_index
        )
        record, reject = stage_c.fit_one_resample(
            base,
            sparse,
            outer_train_raw,
            outer_train_mouse_df,
            seed,
            lambda1_star,
        )
        if record is not None:
            record["resample_index"] = len(valid_records) + 1
            valid_records.append(record)
            if (
                len(valid_records) == 1
                or len(valid_records) % 25 == 0
                or len(valid_records) == STABILITY_TARGET
            ):
                print(
                    f"STAGE_H_STABILITY_PROGRESS outer={outer_index} "
                    f"valid={len(valid_records)}/{STABILITY_TARGET} "
                    f"candidate_index={candidate_index}",
                    flush=True,
                )
        else:
            rejected.append(reject)

    if len(valid_records) < STABILITY_TARGET:
        raise OuterSelectionFailure(
            f"outer {outer_index}: only {len(valid_records)} valid stability "
            f"resamples; target={STABILITY_TARGET}"
        )

    summary = stage_c.summarize_features(base, valid_records)
    return valid_records, rejected, summary


def derive_block_structures(blocks_df, valid_records):
    active_matrix = np.vstack(
        [r["active"] for r in valid_records]
    ).astype(bool)
    feature_order = {
        feature: i for i, feature in enumerate(
            blocks_df.sort_values("feature_order")["feature"].tolist()
        )
    }

    block_defs = {}
    for block_id, sub in blocks_df[
        blocks_df["is_correlation_block"].astype(bool)
    ].groupby("block_id", sort=False):
        members = (
            sub.sort_values("feature_order")["feature"]
            .astype(str).tolist()
        )
        block_defs[str(block_id)] = members

    block_stats = {}
    all_features = blocks_df.sort_values("feature_order")["feature"].astype(str).tolist()
    index = {f: i for i, f in enumerate(all_features)}
    for block_id, members in block_defs.items():
        A = active_matrix[:, [index[f] for f in members]]
        count = A.sum(axis=1)
        block_stats[block_id] = {
            "members": members,
            "pi_block_any_selected": float(np.mean(count >= 1)),
            "p_exactly_one_selected": float(np.mean(count == 1)),
            "p_multiple_selected": float(np.mean(count >= 2)),
            "p_all_selected": float(np.mean(count == len(members))),
        }
    return block_defs, block_stats


def summarize_ablation_rows(stage_e, rows, key_col):
    if not rows:
        return pd.DataFrame()
    return stage_e.summarize_ablation(
        pd.DataFrame(rows),
        [key_col],
    )


def run_ablation(
    base, sparse, stage_e, inner_splits, lambda1_star,
    stability_summary, block_defs
):
    reference = {}
    failures = []
    for split in inner_splits:
        fit, err = stage_e.evaluate_fit(
            base, sparse, split, lambda1_star, []
        )
        if err:
            failures.append(("reference", "", split["seed"], err))
            continue
        reference[int(split["seed"])] = fit
    if failures or len(reference) != len(inner_splits):
        raise OuterSelectionFailure(
            f"Reference inner ablation fits failed: {len(failures)}"
        )

    feature_targets = (
        stability_summary[
            stability_summary["category"].isin(["core", "candidate"])
        ]
        .sort_values("stability_rank")["feature"]
        .astype(str).tolist()
    )

    feature_rows = []
    for feature in feature_targets:
        for split in inner_splits:
            ref = reference[int(split["seed"])]
            abl, err = stage_e.evaluate_fit(
                base, sparse, split, lambda1_star, [feature]
            )
            if err:
                raise OuterSelectionFailure(
                    f"Feature ablation {feature}, seed={split['seed']}: "
                    + " | ".join(err["errors"])
                )
            row = {
                "feature": feature,
                "seed": int(split["seed"]),
                "fold": int(split["split_index"]) + 1,
                "forced_zero_count": 1,
                "forced_zero_features": feature,
                "delta_active_count": int(
                    abl["active_count"] - ref["active_count"]
                ),
                "delta_slack_sum": float(
                    abl["slack_sum"] - ref["slack_sum"]
                ),
            }
            for metric in METRICS:
                row[f"delta_{metric}"] = float(
                    abl[metric] - ref[metric]
                )
            feature_rows.append(row)

    block_rows = []
    for block_id, members in block_defs.items():
        for split in inner_splits:
            ref = reference[int(split["seed"])]
            abl, err = stage_e.evaluate_fit(
                base, sparse, split, lambda1_star, members
            )
            if err:
                raise OuterSelectionFailure(
                    f"Block ablation {block_id}, seed={split['seed']}: "
                    + " | ".join(err["errors"])
                )
            row = {
                "block_id": block_id,
                "seed": int(split["seed"]),
                "fold": int(split["split_index"]) + 1,
                "forced_zero_count": len(members),
                "forced_zero_features": "|".join(members),
                "delta_active_count": int(
                    abl["active_count"] - ref["active_count"]
                ),
                "delta_slack_sum": float(
                    abl["slack_sum"] - ref["slack_sum"]
                ),
            }
            for metric in METRICS:
                row[f"delta_{metric}"] = float(
                    abl[metric] - ref[metric]
                )
            block_rows.append(row)

    feature_summary = summarize_ablation_rows(
        stage_e, feature_rows, "feature"
    )
    block_summary = summarize_ablation_rows(
        stage_e, block_rows, "block_id"
    )
    return {
        "feature_targets": feature_targets,
        "feature_folds": pd.DataFrame(feature_rows),
        "block_folds": pd.DataFrame(block_rows),
        "feature_summary": feature_summary,
        "block_summary": block_summary,
    }


def ablation_tuple(feature, block_id, feature_abl_map, block_abl_map):
    f = feature_abl_map.get(feature)
    b = block_abl_map.get(block_id) if block_id else None
    src = f if f is not None else b
    if src is None:
        return tuple([-float("inf")] * 10), "none"

    vals = []
    for metric in ("V_pos", "V_sign", "V_margin", "V_eq", "V_var"):
        vals.append(float(src.get(f"p_{metric}_worse", -float("inf"))))
        vals.append(float(src.get(f"delta_{metric}_median", -float("inf"))))
    return tuple(vals), ("feature" if f is not None else "block")


def build_ranking(
    base, blocks_df, stability_summary,
    feature_ablation_summary, block_ablation_summary
):
    canonical = {f: i + 1 for i, f in enumerate(base.MODEL_FEATURES)}
    stability_map = stability_summary.set_index("feature").to_dict(orient="index")
    feature_abl_map = (
        feature_ablation_summary.set_index("feature").to_dict(orient="index")
        if not feature_ablation_summary.empty else {}
    )
    block_abl_map = (
        block_ablation_summary.set_index("block_id").to_dict(orient="index")
        if not block_ablation_summary.empty else {}
    )

    feature_block = {}
    for _, row in blocks_df.iterrows():
        is_block = bool(row["is_correlation_block"])
        feature_block[str(row["feature"])] = (
            str(row["block_id"]) if is_block else None
        )

    records = {}
    for feature in base.MODEL_FEATURES:
        stab = stability_map[feature]
        block_id = feature_block[feature]
        abl_tuple, abl_source = ablation_tuple(
            feature, block_id, feature_abl_map, block_abl_map
        )
        records[feature] = {
            "feature": feature,
            "feature_order": canonical[feature],
            "block_id": block_id,
            "pi_selection": float(stab["pi_selection"]),
            "sign_consistency": (
                float(stab["sign_consistency"])
                if pd.notna(stab["sign_consistency"]) else -1.0
            ),
            "category": str(stab["category"]),
            "abs_gamma_median_selected": (
                float(stab["abs_gamma_median_selected"])
                if pd.notna(stab["abs_gamma_median_selected"]) else 0.0
            ),
            "ablation_tuple": abl_tuple,
            "ablation_source": abl_source,
        }

    def rank_key(feature):
        r = records[feature]
        return (
            -r["pi_selection"],
            -r["sign_consistency"],
            *[-x for x in r["ablation_tuple"]],
            -r["abs_gamma_median_selected"],
            r["feature_order"],
        )

    block_member_order = {}
    block_primary = {}
    block_rows = blocks_df[blocks_df["is_correlation_block"].astype(bool)]
    for block_id, sub in block_rows.groupby("block_id", sort=False):
        members = sub.sort_values("feature_order")["feature"].astype(str).tolist()
        ordered = sorted(members, key=rank_key)
        block_member_order[str(block_id)] = ordered
        block_primary[str(block_id)] = ordered[0]

    # Per frozen Stage F, all features outside correlation blocks remain
    # eligible. Stability category changes ranking but is not a hard filter.
    singleton_features = [
        feature
        for feature in base.MODEL_FEATURES
        if feature_block[feature] is None
    ]

    return {
        "records": records,
        "rank_key": rank_key,
        "feature_block": feature_block,
        "block_member_order": block_member_order,
        "block_primary": block_primary,
        "singleton_features": singleton_features,
        "canonical": canonical,
    }


def metric_summary(df):
    row = {}
    n = len(df)
    for metric in METRICS:
        vals = df[metric].astype(float)
        sd = float(vals.std(ddof=1)) if n >= 2 else 0.0
        row[f"{metric}_mean"] = float(vals.mean())
        row[f"{metric}_sd"] = sd
        row[f"{metric}_se"] = float(sd / math.sqrt(n))
        row[f"{metric}_median"] = float(vals.median())
    return row


def reduced_subset_fit_cached(
    base, sparse, stage_f, outer_train_raw, inner_splits,
    features, canonical, cache, label
):
    features_canonical = tuple(
        sorted(set(features), key=lambda x: canonical[x])
    )
    if features_canonical in cache:
        return cache[features_canonical]

    rows = []
    for split in inner_splits:
        fit, err = stage_f.build_reduced_split(
            base,
            sparse,
            outer_train_raw,
            split,
            features_canonical,
            required_min_train_o=INNER_MIN_TRAIN_O,
            required_min_val_o=INNER_MIN_VAL_O,
        )
        if err:
            raise OuterSelectionFailure(
                f"Reduced subset {label}, inner seed={split['seed']}, "
                f"stage={err['stage']}: "
                + " | ".join(map(str, err["errors"]))
            )
        rows.append({
            "seed": int(split["seed"]),
            "fold": int(split["split_index"]) + 1,
            "features": "|".join(features_canonical),
            **fit["metrics"],
            "active_count": int(fit["active_count"]),
            "slack_sum": float(fit["slack_sum"]),
        })
    df = pd.DataFrame(rows)
    result = (df, metric_summary(df))
    cache[features_canonical] = result
    return result


def compress_blocks_and_build_pool(
    base, sparse, stage_f, outer_train_raw, inner_splits, ranking
):
    block_member_order = ranking["block_member_order"]
    block_primary = ranking["block_primary"]
    singleton_features = ranking["singleton_features"]
    canonical = ranking["canonical"]
    rank_key = ranking["rank_key"]

    cache = {}
    retained = {}
    compression_rows = []
    block_ids = sorted(block_primary)

    for block_id in block_ids:
        ordered = block_member_order[block_id]
        other_primaries = [
            block_primary[b] for b in block_ids if b != block_id
        ]
        anchors = list(dict.fromkeys(singleton_features + other_primaries))
        full_features = list(dict.fromkeys(anchors + ordered))
        _, full_summary = reduced_subset_fit_cached(
            base, sparse, stage_f, outer_train_raw, inner_splits,
            full_features, canonical, cache, f"{block_id}_full",
        )

        selected = ordered.copy()
        for m in range(1, len(ordered) + 1):
            candidate_members = ordered[:m]
            candidate_features = list(dict.fromkeys(
                anchors + candidate_members
            ))
            _, cand_summary = reduced_subset_fit_cached(
                base, sparse, stage_f, outer_train_raw, inner_splits,
                candidate_features, canonical, cache, f"{block_id}_m{m}",
            )
            passes = {}
            all_pass = True
            for metric in PRIORITY_METRICS:
                threshold = (
                    full_summary[f"{metric}_mean"]
                    + full_summary[f"{metric}_se"]
                )
                passed = (
                    cand_summary[f"{metric}_mean"]
                    <= threshold + 1e-15
                )
                passes[metric] = bool(passed)
                all_pass = all_pass and passed

            compression_rows.append({
                "block_id": block_id,
                "m": int(m),
                "candidate_members": "|".join(candidate_members),
                "all_metrics_within_one_se": bool(all_pass),
                **{f"{metric}_pass": passes[metric] for metric in METRICS},
            })
            if all_pass:
                selected = candidate_members
                break
        retained[block_id] = selected

    pool = list(singleton_features)
    for block_id in block_ids:
        pool.extend(retained[block_id])
    pool = list(dict.fromkeys(pool))
    pool = sorted(pool, key=rank_key)

    if len(pool) < MIN_K:
        raise OuterSelectionFailure(
            f"Only {len(pool)} candidates after block compression."
        )

    return {
        "retained_by_block": retained,
        "pool": pool,
        "cache": cache,
        "compression": pd.DataFrame(compression_rows),
    }


def select_k_from_pool(
    base, sparse, stage_f, outer_train_raw, inner_splits,
    ranking, compression_result
):
    canonical = ranking["canonical"]
    pool = compression_result["pool"]
    cache = compression_result["cache"]
    max_k = min(MAX_K, len(pool))

    rows = []
    fold_frames = []
    for k in range(MIN_K, max_k + 1):
        subset_ranked = pool[:k]
        folds, summary = reduced_subset_fit_cached(
            base, sparse, stage_f, outer_train_raw, inner_splits,
            subset_ranked, canonical, cache, f"S{k}",
        )
        row = {
            "k": int(k),
            "ranked_features": "|".join(subset_ranked),
            **summary,
        }
        rows.append(row)
        copy = folds.copy()
        copy["k"] = int(k)
        fold_frames.append(copy)

    table = pd.DataFrame(rows).sort_values("k").reset_index(drop=True)
    survivors = table.copy()
    trace = []
    for metric in METRICS:
        mean_col = f"{metric}_mean"
        se_col = f"{metric}_se"
        best_mean = float(survivors[mean_col].min())
        tied = survivors[np.isclose(
            survivors[mean_col].astype(float).to_numpy(),
            best_mean,
            rtol=0,
            atol=1e-15,
        )].sort_values("k")
        ref = tied.iloc[0]
        threshold = best_mean + float(ref[se_col])
        before = survivors["k"].astype(int).tolist()
        survivors = survivors[
            survivors[mean_col].astype(float) <= threshold + 1e-15
        ].copy().sort_values("k")
        trace.append({
            "metric": metric,
            "reference_best_k": int(ref["k"]),
            "best_mean": best_mean,
            "best_se": float(ref[se_col]),
            "threshold": threshold,
            "survivors_before": before,
            "survivors_after": survivors["k"].astype(int).tolist(),
        })
        if survivors.empty:
            raise OuterSelectionFailure(
                f"No S_k survivors after {metric}."
            )

    selected_k = int(survivors["k"].min())
    selected_features = pool[:selected_k]
    return {
        "selected_k": selected_k,
        "selected_features": selected_features,
        "table": table,
        "folds": pd.concat(fold_frames, ignore_index=True),
        "trace": trace,
        "final_survivors": survivors["k"].astype(int).tolist(),
    }


def required_acquisition_fields(base, selected_features):
    required = set(selected_features)
    latency_to_time = {
        latency: time for time, latency in base.OBJECT_LATENCY_PAIRS
    }
    for feature in list(selected_features):
        if feature in latency_to_time:
            required.add(latency_to_time[feature])

    # Exact deterministic recovery dependencies for a selected object-time
    # feature: TotalTime and the other object-time field.
    for cfg in base.NOR_BLOCKS.values():
        tp = cfg["time_p"]
        ts = cfg["time_s"]
        total = cfg["total"]
        if tp in selected_features:
            required.add(ts)
            required.add(total)
        if ts in selected_features:
            required.add(tp)
            required.add(total)

    return sorted(required)


def fit_selected_outer_model(
    base, sparse, stage_f, long_raw, outer_split, selected_features
):
    final_std, prep = stage_f.reduced_preprocess(
        base,
        long_raw,
        selected_features,
        fit_mouse_ids=outer_split["train_ids"],
    )
    if final_std is None or prep.get("errors"):
        raise OuterSelectionFailure(
            "Outer reduced preprocessing failed: "
            + " | ".join(map(str, prep.get("errors", [])))
        )

    with stage_f.feature_space(base, selected_features):
        train_states, xbar_train, train_stats = base.build_experimental_states(
            final_std,
            state_mouse_ids=outer_split["train_ids"],
            reference_xbar=None,
        )
        val_states, xbar_val, val_stats = base.build_experimental_states(
            final_std,
            state_mouse_ids=outer_split["val_ids"],
            reference_xbar=xbar_train,
        )
        errors = (
            list(train_stats.get("errors", []))
            + list(val_stats.get("errors", []))
        )
        min_train_o = min(int(v["O"]) for v in train_states.values())
        min_val_o = min(int(v["O"]) for v in val_states.values())
        if min_train_o < OUTER_MIN_TRAIN_O:
            errors.append(
                f"Reduced outer train min O={min_train_o} < "
                f"{OUTER_MIN_TRAIN_O}."
            )
        if min_val_o < OUTER_MIN_VAL_O:
            errors.append(
                f"Reduced outer val min O={min_val_o} < "
                f"{OUTER_MIN_VAL_O}."
            )
        if errors:
            raise OuterSelectionFailure(
                "Outer reduced states failed: " + " | ".join(errors)
            )

        train_set = set(outer_split["train_ids"])
        train_df = final_std[
            final_std["mouse_id"].isin(train_set)
        ].copy()
        solution, meta = sparse.solve_sparse_qp(
            base,
            train_df,
            train_states,
            xbar_train,
            lambda1=0.0,
            forced_zero_features=[],
        )
        if solution is None or meta.get("errors"):
            raise OuterSelectionFailure(
                "Outer reduced QP failed: "
                + " | ".join(meta.get("errors", []))
            )

        metrics = base.evaluate_validation_metrics(
            final_std,
            outer_split["val_ids"],
            val_states,
            xbar_train,
            solution["w"],
            rho=sparse.RHO,
        )

        val_group_means = {
            label: float(s["a"] + s["b"] @ solution["w"])
            for label, s in val_states.items()
        }
        train_group_means = {
            label: float(s["a"] + s["b"] @ solution["w"])
            for label, s in train_states.items()
        }

        weights = {
            f: float(w)
            for f, w in zip(selected_features, solution["w"])
        }

    return {
        "metrics": {m: float(metrics[m]) for m in METRICS},
        "validation_min_enri": float(metrics["validation_min_enri"]),
        "weights": weights,
        "slack_sum": float(solution["slack_sum"]),
        "slack_max": float(solution["slack_max"]),
        "solver_status": str(solution["solver_status"]),
        "solver_used": str(solution.get("solver_used", "")),
        "train_group_means": train_group_means,
        "validation_group_means": val_group_means,
        "imputed_selected_cells": int(prep["imputed_selected_cells"]),
        "max_selected_missing": int(prep["max_selected_missing"]),
    }


def block_signature(members):
    return "|".join(sorted(members))


def run_one_outer(
    base, sparse, stage_a, stage_c, stage_e, stage_f,
    long_raw, mouse_df, outer_split, outer_index
):
    outer_train_set = set(outer_split["train_ids"])
    outer_train_raw = long_raw[
        long_raw["mouse_id"].isin(outer_train_set)
    ].copy()
    outer_train_mouse_df = mouse_df[
        mouse_df["mouse_id"].isin(outer_train_set)
    ].copy().reset_index(drop=True)

    inner_splits, inner_rejected = collect_inner_splits(
        base, outer_index, outer_train_raw, outer_train_mouse_df
    )

    pair_table, blocks_df, components = compute_outer_correlation_blocks(
        base,
        stage_a,
        outer_split["final_std"],
        outer_split["train_ids"],
    )
    if blocks_df["is_correlation_block"].dtype != bool:
        blocks_df["is_correlation_block"] = (
            blocks_df["is_correlation_block"].astype(str).str.lower().eq("true")
        )

    lambda_result = choose_lambda1(
        base, sparse, outer_split, inner_splits
    )
    lambda1_star = lambda_result["lambda1_star"]

    valid_records, stability_rejected, stability_summary = stability_selection(
        base,
        sparse,
        stage_c,
        outer_index,
        outer_train_raw,
        outer_train_mouse_df,
        lambda1_star,
    )

    block_defs, block_stats = derive_block_structures(
        blocks_df, valid_records
    )

    ablation = run_ablation(
        base,
        sparse,
        stage_e,
        inner_splits,
        lambda1_star,
        stability_summary,
        block_defs,
    )

    ranking = build_ranking(
        base,
        blocks_df,
        stability_summary,
        ablation["feature_summary"],
        ablation["block_summary"],
    )

    compression = compress_blocks_and_build_pool(
        base,
        sparse,
        stage_f,
        outer_train_raw,
        inner_splits,
        ranking,
    )

    k_result = select_k_from_pool(
        base,
        sparse,
        stage_f,
        outer_train_raw,
        inner_splits,
        ranking,
        compression,
    )

    selected_features = k_result["selected_features"]
    outer_model = fit_selected_outer_model(
        base,
        sparse,
        stage_f,
        long_raw,
        outer_split,
        selected_features,
    )

    acquisition_fields = required_acquisition_fields(
        base, selected_features
    )

    selected_blocks = []
    selected_set = set(selected_features)
    for block_id, members in block_defs.items():
        if selected_set.intersection(members):
            selected_blocks.append({
                "block_id": block_id,
                "signature": block_signature(members),
                "members": members,
                "selected_members": sorted(
                    selected_set.intersection(members)
                ),
                "pi_block_any_selected": float(
                    block_stats[block_id]["pi_block_any_selected"]
                ),
            })

    detail = {
        "outer_index": int(outer_index),
        "outer_seed": int(outer_split["seed"]),
        "outer_train_n": int(len(outer_split["train_ids"])),
        "outer_validation_n": int(len(outer_split["val_ids"])),
        "inner_valid_splits": int(len(inner_splits)),
        "inner_rejected_splits": int(len(inner_rejected)),
        "lambda1_star": float(lambda1_star),
        "lambda1_grid": lambda_result["grid"],
        "lambda1_grid_extended": bool(lambda_result["grid_extended"]),
        "stability_valid_resamples": int(len(valid_records)),
        "stability_rejected_resamples": int(len(stability_rejected)),
        "core_features": stability_summary[
            stability_summary["category"].eq("core")
        ]["feature"].astype(str).tolist(),
        "candidate_features": stability_summary[
            stability_summary["category"].eq("candidate")
        ]["feature"].astype(str).tolist(),
        "correlation_blocks": [
            {
                "block_id": block_id,
                "members": members,
                **block_stats[block_id],
            }
            for block_id, members in block_defs.items()
        ],
        "block_primary": ranking["block_primary"],
        "retained_by_block": compression["retained_by_block"],
        "candidate_pool": compression["pool"],
        "selected_k": int(k_result["selected_k"]),
        "selected_features": selected_features,
        "final_k_survivors": k_result["final_survivors"],
        "required_acquisition_fields": acquisition_fields,
        "selected_blocks": selected_blocks,
        "outer_metrics": outer_model["metrics"],
        "outer_validation_min_enri": float(
            outer_model["validation_min_enri"]
        ),
        "slack_sum": float(outer_model["slack_sum"]),
        "slack_max": float(outer_model["slack_max"]),
        "solver_status": outer_model["solver_status"],
        "solver_used": outer_model["solver_used"],
        "validation_group_means": outer_model["validation_group_means"],
        "train_group_means": outer_model["train_group_means"],
        "weights": outer_model["weights"],
    }

    diagnostics = {
        "lambda_path": lambda_result["aggregate"],
        "stability": stability_summary,
        "feature_ablation": ablation["feature_summary"],
        "block_ablation": ablation["block_summary"],
        "block_compression": compression["compression"],
        "subset_path": k_result["table"],
    }
    return detail, diagnostics


def aggregate_results(base, valid_details, full_data_blocks):
    n = len(valid_details)

    outer_rows = []
    feature_counts = Counter()
    subset_counts = Counter()
    k_counts = Counter()
    lambda_counts = Counter()
    block_signature_exists = Counter()
    block_signature_selected = Counter()

    for d in valid_details:
        selected = tuple(d["selected_features"])
        subset_counts["|".join(selected)] += 1
        k_counts[int(d["selected_k"])] += 1
        lambda_counts[float(d["lambda1_star"])] += 1
        for f in selected:
            feature_counts[f] += 1

        present_sigs = set()
        selected_sigs = set()
        for b in d["correlation_blocks"]:
            sig = block_signature(b["members"])
            present_sigs.add(sig)
        for b in d["selected_blocks"]:
            selected_sigs.add(b["signature"])
        for sig in present_sigs:
            block_signature_exists[sig] += 1
        for sig in selected_sigs:
            block_signature_selected[sig] += 1

        row = {
            "outer_index": int(d["outer_index"]),
            "outer_seed": int(d["outer_seed"]),
            "selected_k": int(d["selected_k"]),
            "selected_features": "|".join(d["selected_features"]),
            "lambda1_star": float(d["lambda1_star"]),
            "required_acquisition_count": int(
                len(d["required_acquisition_fields"])
            ),
            "required_acquisition_fields": "|".join(
                d["required_acquisition_fields"]
            ),
            "slack_sum": float(d["slack_sum"]),
            "slack_max": float(d["slack_max"]),
            "validation_min_enri": float(
                d["outer_validation_min_enri"]
            ),
            "solver_status": d["solver_status"],
            "solver_used": d["solver_used"],
        }
        row.update({
            metric: float(d["outer_metrics"][metric])
            for metric in METRICS
        })
        for label, value in d["validation_group_means"].items():
            row[f"val_mean_{label}"] = float(value)
        outer_rows.append(row)

    outer_df = pd.DataFrame(outer_rows).sort_values("outer_index")
    feature_df = pd.DataFrame([
        {
            "feature": feature,
            "selected_count": int(feature_counts.get(feature, 0)),
            "selected_frequency": float(
                feature_counts.get(feature, 0) / n
            ),
        }
        for feature in base.MODEL_FEATURES
    ]).sort_values(
        ["selected_frequency", "feature"],
        ascending=[False, True],
    ).reset_index(drop=True)

    subset_df = pd.DataFrame([
        {
            "subset": subset,
            "count": int(count),
            "frequency": float(count / n),
            "k": len(subset.split("|")) if subset else 0,
        }
        for subset, count in subset_counts.items()
    ]).sort_values(
        ["count", "k", "subset"],
        ascending=[False, True, True],
    ).reset_index(drop=True)

    k_df = pd.DataFrame([
        {"k": int(k), "count": int(count), "frequency": float(count / n)}
        for k, count in sorted(k_counts.items())
    ])
    lambda_df = pd.DataFrame([
        {
            "lambda1_star": float(lam),
            "count": int(count),
            "frequency": float(count / n),
        }
        for lam, count in sorted(lambda_counts.items())
    ])

    block_sig_df = pd.DataFrame([
        {
            "block_signature": sig,
            "outer_present_count": int(block_signature_exists[sig]),
            "outer_present_frequency": float(
                block_signature_exists[sig] / n
            ),
            "outer_selected_count": int(
                block_signature_selected.get(sig, 0)
            ),
            "outer_selected_frequency": float(
                block_signature_selected.get(sig, 0) / n
            ),
            "selected_given_present": float(
                block_signature_selected.get(sig, 0)
                / block_signature_exists[sig]
            ),
        }
        for sig in sorted(block_signature_exists)
    ]).sort_values(
        ["outer_selected_frequency", "outer_present_frequency"],
        ascending=[False, False],
    ).reset_index(drop=True)

    # Post-hoc aggregation against the original full-data Stage-A blocks.
    # These reference blocks are never used in selection.
    ref_rows = []
    if full_data_blocks is not None:
        b = full_data_blocks.copy()
        if b["is_correlation_block"].dtype != bool:
            b["is_correlation_block"] = (
                b["is_correlation_block"].astype(str).str.lower().eq("true")
            )
        for block_id, sub in b[b["is_correlation_block"]].groupby(
            "block_id", sort=False
        ):
            members = set(sub["feature"].astype(str))
            count = sum(
                bool(members.intersection(d["selected_features"]))
                for d in valid_details
            )
            ref_rows.append({
                "reference_block_id": str(block_id),
                "members": "|".join(
                    sub.sort_values("feature_order")["feature"].astype(str)
                ),
                "selected_outer_count": int(count),
                "selected_outer_frequency": float(count / n),
            })
    ref_block_df = pd.DataFrame(ref_rows)

    metric_summary = {}
    for metric in METRICS:
        vals = outer_df[metric].astype(float)
        metric_summary[metric] = {
            "mean": float(vals.mean()),
            "median": float(vals.median()),
            "sd": float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0,
            "q10": float(vals.quantile(0.10)),
            "q90": float(vals.quantile(0.90)),
        }

    return {
        "outer": outer_df,
        "feature_frequency": feature_df,
        "subset_frequency": subset_df,
        "k_distribution": k_df,
        "lambda_distribution": lambda_df,
        "block_signature_frequency": block_sig_df,
        "reference_block_frequency": ref_block_df,
        "metric_summary": metric_summary,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = load_module(BASE_SOLVE, "enri_base_model_h")
    stage_a = load_module(STAGE_A_PY, "enri_stage_a_h")
    sparse = load_module(STAGE_B_PY, "enri_stage_b_h")
    stage_c = load_module(STAGE_C_PY, "enri_stage_c_h")
    stage_e = load_module(STAGE_E_PY, "enri_stage_e_h")
    stage_f = load_module(STAGE_F_PY, "enri_stage_f_h")

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    mouse_df = (
        source[["mouse_id", "group"]]
        .drop_duplicates()
        .sort_values("mouse_id")
        .reset_index(drop=True)
    )
    if len(mouse_df) != 54:
        raise RuntimeError(f"Expected 54 mice, got {len(mouse_df)}.")

    outer_candidates, initial_outer_rejected = collect_outer_splits(
        base, long_raw, mouse_df
    )

    valid_details = []
    rejected_details = list(initial_outer_rejected)
    diagnostic_rows = []

    # collect_outer_splits precollects OUTER_TARGET structurally valid splits.
    # If a complete nested selection later fails, continue with subsequent
    # deterministic outer seeds until OUTER_TARGET complete nested splits exist.
    next_candidate_index = (
        max(s["outer_candidate_index"] for s in outer_candidates) + 1
        if outer_candidates else 0
    )
    pending = list(outer_candidates)

    while len(valid_details) < OUTER_TARGET:
        if not pending:
            if next_candidate_index >= MAX_OUTER_CANDIDATES:
                raise RuntimeError(
                    f"Exhausted outer candidates with only "
                    f"{len(valid_details)}/{OUTER_TARGET} complete splits."
                )
            seed = OUTER_SEED_START + next_candidate_index
            train_ids, val_ids = stratified_split(
                mouse_df, OUTER_TRAIN_FRACTION, seed
            )
            split, reject = prepare_full_feature_split(
                base,
                long_raw,
                train_ids,
                val_ids,
                seed=seed,
                split_index=len(valid_details),
                required_min_train_o=OUTER_MIN_TRAIN_O,
                required_min_val_o=OUTER_MIN_VAL_O,
            )
            next_candidate_index += 1
            if split is None:
                reject["phase"] = "outer_precheck"
                rejected_details.append(reject)
                continue
            split["outer_candidate_index"] = next_candidate_index - 1
            pending.append(split)

        outer_split = pending.pop(0)
        outer_index = len(valid_details)
        # Inner seed formula uses the accepted nested outer index.
        outer_split["split_index"] = outer_index

        print(
            f"STAGE_H_PROGRESS outer={outer_index + 1}/{OUTER_TARGET} "
            f"seed={outer_split['seed']}",
            flush=True,
        )

        try:
            detail, diagnostics = run_one_outer(
                base,
                sparse,
                stage_a,
                stage_c,
                stage_e,
                stage_f,
                long_raw,
                mouse_df,
                outer_split,
                outer_index,
            )
        except Exception as exc:
            rejected_details.append({
                "phase": "nested_selection",
                "outer_seed": int(outer_split["seed"]),
                "outer_candidate_index": int(
                    outer_split["outer_candidate_index"]
                ),
                "error_type": type(exc).__name__,
                "errors": str(exc),
            })
            print(
                f"STAGE_H_REJECT seed={outer_split['seed']} "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )
            continue

        valid_details.append(detail)

        # Compact per-outer diagnostics as JSON-friendly records.
        diagnostic_rows.append({
            "outer_index": outer_index,
            "outer_seed": int(detail["outer_seed"]),
            "lambda1_star": float(detail["lambda1_star"]),
            "selected_k": int(detail["selected_k"]),
            "selected_features": "|".join(detail["selected_features"]),
            "core_features": "|".join(detail["core_features"]),
            "candidate_features": "|".join(detail["candidate_features"]),
            "candidate_pool": "|".join(detail["candidate_pool"]),
            "n_blocks": int(len(detail["correlation_blocks"])),
            "inner_rejected_splits": int(detail["inner_rejected_splits"]),
            "stability_rejected_resamples": int(
                detail["stability_rejected_resamples"]
            ),
        })

        # Checkpoint local files for transparency if later outer splits fail.
        pd.DataFrame(diagnostic_rows).to_csv(
            OUT_DIR / "nested_progress.csv", index=False
        )
        (OUT_DIR / "nested_outer_details.json").write_text(
            json.dumps(
                valid_details,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )

    full_data_blocks = (
        pd.read_csv(FULLDATA_BLOCKS)
        if FULLDATA_BLOCKS.exists() else None
    )
    agg = aggregate_results(base, valid_details, full_data_blocks)

    agg["outer"].to_csv(
        OUT_DIR / "nested_outer_results.csv", index=False
    )
    agg["feature_frequency"].to_csv(
        OUT_DIR / "nested_feature_frequency.csv", index=False
    )
    agg["subset_frequency"].to_csv(
        OUT_DIR / "nested_subset_frequency.csv", index=False
    )
    agg["k_distribution"].to_csv(
        OUT_DIR / "nested_k_distribution.csv", index=False
    )
    agg["lambda_distribution"].to_csv(
        OUT_DIR / "nested_lambda1_distribution.csv", index=False
    )
    agg["block_signature_frequency"].to_csv(
        OUT_DIR / "nested_block_signature_frequency.csv", index=False
    )
    if not agg["reference_block_frequency"].empty:
        agg["reference_block_frequency"].to_csv(
            OUT_DIR / "nested_reference_block_frequency.csv", index=False
        )

    if rejected_details:
        pd.DataFrame(rejected_details).to_csv(
            OUT_DIR / "nested_rejected_outer.csv", index=False
        )

    production = (
        OUTER_TARGET == PRODUCTION_OUTER
        and INNER_TARGET == PRODUCTION_INNER
        and STABILITY_TARGET == PRODUCTION_STABILITY
    )

    feature_top = agg["feature_frequency"].head(15)
    subset_top = agg["subset_frequency"].head(10)

    summary = {
        "stage": "H",
        "status": "READY" if production else "SMOKE_READY",
        "production_configuration": bool(production),
        "configuration": {
            "outer_target": OUTER_TARGET,
            "outer_train_fraction": OUTER_TRAIN_FRACTION,
            "outer_seed_start": OUTER_SEED_START,
            "inner_target": INNER_TARGET,
            "inner_train_fraction": INNER_TRAIN_FRACTION,
            "inner_seed_formula": (
                "10000 + 100*outer_index + candidate_index; "
                "outer_index is 0-based among accepted nested outer splits"
            ),
            "stability_target": STABILITY_TARGET,
            "stability_train_fraction": STABILITY_TRAIN_FRACTION,
            "stability_seed_formula": (
                f"{STABILITY_SEED_BASE} + 1000*outer_index + candidate_index"
            ),
            "outer_min_train_O": OUTER_MIN_TRAIN_O,
            "outer_min_validation_O": OUTER_MIN_VAL_O,
            "inner_min_train_O": INNER_MIN_TRAIN_O,
            "inner_min_validation_O": INNER_MIN_VAL_O,
        },
        "leakage_control": {
            "outer_validation_used_for_selection": False,
            "correlations_outer_train_only": True,
            "lambda1_outer_train_inner_only": True,
            "stability_outer_train_only": True,
            "ablation_outer_train_inner_only": True,
            "subset_selection_outer_train_inner_only": True,
            "reduced_preprocessing_train_only": True,
            "outer_validation_final_evaluation_only": True,
        },
        "completed_outer_splits": int(len(valid_details)),
        "rejected_outer_candidates": int(len(rejected_details)),
        "outer_metric_summary": agg["metric_summary"],
        "k_distribution": [
            {
                "k": int(row["k"]),
                "count": int(row["count"]),
                "frequency": float(row["frequency"]),
            }
            for _, row in agg["k_distribution"].iterrows()
        ],
        "lambda1_distribution": [
            {
                "lambda1_star": float(row["lambda1_star"]),
                "count": int(row["count"]),
                "frequency": float(row["frequency"]),
            }
            for _, row in agg["lambda_distribution"].iterrows()
        ],
        "top_feature_frequency": [
            {
                "feature": str(row["feature"]),
                "selected_count": int(row["selected_count"]),
                "selected_frequency": float(row["selected_frequency"]),
            }
            for _, row in feature_top.iterrows()
        ],
        "top_subset_frequency": [
            {
                "subset": str(row["subset"]),
                "count": int(row["count"]),
                "frequency": float(row["frequency"]),
                "k": int(row["k"]),
            }
            for _, row in subset_top.iterrows()
        ],
        "outputs": {
            "outer_results": "stage_h/nested_outer_results.csv",
            "feature_frequency": "stage_h/nested_feature_frequency.csv",
            "subset_frequency": "stage_h/nested_subset_frequency.csv",
            "k_distribution": "stage_h/nested_k_distribution.csv",
            "lambda1_distribution": "stage_h/nested_lambda1_distribution.csv",
            "block_signature_frequency": (
                "stage_h/nested_block_signature_frequency.csv"
            ),
            "reference_block_frequency": (
                "stage_h/nested_reference_block_frequency.csv"
                if not agg["reference_block_frequency"].empty else None
            ),
            "outer_details": "stage_h/nested_outer_details.json",
            "rejected_outer": (
                "stage_h/nested_rejected_outer.csv"
                if rejected_details else None
            ),
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_h_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "STAGE_H_SUMMARY="
        + json.dumps(summary, ensure_ascii=False, sort_keys=True),
        flush=True,
    )


if __name__ == "__main__":
    main()
