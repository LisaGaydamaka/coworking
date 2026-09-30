#!/usr/bin/env python3
"""
Prepare a deterministic manifest of fixed Stage-H outer splits.

This script performs only outer-split construction/validation. Nested model
selection is not involved, so the chosen outer validation sets cannot depend on
solver success or model-selection outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_SOLVE = ROOT.parent / "enri_mouse_neuroplasticity" / "solve_all0mean.py"
STAGE_H_PY = ROOT / "stage_h.py"

CODE_FILES = [
    BASE_SOLVE,
    ROOT / "stage_a.py",
    ROOT / "stage_b.py",
    ROOT / "stage_c.py",
    ROOT / "stage_e.py",
    ROOT / "stage_f.py",
    STAGE_H_PY,
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outer-target", type=int, default=30)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "stage_h_matrix" / "outer_manifest.json",
    )
    args = parser.parse_args()

    base = load_module(BASE_SOLVE, "enri_base_prepare_h")
    stage_h = load_module(STAGE_H_PY, "enri_stage_h_prepare")

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    mouse_df = (
        source[["mouse_id", "group"]]
        .drop_duplicates()
        .sort_values("mouse_id")
        .reset_index(drop=True)
    )

    accepted = []
    rejected = []
    for candidate_index in range(stage_h.MAX_OUTER_CANDIDATES):
        if len(accepted) >= args.outer_target:
            break

        seed = stage_h.OUTER_SEED_START + candidate_index
        train_ids, val_ids = stage_h.stratified_split(
            mouse_df, stage_h.OUTER_TRAIN_FRACTION, seed
        )

        quick_ok, quick_stats = stage_h.quick_state_count_precheck(
            long_raw,
            train_ids,
            val_ids,
            required_min_train_o=stage_h.OUTER_MIN_TRAIN_O,
            required_min_val_o=stage_h.OUTER_MIN_VAL_O,
        )
        if not quick_ok:
            rejected.append({
                "candidate_index": int(candidate_index),
                "seed": int(seed),
                "phase": "cheap_state_count_precheck",
                **quick_stats,
            })
            continue

        split, reject = stage_h.prepare_full_feature_split(
            base,
            long_raw,
            train_ids,
            val_ids,
            seed=seed,
            split_index=len(accepted),
            required_min_train_o=stage_h.OUTER_MIN_TRAIN_O,
            required_min_val_o=stage_h.OUTER_MIN_VAL_O,
        )
        if split is None:
            rejected.append({
                "candidate_index": int(candidate_index),
                "seed": int(seed),
                "phase": "full_outer_precheck",
                **reject,
            })
            continue

        accepted.append({
            "outer_index": int(len(accepted)),
            "candidate_index": int(candidate_index),
            "seed": int(seed),
            "train_ids": [str(x) for x in train_ids],
            "validation_ids": [str(x) for x in val_ids],
            "train_n": int(len(train_ids)),
            "validation_n": int(len(val_ids)),
            "min_train_O": int(split["min_train_O"]),
            "min_validation_O": int(split["min_val_O"]),
        })
        print(
            f"STAGE_H_PREPARE outer={len(accepted)}/{args.outer_target} "
            f"seed={seed} candidate_index={candidate_index}",
            flush=True,
        )

    if len(accepted) != args.outer_target:
        raise RuntimeError(
            f"Prepared only {len(accepted)}/{args.outer_target} valid outer splits."
        )

    code_hashes = {
        str(path.relative_to(ROOT.parent.parent)): sha256_file(path)
        for path in CODE_FILES
    }

    manifest_core = {
        "schema_version": 1,
        "outer_target": int(args.outer_target),
        "outer_train_fraction": float(stage_h.OUTER_TRAIN_FRACTION),
        "outer_seed_start": int(stage_h.OUTER_SEED_START),
        "outer_min_train_O": int(stage_h.OUTER_MIN_TRAIN_O),
        "outer_min_validation_O": int(stage_h.OUTER_MIN_VAL_O),
        "inner_target": int(stage_h.INNER_TARGET),
        "inner_min_train_O": int(stage_h.INNER_MIN_TRAIN_O),
        "inner_min_validation_O": int(stage_h.INNER_MIN_VAL_O),
        "stability_target": int(stage_h.STABILITY_TARGET),
        "mouse_count": int(len(mouse_df)),
        "code_hashes": code_hashes,
        "splits": accepted,
        "rejected_outer_candidates_before_target": rejected,
    }
    manifest_hash = hashlib.sha256(
        json.dumps(
            manifest_core,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    manifest = {
        **manifest_core,
        "manifest_hash": manifest_hash,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE_H_MANIFEST="
        + json.dumps(
            {
                "outer_target": args.outer_target,
                "manifest_hash": manifest_hash,
                "output": str(args.output),
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
