#!/usr/bin/env python3
"""
Stage D: block stability for eNRI feature selection.

Combines:
- Stage A full-data diagnostic correlation blocks;
- Stage C 200-resample stability-selection active/inactive decisions.

For each non-singleton correlation block, quantify:
- P(any member selected);
- P(no member selected);
- P(exactly one selected);
- P(multiple selected);
- mean/min/max number of selected members;
- per-member selection frequency;
- pairwise joint-selection and XOR/substitution frequencies.

This remains a development diagnostic. In final nested validation, correlation
blocks and block stability must be recomputed inside each outer-train.
"""

from __future__ import annotations

import json
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
STAGE_A_DIR = ROOT / "stage_a"
STAGE_C_DIR = ROOT / "stage_c"
OUT_DIR = ROOT / "stage_d"

BLOCKS_FILE = STAGE_A_DIR / "correlation_blocks.csv"
COEFFICIENTS_FILE = STAGE_C_DIR / "stability_coefficients.csv"
STABILITY_FILE = STAGE_C_DIR / "stability_selection.csv"
STAGE_C_SUMMARY = STAGE_C_DIR / "stage_c_summary.json"

EXPECTED_VALID_RESAMPLES = 200


def as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if mapped.isna().any():
        bad = sorted(series[mapped.isna()].astype(str).unique().tolist())
        raise ValueError(f"Cannot parse boolean values: {bad}")
    return mapped.astype(bool)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for path in (BLOCKS_FILE, COEFFICIENTS_FILE, STABILITY_FILE, STAGE_C_SUMMARY):
        if not path.exists():
            raise FileNotFoundError(path)

    stage_c_summary = json.loads(STAGE_C_SUMMARY.read_text(encoding="utf-8"))
    if stage_c_summary.get("status") != "READY":
        raise RuntimeError("Stage C is not READY.")
    valid_resamples = int(stage_c_summary["resampling"]["valid_resamples"])
    if valid_resamples != EXPECTED_VALID_RESAMPLES:
        raise RuntimeError(
            f"Expected {EXPECTED_VALID_RESAMPLES} Stage-C resamples, got {valid_resamples}."
        )

    blocks = pd.read_csv(BLOCKS_FILE)
    coeff = pd.read_csv(COEFFICIENTS_FILE)
    stability = pd.read_csv(STABILITY_FILE)

    required_block_cols = {
        "block_id", "is_correlation_block", "block_size",
        "feature", "feature_order", "members"
    }
    required_coeff_cols = {
        "resample_index", "seed", "feature", "weight", "active", "gamma_raw_scale"
    }
    if not required_block_cols.issubset(blocks.columns):
        raise RuntimeError(
            "correlation_blocks.csv missing columns: "
            + str(sorted(required_block_cols - set(blocks.columns)))
        )
    if not required_coeff_cols.issubset(coeff.columns):
        raise RuntimeError(
            "stability_coefficients.csv missing columns: "
            + str(sorted(required_coeff_cols - set(coeff.columns)))
        )

    blocks["is_correlation_block"] = as_bool(blocks["is_correlation_block"])
    coeff["active"] = as_bool(coeff["active"])

    feature_set_blocks = set(blocks["feature"].astype(str))
    feature_set_coeff = set(coeff["feature"].astype(str))
    feature_set_stability = set(stability["feature"].astype(str))
    if feature_set_blocks != feature_set_coeff or feature_set_blocks != feature_set_stability:
        raise RuntimeError("Feature sets differ across Stage A/C inputs.")

    if len(feature_set_blocks) != 30:
        raise RuntimeError(f"Expected 30 features, got {len(feature_set_blocks)}.")

    resample_ids = sorted(coeff["resample_index"].astype(int).unique().tolist())
    if len(resample_ids) != valid_resamples:
        raise RuntimeError(
            f"Expected {valid_resamples} unique resamples, got {len(resample_ids)}."
        )

    expected_rows = valid_resamples * len(feature_set_blocks)
    if len(coeff) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} coefficient rows, got {len(coeff)}."
        )

    dup = coeff.duplicated(["resample_index", "feature"])
    if dup.any():
        raise RuntimeError("Duplicate resample_index/feature rows in Stage C coefficients.")

    active_wide = (
        coeff.pivot(index="resample_index", columns="feature", values="active")
        .sort_index()
    )
    active_wide = active_wide.astype(bool)

    pi_map = stability.set_index("feature")["pi_selection"].astype(float).to_dict()
    sign_map = stability.set_index("feature")["sign_consistency"].astype(float).to_dict()
    category_map = stability.set_index("feature")["category"].astype(str).to_dict()

    block_rows = []
    member_rows = []
    pair_rows = []

    block_defs = blocks[blocks["is_correlation_block"]].copy()
    block_ids = (
        block_defs[["block_id", "feature_order"]]
        .groupby("block_id", as_index=False)["feature_order"].min()
        .sort_values("feature_order")["block_id"]
        .tolist()
    )

    for block_id in block_ids:
        sub = block_defs[block_defs["block_id"].eq(block_id)].sort_values("feature_order")
        members = sub["feature"].astype(str).tolist()
        declared_size = int(sub["block_size"].iloc[0])
        if declared_size != len(members):
            raise RuntimeError(
                f"{block_id}: declared size {declared_size} != {len(members)} members."
            )

        A = active_wide[members].to_numpy(dtype=bool)
        selected_count = A.sum(axis=1)
        any_selected = selected_count >= 1
        none_selected = selected_count == 0
        exactly_one = selected_count == 1
        multiple = selected_count >= 2
        all_selected = selected_count == len(members)

        member_pis = {m: float(pi_map[m]) for m in members}
        primary = max(
            members,
            key=lambda m: (
                member_pis[m],
                float(sign_map[m]) if math.isfinite(float(sign_map[m])) else -1.0,
                -int(sub.loc[sub["feature"].eq(m), "feature_order"].iloc[0]),
            ),
        )

        block_rows.append({
            "block_id": block_id,
            "block_size": len(members),
            "members": "|".join(members),
            "valid_resamples": valid_resamples,
            "pi_block_any_selected": float(np.mean(any_selected)),
            "p_none_selected": float(np.mean(none_selected)),
            "p_exactly_one_selected": float(np.mean(exactly_one)),
            "p_multiple_selected": float(np.mean(multiple)),
            "p_all_selected": float(np.mean(all_selected)),
            "selected_members_mean": float(np.mean(selected_count)),
            "selected_members_median": float(np.median(selected_count)),
            "selected_members_min": int(np.min(selected_count)),
            "selected_members_max": int(np.max(selected_count)),
            "primary_member_by_pi": primary,
            "primary_member_pi": float(member_pis[primary]),
            "max_member_pi": float(max(member_pis.values())),
            "min_member_pi": float(min(member_pis.values())),
            "block_gain_over_best_member": float(
                np.mean(any_selected) - max(member_pis.values())
            ),
        })

        for m in members:
            others = [x for x in members if x != m]
            member_active = active_wide[m].to_numpy(dtype=bool)
            any_other = (
                active_wide[others].any(axis=1).to_numpy(dtype=bool)
                if others else np.zeros(valid_resamples, dtype=bool)
            )
            member_rows.append({
                "block_id": block_id,
                "feature": m,
                "feature_order": int(
                    sub.loc[sub["feature"].eq(m), "feature_order"].iloc[0]
                ),
                "pi_selection": float(pi_map[m]),
                "sign_consistency": float(sign_map[m]),
                "stage_c_category": category_map[m],
                "p_selected_and_any_other": float(np.mean(member_active & any_other)),
                "p_selected_alone_within_block": float(np.mean(member_active & ~any_other)),
                "p_not_selected_but_other_selected": float(np.mean(~member_active & any_other)),
            })

        for a, b in combinations(members, 2):
            av = active_wide[a].to_numpy(dtype=bool)
            bv = active_wide[b].to_numpy(dtype=bool)
            pair_rows.append({
                "block_id": block_id,
                "feature_a": a,
                "feature_b": b,
                "p_a_selected": float(np.mean(av)),
                "p_b_selected": float(np.mean(bv)),
                "p_both_selected": float(np.mean(av & bv)),
                "p_neither_selected": float(np.mean(~av & ~bv)),
                "p_exactly_one_selected": float(np.mean(av ^ bv)),
                "p_a_only": float(np.mean(av & ~bv)),
                "p_b_only": float(np.mean(~av & bv)),
                "p_any_selected": float(np.mean(av | bv)),
            })

    block_df = pd.DataFrame(block_rows)
    member_df = pd.DataFrame(member_rows).sort_values(
        ["block_id", "pi_selection", "feature_order"],
        ascending=[True, False, True],
    ).reset_index(drop=True)
    pair_df = pd.DataFrame(pair_rows).sort_values(
        ["block_id", "p_exactly_one_selected", "p_any_selected"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    if len(block_df) != 6:
        raise RuntimeError(f"Expected 6 correlation blocks, got {len(block_df)}.")

    block_df.to_csv(OUT_DIR / "block_stability.csv", index=False)
    member_df.to_csv(OUT_DIR / "block_member_stability.csv", index=False)
    pair_df.to_csv(OUT_DIR / "block_pair_selection.csv", index=False)

    ranked = block_df.sort_values(
        ["pi_block_any_selected", "block_gain_over_best_member", "block_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    ranked["block_stability_rank"] = np.arange(1, len(ranked) + 1)
    ranked.to_csv(OUT_DIR / "block_stability_ranked.csv", index=False)

    summary_blocks = []
    for _, row in ranked.iterrows():
        summary_blocks.append({
            "block_id": str(row["block_id"]),
            "members": str(row["members"]).split("|"),
            "pi_block_any_selected": float(row["pi_block_any_selected"]),
            "p_exactly_one_selected": float(row["p_exactly_one_selected"]),
            "p_multiple_selected": float(row["p_multiple_selected"]),
            "primary_member_by_pi": str(row["primary_member_by_pi"]),
            "primary_member_pi": float(row["primary_member_pi"]),
            "block_gain_over_best_member": float(row["block_gain_over_best_member"]),
        })

    strongest_substitution = (
        pair_df.sort_values(
            ["p_exactly_one_selected", "p_any_selected"],
            ascending=[False, False],
        )
        .head(10)
    )
    substitution_pairs = [
        {
            "block_id": str(row["block_id"]),
            "feature_a": str(row["feature_a"]),
            "feature_b": str(row["feature_b"]),
            "p_exactly_one_selected": float(row["p_exactly_one_selected"]),
            "p_both_selected": float(row["p_both_selected"]),
            "p_any_selected": float(row["p_any_selected"]),
        }
        for _, row in strongest_substitution.iterrows()
    ]

    summary = {
        "stage": "D",
        "status": "READY",
        "purpose": "development_block_stability",
        "warning": (
            "Blocks come from Stage-A full-data diagnostic correlations. "
            "In final nested validation, block construction and block stability "
            "must be recomputed inside each outer-train."
        ),
        "inputs": {
            "correlation_blocks": "stage_a/correlation_blocks.csv",
            "stability_coefficients": "stage_c/stability_coefficients.csv",
            "stability_summary": "stage_c/stability_selection.csv",
            "valid_resamples": valid_resamples,
        },
        "results": {
            "correlation_blocks": int(len(block_df)),
            "block_member_rows": int(len(member_df)),
            "block_pair_rows": int(len(pair_df)),
            "blocks": summary_blocks,
            "top_substitution_pairs": substitution_pairs,
        },
        "outputs": {
            "block_stability": "stage_d/block_stability.csv",
            "block_stability_ranked": "stage_d/block_stability_ranked.csv",
            "block_member_stability": "stage_d/block_member_stability.csv",
            "block_pair_selection": "stage_d/block_pair_selection.csv",
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_d_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STAGE_D_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
