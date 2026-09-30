#!/usr/bin/env bash
set -euo pipefail

pip install -r ../enri_mouse_neuroplasticity/requirements.txt
NESTED_OUTER_TARGET=1 NESTED_INNER_TARGET=3 NESTED_STABILITY_TARGET=10 python stage_h.py
