import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
INPUT = ROOT.parent / "dect2020_scheduled_access_omnetpp" / "ci_results" / "phase5_metrics.csv"
OUT = ROOT / "phase5_output"
OUT.mkdir(parents=True, exist_ok=True)

TCRIT_95_DF9 = 2.2621571627409915
EXPECTED_REPS = 10
EXPECTED_SAMPLES = 1_000_000


def mean(xs):
    return sum(xs) / len(xs)


def sample_sd(xs):
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ci95(xs):
    return TCRIT_95_DF9 * sample_sd(xs) / math.sqrt(len(xs))


def load_runs():
    by_run = {}
    with INPUT.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["type"] != "scalar" or row["module"] != "DectScheduledAccessNetwork.queue":
                continue
            run = by_run.setdefault(row["run"], {"run": row["run"]})
            try:
                run[row["name"]] = float(row["value"])
            except ValueError:
                pass
    return list(by_run.values())


runs = load_runs()
required = ["load_factor_rho_over_rho_sat", "mean_delay_direct_ms", "delay_p95_ms", "delay_p99_ms",
            "delay_p999_ms", "tail_sample_count", "blocking_probability", "rho", "rho_sat"]
for r in runs:
    missing = [k for k in required if k not in r]
    if missing:
        raise RuntimeError(f"Missing Phase-5 scalars in {r.get('run')}: {missing}")

groups = {}
for r in runs:
    factor = round(r["load_factor_rho_over_rho_sat"], 6)
    groups.setdefault(factor, []).append(r)

if len(groups) != 10:
    raise RuntimeError(f"Expected 10 load groups, found {len(groups)}")

rows = []
for factor in sorted(groups):
    rr = groups[factor]
    if len(rr) != EXPECTED_REPS:
        raise RuntimeError(f"Factor {factor}: expected {EXPECTED_REPS} repetitions, got {len(rr)}")
    if min(x["tail_sample_count"] for x in rr) < EXPECTED_SAMPLES:
        raise RuntimeError(f"Factor {factor}: insufficient tail sample count")

    row = {"rho_over_rho_sat": factor, "replications": len(rr)}
    for key, outname in [
        ("mean_delay_direct_ms", "mean_delay_ms"),
        ("delay_p95_ms", "p95_ms"),
        ("delay_p99_ms", "p99_ms"),
        ("delay_p999_ms", "p999_ms"),
        ("blocking_probability", "blocking_probability"),
    ]:
        vals = [x[key] for x in rr]
        row[outname] = mean(vals)
        row[outname + "_ci95"] = ci95(vals)
    row["tail_samples_total"] = int(sum(x["tail_sample_count"] for x in rr))
    rows.append(row)

csv_path = OUT / "phase5_tail_summary.csv"
fields = [
    "rho_over_rho_sat", "replications", "tail_samples_total",
    "mean_delay_ms", "mean_delay_ms_ci95",
    "p95_ms", "p95_ms_ci95",
    "p99_ms", "p99_ms_ci95",
    "p999_ms", "p999_ms_ci95",
    "blocking_probability", "blocking_probability_ci95",
]
with csv_path.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

fig, ax = plt.subplots(figsize=(7.8, 5.2))
x = [r["rho_over_rho_sat"] for r in rows]
for ykey, ekey, label in [
    ("mean_delay_ms", "mean_delay_ms_ci95", "Mean"),
    ("p95_ms", "p95_ms_ci95", "P95"),
    ("p99_ms", "p99_ms_ci95", "P99"),
]:
    y = [r[ykey] for r in rows]
    e = [r[ekey] for r in rows]
    ax.errorbar(x, y, yerr=e, marker="o", linewidth=1.7, markersize=4, capsize=2.5, label=label)

ax.axvline(1.0, linestyle="--", linewidth=1.3)
ax.set_xscale("log")
ax.set_xlim(0.48, 5.2)
ax.set_xticks([0.5, 0.7, 0.8, 1.0, 1.2, 1.5, 2.0, 5.0])
ax.set_xticklabels(["0.5", "0.7", "0.8", "1.0", "1.2", "1.5", "2.0", "5.0"])
ax.set_xlabel(r"Load relative to saturation $\rho/\rho_{\mathrm{sat}}$")
ax.set_ylabel("Type-1 sojourn time [ms]")
ax.legend(frameon=True)
ax.grid(True, linewidth=0.4, alpha=0.35)
fig.tight_layout()
fig.savefig(OUT / "figure_D_tail_latency.pdf", bbox_inches="tight")
fig.savefig(OUT / "figure_D_tail_latency.png", dpi=300, bbox_inches="tight")
plt.close(fig)

lines = [
    "PHASE 5 OMNeT++ TAIL-LATENCY SUMMARY",
    "====================================",
    "D=10, L=2, r=30; 10 replications per load; 1,000,000 measured admitted completions per replication.",
    "95% intervals are Student-t intervals across the 10 replication-level estimates.",
    "",
]
for row in rows:
    lines.append(
        f"factor={row['rho_over_rho_sat']:.1f}: "
        f"mean={row['mean_delay_ms']:.4f}±{row['mean_delay_ms_ci95']:.4f} ms, "
        f"P95={row['p95_ms']:.4f}±{row['p95_ms_ci95']:.4f} ms, "
        f"P99={row['p99_ms']:.4f}±{row['p99_ms_ci95']:.4f} ms, "
        f"blocking={row['blocking_probability']:.6f}"
    )
(OUT / "phase5_tail_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
