#!/usr/bin/env python3
"""Run the independent pooled-week0 GRIP31 longitudinal-only base model."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
from pathlib import Path

HERE = Path(__file__).resolve().parent
WRAPPER = HERE / "solve_all0mean_grip_longitudinal.py"
RESULTS = HERE / "base_results"

spec = importlib.util.spec_from_file_location("enri_longitudinal_base", WRAPPER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot import {WRAPPER}")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RESULTS.mkdir(parents=True, exist_ok=True)
m.RESULTS_DIR = RESULTS
m._base.RESULTS_DIR = RESULTS

_orig_build_experimental_states = m.build_experimental_states
def _build_states_with_metadata(*args, **kwargs):
    states, xbar, stats = _orig_build_experimental_states(*args, **kwargs)
    for label, state in states.items():
        group, week = label.split("^")
        state.setdefault("group", group)
        state.setdefault("week", int(week))
    return states, xbar, stats
m.build_experimental_states = _build_states_with_metadata
m._base.build_experimental_states = _build_states_with_metadata


def _patch_function(fn, replacements, name):
    src = inspect.getsource(fn)
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f"{name}: patch target not found: {old[:100]!r}")
        src = src.replace(old, new)
    exec(src, m._base.__dict__)
    patched = m._base.__dict__[name]
    setattr(m, name, patched)
    return patched


# These are the same pooled-normalization and p=31 compatibility patches used
# by the historical GRIP31 rerun; they do not change the scientific objective.
_patch_function(
    m._base.validate_stage7_outputs,
    [(
'''    pbs0 = enri_df[
        enri_df["group"].eq("PBS") & enri_df["week"].eq(0)
    ]["eNRI"].astype(float)
    pbs0_mean = float(pbs0.mean())
    if abs(pbs0_mean - 1.0) > QP_TOLERANCE:
        errors.append(f"PBS^0 mean eNRI={pbs0_mean}, expected 1.")
''',
'''    pbs0_mean = float(
        enri_df[enri_df["week"].eq(0)]["eNRI"].astype(float).mean()
    )
    if abs(pbs0_mean - 1.0) > QP_TOLERANCE:
        errors.append(f"Pooled week-0 mean eNRI={pbs0_mean}, expected 1.")
''')
    ],
    "validate_stage7_outputs",
)

_patch_function(
    m._base.run_stage7,
    [(
'''        "Direct mean from final enri.csv for PBS week 0.",
''',
'''        "Direct mean from final enri.csv over all mice at week 0.",
'''),
    (
'''        feature="PBS^0",
''',
'''        feature="week0_pooled",
''')
    ],
    "run_stage7",
)

_patch_function(
    m._base.run_stage9,
    [(
'''    # 9. PBS0 normalization.
    pbs0_mean = float(
        enri_df[enri_df["group"].eq("PBS") & enri_df["week"].eq(0)]["eNRI"].mean()
    )
    check(
        9, "pbs0_normalization",
        abs(pbs0_mean - 1.0) <= QP_TOLERANCE,
        f"Mean PBS^0 eNRI={pbs0_mean:.12g}.",
        f"PBS^0 normalization failed: {pbs0_mean:.12g}.",
        value=pbs0_mean,
    )
''',
'''    # 9. Pooled week-0 normalization.
    pbs0_mean = float(enri_df[enri_df["week"].eq(0)]["eNRI"].mean())
    check(
        9, "pbs0_normalization",
        abs(pbs0_mean - 1.0) <= QP_TOLERANCE,
        f"Mean pooled week-0 eNRI={pbs0_mean:.12g}.",
        f"Pooled week-0 normalization failed: {pbs0_mean:.12g}.",
        value=pbs0_mean,
    )
'''),
    (
'''        len(weights_df) == 30
        and weights_df["feature"].astype(str).tolist() == list(MODEL_FEATURES)
''',
'''        len(weights_df) == len(MODEL_FEATURES)
        and weights_df["feature"].astype(str).tolist() == list(MODEL_FEATURES)
'''),
    (
'''        5, "thirty_weights",
        feature_match,
        "weights.csv contains exactly the 30 MODEL_FEATURES in canonical order.",
''',
'''        5, "model_feature_weights",
        feature_match,
        f"weights.csv contains exactly the {len(MODEL_FEATURES)} MODEL_FEATURES in canonical order.",
'''),
    (
'''        len(weight_values) == 30 and np.isfinite(weight_values).all(),
        "All 30 final weights are finite.",
''',
'''        len(weight_values) == len(MODEL_FEATURES) and np.isfinite(weight_values).all(),
        f"All {len(MODEL_FEATURES)} final weights are finite.",
'''),
    (
'''    # 25. model.json can reproduce eNRI for a complete 30-feature vector.
    model_arrays_ok = (
        model.get("features") == list(MODEL_FEATURES)
        and len(model.get("mean", [])) == 30
        and len(model.get("std", [])) == 30
        and len(model.get("xbar_pbs0", [])) == 30
        and len(model.get("weights", [])) == 30
''',
'''    # 25. model.json can reproduce eNRI for a complete model-feature vector.
    model_arrays_ok = (
        model.get("features") == list(MODEL_FEATURES)
        and len(model.get("mean", [])) == len(MODEL_FEATURES)
        and len(model.get("std", [])) == len(MODEL_FEATURES)
        and len(model.get("xbar_pbs0", [])) == len(MODEL_FEATURES)
        and len(model.get("weights", [])) == len(MODEL_FEATURES)
'''),
    (
'''        # Recover the corresponding complete raw 30-vector, then recompute eNRI
''',
'''        # Recover the corresponding complete raw model vector, then recompute eNRI
'''),
    (
'''        f"model.json reproduces eNRI for complete 30-feature vectors; max absolute error={model_repro_err:.3g}.",
''',
'''        f"model.json reproduces eNRI for complete {len(MODEL_FEATURES)}-feature vectors; max absolute error={model_repro_err:.3g}.",
'''),
    (
'''            "model_features": 30,
''',
'''            "model_features": len(MODEL_FEATURES),
''')
    ],
    "run_stage9",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True)
    args = parser.parse_args()
    fn = getattr(m, f"run_stage{args.stage}", None)
    if fn is None:
        raise SystemExit(f"Stage {args.stage} is not implemented")
    fn()


if __name__ == "__main__":
    main()
