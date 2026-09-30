#!/usr/bin/env bash
set -euo pipefail

pip install -r ../enri_mouse_neuroplasticity/requirements.txt
python stage_a.py
python stage_b.py
python stage_c.py
