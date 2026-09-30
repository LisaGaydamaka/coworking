#!/usr/bin/env python3
"""
Stage F: block-aware ranking, within-block compression, and S_3...S_15
development candidate sets.

Key rules:
- ranking uses Stage-C selection frequency -> sign stability -> paired ablation
  -> median |raw-scale gamma| -> canonical feature order;
- individually stable singleton features (Stage-C core/candidate) enter directly;
- every Stage-A correlation block enters first through one primary
  representative, so a correlated information source is not discarded merely
  because its members substitute for one another;
- extra members of a block are retained only when a one-representative reduced
  model is not within one-SE of the full-block reference on the same 22
  development CV splits;
- each S_k is re-fit from scratch with autonomous reduced statistical
  preprocessing using only S_k + week indicators. Group is never an imputer
  predictor. The constrained reduced QP uses beta=lambda2=C=rho=0.1 and
  lambda1=0 after the subset has been fixed.

This is a development stage. Stage G will choose k; final nested validation
must repeat feature selection inside each outer-train.
"""

from __future__ import annotations

import importlib.util
import json
import math
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parent / "enri_mouse_neuroplasticity"
BASE_SOLVE = BASE_DIR / "solve_all0mean.py"
STAGE_B_PY = ROOT / "stage_b.py"
STAGE_C = ROOT / "stage_c" / "stability_selection.csv"
STAGE_A_BLOCKS = ROOT / "stage_a" / "correlation_blocks.csv"
STAGE_D = ROOT / "stage_d" / "block_stability.csv"
STAGE_E_FEATURE = ROOT / "stage_e" / "feature_ablation.csv"
STAGE_E_BLOCK = ROOT / "stage_e" / "block_ablation.csv"
OUT_DIR = ROOT / "stage_f"

METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w")
PRIORITY_METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w")
LAMBDA1_REDUCED = 0.0
MIN_K = 3
MAX_K = 15


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def feature_space(base, features):
    # solve_all0mean.py wraps the original base module. Patch both namespaces
    # so inherited preprocessing/state functions and the ALL0MEAN override use
    # the same reduced feature space.
    modules = [base]
    inner = getattr(base, "_base", None)
    if inner is not None:
        modules.append(inner)

    snapshots = []
    for module in modules:
        snapshots.append((
            module,
            list(module.MODEL_FEATURES),
            list(module.BASE_FEATURES),
        ))
        module.MODEL_FEATURES = list(features)
        module.BASE_FEATURES = list(features)
    try:
        yield
    finally:
        for module, old_model, old_base in snapshots:
            module.MODEL_FEATURES = old_model
            module.BASE_FEATURES = old_base


