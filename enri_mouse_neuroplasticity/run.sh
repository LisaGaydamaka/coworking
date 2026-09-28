#!/usr/bin/env bash
set -euo pipefail
pip install -r requirements.txt
source .run
python solve.py --stage "$STAGE"
