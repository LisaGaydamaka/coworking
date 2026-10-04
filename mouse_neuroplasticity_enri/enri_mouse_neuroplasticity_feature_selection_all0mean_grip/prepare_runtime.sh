#!/usr/bin/env bash
set -euo pipefail

HERE="$(pwd)"
SRC="../enri_mouse_neuroplasticity_feature_selection_all0mean"
BASE_RESULTS="../enri_mouse_neuroplasticity_pooled_grip/results/model.json"

if [[ ! -f "$BASE_RESULTS" ]]; then
  echo "Missing completed base Grip model: $BASE_RESULTS" >&2
  exit 2
fi

# Reuse the exact frozen feature-selection implementation, but execute it in
# this independent project against the 31-feature Grip base model. No previous
# numerical stage outputs are copied.
cp "$SRC"/stage_*.py "$HERE"/
sed -i 's/solve_all0mean\.py/solve_all0mean_grip.py/g' stage_*.py

python - <<'PY'
import json, re
from pathlib import Path

model_path = Path('../enri_mouse_neuroplasticity_pooled_grip/results/model.json')
model = json.loads(model_path.read_text(encoding='utf-8'))
expected_p = len(model['features'])
if expected_p != 31 or model['features'][-1] != 'Grip':
    raise RuntimeError(f'Unexpected Grip model definition: p={expected_p}, last={model["features"][-1]}')
if model['feature_columns']['Grip'] != {'0': 'Grip_0', '16': 'Grip_16', '24': 'Grip_22'}:
    raise RuntimeError('Grip week mapping in model.json is not the frozen 0/16/22->24 mapping')

# Hyperparameters are read from the freshly rerun base model, not inherited
# from the previous 30-feature experiment.
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

# The old Stage-A main() had a safety assertion tied to p=30. Make only that
# dimensionality guard dynamic; the correlation algorithm itself is unchanged.
p = Path('stage_a.py')
s = p.read_text(encoding='utf-8')
old = '''    if len(features) != 30:\n        raise RuntimeError(f"Expected 30 MODEL_FEATURES, got {len(features)}")\n'''
new = '''    if len(features) != len(base.MODEL_FEATURES):\n        raise RuntimeError(\n            f"MODEL_FEATURES dimension mismatch: got {len(features)}, "\n            f"expected {len(base.MODEL_FEATURES)}"\n        )\n'''
if old not in s:
    raise RuntimeError('Stage-A p=30 guard not found')
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')

print('Configured Grip feature selection:', {
    'features': expected_p,
    'grip_mapping': model['feature_columns']['Grip'],
    **vals,
})
PY

rm -rf stage_0 stage_a stage_b stage_c stage_d stage_e stage_f stage_g \
       stage_h stage_h_manifest stage_h_worker_output stage_h_worker_results \
       stage_h_production stage_k
