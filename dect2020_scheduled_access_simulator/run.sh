#!/usr/bin/env bash
set -euo pipefail
python -m pip install -q -r requirements.txt
python compare.py
