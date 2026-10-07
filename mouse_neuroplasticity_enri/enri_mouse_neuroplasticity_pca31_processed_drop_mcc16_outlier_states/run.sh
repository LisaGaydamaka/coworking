#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
pip install -r ../enri_mouse_neuroplasticity/requirements.txt
pip install matplotlib==3.10.7
rm -rf results
mkdir -p results
python run_pca.py
