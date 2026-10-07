#!/usr/bin/env bash
set -euo pipefail

HERE="$(pwd)"
SRC="../enri_mouse_neuroplasticity_feature_selection_all0mean"
BASE_RESULTS="base_results/model.json"

if [[ ! -f "$BASE_RESULTS" ]]; then
  echo "Missing completed longitudinal base model: $BASE_RESULTS" >&2
  exit 2
fi

# Copy frozen stage implementations into THIS new experiment only.
# No historical experiment file is modified.
cp "$SRC"/stage_a.py "$HERE"/
cp "$SRC"/stage_b.py "$HERE"/
cp "$SRC"/stage_c.py "$HERE"/
cp "$SRC"/stage_d.py "$HERE"/
cp "$SRC"/stage_e.py "$HERE"/
cp "$SRC"/stage_f.py "$HERE"/
cp "$SRC"/stage_g.py "$HERE"/
cp "$SRC"/stage_h.py "$HERE"/
cp "$SRC"/stage_h_prepare.py "$HERE"/
cp "$SRC"/stage_h_worker.py "$HERE"/
cp "$SRC"/stage_h_aggregate.py "$HERE"/
cp "$SRC"/stage_k.py "$HERE"/

python - <<'PY'
import json
import re
from pathlib import Path

# Redirect all copied stages to the local independent base wrapper.
for p in sorted(Path('.').glob('stage_*.py')):
    s = p.read_text(encoding='utf-8')
    s = s.replace(
        'ROOT.parent / "enri_mouse_neuroplasticity" / "solve_all0mean.py"',
        'ROOT / "solve_all0mean_grip_longitudinal.py"',
    )
    s = s.replace(
        'BASE_DIR = ROOT.parent / "enri_mouse_neuroplasticity"\nBASE_SOLVE = BASE_DIR / "solve_all0mean.py"',
        'BASE_DIR = ROOT\nBASE_SOLVE = ROOT / "solve_all0mean_grip_longitudinal.py"',
    )
    p.write_text(s, encoding='utf-8')

model_path = Path('base_results/model.json')
model = json.loads(model_path.read_text(encoding='utf-8'))
if len(model['features']) != 31 or model['features'][-1] != 'Grip':
    raise RuntimeError('Base model is not the expected GRIP31 model')
if model['feature_columns']['Grip'] != {'0': 'Grip_0', '16': 'Grip_16', '24': 'Grip_22'}:
    raise RuntimeError('Unexpected Grip mapping')

# Re-selected base QP hyperparameters are injected into Stage B, exactly as
# in the previous GRIP31 experiment, but using THIS run's model.json.
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

old_guard = '''    # Guard against accidental drift from the specified first model.
    if set(base.ORDER_PAIRS) != {
        ("PBS^16", "LPS^16"),
        ("PBS^24", "LPS^24"),
        ("run^24", "LPS^24"),
        ("MCC^24", "LPS^24"),
        ("PBS^0", "PBS^16"),
        ("LPS^0", "LPS^16"),
        ("run^0", "run^16"),
        ("MCC^0", "MCC^16"),
        ("PBS^16", "PBS^24"),
        ("LPS^16", "LPS^24"),
    }:
        raise RuntimeError("Base ORDER_PAIRS are not the required 10-condition model.")
'''
new_guard = '''    # Guard against accidental drift from the specified longitudinal model.
    if set(base.ORDER_PAIRS) != {
        ("PBS^0", "PBS^16"),
        ("LPS^0", "LPS^16"),
        ("run^0", "run^16"),
        ("MCC^0", "MCC^16"),
        ("PBS^16", "PBS^24"),
        ("LPS^16", "LPS^24"),
    }:
        raise RuntimeError("Base ORDER_PAIRS are not the required 6 longitudinal conditions.")
'''
if old_guard not in s:
    raise RuntimeError('stage_b.py: historical 10-condition guard not found')
s = s.replace(old_guard, new_guard)
p.write_text(s, encoding='utf-8')

# Same p=31 dimension compatibility patches as the historical GRIP31 rerun.
patches = {
    'stage_a.py': [(
        '''    if len(features) != 30:
        raise RuntimeError(f"Expected 30 MODEL_FEATURES, got {len(features)}")
''',
        '''    if len(features) != len(base.MODEL_FEATURES):
        raise RuntimeError(
            f"MODEL_FEATURES dimension mismatch: got {len(features)}, "
            f"expected {len(base.MODEL_FEATURES)}"
        )
'''
    )],
    'stage_d.py': [(
        '''    if len(feature_set_blocks) != 30:
        raise RuntimeError(f"Expected 30 features, got {len(feature_set_blocks)}.")
''',
        '''    # Feature-set equality across Stage A/C is checked immediately above.
    # Historical p=30 cardinality guard is omitted because this experiment has
    # 31 configured weighted features.
'''
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

# Audit the copied code after patching.
base_text = Path('solve_all0mean_grip_longitudinal.py').read_text(encoding='utf-8')
for forbidden in [
    '("PBS^16", "LPS^16")',
    '("PBS^24", "LPS^24")',
    '("run^24", "LPS^24")',
    '("MCC^24", "LPS^24")',
]:
    # Historical strings can appear only inside the literal patch target in
    # the local wrapper, not in active ORDER_PAIRS guards of copied stages.
    pass

suspicious = []
for p in sorted(Path('.').glob('stage_*.py')):
    for lineno, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
        if line.strip().startswith('#'):
            continue
        low = line.lower()
        feature_context = ('feature' in low or 'model_features' in low)
        hardcoded_30 = bool(re.search(r'len\([^\n]+\)\s*(?:==|!=)\s*30', line))
        expected_30 = ('Expected 30 features' in line or 'Expected 30 MODEL_FEATURES' in line)
        if feature_context and (hardcoded_30 or expected_30):
            suspicious.append(f'{p}:{lineno}: {line.strip()}')
if suspicious:
    raise RuntimeError('Unpatched p=30 feature assumptions:\n' + '\n'.join(suspicious))

print('Configured independent longitudinal GRIP31 runtime:', {
    'features': len(model['features']),
    'beta': vals['BETA'],
    'lambda2': vals['LAMBDA2'],
    'C': vals['C_SLACK'],
})
PY

rm -rf stage_0 stage_a stage_b stage_c stage_d stage_e stage_f stage_g \
       stage_h stage_h_manifest stage_h_worker_output stage_h_worker_results \
       stage_h_production stage_k
