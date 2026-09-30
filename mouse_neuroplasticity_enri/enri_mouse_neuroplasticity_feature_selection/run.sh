#!/usr/bin/env bash
set -euo pipefail

pip install -r ../enri_mouse_neuroplasticity/requirements.txt

export NESTED_OUTER_TARGET=2
export NESTED_INNER_TARGET=3
export NESTED_STABILITY_TARGET=10
export NESTED_MAX_OUTER_CANDIDATES=10
export NESTED_MAX_INNER_CANDIDATES=50
export NESTED_MAX_STABILITY_CANDIDATES=100

rm -rf stage_h_manifest_smoke stage_h_worker_results_smoke stage_h_production_smoke

python stage_h_prepare.py \
  --outer-target 2 \
  --output stage_h_manifest_smoke/outer_manifest.json

python stage_h_worker.py \
  --outer-index 0 \
  --manifest stage_h_manifest_smoke/outer_manifest.json \
  --output-dir stage_h_worker_results_smoke

python stage_h_worker.py \
  --outer-index 1 \
  --manifest stage_h_manifest_smoke/outer_manifest.json \
  --output-dir stage_h_worker_results_smoke

python stage_h_aggregate.py \
  --manifest stage_h_manifest_smoke/outer_manifest.json \
  --input-dir stage_h_worker_results_smoke \
  --output-dir stage_h_production_smoke \
  --expected-outer 2
