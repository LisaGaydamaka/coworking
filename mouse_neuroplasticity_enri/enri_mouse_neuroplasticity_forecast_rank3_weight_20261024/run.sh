#!/usr/bin/env bash
set -euo pipefail
python -m pip install --disable-pip-version-check -q 'numpy==1.26.4' 'pandas==2.2.3' 'scikit-learn==1.5.2'
python run_forecasts.py
