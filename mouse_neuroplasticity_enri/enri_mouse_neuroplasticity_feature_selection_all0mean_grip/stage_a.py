#!/usr/bin/env python3
"""
Stage A for eNRI feature selection.

This is a full-data diagnostic only:
- reuse the validated preprocessing from the original 0.1/0.1/0.1 model;
- compute pooled and group-centered Spearman correlations for 30 MODEL_FEATURES
  separately at weeks 0, 16 and 24;
- build strong-correlation edges using the frozen plan rule;
- form correlation blocks as connected components.

These full-data blocks are exploratory/diagnostic. During nested validation the
same logic must be re-fit on the corresponding training subset only.
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
BASE_SOLVE = BASE_DIR / "solve_all0mean_grip.py"
OUT_DIR = ROOT / "stage_a"

WEEKS = (0, 16, 24)
STRONG_ABS_RHO = 0.8


def load_base_module():
    if not BASE_SOLVE.exists():
        raise FileNotFoundError(f"Base model not found: {BASE_SOLVE}")
    spec = importlib.util.spec_from_file_location("enri_base_model", BASE_SOLVE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import base model from {BASE_SOLVE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def spearman_matrices(df: pd.DataFrame, features: list[str]):
    pooled = {}
    centered = {}

    for week in WEEKS:
        sub = df[df["week"].eq(week)].copy()
        if sub.empty:
            raise RuntimeError(f"No living rows for week {week}")

        pooled[week] = sub[features].astype(float).corr(method="spearman")

        centered_sub = sub[["group", *features]].copy()
        for feature in features:
            group_median = centered_sub.groupby("group")[feature].transform("median")
            centered_sub[feature] = centered_sub[feature].astype(float) - group_median.astype(float)
        centered[week] = centered_sub[features].corr(method="spearman")

    return pooled, centered


def sign_of(value: float):
    if not math.isfinite(value) or value == 0:
        return 0
    return 1 if value > 0 else -1


def build_pair_table(df: pd.DataFrame, features: list[str], pooled, centered):
    rows = []

    for ia, feature_a in enumerate(features):
        for ib in range(ia + 1, len(features)):
            feature_b = features[ib]
            row = {
                "feature_a": feature_a,
                "feature_b": feature_b,
                "feature_a_order": ia + 1,
                "feature_b_order": ib + 1,
            }

            strong_weeks = []
            strong_signs = []
            centered_opposite_weeks = []

            for week in WEEKS:
                sub = df[df["week"].eq(week)]
                n = int(
                    sub[[feature_a, feature_b]]
                    .dropna()
                    .shape[0]
                )
                rp = float(pooled[week].loc[feature_a, feature_b])
                rc = float(centered[week].loc[feature_a, feature_b])

                row[f"n_{week}"] = n
                row[f"rho_pooled_{week}"] = rp
                row[f"rho_centered_{week}"] = rc

                if math.isfinite(rp) and abs(rp) >= STRONG_ABS_RHO:
                    strong_weeks.append(week)
                    strong_signs.append(sign_of(rp))

            pooled_strong_enough = len(strong_weeks) >= 2
            pooled_sign_consistent = (
                pooled_strong_enough
                and len(set(strong_signs)) == 1
                and 0 not in set(strong_signs)
            )

            primary_sign = strong_signs[0] if pooled_sign_consistent else 0
            if pooled_sign_consistent:
                for week in strong_weeks:
                    rc = row[f"rho_centered_{week}"]
                    if math.isfinite(rc) and sign_of(rc) == -primary_sign:
                        centered_opposite_weeks.append(week)

            # Per frozen plan: a pooled-stable pair is rejected as potentially
            # group-driven only when group-centering reverses its sign in at
            # least two of the pooled-strong weeks.
            potentially_group_driven = (
                pooled_sign_consistent and len(centered_opposite_weeks) >= 2
            )
            edge = pooled_sign_consistent and not potentially_group_driven

            if edge:
                reason = "accepted_strong_stable_pair"
            elif potentially_group_driven:
                reason = "rejected_group_centered_sign_reversal"
            elif not pooled_strong_enough:
                reason = "fewer_than_2_strong_weeks"
            else:
                reason = "pooled_strong_sign_inconsistent"

            row.update({
                "strong_week_count": len(strong_weeks),
                "strong_weeks": ",".join(map(str, strong_weeks)),
                "pooled_strong_sign": primary_sign,
                "centered_opposite_week_count": len(centered_opposite_weeks),
                "centered_opposite_weeks": ",".join(map(str, centered_opposite_weeks)),
                "potentially_group_driven": bool(potentially_group_driven),
                "strong_edge": bool(edge),
                "edge_reason": reason,
            })
            rows.append(row)

    return pd.DataFrame(rows)


def connected_components(features: list[str], pair_table: pd.DataFrame):
    order = {feature: i for i, feature in enumerate(features)}
    adjacency = {feature: set() for feature in features}

    edges = pair_table[pair_table["strong_edge"]]
    for _, row in edges.iterrows():
        a = row["feature_a"]
        b = row["feature_b"]
        adjacency[a].add(b)
        adjacency[b].add(a)

    seen = set()
    components = []
    for feature in features:
        if feature in seen:
            continue
        stack = [feature]
        comp = []
        seen.add(feature)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nxt in sorted(adjacency[cur], key=lambda x: order[x], reverse=True):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        comp.sort(key=lambda x: order[x])
        components.append(comp)

    components.sort(key=lambda c: min(order[x] for x in c))

    rows = []
    block_idx = 0
    singleton_idx = 0
    for comp in components:
        if len(comp) >= 2:
            block_idx += 1
            block_id = f"B{block_idx:02d}"
            is_block = True
        else:
            singleton_idx += 1
            block_id = f"S{singleton_idx:02d}"
            is_block = False

        members = "|".join(comp)
        comp_set = set(comp)
        edge_count = int(
            pair_table[
                pair_table["strong_edge"]
                & pair_table["feature_a"].isin(comp_set)
                & pair_table["feature_b"].isin(comp_set)
            ].shape[0]
        )

        for feature in comp:
            rows.append({
                "block_id": block_id,
                "is_correlation_block": is_block,
                "block_size": len(comp),
                "edge_count": edge_count,
                "feature": feature,
                "feature_order": order[feature] + 1,
                "members": members,
            })

    blocks = pd.DataFrame(rows).sort_values("feature_order").reset_index(drop=True)
    return blocks, components


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = load_base_module()
    features = list(base.MODEL_FEATURES)
    if len(features) != len(base.MODEL_FEATURES):
        raise RuntimeError(
            f"MODEL_FEATURES dimension mismatch: got {len(features)}, "
            f"expected {len(base.MODEL_FEATURES)}"
        )

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    final_std, prep_stats = base.fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=base.IMPUTATION_SEED,
        sample_posterior=False,
    )
    prep_errors = list(prep_stats.get("errors", []))
    if prep_errors:
        raise RuntimeError(
            "Base preprocessing failed: " + " | ".join(map(str, prep_errors))
        )

    living = final_std[
        final_std["status"].isin(["observed", "imputed"])
    ].copy()

    expected_living = 140
    if len(living) != expected_living:
        raise RuntimeError(
            f"Expected {expected_living} living states after preprocessing, got {len(living)}"
        )

    if living[features].isna().any().any():
        raise RuntimeError("Living MODEL_FEATURES contain missing values after preprocessing")

    pooled, centered = spearman_matrices(living, features)
    pair_table = build_pair_table(living, features, pooled, centered)
    blocks, components = connected_components(features, pair_table)

    expected_pairs = len(features) * (len(features) - 1) // 2
    if len(pair_table) != expected_pairs:
        raise RuntimeError(
            f"Expected {expected_pairs} feature pairs, got {len(pair_table)}"
        )
    if len(blocks) != len(features):
        raise RuntimeError(
            f"Expected one block-assignment row per feature ({len(features)}), got {len(blocks)}"
        )

    pair_path = OUT_DIR / "correlation_pairs.csv"
    block_path = OUT_DIR / "correlation_blocks.csv"
    summary_path = OUT_DIR / "stage_a_summary.json"

    pair_table.to_csv(pair_path, index=False)
    blocks.to_csv(block_path, index=False)

    multi_components = [c for c in components if len(c) >= 2]
    singleton_components = [c for c in components if len(c) == 1]

    week_counts = {
        str(week): int(living["week"].eq(week).sum())
        for week in WEEKS
    }
    week_group_counts = {
        str(week): {
            str(group): int(count)
            for group, count in living[living["week"].eq(week)]["group"].value_counts().sort_index().items()
        }
        for week in WEEKS
    }

    summary = {
        "stage": "A",
        "status": "READY",
        "purpose": "full_data_correlation_diagnostic_only",
        "warning": (
            "These full-data correlation blocks are exploratory. "
            "Nested feature selection must recompute the same logic on train only."
        ),
        "base_model": {
            "beta": 0.1,
            "lambda2": 0.1,
            "C": 0.1,
            "rho": 0.1,
            "model_features": len(features),
        },
        "preprocessing": {
            "imputation_method": "IterativeImputer(BayesianRidge)",
            "sample_posterior": False,
            "seed": int(base.IMPUTATION_SEED),
            "imputed_base_cells": int(prep_stats["imputed_base_cells"]),
            "living_states": int(len(living)),
            "week_counts": week_counts,
            "week_group_counts": week_group_counts,
        },
        "correlation_rule": {
            "method": "Spearman",
            "weeks": list(WEEKS),
            "strong_abs_rho": STRONG_ABS_RHO,
            "pooled_requirement": "abs(rho)>=0.8 in at least 2/3 weeks with consistent sign",
            "group_centered": "subtract group x week median before Spearman",
            "group_driven_rejection": (
                "reject a pooled-stable pair if centered sign reverses in at least "
                "2 pooled-strong weeks"
            ),
            "block_definition": "connected component of accepted strong-edge graph",
        },
        "results": {
            "feature_pairs": int(len(pair_table)),
            "accepted_strong_edges": int(pair_table["strong_edge"].sum()),
            "potentially_group_driven_pairs": int(pair_table["potentially_group_driven"].sum()),
            "correlation_blocks_ge2": int(len(multi_components)),
            "singleton_features": int(len(singleton_components)),
            "block_sizes": [int(len(c)) for c in multi_components],
        },
        "outputs": {
            "correlation_pairs": str(pair_path.relative_to(ROOT)),
            "correlation_blocks": str(block_path.relative_to(ROOT)),
        },
        "validation_errors": [],
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    print("STAGE_A_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