def reduced_preprocess(base, long_raw, features, fit_mouse_ids):
    features = list(features)
    fit_mouse_ids = set(fit_mouse_ids)

    # Deterministic NOR construction/censoring still has access to the raw
    # acquisition fields it needs. Statistical imputation below uses only the
    # selected weighted features plus week indicators.
    processed, det_stats = base.deterministic_preprocess(
        long_raw,
        fit_mouse_ids=fit_mouse_ids,
    )
    errors = list(det_stats.get("errors", []))

    living = ~processed["death"]
    fit_mask = living & processed["mouse_id"].isin(fit_mouse_ids)
    baseline_mask = fit_mask & processed["week"].eq(0)

    means = {}
    stds = {}
    n_obs = {}
    for feature in features:
        vals = pd.to_numeric(
            processed.loc[baseline_mask, feature], errors="coerce"
        ).dropna().astype(float)
        n_obs[feature] = int(len(vals))
        if len(vals) < 2:
            errors.append(
                f"{feature}: fewer than 2 available baseline train values ({len(vals)})."
            )
            means[feature] = np.nan
            stds[feature] = np.nan
            continue
        means[feature] = float(vals.mean())
        stds[feature] = float(vals.std(ddof=1))
        if not math.isfinite(means[feature]):
            errors.append(f"{feature}: non-finite baseline train mean.")
        if not math.isfinite(stds[feature]) or stds[feature] <= 0:
            errors.append(f"{feature}: invalid baseline train std={stds[feature]}.")

    selected_missing = processed[features].isna().sum(axis=1).astype(int)
    too_missing = living & (selected_missing > int(base.MAX_MISSING_PER_VISIT))
    if too_missing.any():
        bad = processed.loc[too_missing, ["mouse_id", "week"]].copy()
        bad["selected_missing"] = selected_missing.loc[too_missing].to_numpy()
        errors.append(
            "Reduced living rows exceed MAX_MISSING_PER_VISIT: "
            + bad.to_json(orient="records")
        )

    if errors:
        return None, {
            "errors": errors,
            "deterministic": det_stats,
            "mean": means,
            "std": stds,
            "n_obs": n_obs,
        }

    standardized = pd.DataFrame(index=processed.index, columns=features, dtype=float)
    for feature in features:
        standardized[feature] = (
            pd.to_numeric(processed[feature], errors="coerce") - means[feature]
        ) / stds[feature]

    living_idx = processed.index[living]
    fit_idx = processed.index[fit_mask]

    design = standardized.loc[living_idx, features].copy()
    design["week_16"] = processed.loc[living_idx, "week"].eq(16).astype(float).to_numpy()
    design["week_24"] = processed.loc[living_idx, "week"].eq(24).astype(float).to_numpy()

    fit_design = design.loc[fit_idx]
    if fit_design.empty:
        return None, {
            "errors": ["No living train rows for reduced imputer."],
            "deterministic": det_stats,
        }

    # All weighted MODEL_FEATURES are physically nonnegative by Stage-1 QC.
    # The imputer operates in baseline-standardized coordinates, therefore
    # raw x >= 0 becomes z >= -mean_train / std_train. Bounds are fitted from
    # train-only scaling parameters and are enforced inside IterativeImputer,
    # not by post-hoc clipping.
    unknown_bound_features = [
        feature for feature in features if feature not in set(base.MODEL_FEATURES)
    ]
    if unknown_bound_features:
        return None, {
            "errors": [
                "Reduced bounded imputation received features outside MODEL_FEATURES: "
                + "|".join(unknown_bound_features)
            ],
            "deterministic": det_stats,
        }

    feature_lower_bounds = {
        feature: float(-means[feature] / stds[feature])
        for feature in features
    }
    min_value = np.asarray(
        [feature_lower_bounds[feature] for feature in features] + [0.0, 0.0],
        dtype=float,
    )
    max_value = np.asarray(
        [np.inf for _ in features] + [1.0, 1.0],
        dtype=float,
    )
    missing_before_imputation = design[features].isna().copy()

    imputer = base.IterativeImputer(
        estimator=base.BayesianRidge(),
        sample_posterior=False,
        max_iter=20,
        tol=1e-3,
        random_state=base.IMPUTATION_SEED,
        min_value=min_value,
        max_value=max_value,
    )
    imputer.fit(fit_design)
    transformed = imputer.transform(design)
    expected_width = len(features) + 2
    if transformed.shape[1] != expected_width:
        return None, {
            "errors": [
                f"Reduced imputer output width={transformed.shape[1]}, "
                f"expected={expected_width}."
            ],
            "deterministic": det_stats,
        }

    result = processed.copy(deep=True)
    bounded_hits = []
    design_indices = design.index.to_numpy()
    for j, feature in enumerate(features):
        raw_vals = transformed[:, j] * stds[feature] + means[feature]
        result.loc[living_idx, feature] = raw_vals

        # Record only cells that were actually missing before statistical
        # imputation and whose final imputed value lands on the physical lower
        # bound. Observed raw zeros are not counted as bounded imputations.
        missing_mask = missing_before_imputation[feature].to_numpy(dtype=bool)
        hit_mask = missing_mask & np.isclose(
            transformed[:, j],
            min_value[j],
            rtol=0.0,
            atol=1e-10,
        )
        for pos in np.flatnonzero(hit_mask):
            idx = int(design_indices[pos])
            bounded_hits.append({
                "mouse_id": str(result.at[idx, "mouse_id"]),
                "week": int(result.at[idx, "week"]),
                "feature": feature,
                "standardized_lower_bound": float(min_value[j]),
                "imputed_standardized_value": float(transformed[pos, j]),
                "imputed_raw_value": float(raw_vals[pos]),
            })

    # Primary reduced preprocessing must remain physically valid after bounded
    # imputation. Values below -FLOAT_TOL are blockers; tiny floating-point
    # noise around zero is retained for audit rather than post-hoc clipping.
    negative = []
    for feature in features:
        vals = pd.to_numeric(result.loc[living, feature], errors="coerce")
        bad = vals < -base.FLOAT_TOL
        if bad.any():
            for idx in vals.index[bad]:
                negative.append({
                    "mouse_id": str(result.at[idx, "mouse_id"]),
                    "week": int(result.at[idx, "week"]),
                    "feature": feature,
                    "value": float(vals.loc[idx]),
                })

    remaining = int(result.loc[living, features].isna().to_numpy().sum())
    finite = bool(np.isfinite(result.loc[living, features].to_numpy(dtype=float)).all())
    if negative:
        errors.append(
            "Negative reduced post-imputation values: "
            + json.dumps(negative, ensure_ascii=False)
        )
    if remaining:
        errors.append(f"{remaining} reduced living feature cells remain missing.")
    if not finite:
        errors.append("Reduced standardized design contains non-finite values.")

    final_std = result.copy(deep=True)
    for feature in features:
        final_std.loc[living_idx, feature] = (
            pd.to_numeric(result.loc[living_idx, feature], errors="coerce")
            - means[feature]
        ) / stds[feature]
        final_std.loc[~living, feature] = np.nan

    # Status/missing_count are defined from the selected feature space, not the
    # unused 30-feature space.
    final_std["missing_count"] = selected_missing.astype(int)
    final_std.loc[~living, "missing_count"] = len(features)
    final_std.loc[~living, "status"] = "death"
    final_std.loc[living & selected_missing.eq(0), "status"] = "observed"
    final_std.loc[living & selected_missing.gt(0), "status"] = "imputed"

    return final_std, {
        "errors": errors,
        "deterministic": det_stats,
        "mean": means,
        "std": stds,
        "n_obs": n_obs,
        "imputer_n_iter": int(imputer.n_iter_),
        "imputed_selected_cells": int(
            processed.loc[living, features].isna().to_numpy().sum()
        ),
        "max_selected_missing": int(selected_missing.loc[living].max()),
        "bounded_imputation_hit_count": int(len(bounded_hits)),
        "bounded_imputation_hits": bounded_hits,
        "standardized_lower_bounds": feature_lower_bounds,
        "negative_values": negative,
    }


