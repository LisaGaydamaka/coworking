#!/usr/bin/env python3
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: analyze.py SCALARS_CSV OUTPUT_DIR")

src = Path(sys.argv[1])
outdir = Path(sys.argv[2])
outdir.mkdir(parents=True, exist_ok=True)

needed = {
    "D", "r", "L_effective", "rho", "rho_sat",
    "mean_type1_service_ms", "type2_service_ms",
    "mean_delay_direct_ms", "blocking_probability",
    "effective_throughput_departures_per_ms",
}

runs = defaultdict(dict)
with src.open(newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        if row.get("type") != "scalar":
            continue
        if row.get("module") != "DectScheduledAccessNetwork.queue":
            continue
        name = row.get("name", "")
        if name not in needed:
            continue
        value = row.get("value", "")
        if value == "":
            continue
        runs[row["run"]][name] = float(value)

per_run = []
for run_name, d in runs.items():
    missing = needed - d.keys()
    if missing:
        raise RuntimeError(f"{run_name}: missing scalars {sorted(missing)}")
    throughput = d["effective_throughput_departures_per_ms"]
    if not math.isfinite(throughput) or throughput <= 0:
        raise RuntimeError(f"{run_name}: invalid throughput {throughput}")
    paoi = d["mean_delay_direct_ms"] + 1.0 / throughput
    per_run.append({
        "run": run_name,
        **d,
        "paoi_ms": paoi,
    })

groups = defaultdict(list)
for row in per_run:
    key = (int(round(row["r"])), round(row["rho"], 12))
    groups[key].append(row)

def mean(xs):
    return statistics.fmean(xs)

def sem(xs):
    if len(xs) < 2:
        return float("nan")
    return statistics.stdev(xs) / math.sqrt(len(xs))

aggregate = []
for (r, rho), rows in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    aggregate.append({
        "r": r,
        "rho": rho,
        "repetitions": len(rows),
        "D": mean([x["D"] for x in rows]),
        "L_effective": mean([x["L_effective"] for x in rows]),
        "rho_sat": mean([x["rho_sat"] for x in rows]),
        "mean_type1_service_ms": mean([x["mean_type1_service_ms"] for x in rows]),
        "type2_service_ms": mean([x["type2_service_ms"] for x in rows]),
        "mean_delay_ms": mean([x["mean_delay_direct_ms"] for x in rows]),
        "blocking_probability": mean([x["blocking_probability"] for x in rows]),
        "throughput_per_ms": mean([x["effective_throughput_departures_per_ms"] for x in rows]),
        "paoi_ms": mean([x["paoi_ms"] for x in rows]),
        "paoi_sem_ms": sem([x["paoi_ms"] for x in rows]),
    })

expected_r = {5, 10, 20, 30, 40, 50}
expected_rho = [round(0.01 + 0.083 * i, 12) for i in range(32)]
seen_r = {x["r"] for x in aggregate}
if seen_r != expected_r:
    raise RuntimeError(f"unexpected r values: {sorted(seen_r)}")
for r in sorted(expected_r):
    got = [x["rho"] for x in aggregate if x["r"] == r]
    if got != expected_rho:
        raise RuntimeError(f"r={r}: rho grid mismatch: {got}")

fieldnames = list(aggregate[0].keys())
with (outdir / "paper_plot_data.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(aggregate)

# Also preserve run-level PAoI calculations for auditability.
run_fields = [
    "run", "D", "r", "L_effective", "rho", "rho_sat",
    "mean_type1_service_ms", "type2_service_ms",
    "mean_delay_direct_ms", "blocking_probability",
    "effective_throughput_departures_per_ms", "paoi_ms",
]
with (outdir / "paper_plot_runs.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=run_fields)
    w.writeheader()
    for row in sorted(per_run, key=lambda x: (x["r"], x["rho"], x["run"])):
        w.writerow({k: row[k] for k in run_fields})

# Dependency-free SVG plot.
width, height = 1050, 680
left, right, top, bottom = 90, 30, 40, 80
plot_w = width - left - right
plot_h = height - top - bottom
xmin, xmax = 0.0, max(x["rho"] for x in aggregate)
ymax_data = max(x["paoi_ms"] for x in aggregate)
# Round the y ceiling up to a clean multiple of 25 ms.
ymax = max(25.0, math.ceil(ymax_data / 25.0) * 25.0)

def X(x):
    return left + (x - xmin) / (xmax - xmin) * plot_w

def Y(y):
    return top + plot_h - y / ymax * plot_h

styles = {
    50: ("", "circle"),
    40: ("8 4", "square"),
    30: ("2 3", "circle-open"),
    20: ("10 3 2 3", "triangle"),
    10: ("5 5", "none"),
    5: ("1 0", "none"),
}

def marker_svg(kind, x, y):
    if kind == "circle":
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.8" fill="black"/>'
    if kind == "circle-open":
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.0" fill="white" stroke="black" stroke-width="1.2"/>'
    if kind == "square":
        return f'<rect x="{x-2.8:.2f}" y="{y-2.8:.2f}" width="5.6" height="5.6" fill="white" stroke="black" stroke-width="1.2"/>'
    if kind == "triangle":
        pts = f"{x:.2f},{y-3.5:.2f} {x-3.3:.2f},{y+2.8:.2f} {x+3.3:.2f},{y+2.8:.2f}"
        return f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="1.2"/>'
    return ""

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
svg.append('<rect width="100%" height="100%" fill="white"/>')
svg.append('<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.tick{font-size:14px}.label{font-size:18px}.legend{font-size:14px}</style>')

# Grid and axes.
for i in range(6):
    yv = ymax * i / 5
    yy = Y(yv)
    svg.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{left+plot_w}" y2="{yy:.2f}" stroke="#dddddd" stroke-width="1"/>')
    svg.append(f'<text class="tick" x="{left-12}" y="{yy+5:.2f}" text-anchor="end">{yv:.0f}</text>')
for xv in [0, 0.5, 1.0, 1.5, 2.0, 2.5]:
    xx = X(xv)
    svg.append(f'<line x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{top+plot_h}" stroke="#e5e5e5" stroke-width="1"/>')
    svg.append(f'<text class="tick" x="{xx:.2f}" y="{top+plot_h+26}" text-anchor="middle">{xv:g}</text>')

svg.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="black" stroke-width="1.5"/>')
svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="black" stroke-width="1.5"/>')
svg.append(f'<text class="label" x="{left+plot_w/2:.2f}" y="{height-22}" text-anchor="middle">ρ</text>')
svg.append(f'<text class="label" transform="translate(24 {top+plot_h/2:.2f}) rotate(-90)" text-anchor="middle">Packet-average PAoI Δ, ms</text>')

# Lines.
for r in [50, 40, 30, 20, 10, 5]:
    pts = [x for x in aggregate if x["r"] == r]
    d = " ".join(("M" if i == 0 else "L") + f" {X(p['rho']):.2f} {Y(p['paoi_ms']):.2f}" for i, p in enumerate(pts))
    dash, marker = styles[r]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<path d="{d}" fill="none" stroke="black" stroke-width="1.8"{dash_attr}/>')
    if marker != "none":
        for p in pts:
            svg.append(marker_svg(marker, X(p["rho"]), Y(p["paoi_ms"])))

# Legend.
lx, ly = left + 24, top + 22
svg.append(f'<rect x="{lx-14}" y="{ly-18}" width="135" height="146" fill="white" stroke="black" stroke-width="1"/>')
for idx, r in enumerate([50, 40, 30, 20, 10, 5]):
    yy = ly + idx * 22
    dash, marker = styles[r]
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<line x1="{lx}" y1="{yy}" x2="{lx+42}" y2="{yy}" stroke="black" stroke-width="1.8"{dash_attr}/>')
    svg.append(marker_svg(marker, lx+21, yy))
    svg.append(f'<text class="legend" x="{lx+52}" y="{yy+5}">r={r}</text>')

svg.append(f'<text class="tick" x="{left+plot_w}" y="{height-6}" text-anchor="end">OMNeT++ simulation; 3 repetitions per point</text>')
svg.append('</svg>')
(outdir / "paper_plot.svg").write_text("\n".join(svg), encoding="utf-8")

# Compact human-readable summary.
with (outdir / "summary.txt").open("w", encoding="utf-8") as f:
    f.write("MONETEC PAoI plot reproduction using canonical OMNeT++ simulator\n")
    f.write(f"runs={len(per_run)} groups={len(aggregate)}\n")
    f.write("PAoI per run = mean_delay_direct_ms + 1/effective_throughput_departures_per_ms\n")
    f.write(f"D={aggregate[0]['D']:.0f}, L={aggregate[0]['L_effective']:.0f}, mB={aggregate[0]['mean_type1_service_ms']:.9g} ms, mF={aggregate[0]['type2_service_ms']:.9g} ms\n")
    f.write(f"rho range={min(x['rho'] for x in aggregate):.3f}..{max(x['rho'] for x in aggregate):.3f}\n")
    f.write(f"PAoI range={min(x['paoi_ms'] for x in aggregate):.6g}..{max(x['paoi_ms'] for x in aggregate):.6g} ms\n")
