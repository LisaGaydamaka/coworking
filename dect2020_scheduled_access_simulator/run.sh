#!/usr/bin/env bash
set -euo pipefail
python -m pip install -q -r requirements.txt
python phase0_reference.py
python compare.py
