#!/usr/bin/env python3
"""
Stage G: choose the minimal sufficient development subset size k.

Input:
- Stage-F autonomous reduced-model CV for S_3...S_15 on the same 22
  development mouse-level splits.

Rule:
- sequential lexicographic one-SE filtering:
  V_pos -> V_sign -> V_margin -> V_eq -> V_var -> V_w;
- at each metric, retain subsets whose mean loss is no worse than
  best_mean + SE(best);
- if exact best-mean ties occur, use the smallest-k tied row as the
  deterministic SE reference;
- after all metrics, choose the smallest surviving k.

The SE is SD across the repeated/overlapping development splits divided by
sqrt(N); it is a heuristic stability/error measure, not a classical
independent-sample inferential SE.

This is still a development selection. The final nested procedure must repeat
selection inside each outer-train.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
STAGE_F_DIR = ROOT / "stage_f"
SUBSET_CV = STAGE_F_DIR / "subset_cv.csv"
SUBSET_FOLDS = STAGE_F_DIR / "subset_cv_folds.csv"
RANKING = STAGE_F_DIR / "block_aware_ranking.csv"
CANDIDATE_SETS = STAGE_F_DIR / "candidate_sets.csv"
OUT_DIR = ROOT / "stage_g"

METRICS = ("V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w")
EXPECTED_K = tuple(range(3, 16))
EXPECTED_SPLITS = 22
COMPARE_TOL = 1e-9


def recalc_summary(folds: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for k in sorted(folds["k"].astype(int).unique()):
        sub = folds[folds["k"].astype(int).eq(k)].copy()
        row = {
            "k": int(k),
            "folds": int(len(sub)),
            "features": str(sub["features"].iloc[0]),
        }
        if sub["features"].nunique() != 1:
            raise RuntimeError(f"k={k}: multiple feature definitions in fold file.")

        for metric in METRICS:
            vals = sub[metric].astype(float)
            if not np.isfinite(vals.to_numpy()).all():
                raise RuntimeError(f"k={k}: non-finite {metric}.")
            sd = float(vals.std(ddof=1)) if len(vals) >= 2 else 0.0
            row[f"{metric}_mean"] = float(vals.mean())
            row[f"{metric}_sd"] = sd
            row[f"{metric}_se"] = float(sd / math.sqrt(len(vals))) if len(vals) else np.nan
            row[f"{metric}_median"] = float(vals.median())
        rows.append(row)
    return pd.DataFrame(rows)


def validate_same_splits(folds: pd.DataFrame):
    reference = None
    reference_k = None
    for k in sorted(folds["k"].astype(int).unique()):
        sub = folds[folds["k"].astype(int).eq(k)]
        keys = sorted(
            (int(seed), int(fold))
            for seed, fold in zip(sub["seed"], sub["fold"])
        )
        if len(keys) != EXPECTED_SPLITS:
            raise RuntimeError(
                f"k={k}: expected {EXPECTED_SPLITS} folds, got {len(keys)}."
            )
        if len(set(keys)) != len(keys):
            raise RuntimeError(f"k={k}: duplicate seed/fold keys.")
        if reference is None:
            reference = keys
            reference_k = k
        elif keys != reference:
            raise RuntimeError(
                f"k={k}: split keys differ from k={reference_k}."
            )
    return reference


def validate_against_stage_f(recalc: pd.DataFrame, persisted: pd.DataFrame):
    merged = recalc.merge(
        persisted,
        on="k",
        how="inner",
        validate="one_to_one",
        suffixes=("_recalc", "_stage_f"),
    )
    if len(merged) != len(recalc):
        raise RuntimeError("Stage-F subset_cv.csv does not cover all recalculated k.")

    max_diffs = {}
    for metric in METRICS:
        for stat in ("mean", "sd", "se", "median"):
            a = merged[f"{metric}_{stat}_recalc"].astype(float).to_numpy()
            b = merged[f"{metric}_{stat}_stage_f"].astype(float).to_numpy()
            diff = np.abs(a - b)
            key = f"{metric}_{stat}"
            max_diffs[key] = float(diff.max())
            if max_diffs[key] > COMPARE_TOL:
                raise RuntimeError(
                    f"Stage-F mismatch {key}: max diff={max_diffs[key]}."
                )
    return max_diffs


def sequential_one_se(summary: pd.DataFrame):
    survivors = summary.copy()
    trace = []
    eliminated = {}

    for step, metric in enumerate(METRICS, start=1):
        mean_col = f"{metric}_mean"
        se_col = f"{metric}_se"

        best_mean = float(survivors[mean_col].min())
        tied = survivors[
            np.isclose(
                survivors[mean_col].astype(float).to_numpy(),
                best_mean,
                rtol=0,
                atol=1e-15,
            )
        ].sort_values("k")
        reference = tied.iloc[0]
        reference_k = int(reference["k"])
        best_se = float(reference[se_col])
        threshold = best_mean + best_se

        before = sorted(survivors["k"].astype(int).tolist())
        keep_mask = survivors[mean_col].astype(float) <= threshold + 1e-15
        dropped = sorted(
            survivors.loc[~keep_mask, "k"].astype(int).tolist()
        )
        survivors = survivors.loc[keep_mask].copy().sort_values("k")

        for k in dropped:
            eliminated.setdefault(k, metric)

        trace.append({
            "step": step,
            "metric": metric,
            "reference_best_k": reference_k,
            "best_mean": best_mean,
            "best_se": best_se,
            "one_se_threshold": threshold,
            "survivors_before": "|".join(map(str, before)),
            "dropped_at_step": "|".join(map(str, dropped)),
            "survivors_after": "|".join(
                map(str, survivors["k"].astype(int).tolist())
            ),
            "n_survivors_after": int(len(survivors)),
        })

        if survivors.empty:
            raise RuntimeError(f"No survivors after metric {metric}.")

    selected_k = int(survivors["k"].min())
    return selected_k, survivors, pd.DataFrame(trace), eliminated


def paired_compare(folds: pd.DataFrame, k_a: int, k_b: int):
    """
    Return paired differences b-a on the same splits.
    Negative delta means k_b has a lower/better loss than k_a.
    """
    a = folds[folds["k"].astype(int).eq(k_a)].copy()
    b = folds[folds["k"].astype(int).eq(k_b)].copy()
    merged = a.merge(
        b,
        on=["seed", "fold"],
        how="inner",
        validate="one_to_one",
        suffixes=(f"_k{k_a}", f"_k{k_b}"),
    )
    if len(merged) != EXPECTED_SPLITS:
        raise RuntimeError(
            f"Paired comparison k={k_a} vs k={k_b} has {len(merged)} rows."
        )

    out = {}
    for metric in METRICS:
        d = (
            merged[f"{metric}_k{k_b}"].astype(float)
            - merged[f"{metric}_k{k_a}"].astype(float)
        )
        out[metric] = {
            "mean_delta_b_minus_a": float(d.mean()),
            "median_delta_b_minus_a": float(d.median()),
            "q10": float(d.quantile(0.10)),
            "q90": float(d.quantile(0.90)),
            "p_b_better": float(np.mean(d < 0)),
            "p_equal": float(np.mean(np.isclose(d, 0.0, atol=1e-12, rtol=0))),
            "p_b_worse": float(np.mean(d > 0)),
        }
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for path in (SUBSET_CV, SUBSET_FOLDS, RANKING, CANDIDATE_SETS):
        if not path.exists():
            raise FileNotFoundError(path)

    persisted = pd.read_csv(SUBSET_CV)
    folds = pd.read_csv(SUBSET_FOLDS)
    ranking = pd.read_csv(RANKING)
    candidate_sets = pd.read_csv(CANDIDATE_SETS)

    ks = tuple(sorted(folds["k"].astype(int).unique().tolist()))
    if ks != EXPECTED_K:
        raise RuntimeError(f"Expected k={EXPECTED_K}, got {ks}.")
    if tuple(sorted(candidate_sets["k"].astype(int).tolist())) != EXPECTED_K:
        raise RuntimeError("candidate_sets.csv k range mismatch.")

    split_keys = validate_same_splits(folds)
    recalc = recalc_summary(folds)
    stage_f_max_diffs = validate_against_stage_f(recalc, persisted)

    selected_k, survivors, trace_df, eliminated = sequential_one_se(recalc)
    selected_row = recalc[recalc["k"].eq(selected_k)].iloc[0]
    selected_features = str(selected_row["features"]).split("|")

    candidate_selected = candidate_sets[
        candidate_sets["k"].astype(int).eq(selected_k)
    ]
    if len(candidate_selected) != 1:
        raise RuntimeError("Selected k missing/duplicated in candidate_sets.csv.")
    candidate_features = str(candidate_selected.iloc[0]["features"]).split("|")
    if selected_features != candidate_features:
        raise RuntimeError(
            "Selected feature list differs between fold summaries and candidate_sets.csv."
        )

    rank_map = ranking.set_index("feature").to_dict(orient="index")
    selected_feature_rows = []
    for position, feature in enumerate(selected_features, start=1):
        if feature not in rank_map:
            raise RuntimeError(f"Selected feature absent from Stage-F ranking: {feature}")
        r = rank_map[feature]
        selected_feature_rows.append({
            "selected_position": position,
            "feature": feature,
            "stage_f_rank": int(r["rank"]),
            "block_id": "" if pd.isna(r["block_id"]) else str(r["block_id"]),
            "pi_selection": float(r["pi_selection"]),
            "sign_consistency": float(r["sign_consistency"]),
            "stage_c_category": str(r["category"]),
            "ablation_source": str(r["ablation_source"]),
            "abs_gamma_median_selected": float(r["abs_gamma_median_selected"]),
        })

    selected_features_df = pd.DataFrame(selected_feature_rows)
    selected_features_df.to_csv(OUT_DIR / "selected_subset.csv", index=False)

    trace_df["selected_k"] = selected_k
    trace_df.to_csv(OUT_DIR / "k_selection_trace.csv", index=False)

    selected_fold_df = folds[
        folds["k"].astype(int).eq(selected_k)
    ].copy()
    selected_fold_df.to_csv(
        OUT_DIR / "selected_k_fold_metrics.csv", index=False
    )

    # Make an auditable status table for every k.
    status_rows = []
    final_survivors = set(survivors["k"].astype(int).tolist())
    for _, row in recalc.sort_values("k").iterrows():
        k = int(row["k"])
        rec = {
            "k": k,
            "features": str(row["features"]),
            "selected": k == selected_k,
            "final_survivor": k in final_survivors,
            "eliminated_at_metric": eliminated.get(k, ""),
        }
        for metric in METRICS:
            rec[f"{metric}_mean"] = float(row[f"{metric}_mean"])
            rec[f"{metric}_se"] = float(row[f"{metric}_se"])
        status_rows.append(rec)
    status_df = pd.DataFrame(status_rows)
    status_df.to_csv(OUT_DIR / "k_selection_status.csv", index=False)

    # k3 vs selected is especially useful here because V_pos leaves only k3,k4.
    pairwise_k3_selected = (
        paired_compare(folds, 3, selected_k)
        if selected_k != 3
        else None
    )

    selected_metrics = {
        metric: {
            "mean": float(selected_row[f"{metric}_mean"]),
            "se": float(selected_row[f"{metric}_se"]),
            "median": float(selected_row[f"{metric}_median"]),
        }
        for metric in METRICS
    }

    summary = {
        "stage": "G",
        "status": "READY",
        "purpose": "development_minimal_sufficient_k_selection",
        "warning": (
            "Selected k is a development result from the fixed 22 Stage-F splits. "
            "It is not the final feature subset. In Stage H, the complete selection "
            "procedure must be repeated independently inside each outer-train."
        ),
        "rule": {
            "priority": list(METRICS),
            "filter": "mean <= best_mean + SE(best) at each sequential metric",
            "exact_best_tie_reference": "smallest k among exact best-mean ties",
            "final_choice": "smallest k among final survivors",
            "se_definition": "SD(valid repeated splits) / sqrt(N_valid_splits)",
            "se_interpretation": (
                "heuristic stability/error measure because repeated splits overlap; "
                "not a classical independent-sample inferential SE"
            ),
        },
        "validation": {
            "k_values": list(EXPECTED_K),
            "splits_per_k": EXPECTED_SPLITS,
            "same_split_keys_for_all_k": True,
            "split_keys": [
                {"seed": int(seed), "fold": int(fold)}
                for seed, fold in split_keys
            ],
            "max_recalc_diff_vs_stage_f": stage_f_max_diffs,
        },
        "selection": {
            "selected_k": selected_k,
            "selected_features": selected_features,
            "selected_metrics": selected_metrics,
            "final_survivor_k": sorted(final_survivors),
            "eliminated_at_metric": {
                str(k): metric for k, metric in sorted(eliminated.items())
            },
        },
        "paired_k3_vs_selected": pairwise_k3_selected,
        "outputs": {
            "selection_trace": "stage_g/k_selection_trace.csv",
            "selection_status": "stage_g/k_selection_status.csv",
            "selected_subset": "stage_g/selected_subset.csv",
            "selected_k_fold_metrics": "stage_g/selected_k_fold_metrics.csv",
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_g_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STAGE_G_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
