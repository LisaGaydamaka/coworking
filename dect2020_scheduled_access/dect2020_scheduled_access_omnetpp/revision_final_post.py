#!/usr/bin/env python3
"""Final long-run verification of five original near-saturation cases.

Uses only stdlib and original OMNeT++ CSV-R scalars. Never overwrites the
original Phase 2 outputs. Companion analysis under sibling analysis/
computes the exact stationary analytical predictions separately.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE/"ci_results"
T95_19=2.093024054408263
T95_9=2.2621571627409915
def load_runs(path):
    byrun=defaultdict(dict)
    with path.open(newline="",encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("type")!="scalar" or row.get("module")!="DectScheduledAccessNetwork.queue":continue
            try:byrun[row["run"]][row["name"]]=float(row["value"])
            except (ValueError,TypeError):continue
    return list(byrun.values())
def mean(x):return sum(x)/len(x)
def ci(x):
    n=len(x)
    if n<2:return 0.0
    sd=math.sqrt(sum((v-mean(x))**2 for v in x)/(n-1))
    t=T95_19 if n==20 else (T95_9 if n==10 else 2.0)
    return t*sd/math.sqrt(n)
def save(path,rows):
    if not rows:raise RuntimeError("No results for "+str(path))
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

newruns=load_runs(ROOT/"revision-final-saturation_scalars.csv")
oldruns=load_runs(ROOT/"phase2_metrics.csv")
cases={(10,20),(10,50),(20,5),(20,20),(20,50)}
def grouped(runs):
    groups=defaultdict(list)
    for z in runs:
        D=int(z.get("D",-1));r=int(z.get("r",-1))
        if (D,r) not in cases:continue
        if abs(z.get("rho",0)-({10:0.084745762712,20:0.042016806723}[D]))>1e-8:continue
        groups[(D,r)].append(z)
    return groups
new=grouped(newruns);old=grouped(oldruns)
if set(new)!=cases:raise RuntimeError("Missing saturation cases: "+str(cases-set(new)))
if sum(map(len,new.values()))!=100 or any(len(new[k])!=20 for k in cases):
    raise RuntimeError("Expected 5x20 independent new long-run replications")
if any(len(old.get(k,[]))!=10 for k in cases):
    raise RuntimeError("Expected existing 5x10 Phase-2 replications")
metrics=("mean_delay_direct_ms","blocking_probability","mean_type1_number",
         "effective_throughput_departures_per_ms","mean_delay_little_ms")
rows=[]
for D,r in sorted(cases):
    ns=new[(D,r)];os=old[(D,r)]
    v={"D":D,"r":r,"rho":ns[0]["rho"],"lambda_per_ms":ns[0]["lambda_per_ms"],
       "warmup_new":int(ns[0]["warmup_type1_completions"]),
       "measured_completed_new_per_rep":int(ns[0]["measured_completed_packets"]),
       "new_repetitions":len(ns),"old_repetitions":len(os)}
    for m in metrics:
        xv=[s[m] for s in ns]
        ov=[s[m] for s in os]
        v[m+"_new_mean"]=mean(xv)
        v[m+"_new_ci95_halfwidth"]=ci(xv)
        v[m+"_old_mean"]=mean(ov)
        v[m+"_old_ci95_halfwidth"]=ci(ov)
        v[m+"_new_minus_old"]=mean(xv)-mean(ov)
    rows.append(v)
path=ROOT/"revision-final-saturation_summary.csv"
save(path,rows)
lines=["# Long-run original-queue saturation audit (GitHub Actions)",
       "5 original mismatch cases, 20 repetitions each, 1,000,000 warm-up",
       "and 5,000,000 measured completions per new replication.",
       "Published C++ queue model and original Phase-2 CSV unchanged.",
       "Ten old seeds are intentionally reused for a paired robustness check.",
       "Analytical comparison is calculated in analysis/revision_final_analysis.py.",
       ""]
for v in rows:
    lines.append("D=%s r=%s: old %.6f +/- %.6f ms, long %.6f +/- %.6f ms (95%%)"%
       (v["D"],v["r"],v["mean_delay_direct_ms_old_mean"],v["mean_delay_direct_ms_old_ci95_halfwidth"],
        v["mean_delay_direct_ms_new_mean"],v["mean_delay_direct_ms_new_ci95_halfwidth"]))
(ROOT/"revision-final-saturation_report.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
