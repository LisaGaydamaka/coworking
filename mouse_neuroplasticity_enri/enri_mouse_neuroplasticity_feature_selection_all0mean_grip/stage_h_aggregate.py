#!/usr/bin/env python3
"""
Aggregate independently computed fixed Stage-H outer workers.

This script never performs model selection. It only validates the worker
outputs against the manifest and summarizes the already-computed outer results.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE_SOLVE = ROOT.parent / "enri_mouse_neuroplasticity" / "solve_all0mean_grip.py"
STAGE_H_PY = ROOT / "stage_h.py"
FULLDATA_BLOCKS = ROOT / "stage_a" / "correlation_blocks.csv"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "stage_h_manifest" / "outer_manifest.json",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=ROOT / "stage_h_worker_results",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "stage_h_production",
    )
    parser.add_argument("--expected-outer", type=int, default=None)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    expected_outer = (
        int(args.expected_outer)
        if args.expected_outer is not None
        else int(manifest["outer_target"])
    )
    if expected_outer != int(manifest["outer_target"]):
        raise RuntimeError(
            f"expected_outer={expected_outer} differs from manifest outer_target="
            f"{manifest['outer_target']}"
        )

    files = sorted(args.input_dir.glob("outer_*.json"))
    if len(files) != expected_outer:
        raise RuntimeError(
            f"Expected {expected_outer} worker files, found {len(files)} in "
            f"{args.input_dir}"
        )

    payloads = []
    seen_indices = set()
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("manifest_hash") != manifest["manifest_hash"]:
            raise RuntimeError(
                f"{path.name}: manifest hash mismatch."
            )
        idx = int(payload["outer_index"])
        if idx in seen_indices:
            raise RuntimeError(f"Duplicate outer_index={idx}.")
        seen_indices.add(idx)

        spec = manifest["splits"][idx]
        if int(payload["outer_seed"]) != int(spec["seed"]):
            raise RuntimeError(
                f"outer {idx}: worker seed {payload['outer_seed']} != "
                f"manifest seed {spec['seed']}"
            )
        detail = payload["detail"]
        if int(detail["outer_index"]) != idx:
            raise RuntimeError(f"outer {idx}: detail outer_index mismatch.")
        if int(detail["outer_seed"]) != int(spec["seed"]):
            raise RuntimeError(f"outer {idx}: detail seed mismatch.")
        payloads.append(payload)

    expected_indices = set(range(expected_outer))
    if seen_indices != expected_indices:
        raise RuntimeError(
            f"Worker index set mismatch: got={sorted(seen_indices)}, "
            f"expected={sorted(expected_indices)}"
        )

    payloads.sort(key=lambda x: int(x["outer_index"]))
    details = [p["detail"] for p in payloads]

    base = load_module(BASE_SOLVE, "enri_base_aggregate_h")
    stage_h = load_module(STAGE_H_PY, "enri_stage_h_aggregate")

    full_data_blocks = (
        pd.read_csv(FULLDATA_BLOCKS)
        if FULLDATA_BLOCKS.exists()
        else None
    )
    agg = stage_h.aggregate_results(base, details, full_data_blocks)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    agg["outer"].to_csv(
        args.output_dir / "nested_outer_results.csv", index=False
    )
    agg["feature_frequency"].to_csv(
        args.output_dir / "nested_feature_frequency.csv", index=False
    )
    agg["subset_frequency"].to_csv(
        args.output_dir / "nested_subset_frequency.csv", index=False
    )
    agg["k_distribution"].to_csv(
        args.output_dir / "nested_k_distribution.csv", index=False
    )
    agg["lambda_distribution"].to_csv(
        args.output_dir / "nested_lambda1_distribution.csv", index=False
    )
    agg["block_signature_frequency"].to_csv(
        args.output_dir / "nested_block_signature_frequency.csv", index=False
    )
    if not agg["reference_block_frequency"].empty:
        agg["reference_block_frequency"].to_csv(
            args.output_dir / "nested_reference_block_frequency.csv", index=False
        )

    (args.output_dir / "nested_outer_details.json").write_text(
        json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(args.manifest, args.output_dir / "outer_manifest.json")

    feature_top = agg["feature_frequency"].head(15)
    subset_top = agg["subset_frequency"].head(10)

    production = (
        expected_outer == stage_h.PRODUCTION_OUTER
        and int(manifest["inner_target"]) == stage_h.PRODUCTION_INNER
        and int(manifest["stability_target"]) == stage_h.PRODUCTION_STABILITY
    )

    summary = {
        "stage": "H",
        "status": "READY" if production else "SMOKE_READY",
        "production_configuration": bool(production),
        "execution_architecture": {
            "fixed_outer_manifest": True,
            "one_worker_per_outer_split": True,
            "outer_seed_substitution_on_worker_failure": False,
            "worker_outputs_aggregated_only_after_all_success": True,
            "manifest_hash": manifest["manifest_hash"],
        },
        "configuration": {
            "outer_target": expected_outer,
            "outer_train_fraction": float(manifest["outer_train_fraction"]),
            "outer_min_train_O": int(manifest["outer_min_train_O"]),
            "outer_min_validation_O": int(manifest["outer_min_validation_O"]),
            "inner_target": int(manifest["inner_target"]),
            "inner_min_train_O": int(manifest["inner_min_train_O"]),
            "inner_min_validation_O": int(manifest["inner_min_validation_O"]),
            "stability_target": int(manifest["stability_target"]),
        },
        "leakage_control": {
            "outer_validation_used_for_selection": False,
            "correlations_outer_train_only": True,
            "lambda1_outer_train_inner_only": True,
            "stability_outer_train_only": True,
            "ablation_outer_train_inner_only": True,
            "subset_selection_outer_train_inner_only": True,
            "reduced_preprocessing_train_only": True,
            "outer_validation_final_evaluation_only": True,
        },
        "completed_outer_splits": expected_outer,
        "outer_metric_summary": agg["metric_summary"],
        "k_distribution": [
            {
                "k": int(row["k"]),
                "count": int(row["count"]),
                "frequency": float(row["frequency"]),
            }
            for _, row in agg["k_distribution"].iterrows()
        ],
        "lambda1_distribution": [
            {
                "lambda1_star": float(row["lambda1_star"]),
                "count": int(row["count"]),
                "frequency": float(row["frequency"]),
            }
            for _, row in agg["lambda_distribution"].iterrows()
        ],
        "top_feature_frequency": [
            {
                "feature": str(row["feature"]),
                "selected_count": int(row["selected_count"]),
                "selected_frequency": float(row["selected_frequency"]),
            }
            for _, row in feature_top.iterrows()
        ],
        "top_subset_frequency": [
            {
                "subset": str(row["subset"]),
                "count": int(row["count"]),
                "frequency": float(row["frequency"]),
                "k": int(row["k"]),
            }
            for _, row in subset_top.iterrows()
        ],
        "outputs": {
            "outer_results": "stage_h_production/nested_outer_results.csv",
            "feature_frequency": "stage_h_production/nested_feature_frequency.csv",
            "subset_frequency": "stage_h_production/nested_subset_frequency.csv",
            "k_distribution": "stage_h_production/nested_k_distribution.csv",
            "lambda1_distribution": "stage_h_production/nested_lambda1_distribution.csv",
            "block_signature_frequency": (
                "stage_h_production/nested_block_signature_frequency.csv"
            ),
            "reference_block_frequency": (
                "stage_h_production/nested_reference_block_frequency.csv"
                if not agg["reference_block_frequency"].empty
                else None
            ),
            "outer_details": "stage_h_production/nested_outer_details.json",
            "outer_manifest": "stage_h_production/outer_manifest.json",
        },
        "validation_errors": [],
    }

    (args.output_dir / "stage_h_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "STAGE_H_AGGREGATE="
        + json.dumps(summary, ensure_ascii=False, sort_keys=True),
        flush=True,
    )


if __name__ == "__main__":
    main()
