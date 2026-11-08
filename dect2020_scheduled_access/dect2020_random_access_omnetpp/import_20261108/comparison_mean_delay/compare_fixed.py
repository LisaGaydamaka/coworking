"""Compare untouched Python, two-fix Python, and untouched OMNeT++ (independent RNG)."""
import csv
import math
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
MODELS = {
    "Python original": ROOT / "4_random_access_my_parameters.py",
    "Python corrected": ROOT / "4_random_access_corrected.py",
}
EXEC = ROOT / "build" / "ra_compare"
SYMBOLS = int(os.environ.get("COMPARISON_SYMBOLS", "2000000"))
DS = [110, 120, 150, 190, 230, 250, 310, 390, 500]
SEEDS = [0, 1, 2]
for path in [*MODELS.values(), EXEC]:
    assert path.is_file(), path
rows = []

def scalar(path, metric):
    for line in path.read_text().splitlines():
        p = line.split()
        if len(p) >= 4 and p[0] == "scalar" and p[2] == metric:
            return float(p[3])
    raise RuntimeError(f"Missing {metric} in {path}")

def read_python(name, path, d, seed):
    p = subprocess.run([sys.executable, str(path), "--d", str(d), "--seed", str(seed),
                       "--symbols", str(SYMBOLS)], cwd=ROOT, text=True, capture_output=True)
    (RESULTS / f"fixed_{name.lower().replace(' ', '_')}_d{d}_s{seed}.log").write_text(
        p.stdout + "\n" + p.stderr)
    p.check_returncode()
    match = re.search(r"Средняя задержка, символов:\s*([\d.]+)", p.stdout)
    delivered = re.search(r"Доставлено уникальных пакетов:\s*(\d+)", p.stdout)
    if not match or not delivered:
        raise RuntimeError(f"Missing Python output for d={d}, seed={seed}: {p.stdout}")
    return float(match.group(1)), int(delivered.group(1))

def read_omnet(d, seed):
    ini = RESULTS / f"fixed_omnet_d{d}_s{seed}.ini"
    ini.write_text(f"""[General]
network = DectRandomAccess
simtime-resolution = ps
seed-set = {seed}
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
    sca = RESULTS / f"fixed_omnet_d{d}_s{seed}.sca"
    cmd = [str(EXEC), "-u", "Cmdenv", "-n", str(ROOT / "build"),
           "-f", str(ini), f"--output-scalar-file={sca}", "--cmdenv-express-mode=true"]
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    (RESULTS / f"fixed_omnet_d{d}_s{seed}.log").write_text(p.stdout + "\n" + p.stderr)
    p.check_returncode()
    return scalar(sca, "meanEndToEndDelaySymbols"), int(scalar(sca, "measuredDeliveredPackets"))

for d in DS:
    for seed in SEEDS:
        values = {}
        for name, path in MODELS.items():
            values[name] = read_python(name, path, d, seed)
        values["OMNeT++"] = read_omnet(d, seed)
        row = {
            "d": d, "seed": seed, "symbols": SYMBOLS,
            "python_original_delay_symbols": values["Python original"][0],
            "python_corrected_delay_symbols": values["Python corrected"][0],
            "omnet_delay_symbols": values["OMNeT++"][0],
            "python_original_delivered": values["Python original"][1],
            "python_corrected_delivered": values["Python corrected"][1],
            "omnet_delivered": values["OMNeT++"][1],
        }
        rows.append(row)
        print(f"d={d:>3} seed={seed}: original={row['python_original_delay_symbols']:9.3f} "
              f"corrected={row['python_corrected_delay_symbols']:9.3f} "
              f"OMNeT++={row['omnet_delay_symbols']:9.3f} symbols", flush=True)

with (RESULTS / "fixed_raw_comparison.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

columns = {
    "Python original": "python_original_delay_symbols",
    "Python corrected": "python_corrected_delay_symbols",
    "OMNeT++": "omnet_delay_symbols"
}
summary = []
for d in DS:
    group = [r for r in rows if r["d"] == d]
    out = {"d": d, "symbols": SYMBOLS, "seeds": len(SEEDS)}
    for name, field in columns.items():
        prefix = {"Python original": "python_original",
                  "Python corrected": "python_corrected", "OMNeT++": "omnet"}[name]
        arr = [r[field] for r in group]
        out[prefix + "_mean_symbols"] = statistics.mean(arr)
        out[prefix + "_sd_symbols"] = statistics.stdev(arr)
        out[prefix + "_mean_ms"] = statistics.mean(arr) / 24
    out["corrected_vs_omnet_pct"] = 100 * (
        out["python_corrected_mean_symbols"] / out["omnet_mean_symbols"] - 1)
    out["original_vs_omnet_pct"] = 100 * (
        out["python_original_mean_symbols"] / out["omnet_mean_symbols"] - 1)
    summary.append(out)

with (RESULTS / "fixed_summary_comparison.csv").open("w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=summary[0].keys())
    writer.writeheader()
    writer.writerows(summary)

x = [r["d"] for r in summary]
fig, ax = plt.subplots(figsize=(10.4, 6), dpi=180)
for label, prefix, style in [
        ("Python original", "python_original", "o--"),
        ("Python corrected (ACK/LBT + delay)", "python_corrected", "o-"),
        ("OMNeT++ (unchanged)", "omnet", "s-")]:
    y = [r[prefix + "_mean_symbols"] for r in summary]
    ax.plot(x, y, style, linewidth=2.2, markersize=5, label=label)
ax.set_title(f"DECT-2020 RA | Mean packet delay | 2 PT | {SYMBOLS:,} symbols | 3 seeds")
ax.set_xlabel("Packet generation interval d (symbols)")
ax.set_ylabel("Mean generation-to-last-delivery delay (symbols)")
ax.grid(alpha=0.27)
ax.legend(loc="upper right")
fig.tight_layout()
fig.savefig(RESULTS / "mean_delay_after_two_fixes.png")
plt.close(fig)

fig, ax = plt.subplots(figsize=(10.4, 4.8), dpi=180)
ax.axhline(0, linewidth=1, color="gray")
ax.plot(x, [r["original_vs_omnet_pct"] for r in summary], "o--",
        linewidth=2, label="Python original vs OMNeT++")
ax.plot(x, [r["corrected_vs_omnet_pct"] for r in summary], "o-",
        linewidth=2, label="Python corrected vs OMNeT++")
ax.set_title("Relative mean-delay difference | identical scenario, independent RNG")
ax.set_xlabel("Packet generation interval d (symbols)")
ax.set_ylabel("(Python / OMNeT++ - 1) × 100%")
ax.grid(alpha=.27)
ax.legend()
fig.tight_layout()
fig.savefig(RESULTS / "mean_delay_relative_difference_after_fixes.png")
plt.close(fig)
print("SAVED: fixed_raw_comparison.csv, fixed_summary_comparison.csv, "
      "mean_delay_after_two_fixes.png, mean_delay_relative_difference_after_fixes.png", flush=True)
