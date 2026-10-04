#!/usr/bin/env python3
"""
Stage C: mouse-level stability selection for sparse eNRI.

Uses the development lambda1* from Stage B and repeatedly refits the complete
train-only preprocessing + constrained Elastic-Net model on stratified 80%
mouse subsamples.

The output quantifies, for each of the 30 MODEL_FEATURES:
- selection frequency pi_j = P(|w_j| > 1e-6);
- positive/negative sign frequencies among selected fits;
- sign consistency s_j;
- raw-scale slope gamma_j = w_j / training baseline SD;
- core/candidate stability category.

This is still a development analysis. In final nested validation the same
procedure must be repeated inside each outer-train.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit


ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parent / "enri_mouse_neuroplasticity"
BASE_SOLVE = BASE_DIR / "solve_all0mean_grip.py"
STAGE_B_PY = ROOT / "stage_b.py"
STAGE_B_SUMMARY = ROOT / "stage_b" / "stage_b_summary.json"
OUT_DIR = ROOT / "stage_c"

TARGET_VALID_RESAMPLES = 200
MIN_VALID_RESAMPLES = 100
TRAIN_FRACTION = 0.80
SEED_START = 20000
MAX_CANDIDATE_SEEDS = 5000
ACTIVE_TOL = 1e-6
MIN_TRAIN_O = 5

CORE_PI = 0.80
CORE_SIGN = 0.90
CANDIDATE_PI = 0.60
CANDIDATE_SIGN = 0.80


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_lambda1_star():
    if not STAGE_B_SUMMARY.exists():
        raise FileNotFoundError(STAGE_B_SUMMARY)
    summary = json.loads(STAGE_B_SUMMARY.read_text(encoding="utf-8"))
    if summary.get("status") != "READY":
        raise RuntimeError("Stage B is not READY.")
    value = float(summary["development_selection"]["lambda1_star"])
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(f"Invalid lambda1*: {value}")
    return value


def make_stratified_train_ids(mouse_df: pd.DataFrame, seed: int):
    X = np.zeros((len(mouse_df), 1), dtype=float)
    y = mouse_df["group"].to_numpy()
    splitter = StratifiedShuffleSplit(
        n_splits=1,
        train_size=TRAIN_FRACTION,
        random_state=int(seed),
    )
    train_idx, holdout_idx = next(splitter.split(X, y))
    train_ids = mouse_df.iloc[train_idx]["mouse_id"].tolist()
    holdout_ids = mouse_df.iloc[holdout_idx]["mouse_id"].tolist()
    return train_ids, holdout_ids


def fit_one_resample(base, sparse, long_raw, mouse_df, seed, lambda1_star):
    train_ids, holdout_ids = make_stratified_train_ids(mouse_df, seed)
    train_id_set = set(train_ids)

    # Stability selection does not need held-out predictions. Restrict the
    # preprocessing input to the training mice so all deterministic/statistical
    # checks concern only the subsample being fitted.
    train_raw = long_raw[long_raw["mouse_id"].isin(train_id_set)].copy()

    final_std, prep_stats = base.fit_transform_stage3(
        train_raw,
        fit_mouse_ids=train_ids,
        random_state=base.IMPUTATION_SEED,
        sample_posterior=False,
    )
    reasons = list(prep_stats.get("errors", []))

    if prep_stats.get("deterministic", {}).get("fit_scope") != "train_only":
        reasons.append("Censor maxima were not fitted train-only.")
    if prep_stats.get("scaling", {}).get("fit_scope") != "train_only":
        reasons.append("Baseline scaling was not fitted train-only.")

    states, xbar, state_stats = base.build_experimental_states(
        final_std,
        state_mouse_ids=train_ids,
        reference_xbar=None,
    )

    train_o = {label: int(s["O"]) for label, s in states.items()}
    min_train_o = min(train_o.values()) if train_o else 0
    if min_train_o < MIN_TRAIN_O:
        bad = {k: v for k, v in train_o.items() if v < MIN_TRAIN_O}
        reasons.append(
            "train O_A below 5: " + json.dumps(bad, ensure_ascii=False, sort_keys=True)
        )
    else:
        reasons.extend(state_stats.get("errors", []))

    if xbar is None:
        reasons.append("Missing xbar_PBS0_train.")

    train_group_counts = {
        g: int(mouse_df[mouse_df["mouse_id"].isin(train_id_set)]["group"].eq(g).sum())
        for g in base.STATE_GROUPS
    }

    if reasons:
        return None, {
            "seed": int(seed),
            "reason": " | ".join(map(str, reasons)),
            "train_n": int(len(train_ids)),
            "holdout_n": int(len(holdout_ids)),
            "min_train_O": int(min_train_o),
            "train_group_counts": train_group_counts,
        }

    solution, meta = sparse.solve_sparse_qp(
        base,
        final_std,
        states,
        xbar,
        lambda1=lambda1_star,
    )
    if solution is None or meta.get("errors"):
        return None, {
            "seed": int(seed),
            "reason": "sparse QP: " + " | ".join(meta.get("errors", [])),
            "train_n": int(len(train_ids)),
            "holdout_n": int(len(holdout_ids)),
            "min_train_O": int(min_train_o),
            "train_group_counts": train_group_counts,
        }

    stds = prep_stats["scaling"]["std"]
    weights = np.asarray(solution["w"], dtype=float)
    active = np.abs(weights) > ACTIVE_TOL
    gamma = np.asarray([
        float(weights[j]) / float(stds[feature])
        for j, feature in enumerate(base.MODEL_FEATURES)
    ], dtype=float)

    if not np.isfinite(gamma).all():
        return None, {
            "seed": int(seed),
            "reason": "non-finite raw-scale gamma",
            "train_n": int(len(train_ids)),
            "holdout_n": int(len(holdout_ids)),
            "min_train_O": int(min_train_o),
            "train_group_counts": train_group_counts,
        }

    record = {
        "seed": int(seed),
        "train_n": int(len(train_ids)),
        "holdout_n": int(len(holdout_ids)),
        "min_train_O": int(min_train_o),
        "train_ids": "|".join(map(str, sorted(train_ids))),
        "holdout_ids": "|".join(map(str, sorted(holdout_ids))),
        "group_counts": train_group_counts,
        "active_count": int(active.sum()),
        "slack_sum": float(solution["slack_sum"]),
        "slack_max": float(solution["slack_max"]),
        "min_live_enri": float(solution["min_live_enri"]),
        "solver_status": str(solution["solver_status"]),
        "solver_used": str(solution.get("solver_used", "")),
        "weights": weights,
        "active": active,
        "gamma": gamma,
    }
    return record, None


def summarize_features(base, valid_records):
    n = len(valid_records)
    rows = []

    weight_matrix = np.vstack([r["weights"] for r in valid_records])
    active_matrix = np.vstack([r["active"] for r in valid_records]).astype(bool)
    gamma_matrix = np.vstack([r["gamma"] for r in valid_records])

    for j, feature in enumerate(base.MODEL_FEATURES):
        active = active_matrix[:, j]
        selected_count = int(active.sum())
        pi = float(selected_count / n)

        selected_weights = weight_matrix[active, j]
        pos_count = int(np.sum(selected_weights > 0))
        neg_count = int(np.sum(selected_weights < 0))

        if selected_count:
            pos_freq_selected = float(pos_count / selected_count)
            neg_freq_selected = float(neg_count / selected_count)
            sign_consistency = float(max(pos_freq_selected, neg_freq_selected))
            modal_sign = 1 if pos_count >= neg_count else -1
        else:
            pos_freq_selected = float("nan")
            neg_freq_selected = float("nan")
            sign_consistency = float("nan")
            modal_sign = 0

        gamma_all = gamma_matrix[:, j]
        gamma_selected = gamma_matrix[active, j]

        if (
            pi >= CORE_PI
            and math.isfinite(sign_consistency)
            and sign_consistency >= CORE_SIGN
        ):
            category = "core"
        elif (
            pi >= CANDIDATE_PI
            and pi < CORE_PI
            and math.isfinite(sign_consistency)
            and sign_consistency >= CANDIDATE_SIGN
        ):
            category = "candidate"
        elif pi >= CORE_PI:
            category = "high_frequency_unstable_sign"
        else:
            category = "other"

        row = {
            "feature": feature,
            "feature_order": j + 1,
            "valid_resamples": n,
            "selected_count": selected_count,
            "pi_selection": pi,
            "positive_selected_count": pos_count,
            "negative_selected_count": neg_count,
            "positive_frequency_given_selected": pos_freq_selected,
            "negative_frequency_given_selected": neg_freq_selected,
            "sign_consistency": sign_consistency,
            "modal_sign": modal_sign,
            "category": category,
            "weight_median_all": float(np.median(weight_matrix[:, j])),
            "weight_q10_all": float(np.quantile(weight_matrix[:, j], 0.10)),
            "weight_q90_all": float(np.quantile(weight_matrix[:, j], 0.90)),
            "gamma_median_all": float(np.median(gamma_all)),
            "gamma_q10_all": float(np.quantile(gamma_all, 0.10)),
            "gamma_q90_all": float(np.quantile(gamma_all, 0.90)),
        }

        if selected_count:
            row.update({
                "gamma_median_selected": float(np.median(gamma_selected)),
                "gamma_q10_selected": float(np.quantile(gamma_selected, 0.10)),
                "gamma_q90_selected": float(np.quantile(gamma_selected, 0.90)),
                "abs_gamma_median_selected": float(np.median(np.abs(gamma_selected))),
            })
        else:
            row.update({
                "gamma_median_selected": np.nan,
                "gamma_q10_selected": np.nan,
                "gamma_q90_selected": np.nan,
                "abs_gamma_median_selected": np.nan,
            })

        rows.append(row)

    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["pi_selection", "sign_consistency", "abs_gamma_median_selected", "feature_order"],
        ascending=[False, False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    out["stability_rank"] = np.arange(1, len(out) + 1)
    return out


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base = load_module(BASE_SOLVE, "enri_base_model_c")
    sparse = load_module(STAGE_B_PY, "enri_stage_b_c")
    lambda1_star = load_lambda1_star()

    # The normalization experiment is allowed to change the development
    # lambda1 selected by Stage B. Stage C must use that newly selected value,
    # not the historical 0.03 from the PBS^0-centered experiment.

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

    valid_records = []
    rejected_records = []

    for offset in range(MAX_CANDIDATE_SEEDS):
        if len(valid_records) >= TARGET_VALID_RESAMPLES:
            break
        seed = SEED_START + offset
        record, rejected = fit_one_resample(
            base, sparse, long_raw, mouse_df, seed, lambda1_star
        )
        if record is not None:
            record["resample_index"] = len(valid_records) + 1
            valid_records.append(record)
        else:
            rejected_records.append(rejected)

    if len(valid_records) < MIN_VALID_RESAMPLES:
        raise RuntimeError(
            f"Only {len(valid_records)} valid stability resamples; "
            f"minimum required={MIN_VALID_RESAMPLES}."
        )
    if len(valid_records) < TARGET_VALID_RESAMPLES:
        raise RuntimeError(
            f"Only {len(valid_records)} valid stability resamples; "
            f"target={TARGET_VALID_RESAMPLES}."
        )

    feature_summary = summarize_features(base, valid_records)

    resample_rows = []
    coefficient_rows = []
    for r in valid_records:
        resample_rows.append({
            "resample_index": int(r["resample_index"]),
            "seed": int(r["seed"]),
            "train_n": int(r["train_n"]),
            "holdout_n": int(r["holdout_n"]),
            "min_train_O": int(r["min_train_O"]),
            "PBS_train": int(r["group_counts"]["PBS"]),
            "LPS_train": int(r["group_counts"]["LPS"]),
            "run_train": int(r["group_counts"]["run"]),
            "MCC_train": int(r["group_counts"]["MCC"]),
            "active_count": int(r["active_count"]),
            "slack_sum": float(r["slack_sum"]),
            "slack_max": float(r["slack_max"]),
            "min_live_enri": float(r["min_live_enri"]),
            "solver_status": r["solver_status"],
            "solver_used": r["solver_used"],
            "train_ids": r["train_ids"],
            "holdout_ids": r["holdout_ids"],
        })
        for j, feature in enumerate(base.MODEL_FEATURES):
            coefficient_rows.append({
                "resample_index": int(r["resample_index"]),
                "seed": int(r["seed"]),
                "feature": feature,
                "weight": float(r["weights"][j]),
                "active": bool(r["active"][j]),
                "gamma_raw_scale": float(r["gamma"][j]),
            })

    resamples_df = pd.DataFrame(resample_rows)
    coefficients_df = pd.DataFrame(coefficient_rows)
    rejected_df = pd.DataFrame(rejected_records)

    feature_summary.to_csv(OUT_DIR / "stability_selection.csv", index=False)
    resamples_df.to_csv(OUT_DIR / "stability_resamples.csv", index=False)
    coefficients_df.to_csv(OUT_DIR / "stability_coefficients.csv", index=False)
    if not rejected_df.empty:
        rejected_df.to_csv(OUT_DIR / "stability_rejected.csv", index=False)

    core = feature_summary[feature_summary["category"].eq("core")]
    candidate = feature_summary[feature_summary["category"].eq("candidate")]

    active_counts = resamples_df["active_count"].astype(float)
    slack_sums = resamples_df["slack_sum"].astype(float)

    summary = {
        "stage": "C",
        "status": "READY",
        "purpose": "development_mouse_level_stability_selection",
        "warning": (
            "Development stability results are not the final nested-CV feature "
            "frequencies. The same procedure must be rerun inside each outer-train."
        ),
        "lambda1_star": float(lambda1_star),
        "active_threshold": ACTIVE_TOL,
        "resampling": {
            "method": "StratifiedShuffleSplit mouse-level 80/20",
            "target_valid_resamples": TARGET_VALID_RESAMPLES,
            "valid_resamples": int(len(valid_records)),
            "rejected_resamples": int(len(rejected_records)),
            "seed_start": SEED_START,
            "first_valid_seed": int(valid_records[0]["seed"]),
            "last_valid_seed": int(valid_records[-1]["seed"]),
            "train_fraction": TRAIN_FRACTION,
            "min_train_O": MIN_TRAIN_O,
        },
        "active_count": {
            "mean": float(active_counts.mean()),
            "median": float(active_counts.median()),
            "min": int(active_counts.min()),
            "max": int(active_counts.max()),
            "q10": float(active_counts.quantile(0.10)),
            "q90": float(active_counts.quantile(0.90)),
        },
        "slack_sum": {
            "mean": float(slack_sums.mean()),
            "median": float(slack_sums.median()),
            "q10": float(slack_sums.quantile(0.10)),
            "q90": float(slack_sums.quantile(0.90)),
        },
        "thresholds": {
            "core": f"pi>={CORE_PI} and sign_consistency>={CORE_SIGN}",
            "candidate": (
                f"{CANDIDATE_PI}<=pi<{CORE_PI} and "
                f"sign_consistency>={CANDIDATE_SIGN}"
            ),
        },
        "core_features": [
            {
                "feature": str(row["feature"]),
                "pi_selection": float(row["pi_selection"]),
                "sign_consistency": float(row["sign_consistency"]),
                "modal_sign": int(row["modal_sign"]),
                "gamma_median_selected": float(row["gamma_median_selected"]),
            }
            for _, row in core.iterrows()
        ],
        "candidate_features": [
            {
                "feature": str(row["feature"]),
                "pi_selection": float(row["pi_selection"]),
                "sign_consistency": float(row["sign_consistency"]),
                "modal_sign": int(row["modal_sign"]),
                "gamma_median_selected": float(row["gamma_median_selected"]),
            }
            for _, row in candidate.iterrows()
        ],
        "counts": {
            "core_features": int(len(core)),
            "candidate_features": int(len(candidate)),
            "other_features": int(
                len(feature_summary)
                - len(core)
                - len(candidate)
            ),
        },
        "outputs": {
            "feature_summary": "stage_c/stability_selection.csv",
            "resamples": "stage_c/stability_resamples.csv",
            "coefficients": "stage_c/stability_coefficients.csv",
            "rejected": (
                "stage_c/stability_rejected.csv"
                if not rejected_df.empty
                else None
            ),
        },
        "validation_errors": [],
    }

    (OUT_DIR / "stage_c_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print("STAGE_C_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
