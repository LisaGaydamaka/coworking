#!/usr/bin/env python3
"""Run original eNRI stages with pooled week-0 mouse-mean normalization."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parent / "enri_mouse_neuroplasticity"
WRAPPER = BASE_DIR / "solve_all0mean.py"
RESULTS = BASE_DIR / "results_pooled"

spec = importlib.util.spec_from_file_location("enri_pooled_base", WRAPPER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot import {WRAPPER}")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RESULTS.mkdir(parents=True, exist_ok=True)
m.RESULTS_DIR = RESULTS
m._base.RESULTS_DIR = RESULTS


def _patch_function(fn, replacements, name):
    src = inspect.getsource(fn)
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f"{name}: patch target not found: {old[:80]!r}")
        src = src.replace(old, new)
    exec(src, m._base.__dict__)
    patched = m._base.__dict__[name]
    setattr(m, name, patched)
    return patched


# Stage 5 / all QP fits: keep the original QP objective and constraints.
# Only change the normalization validation diagnostic from PBS^0 to the
# mouse-count-weighted mean of all four week-0 group states.
_patch_function(
    m._base.solve_qp_smoke,
    [(
'''    # PBS^0 normalization should be exactly one up to floating-point noise.
    pbs0_normalization_error = abs(group_means["PBS^0"] - 1.0)
''',
'''    # Pooled week-0 normalization should be exactly one.
    total_n0 = sum(int(states[f"{g}^0"]["N"]) for g in STATE_GROUPS)
    pooled0_mean = sum(
        int(states[f"{g}^0"]["N"]) * group_means[f"{g}^0"]
        for g in STATE_GROUPS
    ) / float(total_n0)
    pbs0_normalization_error = abs(pooled0_mean - 1.0)
'''),
    (
'''            f"PBS^0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."
''',
'''            f"Pooled week-0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."
''')
    ],
    "solve_qp_smoke",
)

# Stage 7: validate the direct arithmetic mean over all week-0 mice.
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

# Stage 7 diagnostics: same check name is retained for compatibility, but the
# displayed definition is corrected to the pooled baseline.
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

# Stage 9: preserve all 25 final checks and change only check 9.
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