def build_reduced_split(
    base, sparse, long_raw, split, features,
    required_min_train_o=None, required_min_val_o=None,
):
    features = list(features)
    final_std, prep = reduced_preprocess(
        base,
        long_raw,
        features,
        fit_mouse_ids=split["train_ids"],
    )
    if final_std is None or prep.get("errors"):
        return None, {
            "stage": "preprocess",
            "errors": prep.get("errors", ["unknown reduced preprocessing error"]),
        }

    with feature_space(base, features):
        train_states, xbar_train, train_stats = base.build_experimental_states(
            final_std,
            state_mouse_ids=split["train_ids"],
            reference_xbar=None,
        )
        val_states, xbar_val, val_stats = base.build_experimental_states(
            final_std,
            state_mouse_ids=split["val_ids"],
            reference_xbar=xbar_train,
        )

        train_o = {k: int(v["O"]) for k, v in train_states.items()}
        val_o = {k: int(v["O"]) for k, v in val_states.items()}
        min_train_o = min(train_o.values()) if train_o else 0
        min_val_o = min(val_o.values()) if val_o else 0

        errors = list(train_stats.get("errors", [])) + list(val_stats.get("errors", []))
        required_train_o = (
            base.CV_MIN_TRAIN_O
            if required_min_train_o is None
            else int(required_min_train_o)
        )
        required_val_o = (
            base.CV_MIN_VAL_O
            if required_min_val_o is None
            else int(required_min_val_o)
        )
        if min_train_o < required_train_o:
            errors.append(f"Reduced train min O={min_train_o} < {required_train_o}.")
        if min_val_o < required_val_o:
            errors.append(f"Reduced val min O={min_val_o} < {required_val_o}.")
        if xbar_train is None or xbar_val is None:
            errors.append("Missing reduced xbar_PBS0_train.")
        elif not np.allclose(
            np.asarray(xbar_train, dtype=float),
            np.asarray(xbar_val, dtype=float),
            rtol=0,
            atol=0,
        ):
            errors.append("Reduced validation did not reuse train xbar exactly.")

        if errors:
            return None, {"stage": "states", "errors": errors}

        train_ids = set(split["train_ids"])
        train_df = final_std[final_std["mouse_id"].isin(train_ids)].copy()
        solution, meta = sparse.solve_sparse_qp(
            base,
            train_df,
            train_states,
            xbar_train,
            lambda1=LAMBDA1_REDUCED,
            forced_zero_features=[],
        )
        if solution is None or meta.get("errors"):
            return None, {
                "stage": "qp",
                "errors": meta.get("errors", ["unknown reduced QP error"]),
            }

        metrics = base.evaluate_validation_metrics(
            final_std,
            split["val_ids"],
            val_states,
            xbar_train,
            solution["w"],
            rho=sparse.RHO,
        )

    return {
        "metrics": {m: float(metrics[m]) for m in METRICS},
        "weights": {
            f: float(w) for f, w in zip(features, solution["w"])
        },
        "active_count": int(solution["active_count"]),
        "slack_sum": float(solution["slack_sum"]),
        "slack_max": float(solution["slack_max"]),
        "train_min_live_enri": float(solution["min_live_enri"]),
        "validation_min_enri": float(metrics["validation_min_enri"]),
        "imputed_selected_cells": int(prep["imputed_selected_cells"]),
        "max_selected_missing": int(prep["max_selected_missing"]),
        "imputer_n_iter": int(prep["imputer_n_iter"]),
        "solver_used": str(solution.get("solver_used", "")),
    }, None


