#!/usr/bin/env bash
set -euo pipefail

pip install -r ../enri_mouse_neuroplasticity/requirements.txt
python stage_0.py
python stage_a.py
python stage_b.py
python stage_c.py
python stage_d.py
python stage_e.py
python stage_f.py
python stage_g.py
