#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python -m pip install numpy==1.26.4 scipy==1.13.1 pandas==2.2.3 scikit-learn==1.5.2 factor_analyzer==0.5.1 openpyxl==3.1.5 cvxpy==1.6.7
mkdir -p results
python validate.py
