#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
source=Path("../dect2020_ra_ira_omnetpp/src").resolve()
assert source.is_dir(),source
paths=sorted(p for p in source.rglob("*") if p.is_file())
assert len(paths)==10,[p.name for p in paths]
with ZipFile("src.zip","w",compression=ZIP_DEFLATED,compresslevel=9) as z:
    for p in paths:
        z.write(p,arcname=str(Path("src")/p.relative_to(source)))
with ZipFile("src.zip") as z:
    assert z.testzip() is None
    assert len(z.namelist())==10
print("Saved src.zip with",len(paths),"source files")
PY
