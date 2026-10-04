#!/usr/bin/env bash
set -euo pipefail
pip install -r ../enri_mouse_neuroplasticity/requirements.txt
rm -rf ../enri_mouse_neuroplasticity/results_pooled_grip results
python run_pooled_grip.py --stage 6
python run_pooled_grip.py --stage 7
python run_pooled_grip.py --stage 8
python run_pooled_grip.py --stage 9
cp -a ../enri_mouse_neuroplasticity/results_pooled_grip results
rm -rf ../enri_mouse_neuroplasticity/results_pooled_grip
