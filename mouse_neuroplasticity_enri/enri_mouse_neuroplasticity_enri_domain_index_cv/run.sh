#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python -m pip install numpy==1.26.4 pandas==2.2.3 scipy==1.13.1 scikit-learn==1.5.2 factor_analyzer==0.5.1 cvxpy==1.6.5 osqp==1.0.4 clarabel==0.11.1 openpyxl==3.1.5
mkdir -p results
if [ ! -f results/paired_grouped_cv_metrics.csv ] || [ ! -f results/fullfit_metrics.csv ]; then
  python run_index_cv.py 2>&1 | tee results/run_stdout.log
fi
python audit_null_model.py 2>&1 | tee results/null_model_stdout.log
