"""Actual Python + OMNeT++ sweep. No protocol changes to either uploaded source."""
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "4_random_access_my_parameters.py"
EXECUTABLE = ROOT / "build" / "ra_compare"
SYMBOLS = int(os.environ.get("COMPARISON_SYMBOLS", "300000"))
DS = [110, 150, 190, 230, 270, 310, 350, 390, 500]
SEED = 0

assert SOURCE.is_file(), SOURCE
assert EXECUTABLE.is_file(), EXECUTABLE
(ROOT / "results").mkdir(exist_ok=True)
rows = []

def read_scalar(path, metric):
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "scalar" and parts[2] == metric:
            return float(parts[3])
    raise RuntimeError(f"Scalar {metric} missing in {path}")

for d in DS:
    print(f"Running d={d}, symbols={SYMBOLS}, seed={SEED}", flush=True)
    out = subprocess.run(
        [sys.executable, str(SOURCE), "--d", str(d), "--seed", str(SEED), "--symbols", str(SYMBOLS)],
        cwd=ROOT, text=True, capture_output=True, check=True)
    (ROOT / "results" / f"python_d{d}.log").write_text(out.stdout)
    match = re.search(r"Средняя задержка, символов:\s*([\d.]+)", out.stdout)
    if not match:
        raise RuntimeError(f"Python mean delay missing at d={d}\n{out.stdout}")
    py_delay = float(match.group(1))
    py_delivered = int(re.search(r"Доставлено уникальных пакетов:\s*(\d+)", out.stdout).group(1))

    ini = ROOT / "results" / f"omnet_d{d}.ini"
    ini.write_text(f"""[General]
network = DectRandomAccess
simtime-resolution = ps
seed-set = {SEED}
*.model.ptCount = 2
*.model.generationIntervalSymbols = {d}
*.model.cMin = 5
*.model.cMax = 40
*.model.resetBackoffAfterNoAck = false
*.model.lbtSymbols = 2
*.model.dataSymbols = 10
*.model.procSymbols = 10
*.model.ackSymbols = 5
*.model.symbolTime = 41.666666667us
*.model.simulationSymbols = {SYMBOLS}
*.model.warmupSymbols = 0
**.vector-recording = false
""")
    sca = ROOT / "results" / f"omnet_d{d}.sca"
    cmd = [str(EXECUTABLE), "-u", "Cmdenv", "-n", str(ROOT / "build"),
           "-f", str(ini), f"--output-scalar-file={sca}", "--cmdenv-express-mode=true"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    (ROOT / "results" / f"omnet_d{d}.log").write_text(proc.stdout + "\n" + proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"OMNeT++ failed at d={d}: exit={proc.returncode}\n{proc.stdout[-1500:]}\n{proc.stderr[-1500:]}")
    om_delay = read_scalar(sca, "meanEndToEndDelaySymbols")
    om_delivered = int(read_scalar(sca, "measuredDeliveredPackets"))
    row = dict(d=d, symbols=SYMBOLS, seed=SEED, python_delay_symbols=py_delay,
               omnet_delay_symbols=om_delay,
               python_delay_ms=py_delay / 24, omnet_delay_ms=om_delay / 24,
               relative_difference_percent=100*(om_delay-py_delay)/py_delay,
               python_unique_delivered=py_delivered, omnet_unique_delivered=om_delivered)
    rows.append(row)
    print(f"  Python {py_delay:.4f} symbols ({py_delivered} delivered); OMNeT++ {om_delay:.4f} symbols ({om_delivered} delivered)", flush=True)

with (ROOT / "results" / "comparison.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

fig, ax = plt.subplots(figsize=(9, 5.2), dpi=160)
ax.plot([r["d"] for r in rows], [r["python_delay_ms"] for r in rows], "o-", lw=2, ms=5, label="Python (uploaded)")
ax.plot([r["d"] for r in rows], [r["omnet_delay_ms"] for r in rows], "s-", lw=2, ms=5, label="OMNeT++ (uploaded ZIP)")
ax.set_xlabel("Packet generation interval d (symbols)")
ax.set_ylabel("Mean end-to-end delay (ms)")
ax.set_title(f"DECT-2020 RA: 2 PT, Cmin=5, Cmax=40, {SYMBOLS:,} symbols, seed={SEED}")
ax.grid(alpha=.3)
ax.legend()
fig.tight_layout()
fig.savefig(ROOT / "results" / "mean_delay_comparison.png", bbox_inches="tight")
plt.close(fig)
print("Saved results/comparison.csv and results/mean_delay_comparison.png", flush=True)
