#!/usr/bin/env python3
"""
Independent pooled-week0 GRIP31 eNRI model with only longitudinal
directional constraints.

All historical source files are imported read-only. The only scientific
model-definition change is ORDER_PAIRS, which contains six within-group
longitudinal inequalities and no between-group directional comparison.
"""

from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

_PARENT = Path(__file__).resolve().parent.parent / "enri_mouse_neuroplasticity" / "solve_all0mean_grip.py"
_spec = importlib.util.spec_from_file_location(
    "enri_all0mean_grip_longitudinal_parent", _PARENT
)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot import historical pooled Grip model from {_PARENT}")
_parent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent)

LONGITUDINAL_ORDER_PAIRS = [
    ("PBS^0", "PBS^16"),
    ("LPS^0", "LPS^16"),
    ("run^0", "run^16"),
    ("MCC^0", "MCC^16"),
    ("PBS^16", "PBS^24"),
    ("LPS^16", "LPS^24"),
]

_base = _parent._base
for _mod in (_parent, _base):
    _mod.ORDER_PAIRS = list(LONGITUDINAL_ORDER_PAIRS)

# solve_qp_smoke intentionally contains a hard-coded model-definition guard.
# Replace only the expected order-pair set; the objective and all other
# constraints are inherited unchanged.
_src = inspect.getsource(_base.solve_qp_smoke)
_old = '''    expected_O = {
        ("PBS^16", "LPS^16"),
        ("PBS^24", "LPS^24"),
        ("run^24", "LPS^24"),
        ("MCC^24", "LPS^24"),
        ("PBS^0", "PBS^16"),
        ("LPS^0", "LPS^16"),
        ("run^0", "run^16"),
        ("MCC^0", "MCC^16"),
        ("PBS^16", "PBS^24"),
        ("LPS^16", "LPS^24"),
    }
'''
_new = '''    expected_O = {
        ("PBS^0", "PBS^16"),
        ("LPS^0", "LPS^16"),
        ("run^0", "run^16"),
        ("MCC^0", "MCC^16"),
        ("PBS^16", "PBS^24"),
        ("LPS^16", "LPS^24"),
    }
'''
if _old not in _src:
    raise RuntimeError("Historical solve_qp_smoke order-pair guard not found")
_src = _src.replace(_old, _new)

_old_norm = '''    # PBS^0 normalization should be exactly one up to floating-point noise.
    pbs0_normalization_error = abs(group_means["PBS^0"] - 1.0)
'''
_new_norm = '''    # Pooled week-0 normalization should be exactly one.
    total_n0 = sum(int(states[f"{g}^0"]["N"]) for g in STATE_GROUPS)
    pooled0_mean = sum(
        int(states[f"{g}^0"]["N"]) * group_means[f"{g}^0"]
        for g in STATE_GROUPS
    ) / float(total_n0)
    pbs0_normalization_error = abs(pooled0_mean - 1.0)
'''
if _old_norm not in _src:
    raise RuntimeError("Historical solve_qp_smoke normalization patch target not found")
_src = _src.replace(_old_norm, _new_norm)
_src = _src.replace(
    'f"PBS^0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."',
    'f"Pooled week-0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."',
)
exec(_src, _base.__dict__)
_parent.solve_qp_smoke = _base.solve_qp_smoke

for _name in dir(_parent):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_parent, _name)

ORDER_PAIRS = list(LONGITUDINAL_ORDER_PAIRS)
_base.ORDER_PAIRS = list(LONGITUDINAL_ORDER_PAIRS)
_parent.ORDER_PAIRS = list(LONGITUDINAL_ORDER_PAIRS)

assert len(MODEL_FEATURES) == 31
assert MODEL_FEATURES[-1] == "Grip"
assert set(ORDER_PAIRS) == set(LONGITUDINAL_ORDER_PAIRS)
assert len(ORDER_PAIRS) == 6
