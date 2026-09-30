#!/usr/bin/env python3
"""
Stage K: final-subset decision from completed production nested validation.

This stage deliberately does not invent a new post-hoc frequency threshold.
It applies the pre-specified critical stopping rule: if no small fixed subset
is reproducible across changes in mouse composition, report that result rather
than force a final reduced eNRI.

Outputs distinguish:
- descriptive consensus ranking of individual features/blocks;
- the development S4 result;
- whether a fixed final weighted subset can be justified.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_SOLVE = ROOT.parent / "enri_mouse_neuroplasticity" / "solve_all0mean.py"
H_DIR = ROOT / "stage_h_production"
G_SELECTED = ROOT / "stage_g" / "selected_subset.csv"
OUT_DIR = ROOT / "stage_k"

FEATURE_FREQ = H_DIR / "nested_feature_frequency.csv"
SUBSET_FREQ = H_DIR / "nested_subset_frequency.csv"
K_DIST = H_DIR / "nested_k_distribution.csv"
OUTER_RESULTS = H_DIR / "nested_outer_results.csv"
REF_BLOCK_FREQ = H_DIR / "nested_reference_block_frequency.csv"
H_SUMMARY = H_DIR / "stage_h_summary.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_subset(text: str):
    return frozenset(
        x for x in str(text).split("|")
        if x and x.lower() != "nan"
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (
        FEATURE_FREQ, SUBSET_FREQ, K_DIST, OUTER_RESULTS,
        REF_BLOCK_FREQ, H_SUMMARY, G_SELECTED,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    base = load_module(BASE_SOLVE, "enri_base_stage_k")
    canonical = {f: i + 1 for i, f in enumerate(base.MODEL_FEATURES)}

    feature = pd.read_csv(FEATURE_FREQ)
    subsets = pd.read_csv(SUBSET_FREQ)
    kdist = pd.read_csv(K_DIST)
    outer = pd.read_csv(OUTER_RESULTS)
    blocks = pd.read_csv(REF_BLOCK_FREQ)
    h_summary = json.loads(H_SUMMARY.read_text(encoding="utf-8"))
    dev = pd.read_csv(G_SELECTED).sort_values("selected_position")

    if h_summary.get("status") != "READY":
        raise RuntimeError(
            f"Stage H must be production READY, got {h_summary.get('status')}"
        )
    if int(h_summary.get("completed_outer_splits", 0)) != 30:
        raise RuntimeError("Stage K requires exactly 30 completed outer splits.")
    if len(outer) != 30:
        raise RuntimeError(f"Expected 30 outer rows, got {len(outer)}.")

    # Re-sort with canonical order only as deterministic tie-break.
    feature["canonical_order"] = feature["feature"].map(canonical)
    feature = feature.sort_values(
        ["selected_frequency", "selected_count", "canonical_order"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    feature.insert(0, "consensus_rank", np.arange(1, len(feature) + 1))
    feature["interpretation"] = "descriptive_nested_selection_frequency"
    feature.to_csv(OUT_DIR / "feature_consensus_ranking.csv", index=False)

    blocks = blocks.sort_values(
        ["selected_outer_frequency", "reference_block_id"],
        ascending=[False, True],
    ).reset_index(drop=True)
    blocks.insert(0, "consensus_rank", np.arange(1, len(blocks) + 1))
    blocks["interpretation"] = "descriptive_reference_block_selection_frequency"
    blocks.to_csv(OUT_DIR / "block_consensus_ranking.csv", index=False)

    kdist = kdist.sort_values("k").reset_index(drop=True)
    k_values_expanded = []
    for _, row in kdist.iterrows():
        k_values_expanded.extend([int(row["k"])] * int(row["count"]))
    k_array = np.asarray(k_values_expanded, dtype=float)

    max_k_count = int(kdist["count"].max())
    modal_k = (
        kdist.loc[kdist["count"].eq(max_k_count), "k"]
        .astype(int).tolist()
    )

    max_subset_count = int(subsets["count"].max())
    most_repeated = subsets[subsets["count"].eq(max_subset_count)].copy()
    unique_subset_count = int(len(subsets))

    development_features = dev["feature"].astype(str).tolist()
    development_set = frozenset(development_features)
    exact_dev_matches = int(
        outer["selected_features"]
        .fillna("")
        .map(normalize_subset)
        .eq(development_set)
        .sum()
    )

    # Minimal reproducibility fact: no exact subset recurred in two independent
    # outer iterations. This is sufficient to fail the pre-specified
    # reproducibility requirement; it is not presented as an acceptance
    # threshold for future analyses.
    no_exact_subset_recurrence = max_subset_count == 1

    # The development choice itself is also checked without reusing full-data
    # fit information.
    development_reproduced = exact_dev_matches > 0

    decision = (
        "NO_STABLE_FIXED_SUBSET"
        if no_exact_subset_recurrence
        else "FIXED_SUBSET_REQUIRES_FURTHER_RULE"
    )

    # No final weighted subset is forced when the critical stopping rule fires.
    selected_features = pd.DataFrame(
        columns=[
            "feature",
            "final_selected",
            "reason",
            "outer_selected_count",
            "outer_selected_frequency",
        ]
    )
    selected_features.to_csv(OUT_DIR / "selected_features.csv", index=False)

    # Preserve useful descriptive candidates without calling them a final set.
    consensus = feature[
        [
            "consensus_rank",
            "feature",
            "selected_count",
            "selected_frequency",
            "canonical_order",
        ]
    ].copy()
    consensus["final_status"] = "not_fixed_due_to_stopping_rule"
    consensus.to_csv(OUT_DIR / "consensus_candidates.csv", index=False)

    diagnostics = {
        "stage": "K",
        "status": decision,
        "final_subset_fixed": False,
        "reason": (
            "The pre-specified critical stopping rule is triggered: across the "
            "30 production outer iterations, no exact selected weighted subset "
            "recurred. Therefore a small fixed reduced eNRI subset is not forced."
        ),
        "nested_evidence": {
            "outer_splits": int(len(outer)),
            "unique_selected_subsets": unique_subset_count,
            "max_exact_subset_recurrence_count": max_subset_count,
            "max_exact_subset_recurrence_frequency": float(
                max_subset_count / len(outer)
            ),
            "development_subset_exact_recurrence_count": exact_dev_matches,
            "development_subset_exact_recurrence_frequency": float(
                exact_dev_matches / len(outer)
            ),
            "k_min": int(k_array.min()),
            "k_q25": float(np.quantile(k_array, 0.25)),
            "k_median": float(np.median(k_array)),
            "k_mean": float(np.mean(k_array)),
            "k_q75": float(np.quantile(k_array, 0.75)),
            "k_max": int(k_array.max()),
            "modal_k": modal_k,
            "modal_k_count_each": max_k_count,
            "modal_k_frequency_each": float(max_k_count / len(outer)),
        },
        "development_subset": {
            "k": int(len(development_features)),
            "features": development_features,
            "reproduced_exactly_in_nested_outer": bool(development_reproduced),
        },
        "top_individual_feature_frequencies": [
            {
                "rank": int(row["consensus_rank"]),
                "feature": str(row["feature"]),
                "selected_count": int(row["selected_count"]),
                "selected_frequency": float(row["selected_frequency"]),
            }
            for _, row in feature.head(10).iterrows()
        ],
        "reference_block_frequencies": [
            {
                "block_id": str(row["reference_block_id"]),
                "members": str(row["members"]),
                "selected_outer_count": int(row["selected_outer_count"]),
                "selected_outer_frequency": float(
                    row["selected_outer_frequency"]
                ),
            }
            for _, row in blocks.iterrows()
        ],
        "interpretation": {
            "feature_frequency": (
                "Useful for consensus ranking, but not sufficient by itself to "
                "define a final weighted subset after observing outer results."
            ),
            "block_frequency": (
                "Useful evidence about stable information sources; B01/B02 can "
                "remain biologically/statistically relevant even when exact "
                "members substitute across outer iterations."
            ),
            "next_model_stage": (
                "Stage L final reduced refit is blocked because no final fixed "
                "weighted subset has been justified under the frozen rules."
            ),
        },
        "outputs": {
            "selected_features": "stage_k/selected_features.csv",
            "consensus_candidates": "stage_k/consensus_candidates.csv",
            "feature_consensus_ranking": "stage_k/feature_consensus_ranking.csv",
            "block_consensus_ranking": "stage_k/block_consensus_ranking.csv",
            "summary": "stage_k/stage_k_summary.json",
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_k_summary.json").write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )

    print(
        "STAGE_K_SUMMARY="
        + json.dumps(diagnostics, ensure_ascii=False, sort_keys=True),
        flush=True,
    )


if __name__ == "__main__":
    main()
