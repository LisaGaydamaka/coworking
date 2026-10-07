#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

pip install -r ../enri_mouse_neuroplasticity/requirements.txt

echo "=== Base model: re-select QP hyperparameters under 6 longitudinal constraints ==="
rm -rf base_results
python run_longitudinal.py --stage 6
python run_longitudinal.py --stage 7
python run_longitudinal.py --stage 8
python run_longitudinal.py --stage 9

echo "=== Frozen feature-selection pipeline ==="
bash prepare_runtime.sh
python stage_0.py
python stage_a.py
python stage_b.py
python stage_c.py
python stage_d.py
python stage_e.py
python stage_f.py
python stage_g.py

echo "=== Production nested validation: 30 outer x 20 inner x 100 stability ==="
rm -rf stage_h_manifest stage_h_worker_output stage_h_production
python stage_h_prepare.py \
  --outer-target 30 \
  --output stage_h_manifest/outer_manifest.json

seq 0 29 | xargs -P 6 -I{} bash -c '
  set -euo pipefail
  echo "STAGE_H_WORKER outer={}"
  python stage_h_worker.py \
    --outer-index {} \
    --manifest stage_h_manifest/outer_manifest.json \
    --output-dir stage_h_worker_output
'

python stage_h_aggregate.py \
  --manifest stage_h_manifest/outer_manifest.json \
  --input-dir stage_h_worker_output \
  --output-dir stage_h_production \
  --expected-outer 30

echo "=== Pre-specified Stage K stopping rule ==="
python stage_k.py

echo "=== Compact experiment summary ==="
python summarize_results.py
