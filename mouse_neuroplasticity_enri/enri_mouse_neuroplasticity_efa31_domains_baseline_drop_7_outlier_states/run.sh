#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

pip install factor_analyzer==0.5.1 matplotlib==3.10.7
rm -rf results
mkdir -p results
python run_efa.py
