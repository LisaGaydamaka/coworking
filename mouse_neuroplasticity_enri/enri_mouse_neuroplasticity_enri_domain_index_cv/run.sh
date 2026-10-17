#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.13.1 scikit-learn==1.5.2 factor_analyzer==0.5.1 cvxpy==1.6.5 osqp==1.0.4 clarabel==0.11.1 openpyxl==3.1.5
rm -rf results
mkdir results
python run_index_cv.py > results/run_stdout.log 2>&1
