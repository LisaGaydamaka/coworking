#!/usr/bin/env python3
"""Rebuild the fixed 30-feature eNRI under ALL0MEAN normalization."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE_SOLVE = ROOT.parent / "enri_mouse_neuroplasticity" / "solve_all0mean.py"
STAGE_B_PY = ROOT / "stage_b.py"
OUT_DIR = ROOT / "stage_0"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = load_module(BASE_SOLVE, "enri_all0mean_stage0_base")
    sparse = load_module(STAGE_B_PY, "enri_all0mean_stage0_sparse")

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    final_std, prep = base.fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=base.IMPUTATION_SEED,
        sample_posterior=False,
    )
    errors = list(prep.get("errors", []))
    states, xbar, state_stats = base.build_experimental_states(final_std)
    errors.extend(base.validate_full_stage4(states, xbar, state_stats))
    if errors:
        raise RuntimeError("Stage-0 preprocessing/state errors: " + " | ".join(errors))

    solution, meta = sparse.solve_sparse_qp(
        base, final_std, states, xbar, lambda1=0.0, forced_zero_features=[]
    )
    if solution is None or meta.get("errors"):
        raise RuntimeError(
            "Stage-0 fixed QP failed: " + " | ".join(meta.get("errors", []))
        )

    group_means = {
        label: float(st["a"] + st["b"] @ solution["w"])
        for label, st in states.items()
    }
    baseline_labels = ["PBS^0", "LPS^0", "run^0", "MCC^0"]
    baseline_state_mean = float(np.mean([group_means[x] for x in baseline_labels]))
    if abs(baseline_state_mean - 1.0) > 1e-8:
        raise RuntimeError(
            f"ALL0MEAN normalization failed: four-state mean={baseline_state_mean}"
        )

    baseline_rows = final_std[
        final_std["week"].eq(0)
        & final_std["status"].isin(["observed", "imputed"])
    ]
    X0 = baseline_rows[base.MODEL_FEATURES].to_numpy(dtype=float)
    baseline_mouse_enri = 1.0 + (X0 - np.asarray(xbar)) @ solution["w"]

    pd.DataFrame({
        "feature": list(base.MODEL_FEATURES),
        "weight": [float(x) for x in solution["w"]],
    }).to_csv(OUT_DIR / "weights.csv", index=False)

    pd.DataFrame([
        {
            "state": label,
            "group": label.split("^")[0],
            "week": int(label.split("^")[1]),
            "mean_eNRI": group_means[label],
        }
        for week in base.STATE_WEEKS
        for label in [f"{g}^{week}" for g in base.STATE_GROUPS]
    ]).to_csv(OUT_DIR / "group_means.csv", index=False)

    living = final_std["status"].isin(["observed", "imputed"])
    enri = final_std[["mouse_id", "group", "week", "status"]].copy()
    enri["eNRI"] = 0.0
    Xlive = final_std.loc[living, base.MODEL_FEATURES].to_numpy(dtype=float)
    enri.loc[living, "eNRI"] = (
        1.0 + (Xlive - np.asarray(xbar, dtype=float)) @ solution["w"]
    )
    enri.to_csv(OUT_DIR / "enri.csv", index=False)

    normalization = {
        "mode": base.NORMALIZATION_MODE,
        "definition": (
            "equal arithmetic mean of the four week-0 experimental-state "
            "feature means: PBS^0, LPS^0, run^0, MCC^0"
        ),
        "state_weighting": "equal 1/4 per state; not mouse-count weighted",
        "reference_vector_standardized": [float(x) for x in np.asarray(xbar)],
        "baseline_state_labels": baseline_labels,
        "baseline_state_mean_eNRI": baseline_state_mean,
        "baseline_mouse_weighted_mean_eNRI_diagnostic": float(
            np.mean(baseline_mouse_enri)
        ),
    }
    (OUT_DIR / "normalization.json").write_text(
        json.dumps(normalization, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    summary = {
        "stage": "0",
        "status": "READY",
        "normalization": normalization,
        "fixed_model": {
            "beta": sparse.BETA,
            "lambda2": sparse.LAMBDA2,
            "C": sparse.C_SLACK,
            "rho": sparse.RHO,
            "lambda1": 0.0,
            "order_constraints": len(base.ORDER_PAIRS),
            "soft_equalities": len(base.EQUALITY_PAIRS),
            "features": len(base.MODEL_FEATURES),
        },
        "solver_status": str(solution["solver_status"]),
        "living_eNRI_min": float(enri.loc[living, "eNRI"].min()),
        "living_eNRI_max": float(enri.loc[living, "eNRI"].max()),
        "slack_sum": float(solution["slack_sum"]),
        "group_means": group_means,
        "validation_errors": [],
    }
    (OUT_DIR / "stage_0_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("STAGE_0_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
