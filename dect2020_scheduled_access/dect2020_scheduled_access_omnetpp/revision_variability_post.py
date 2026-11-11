#!/usr/bin/env python3
"""Summarize 90 frame-aligned original-queue OMNeT++ Phase-6 replications."""
import csv
import math
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"ci_results"/"revision-variability-aligned_scalars.csv"
DEST=ROOT/"ci_results"/"revision-variability-aligned_summary.csv"
groups=defaultdict(dict)
with SRC.open(newline="") as f:
    for z in csv.DictReader(f):
        if z.get("type")!="scalar" or not z.get("module","").endswith(".queue"):continue
        try:groups[z["run"]][z["name"]]=float(z["value"])
        except (ValueError,KeyError):pass
bykey=defaultdict(list)
for r in groups.values():
    k=(int(r["type1_service_distribution_code"]),
       round(r["load_factor_rho_over_rho_sat"],4))
    bykey[k].append(r)
def mean(x):return sum(x)/len(x)
def ci(x):
    if len(x)<2:return 0
    avg=mean(x)
    sd=math.sqrt(sum((z-avg)**2 for z in x)/(len(x)-1))
    return 2.262157163*sd/math.sqrt(len(x))
names={0:"deterministic",1:"exponential",2:"hyperexponential_SCv4"}
rows=[]
for (code,load),values in sorted(bykey.items()):
    d=dict(distribution_code=code,distribution=names[code],physical_load_factor=load,
           D=10,r=30,L=2,frame_aligned_F_ms=9.1666666667,
           repetitions=len(values))
    for key in ("mean_delay_direct_ms","delay_p95_ms","delay_p99_ms",
                "delay_p999_ms","blocking_probability"):
        xs=[x[key] for x in values]
        d[key]=mean(xs)
        d[key+"_ci95"]=ci(xs)
    rows.append(d)
assert len(groups)==90 and len(rows)==9, (len(groups),len(rows))
assert all(r["repetitions"]==10 for r in rows)
with DEST.open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]))
    w.writeheader();w.writerows(rows)
report=["# Corrected 10-ms frame-aligned Phase-6 variability",
        "Original OMNeT++ vacation-queue C++ source unchanged.",
        "90 successful simulation runs, 9 groups and 10 repetitions each.",
        "D10, L2, r30; mean B=10/24ms, deterministic F=9.1666666667ms.",
        "Each repetition: 200,000 warm-up and 1,000,000 measured completions.",
        "", "Distribution, physical saturation load, P99 [ms], blocking:"]
for r in rows:
    report.append("%s, %.1f, %.5f +/- %.5f, %.6f"%
                  (r["distribution"],r["physical_load_factor"],
                   r["delay_p99_ms"],r["delay_p99_ms_ci95"],r["blocking_probability"]))
(ROOT/"ci_results"/"revision-variability-aligned_report.md").write_text("\n".join(report)+"\n")
print("\n".join(report))
