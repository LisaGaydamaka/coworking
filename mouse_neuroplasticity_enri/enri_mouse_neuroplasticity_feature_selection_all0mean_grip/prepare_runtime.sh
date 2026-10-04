#!/usr/bin/env bash
set -euo pipefail

HERE="$(pwd)"
SRC="../enri_mouse_neuroplasticity_feature_selection_all0mean"
BASE_RESULTS="../enri_mouse_neuroplasticity_pooled_grip/results/model.json"

if [[ ! -f "$BASE_RESULTS" ]]; then
  echo "Missing completed base Grip model: $BASE_RESULTS" >&2
  exit 2
fi

# Reuse the exact previously frozen feature-selection implementation, but run
# it in this independent output directory and point it at the 31-feature Grip
# base model. No prior stage outputs are copied.
cp "$SRC"/stage_*.py "$HERE"/

# All stages must import the Grip-aware pooled model.
sed -i 's/solve_all0mean\.py/solve_all0mean_grip.py/g' stage_*.py

# Base QP hyperparameters are not inherited from the previous experiment.
# They are read from the freshly completed 31-feature Stage 6/7 result.
python - <<'PY'
import json, re
from pathlib import Path

model_path = Path('../enri_mouse_neuroplasticity_pooled_grip/results/model.json')
model = json.loads(model_path.read_text(encoding='utf-8'))
vals = {
    'BETA': float(model['beta']),
    'LAMBDA2': float(model['lambda']),
    'C_SLACK': float(model['C']),
}
p = Path('stage_b.py')
s = p.read_text(encoding='utf-8')
for name, value in vals.items():
    s, n = re.subn(rf'^{name}\s*=\s*[^\n]+$', f'{name} = {value!r}', s, flags=re.M)
    if n != 1:
        raise RuntimeError(f'Expected one {name} assignment, found {n}')
p.write_text(s, encoding='utf-8')
print('Configured feature selection with', vals)
PY

# The source code is unchanged mathematically apart from the model definition;
# remove stale runtime outputs if this job is rerun.
rm -rf stage_0 stage_a stage_b stage_c stage_d stage_e stage_f stage_g \
       stage_h stage_h_manifest stage_h_worker_output stage_h_worker_results \
       stage_h_production stage_k
