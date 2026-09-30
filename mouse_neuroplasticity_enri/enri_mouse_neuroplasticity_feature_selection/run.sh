#!/usr/bin/env bash
set -euo pipefail

pip install -r ../enri_mouse_neuroplasticity/requirements.txt
python stage_f.py
