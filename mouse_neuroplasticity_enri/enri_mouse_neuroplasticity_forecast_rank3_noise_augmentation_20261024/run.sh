#!/usr/bin/env bash
set -euo pipefail
python -m pip install -q --disable-pip-version-check 'numpy==1.26.4' 'pandas==2.2.3' 'scipy==1.13.1' 'scikit-learn==1.5.2' 'matplotlib==3.9.2' 'python-docx==1.1.2'
python run_forecasts.py
