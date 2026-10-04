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

# Hyperparameters come from the newly rerun 31-feature Stage 6/7 model.
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

# Dimension-only safety assertions from the original p=30 implementation are
# adapted to the configured model. No objective, threshold, ranking,
# resampling or stopping rule is changed.
patches = {
    'stage_a.py': [(
        '''    if len(features) != 30:\n        raise RuntimeError(f"Expected 30 MODEL_FEATURES, got {len(features)}")\n''',
        '''    if len(features) != len(base.MODEL_FEATURES):\n        raise RuntimeError(\n            f"MODEL_FEATURES dimension mismatch: got {len(features)}, "\n            f"expected {len(base.MODEL_FEATURES)}"\n        )\n'''
    )],
    'stage_d.py': [(
        '''    if len(feature_set_blocks) != 30:\n        raise RuntimeError(f"Expected 30 features, got {len(feature_set_blocks)}.")\n''',
        '''    # Feature-set equality across Stage A/C is checked immediately above.\n    # The historical p=30 cardinality guard is intentionally omitted because\n    # this experiment has 31 configured weighted features.\n'''
    )],
}
for filename, replacements in patches.items():
    p = Path(filename)
    s = p.read_text(encoding='utf-8')
    for old, new in replacements:
        if old not in s:
            raise RuntimeError(f'{filename}: expected p=30 guard not found')
        s = s.replace(old, new)
    p.write_text(s, encoding='utf-8')

# Audit only feature-dimension guards. Constants such as 30 outer nested
# validation splits are part of the frozen design and must remain unchanged.
suspicious = []
for p in sorted(Path('.').glob('stage_*.py')):
    for lineno, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        low = line.lower()
        feature_context = ('feature' in low or 'model_features' in low)
        hardcoded_30 = bool(re.search(r'len\([^\n]+\)\s*(?:==|!=)\s*30', line))
        expected_30 = ('Expected 30 features' in line or 'Expected 30 MODEL_FEATURES' in line)
        if feature_context and (hardcoded_30 or expected_30):
            suspicious.append(f'{p}:{lineno}: {line.strip()}')
if suspicious:
    raise RuntimeError('Unpatched p=30 feature-dimension assumptions:\n' + '\n'.join(suspicious))

print('Configured Grip feature selection:', {
    'features': expected_p,
    'grip_mapping': model['feature_columns']['Grip'],
    **vals,
})
PY

rm -rf stage_0 stage_a stage_b stage_c stage_d stage_e stage_f stage_g \
       stage_h stage_h_manifest stage_h_worker_output stage_h_worker_results \
       stage_h_production stage_k
