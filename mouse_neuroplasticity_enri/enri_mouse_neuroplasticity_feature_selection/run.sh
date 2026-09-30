#!/usr/bin/env bash
set -euo pipefail

pip install -r ../enri_mouse_neuroplasticity/requirements.txt
NESTED_OUTER_TARGET=1 NESTED_INNER_TARGET=3 NESTED_STABILITY_TARGET=10 NESTED_MAX_OUTER_CANDIDATES=3 NESTED_MAX_INNER_CANDIDATES=50 NESTED_MAX_STABILITY_CANDIDATES=100 python stage_h.py
