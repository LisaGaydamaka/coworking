#!/usr/bin/env python3
"""
Pooled week-0 eNRI model with Grip added as the 31st weighted feature.

Grip mapping is fixed before fitting:
  week 0  -> Grip_0
  week 16 -> Grip_16
  week 24 -> Grip_22

CFI is intentionally not added.  All other preprocessing, normalization,
constraints and model logic are inherited unchanged from solve_all0mean.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_PARENT = Path(__file__).resolve().parent / "solve_all0mean.py"
_spec = importlib.util.spec_from_file_location("enri_all0mean_grip_parent", _PARENT)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot import pooled model from {_PARENT}")
_parent = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_parent)

# The inherited functions from solve.py keep their globals in _parent._base.
# Patch both namespaces before exposing the public model API.
_GRIP_MAP = {0: "Grip_0", 16: "Grip_16", 24: "Grip_22"}
for _mod in (_parent, _parent._base):
    _fc = dict(_mod.FEATURE_COLUMNS)
    _fc["Grip"] = dict(_GRIP_MAP)
    _mod.FEATURE_COLUMNS = _fc

    _mf = list(_mod.MODEL_FEATURES)
    if "Grip" not in _mf:
        _mf.append("Grip")
    _mod.MODEL_FEATURES = _mf

    if hasattr(_mod, "BASE_FEATURES"):
        _bf = list(_mod.BASE_FEATURES)
        if "Grip" not in _bf:
            _bf.append("Grip")
        _mod.BASE_FEATURES = _bf

for _name in dir(_parent):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_parent, _name)

# Explicit public definitions after the copy above.
FEATURE_COLUMNS = dict(_parent.FEATURE_COLUMNS)
MODEL_FEATURES = list(_parent.MODEL_FEATURES)
BASE_FEATURES = list(_parent.BASE_FEATURES) if hasattr(_parent, "BASE_FEATURES") else list(MODEL_FEATURES)
GRIP_WEEK_MAPPING = dict(_GRIP_MAP)
GRIP_SOURCE_WEEK_FOR_MODEL_WEEK_24 = 22
NORMALIZATION_MODE = _parent.NORMALIZATION_MODE

# Keep the underlying original module synchronized for inherited functions.
_base = _parent._base
_base.FEATURE_COLUMNS = FEATURE_COLUMNS
_base.MODEL_FEATURES = MODEL_FEATURES
if hasattr(_base, "BASE_FEATURES"):
    _base.BASE_FEATURES = BASE_FEATURES

assert len(MODEL_FEATURES) == 31, f"Expected 31 weighted features, got {len(MODEL_FEATURES)}"
assert MODEL_FEATURES[-1] == "Grip"
