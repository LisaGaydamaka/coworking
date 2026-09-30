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
    "D", "r", "L_effective", "rho",
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
    per_run.append({"run": run_name, **d, "paoi_ms": paoi})

groups = defaultdict(list)
for row in per_run:
    key = (int(round(row["r"])), round(row["rho"], 12))
    groups[key].append(row)

def mean(xs):
    return statistics.fmean(xs)

def sem(xs):
    return statistics.stdev(xs) / math.sqrt(len(xs)) if len(xs) >= 2 else float("nan")

aggregate = []
for (r, rho), rows in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    aggregate.append({
        "r": r,
        "rho": rho,
        "repetitions": len(rows),
        "D": mean([x["D"] for x in rows]),
        "L_effective": mean([x["L_effective"] for x in rows]),
        "mean_type1_service_ms": mean([x["mean_type1_service_ms"] for x in rows]),
        "type2_service_ms": mean([x["type2_service_ms"] for x in rows]),
        "mean_delay_ms": mean([x["mean_delay_direct_ms"] for x in rows]),
        "blocking_probability": mean([x["blocking_probability"] for x in rows]),
        "throughput_per_ms": mean([x["effective_throughput_departures_per_ms"] for x in rows]),
        "paoi_ms": mean([x["paoi_ms"] for x in rows]),
        "paoi_sem_ms": sem([x["paoi_ms"] for x in rows]),
    })

expected_r = {1,4,7,10,13,16}
expected_rho = [round(0.005*i, 12) for i in range(1,61)]
if {x["r"] for x in aggregate} != expected_r:
    raise RuntimeError("r grid mismatch")
for r in sorted(expected_r):
    got = [x["rho"] for x in aggregate if x["r"] == r]
    if got != expected_rho:
        raise RuntimeError(f"rho grid mismatch for r={r}")

with (outdir/"focused_paoi_data.csv").open("w", newline="", encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=list(aggregate[0].keys()))
    w.writeheader()
    w.writerows(aggregate)

run_fields=["run","D","r","L_effective","rho","mean_type1_service_ms","type2_service_ms",
            "mean_delay_direct_ms","blocking_probability","effective_throughput_departures_per_ms","paoi_ms"]
with (outdir/"focused_paoi_runs.csv").open("w", newline="", encoding="utf-8") as f:
    w=csv.DictWriter(f, fieldnames=run_fields)
    w.writeheader()
    for row in sorted(per_run, key=lambda x:(x["r"],x["rho"],x["run"])):
        w.writerow({k:row[k] for k in run_fields})

# Dependency-free SVG tuned to reveal the low-rho shape.
width,height=1100,700
left,right,top,bottom=90,30,35,85
plot_w=width-left-right
plot_h=height-top-bottom
xmin,xmax=0.0,0.30
ymin=0.0
ymax=max(100.0, math.ceil(max(x["paoi_ms"] for x in aggregate)/10.0)*10.0)

def X(x): return left+(x-xmin)/(xmax-xmin)*plot_w
def Y(y): return top+plot_h-(y-ymin)/(ymax-ymin)*plot_h

styles={
    1:("", "circle"),
    4:("8 4","square"),
    7:("2 3","circle-open"),
    10:("10 3 2 3","triangle"),
    13:("5 5","diamond"),
    16:("1 0","none"),
}

def marker(kind,x,y):
    if kind=="circle":
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.4" fill="black"/>'
    if kind=="circle-open":
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.6" fill="white" stroke="black" stroke-width="1.1"/>'
    if kind=="square":
        return f'<rect x="{x-2.5:.2f}" y="{y-2.5:.2f}" width="5" height="5" fill="white" stroke="black" stroke-width="1.1"/>'
    if kind=="triangle":
        pts=f"{x:.2f},{y-3:.2f} {x-2.9:.2f},{y+2.4:.2f} {x+2.9:.2f},{y+2.4:.2f}"
        return f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="1.1"/>'
    if kind=="diamond":
        pts=f"{x:.2f},{y-3:.2f} {x-3:.2f},{y:.2f} {x:.2f},{y+3:.2f} {x+3:.2f},{y:.2f}"
        return f'<polygon points="{pts}" fill="white" stroke="black" stroke-width="1.1"/>'
    return ""

svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
     '<rect width="100%" height="100%" fill="white"/>',
     '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#111}.tick{font-size:14px}.label{font-size:18px}.legend{font-size:14px}</style>']

for yv in range(0,int(ymax)+1,20):
    yy=Y(yv)
    svg.append(f'<line x1="{left}" y1="{yy:.2f}" x2="{left+plot_w}" y2="{yy:.2f}" stroke="#dddddd" stroke-width="1"/>')
    svg.append(f'<text class="tick" x="{left-12}" y="{yy+5:.2f}" text-anchor="end">{yv}</text>')
for xv in [0,0.05,0.10,0.15,0.20,0.25,0.30]:
    xx=X(xv)
    svg.append(f'<line x1="{xx:.2f}" y1="{top}" x2="{xx:.2f}" y2="{top+plot_h}" stroke="#e5e5e5" stroke-width="1"/>')
    svg.append(f'<text class="tick" x="{xx:.2f}" y="{top+plot_h+28}" text-anchor="middle">{xv:.2f}</text>')

svg.append(f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" stroke="black" stroke-width="1.5"/>')
svg.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" stroke="black" stroke-width="1.5"/>')
svg.append(f'<text class="label" x="{left+plot_w/2:.2f}" y="{height-25}" text-anchor="middle">ρ</text>')
svg.append(f'<text class="label" transform="translate(25 {top+plot_h/2:.2f}) rotate(-90)" text-anchor="middle">Packet-average PAoI Δ, ms</text>')

for r in [1,4,7,10,13,16]:
    pts=[x for x in aggregate if x["r"]==r]
    d=" ".join(("M" if i==0 else "L")+f" {X(p['rho']):.2f} {Y(p['paoi_ms']):.2f}" for i,p in enumerate(pts))
    dash,m=styles[r]
    dash_attr=f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<path d="{d}" fill="none" stroke="black" stroke-width="1.7"{dash_attr}/>')
    if m!="none":
        # mark every second point to keep 60-point curves readable
        for i,p in enumerate(pts):
            if i%2==0:
                svg.append(marker(m,X(p["rho"]),Y(p["paoi_ms"])))

lx,ly=left+24,top+24
svg.append(f'<rect x="{lx-14}" y="{ly-18}" width="135" height="145" fill="white" stroke="black" stroke-width="1"/>')
for i,r in enumerate([1,4,7,10,13,16]):
    yy=ly+i*22
    dash,m=styles[r]
    dash_attr=f' stroke-dasharray="{dash}"' if dash else ""
    svg.append(f'<line x1="{lx}" y1="{yy}" x2="{lx+42}" y2="{yy}" stroke="black" stroke-width="1.7"{dash_attr}/>')
    svg.append(marker(m,lx+21,yy))
    svg.append(f'<text class="legend" x="{lx+52}" y="{yy+5}">r={r}</text>')

svg.append(f'<text class="tick" x="{left+plot_w}" y="{height-7}" text-anchor="end">OMNeT++ simulation; 3 repetitions per point</text>')
svg.append('</svg>')
(outdir/"focused_paoi_plot.svg").write_text("\n".join(svg),encoding="utf-8")

with (outdir/"summary.txt").open("w",encoding="utf-8") as f:
    f.write("Focused MONETEC PAoI sweep using canonical OMNeT++ simulator\n")
    f.write(f"runs={len(per_run)} groups={len(aggregate)}\n")
    f.write("r={1,4,7,10,13,16}\n")
    f.write("rho=0.005..0.300 step 0.005\n")
    f.write("PAoI = direct mean sojourn time + 1/successful departure throughput\n")
    for r in [1,4,7,10,13,16]:
        pts=[x for x in aggregate if x["r"]==r]
        mn=min(pts,key=lambda x:x["paoi_ms"])
        f.write(f"r={r}: minimum PAoI={mn['paoi_ms']:.6f} ms at rho={mn['rho']:.3f}\n")
