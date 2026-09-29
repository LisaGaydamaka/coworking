#!/usr/bin/env bash
set -euo pipefail
python -m pip install -r ../enri_mouse_neuroplasticity/requirements.txt
python stage7_finegrid.py
