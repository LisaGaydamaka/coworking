#!/usr/bin/env python3
"""Run the full pooled-week0 eNRI experiment with Grip as feature 31."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parent / "enri_mouse_neuroplasticity"
WRAPPER = BASE_DIR / "solve_all0mean_grip.py"
RESULTS = BASE_DIR / "results_pooled_grip"

spec = importlib.util.spec_from_file_location("enri_pooled_grip_base", WRAPPER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot import {WRAPPER}")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RESULTS.mkdir(parents=True, exist_ok=True)
m.RESULTS_DIR = RESULTS
m._base.RESULTS_DIR = RESULTS

# Reporting stages expect explicit group/week metadata in state dictionaries.
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


# Preserve the original QP and change only the baseline normalization check.
_patch_function(
    m._base.solve_qp_smoke,
    [(
'''    # PBS^0 normalization should be exactly one up to floating-point noise.\n    pbs0_normalization_error = abs(group_means["PBS^0"] - 1.0)\n''',
'''    # Pooled week-0 normalization should be exactly one.\n    total_n0 = sum(int(states[f"{g}^0"]["N"]) for g in STATE_GROUPS)\n    pooled0_mean = sum(\n        int(states[f"{g}^0"]["N"]) * group_means[f"{g}^0"]\n        for g in STATE_GROUPS\n    ) / float(total_n0)\n    pbs0_normalization_error = abs(pooled0_mean - 1.0)\n'''),
    (
'''            f"PBS^0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."\n''',
'''            f"Pooled week-0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."\n''')
    ],
    "solve_qp_smoke",
)

_patch_function(
    m._base.validate_stage7_outputs,
    [(
'''    pbs0 = enri_df[\n        enri_df["group"].eq("PBS") & enri_df["week"].eq(0)\n    ]["eNRI"].astype(float)\n    pbs0_mean = float(pbs0.mean())\n    if abs(pbs0_mean - 1.0) > QP_TOLERANCE:\n        errors.append(f"PBS^0 mean eNRI={pbs0_mean}, expected 1.")\n''',
'''    pbs0_mean = float(\n        enri_df[enri_df["week"].eq(0)]["eNRI"].astype(float).mean()\n    )\n    if abs(pbs0_mean - 1.0) > QP_TOLERANCE:\n        errors.append(f"Pooled week-0 mean eNRI={pbs0_mean}, expected 1.")\n''')
    ],
    "validate_stage7_outputs",
)

_patch_function(
    m._base.run_stage7,
    [(
'''        "Direct mean from final enri.csv for PBS week 0.",\n''',
'''        "Direct mean from final enri.csv over all mice at week 0.",\n'''),
    (
'''        feature="PBS^0",\n''',
'''        feature="week0_pooled",\n''')
    ],
    "run_stage7",
)

# Stage 9: keep all 25 checks, but update normalization and feature-count checks.
_patch_function(
    m._base.run_stage9,
    [(
'''    # 9. PBS0 normalization.\n    pbs0_mean = float(\n        enri_df[enri_df["group"].eq("PBS") & enri_df["week"].eq(0)]["eNRI"].mean()\n    )\n    check(\n        9, "pbs0_normalization",\n        abs(pbs0_mean - 1.0) <= QP_TOLERANCE,\n        f"Mean PBS^0 eNRI={pbs0_mean:.12g}.",\n        f"PBS^0 normalization failed: {pbs0_mean:.12g}.",\n        value=pbs0_mean,\n    )\n''',
'''    # 9. Pooled week-0 normalization.\n    pbs0_mean = float(enri_df[enri_df["week"].eq(0)]["eNRI"].mean())\n    check(\n        9, "pbs0_normalization",\n        abs(pbs0_mean - 1.0) <= QP_TOLERANCE,\n        f"Mean pooled week-0 eNRI={pbs0_mean:.12g}.",\n        f"Pooled week-0 normalization failed: {pbs0_mean:.12g}.",\n        value=pbs0_mean,\n    )\n'''),
    (
'''        len(weights_df) == 30\n        and weights_df["feature"].astype(str).tolist() == list(MODEL_FEATURES)\n''',
'''        len(weights_df) == len(MODEL_FEATURES)\n        and weights_df["feature"].astype(str).tolist() == list(MODEL_FEATURES)\n'''),
    (
'''        5, "thirty_weights",\n        feature_match,\n        "weights.csv contains exactly the 30 MODEL_FEATURES in canonical order.",\n''',
'''        5, "model_feature_weights",\n        feature_match,\n        f"weights.csv contains exactly the {len(MODEL_FEATURES)} MODEL_FEATURES in canonical order.",\n'''),
    (
'''        len(weight_values) == 30 and np.isfinite(weight_values).all(),\n        "All 30 final weights are finite.",\n''',
'''        len(weight_values) == len(MODEL_FEATURES) and np.isfinite(weight_values).all(),\n        f"All {len(MODEL_FEATURES)} final weights are finite.",\n''')
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
