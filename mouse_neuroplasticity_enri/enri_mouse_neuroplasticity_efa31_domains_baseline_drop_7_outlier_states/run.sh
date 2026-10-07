#!/usr/bin/env bash
set -euo pipefail

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

pip install numpy==1.26.4 scipy==1.13.1 pandas==2.2.3 scikit-learn==1.5.2 factor_analyzer==0.5.1 matplotlib==3.10.7
rm -rf results
mkdir -p results
python run_efa.py