def metric_summary(fold_df):
    out = {}
    n = len(fold_df)
    for metric in METRICS:
        vals = fold_df[metric].astype(float)
        sd = float(vals.std(ddof=1)) if n >= 2 else 0.0
        out[f"{metric}_mean"] = float(vals.mean())
        out[f"{metric}_sd"] = sd
        out[f"{metric}_se"] = float(sd / math.sqrt(n)) if n else np.nan
        out[f"{metric}_median"] = float(vals.median())
        out[f"{metric}_q10"] = float(vals.quantile(0.10))
        out[f"{metric}_q90"] = float(vals.quantile(0.90))
    return out


def ablation_tuple_for_feature(feature, block_id, feat_abl, block_abl):
    f = feat_abl.get(feature)
    b = block_abl.get(block_id) if block_id else None
    src = f if f is not None else b
    if src is None:
        return tuple([-float("inf")] * 10), "none"

    vals = []
    for metric in ("V_pos", "V_sign", "V_margin", "V_eq", "V_var"):
        vals.append(float(src.get(f"p_{metric}_worse", -float("inf"))))
        vals.append(float(src.get(f"delta_{metric}_median", -float("inf"))))
    return tuple(vals), ("feature" if f is not None else "block")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (
        BASE_SOLVE, STAGE_B_PY, STAGE_C, STAGE_A_BLOCKS,
        STAGE_D, STAGE_E_FEATURE, STAGE_E_BLOCK,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    base = load_module(BASE_SOLVE, "enri_base_model_f")
    sparse = load_module(STAGE_B_PY, "enri_stage_b_f")
    original_feature_order = list(base.MODEL_FEATURES)
    canonical = {f: i + 1 for i, f in enumerate(original_feature_order)}

    stability = pd.read_csv(STAGE_C)
    blocks = pd.read_csv(STAGE_A_BLOCKS)
    block_stability = pd.read_csv(STAGE_D)
    feature_ablation = pd.read_csv(STAGE_E_FEATURE)
    block_ablation = pd.read_csv(STAGE_E_BLOCK)

    if blocks["is_correlation_block"].dtype != bool:
        blocks["is_correlation_block"] = (
            blocks["is_correlation_block"].astype(str).str.lower().eq("true")
        )

    feature_block = {
        str(row["feature"]): (
            str(row["block_id"]) if bool(row["is_correlation_block"]) else None
        )
        for _, row in blocks.iterrows()
    }

    stab = stability.set_index("feature").to_dict(orient="index")
    feat_abl = feature_ablation.set_index("feature").to_dict(orient="index")
    block_abl = block_ablation.set_index("block_id").to_dict(orient="index")

    rank_records = []
    for feature in original_feature_order:
        rec = stab[feature]
        block_id = feature_block[feature]
        ab_tuple, ab_source = ablation_tuple_for_feature(
            feature, block_id, feat_abl, block_abl
        )
        rank_records.append({
            "feature": feature,
            "feature_order": canonical[feature],
            "block_id": "" if block_id is None else block_id,
            "pi_selection": float(rec["pi_selection"]),
            "sign_consistency": (
                float(rec["sign_consistency"])
                if pd.notna(rec["sign_consistency"])
                else -1.0
            ),
            "category": str(rec["category"]),
            "abs_gamma_median_selected": (
                float(rec["abs_gamma_median_selected"])
                if pd.notna(rec["abs_gamma_median_selected"])
                else 0.0
            ),
            "ablation_source": ab_source,
            "ablation_tuple": ab_tuple,
        })

    def rank_key(rec):
        # Descending all scientific criteria; ascending canonical order.
        return (
            -rec["pi_selection"],
            -rec["sign_consistency"],
            *[-x for x in rec["ablation_tuple"]],
            -rec["abs_gamma_median_selected"],
            rec["feature_order"],
        )

    rank_by_feature = {r["feature"]: r for r in rank_records}

    # F1: rank all members within each block.
    block_member_order = {}
    block_primary = {}
    for block_id, sub in blocks[blocks["is_correlation_block"]].groupby("block_id", sort=False):
        members = sub.sort_values("feature_order")["feature"].astype(str).tolist()
        ordered = sorted(members, key=lambda f: rank_key(rank_by_feature[f]))
        block_member_order[str(block_id)] = ordered
        block_primary[str(block_id)] = ordered[0]

    # Per the frozen Stage-F plan, every feature outside a correlation block
    # remains eligible for the global ranking. Stability categories affect its
    # rank but are not a hard pre-filter. Every correlation block first enters
    # through one primary representative.
    singleton_features = [
        feature
        for feature in original_feature_order
        if feature_block[feature] is None
    ]

    initial_pool = list(singleton_features) + [
        block_primary[bid] for bid in sorted(block_primary)
    ]
    initial_pool = list(dict.fromkeys(initial_pool))

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    accepted_splits, rejected_splits = base.prepare_cv_splits(long_raw, source)
    if len(accepted_splits) != 22:
        raise RuntimeError(f"Expected 22 accepted development splits, got {len(accepted_splits)}.")

    # Cache reduced split fits because the same candidate set can appear in
    # compression and S_k evaluation.
    cache = {}
    failures = []

    def evaluate_subset(features, label):
        features = tuple(sorted(set(features), key=lambda x: canonical[x]))
        cache_key = features
        if cache_key in cache:
            return cache[cache_key]

        rows = []
        for split in accepted_splits:
            fit, err = build_reduced_split(
                base, sparse, long_raw, split, features
            )
            if err:
                failures.append({
                    "label": label,
                    "features": "|".join(features),
                    "seed": int(split["seed"]),
                    "fold": int(split["fold"]),
                    "stage": err["stage"],
                    "errors": " | ".join(map(str, err["errors"])),
                })
                continue

            row = {
                "seed": int(split["seed"]),
                "fold": int(split["fold"]),
                "feature_count": len(features),
                "features": "|".join(features),
                **fit["metrics"],
                "active_count": fit["active_count"],
                "slack_sum": fit["slack_sum"],
                "slack_max": fit["slack_max"],
                "train_min_live_enri": fit["train_min_live_enri"],
                "validation_min_enri": fit["validation_min_enri"],
                "imputed_selected_cells": fit["imputed_selected_cells"],
                "max_selected_missing": fit["max_selected_missing"],
                "imputer_n_iter": fit["imputer_n_iter"],
                "solver_used": fit["solver_used"],
            }
            rows.append(row)

        if len(rows) != len(accepted_splits):
            if failures:
                pd.DataFrame(failures).to_csv(
                    OUT_DIR / "stage_f_failures.csv", index=False
                )
            raise RuntimeError(
                f"Reduced subset {label} has {len(rows)}/{len(accepted_splits)} valid fits."
            )

        df = pd.DataFrame(rows)
        result = (df, metric_summary(df))
        cache[cache_key] = result
        return result

    # F3: block compression in a common context:
    # all singleton anchors + one primary representative of every other block.
    compression_rows = []
    retained_by_block = {}

    all_block_ids = sorted(block_primary)
    for block_id in all_block_ids:
        ordered_members = block_member_order[block_id]
        other_primaries = [
            block_primary[b] for b in all_block_ids if b != block_id
        ]
        anchors = list(dict.fromkeys(singleton_features + other_primaries))

        full_features = list(dict.fromkeys(anchors + ordered_members))
        full_folds, full_summary = evaluate_subset(
            full_features, f"{block_id}_full"
        )

        selected_m = len(ordered_members)
        selected_features = ordered_members.copy()

        for m in range(1, len(ordered_members) + 1):
            candidate_members = ordered_members[:m]
            candidate_features = list(dict.fromkeys(anchors + candidate_members))
            cand_folds, cand_summary = evaluate_subset(
                candidate_features, f"{block_id}_m{m}"
            )

            metric_pass = {}
            all_pass = True
            for metric in PRIORITY_METRICS:
                threshold = (
                    full_summary[f"{metric}_mean"]
                    + full_summary[f"{metric}_se"]
                )
                passed = cand_summary[f"{metric}_mean"] <= threshold + 1e-15
                metric_pass[metric] = bool(passed)
                all_pass = all_pass and passed

            compression_rows.append({
                "block_id": block_id,
                "m": m,
                "candidate_members": "|".join(candidate_members),
                "candidate_feature_count_total": len(candidate_features),
                "full_block_members": "|".join(ordered_members),
                "full_feature_count_total": len(full_features),
                "all_metrics_within_one_se": bool(all_pass),
                **{
                    f"{metric}_candidate_mean": cand_summary[f"{metric}_mean"]
                    for metric in METRICS
                },
                **{
                    f"{metric}_full_mean": full_summary[f"{metric}_mean"]
                    for metric in METRICS
                },
                **{
                    f"{metric}_full_se": full_summary[f"{metric}_se"]
                    for metric in METRICS
                },
                **{
                    f"{metric}_pass": metric_pass[metric]
                    for metric in METRICS
                },
            })

            if all_pass:
                selected_m = m
                selected_features = candidate_members
                break

        retained_by_block[block_id] = selected_features

    compression_df = pd.DataFrame(compression_rows)
    compression_df.to_csv(OUT_DIR / "block_compression.csv", index=False)

    # Candidate pool after compression: all singleton features plus only the
    # number of block representatives justified above.
    final_pool = list(singleton_features)
    for block_id in all_block_ids:
        final_pool.extend(retained_by_block[block_id])
    final_pool = list(dict.fromkeys(final_pool))
    final_pool = sorted(final_pool, key=lambda f: rank_key(rank_by_feature[f]))

    if len(final_pool) < MIN_K:
        raise RuntimeError(f"Only {len(final_pool)} candidates after block compression.")

    ranking_rows = []
    for rank, feature in enumerate(final_pool, start=1):
        r = rank_by_feature[feature]
        block_id = feature_block[feature]
        ranking_rows.append({
            "rank": rank,
            "feature": feature,
            "feature_order": r["feature_order"],
            "block_id": "" if block_id is None else block_id,
            "is_block_primary": (
                bool(block_id) and block_primary.get(block_id) == feature
            ),
            "pi_selection": r["pi_selection"],
            "sign_consistency": r["sign_consistency"],
            "category": r["category"],
            "ablation_source": r["ablation_source"],
            "abs_gamma_median_selected": r["abs_gamma_median_selected"],
            "retained_members_for_block": (
                ""
                if not block_id
                else "|".join(retained_by_block[block_id])
            ),
        })
    ranking_df = pd.DataFrame(ranking_rows)
    ranking_df.to_csv(OUT_DIR / "block_aware_ranking.csv", index=False)

    # F4: build S_3...S_15 and refit each subset from scratch with reduced
    # preprocessing. Stage G will apply the final one-SE k selection.
    max_k = min(MAX_K, len(final_pool))
    subset_rows = []
    subset_fold_frames = []
    candidate_rows = []

    for k in range(MIN_K, max_k + 1):
        subset = final_pool[:k]
        candidate_rows.append({
            "k": k,
            "features": "|".join(subset),
        })
        folds, summary = evaluate_subset(subset, f"S{k}")
        fold_copy = folds.copy()
        fold_copy.insert(0, "k", k)
        subset_fold_frames.append(fold_copy)

        row = {
            "k": k,
            "features": "|".join(subset),
            "folds": int(len(folds)),
            "mean_active_count": float(folds["active_count"].mean()),
            "median_active_count": float(folds["active_count"].median()),
            "mean_slack_sum": float(folds["slack_sum"].mean()),
            "median_slack_sum": float(folds["slack_sum"].median()),
            "max_selected_missing": int(folds["max_selected_missing"].max()),
            "mean_imputed_selected_cells": float(folds["imputed_selected_cells"].mean()),
        }
        row.update(summary)
        subset_rows.append(row)

    candidate_df = pd.DataFrame(candidate_rows)
    subset_df = pd.DataFrame(subset_rows)
    subset_folds_df = pd.concat(subset_fold_frames, ignore_index=True)

    candidate_df.to_csv(OUT_DIR / "candidate_sets.csv", index=False)
    subset_df.to_csv(OUT_DIR / "subset_cv.csv", index=False)
    subset_folds_df.to_csv(OUT_DIR / "subset_cv_folds.csv", index=False)

    # Save a compact within-block ranking audit for all original block members.
    member_rows = []
    for block_id in all_block_ids:
        for pos, feature in enumerate(block_member_order[block_id], start=1):
            r = rank_by_feature[feature]
            member_rows.append({
                "block_id": block_id,
                "within_block_rank": pos,
                "feature": feature,
                "pi_selection": r["pi_selection"],
                "sign_consistency": r["sign_consistency"],
                "category": r["category"],
                "ablation_source": r["ablation_source"],
                "abs_gamma_median_selected": r["abs_gamma_median_selected"],
                "retained_after_compression": feature in retained_by_block[block_id],
            })
    pd.DataFrame(member_rows).to_csv(
        OUT_DIR / "within_block_ranking.csv", index=False
    )

    summary = {
        "stage": "F",
        "status": "READY",
        "purpose": "development_block_aware_ranking_compression_and_subset_path",
        "warning": (
            "These development rankings/subsets are not final. Stage G chooses k, "
            "and the complete procedure must be rerun inside each outer-train in "
            "nested validation."
        ),
        "ranking_rule": (
            "pi_selection -> sign_consistency -> paired ablation tuple "
            "(V_pos,V_sign,V_margin,V_eq,V_var; p_worse then median delta) -> "
            "median |gamma| -> canonical feature order"
        ),
        "pool_rule": (
            "All singleton features plus one primary representative from every "
            "correlation block; stability affects ranking rather than eligibility; "
            "extra block members "
            "only when required by within-block one-SE compression."
        ),
        "reduced_model": {
            "lambda1": LAMBDA1_REDUCED,
            "beta": float(sparse.BETA),
            "lambda2": float(sparse.LAMBDA2),
            "C": float(sparse.C_SLACK),
            "rho": float(sparse.RHO),
            "imputation_predictors": "selected weighted features + week_16 + week_24",
            "group_used_as_imputer_predictor": False,
            "unselected_model_features_used_as_statistical_predictors": False,
        },
        "development_splits": {
            "accepted": int(len(accepted_splits)),
            "rejected": int(len(rejected_splits)),
        },
        "initial_pool_count": int(len(initial_pool)),
        "singleton_feature_count": int(len(singleton_features)),
        "block_primary": block_primary,
        "within_block_order": block_member_order,
        "retained_by_block": retained_by_block,
        "final_pool_count": int(len(final_pool)),
        "final_ranking": final_pool,
        "subset_range": {
            "min_k": MIN_K,
            "max_k": max_k,
            "count": int(max_k - MIN_K + 1),
        },
        "cached_unique_reduced_subsets": int(len(cache)),
        "solver_or_preprocessing_failures": 0,
        "outputs": {
            "within_block_ranking": "stage_f/within_block_ranking.csv",
            "block_compression": "stage_f/block_compression.csv",
            "block_aware_ranking": "stage_f/block_aware_ranking.csv",
            "candidate_sets": "stage_f/candidate_sets.csv",
            "subset_cv": "stage_f/subset_cv.csv",
            "subset_cv_folds": "stage_f/subset_cv_folds.csv",
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_f_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STAGE_F_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
