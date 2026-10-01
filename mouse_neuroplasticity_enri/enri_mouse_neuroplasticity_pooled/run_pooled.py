#!/usr/bin/env python3
"""Run the original eNRI stages with pooled week-0 mouse-mean normalization."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE_DIR = HERE.parent / "enri_mouse_neuroplasticity"
WRAPPER = BASE_DIR / "solve_all0mean.py"

# The original solver writes paths relative to its own ROOT, so keep the
# working results directory inside BASE_DIR. run.sh copies the completed
# package into this standalone experiment directory before commit.
RESULTS = BASE_DIR / "results_pooled"

spec = importlib.util.spec_from_file_location("enri_pooled_base", WRAPPER)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot import {WRAPPER}")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

RESULTS.mkdir(parents=True, exist_ok=True)
m.RESULTS_DIR = RESULTS
m._base.RESULTS_DIR = RESULTS


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
