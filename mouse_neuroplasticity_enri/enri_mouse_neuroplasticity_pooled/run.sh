#!/usr/bin/env bash
set -euo pipefail
pip install -r ../enri_mouse_neuroplasticity/requirements.txt
python run_pooled.py --stage 6
python run_pooled.py --stage 7
python run_pooled.py --stage 8
python run_pooled.py --stage 9
