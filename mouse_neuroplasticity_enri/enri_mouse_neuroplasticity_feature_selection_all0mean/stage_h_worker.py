#!/usr/bin/env python3
"""
Run exactly one fixed Stage-H outer split from a prepared manifest.

A worker never substitutes another seed if nested selection fails. Failure of a
fixed outer split is a computation failure that must be corrected/retried for
the same outer_index.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


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


def current_code_hashes():
    return {
        str(path.relative_to(ROOT.parent.parent)): sha256_file(path)
        for path in CODE_FILES
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outer-index", type=int, required=True)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "stage_h_manifest" / "outer_manifest.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "stage_h_worker_output",
    )
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    outer_index = int(args.outer_index)
    splits = manifest["splits"]
    if outer_index < 0 or outer_index >= len(splits):
        raise ValueError(
            f"outer_index={outer_index} outside manifest range 0..{len(splits)-1}"
        )

    actual_hashes = current_code_hashes()
    if actual_hashes != manifest.get("code_hashes"):
        mismatches = {
            key: {
                "manifest": manifest.get("code_hashes", {}).get(key),
                "current": actual_hashes.get(key),
            }
            for key in sorted(set(actual_hashes) | set(manifest.get("code_hashes", {})))
            if actual_hashes.get(key) != manifest.get("code_hashes", {}).get(key)
        }
        raise RuntimeError(
            "Worker code does not match outer manifest: "
            + json.dumps(mismatches, sort_keys=True)
        )

    base = load_module(BASE_SOLVE, f"enri_base_worker_{outer_index}")
    stage_a = load_module(ROOT / "stage_a.py", f"enri_stage_a_worker_{outer_index}")
    sparse = load_module(ROOT / "stage_b.py", f"enri_stage_b_worker_{outer_index}")
    stage_c = load_module(ROOT / "stage_c.py", f"enri_stage_c_worker_{outer_index}")
    stage_e = load_module(ROOT / "stage_e.py", f"enri_stage_e_worker_{outer_index}")
    stage_f = load_module(ROOT / "stage_f.py", f"enri_stage_f_worker_{outer_index}")
    stage_h = load_module(STAGE_H_PY, f"enri_stage_h_worker_{outer_index}")

    if int(stage_h.INNER_TARGET) != int(manifest["inner_target"]):
        raise RuntimeError(
            f"INNER_TARGET mismatch: worker={stage_h.INNER_TARGET}, "
            f"manifest={manifest['inner_target']}"
        )
    if int(stage_h.STABILITY_TARGET) != int(manifest["stability_target"]):
        raise RuntimeError(
            f"STABILITY_TARGET mismatch: worker={stage_h.STABILITY_TARGET}, "
            f"manifest={manifest['stability_target']}"
        )

    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    mouse_df = (
        source[["mouse_id", "group"]]
        .drop_duplicates()
        .sort_values("mouse_id")
        .reset_index(drop=True)
    )

    spec = splits[outer_index]
    if int(spec["outer_index"]) != outer_index:
        raise RuntimeError("Manifest outer_index ordering is inconsistent.")

    all_ids = set(mouse_df["mouse_id"].astype(str))
    train_ids = [str(x) for x in spec["train_ids"]]
    val_ids = [str(x) for x in spec["validation_ids"]]
    if set(train_ids) & set(val_ids):
        raise RuntimeError("Manifest train/validation mouse IDs overlap.")
    if set(train_ids) | set(val_ids) != all_ids:
        raise RuntimeError("Manifest train/validation IDs do not partition all mice.")

    split, reject = stage_h.prepare_full_feature_split(
        base,
        long_raw,
        train_ids,
        val_ids,
        seed=int(spec["seed"]),
        split_index=outer_index,
        required_min_train_o=stage_h.OUTER_MIN_TRAIN_O,
        required_min_val_o=stage_h.OUTER_MIN_VAL_O,
    )
    if split is None:
        raise RuntimeError(
            "Fixed outer split no longer passes preprocessing validation: "
            + json.dumps(reject, ensure_ascii=False, sort_keys=True)
        )
    split["outer_candidate_index"] = int(spec["candidate_index"])

    print(
        f"STAGE_H_WORKER_START outer={outer_index} seed={spec['seed']} "
        f"inner={stage_h.INNER_TARGET} stability={stage_h.STABILITY_TARGET}",
        flush=True,
    )

    detail, diagnostics = stage_h.run_one_outer(
        base,
        sparse,
        stage_a,
        stage_c,
        stage_e,
        stage_f,
        long_raw,
        mouse_df,
        split,
        outer_index,
    )

    payload = {
        "schema_version": 1,
        "manifest_hash": manifest["manifest_hash"],
        "outer_index": outer_index,
        "outer_seed": int(spec["seed"]),
        "detail": detail,
        "diagnostic_summary": {
            "lambda_path_rows": int(len(diagnostics["lambda_path"])),
            "stability_rows": int(len(diagnostics["stability"])),
            "feature_ablation_rows": int(len(diagnostics["feature_ablation"])),
            "block_ablation_rows": int(len(diagnostics["block_ablation"])),
            "block_compression_rows": int(len(diagnostics["block_compression"])),
            "subset_path_rows": int(len(diagnostics["subset_path"])),
        },
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / f"outer_{outer_index:02d}.json"
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE_H_WORKER_DONE="
        + json.dumps(
            {
                "outer_index": outer_index,
                "seed": int(spec["seed"]),
                "selected_k": int(detail["selected_k"]),
                "selected_features": detail["selected_features"],
                "output": str(output),
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
