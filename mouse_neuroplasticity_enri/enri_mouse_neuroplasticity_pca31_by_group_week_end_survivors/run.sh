#!/usr/bin/env bash
set -euo pipefail
pip install numpy==1.26.4 pandas==2.2.3 scikit-learn==1.5.2
rm -rf results && mkdir -p results
python run_pca.py
