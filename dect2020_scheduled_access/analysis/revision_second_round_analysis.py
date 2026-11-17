#!/usr/bin/env python3
"""Independent analytical comparisons for the second-round fixed-slot checks.

Reads the completed, frozen simulation summary, evaluates the existing
frame-aligned M/G/1 finite-buffer stationary solver at IDENTICAL offered rates,
and writes an auditable table. Does not alter any simulation observations.
"""
import csv
from pathlib import Path
import phase4_dimensioning as a

ROOT=Path(__file__).resolve().parent
IN=ROOT.parent/"dect2020_scheduled_access_omnetpp"/"ci_results"/"revision-second-round_summary.csv"
OUT=ROOT/"revision_output"
OUT.mkdir(exist_ok=True)
B=10./24.
with IN.open(newline="",encoding="utf8") as f:
    raw=list(csv.DictReader(f))
if len(raw)!=22:
    raise RuntimeError("Second-round experiment is not complete (expected 22 groups)")
rows=[]
for z in raw:
    D=int(z["D"]);r=int(z["r"]);L=24//D
    lam=float(z["lambda_per_ms"]);mF=10-L*B
    beta,bt=a.det_counts(lam,B,r+4)
    phi,pt=a.det_counts(lam,mF,r+4)
    P=a.transition_matrix(r,L,beta,phi,bt,pt)
    q=a.stationary(P)
    N,pi,v=a.reward_metrics(lam,r,L,mF,q,bt,pt)
    physical_v=float(z["mean_delay_direct_ms"])
    physical_pi=float(z["blocking_probability"])
    rows.append({
        "case":"low_load" if lam<0.75 and D==2 else "deterministic_threshold",
        "D":D,"r":r,"L":L,
        "slot_layout":"contiguous" if int(z["slot_layout_code"])==0 else "distributed",
        "lambda_per_ms":lam,"load_factor":float(z["physical_load_factor"]),
        "replications":int(z["repetitions"]),
        "physical_mean_delay_ms":physical_v,
        "physical_mean_delay_ci95_ms":float(z["mean_delay_direct_ms_ci95"]),
        "analytical_det_mean_delay_ms":v,
        "relative_delay_error_pct":100*(v/physical_v-1),
        "physical_blocking":physical_pi,
        "physical_blocking_ci95":float(z["blocking_probability_ci95"]),
        "analytical_det_blocking":pi,
        "blocking_error_percentage_points":100*(physical_pi-pi)
    })
rows.sort(key=lambda z:(z["case"],z["D"],z["slot_layout"],z["lambda_per_ms"]))
with (OUT/"revision_second_round_validation.csv").open("w",newline="",encoding="utf8") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]))
    w.writeheader();w.writerows(rows)
low=[z for z in rows if z["case"]=="low_load"]
high=[z for z in rows if z["case"]=="deterministic_threshold"]
assert len(low)==4 and len(high)==18
report=["# Second-round fixed-slot numerical audit",
 "",
 "All 22 points use 5 independent replications, 100,000 warm-up and",
 "400,000 measured admitted completions per run.",
 "Physical data: ci_results/revision-second-round_summary.csv",
 "Analytical independent solver: analysis/phase4_dimensioning.py",
 "",
 "## D2 low-load comparison"]
for z in low:
    report.append("lambda=%.6f, load=%.1f, layout=%s: fixed-slot mean %.6f +/- %.6f ms, analytical %.6f ms, relative analytical error %+.3f%%."%
        (z["lambda_per_ms"],z["load_factor"],z["slot_layout"],z["physical_mean_delay_ms"],
         z["physical_mean_delay_ci95_ms"],z["analytical_det_mean_delay_ms"],z["relative_delay_error_pct"]))
report+=["","## Deterministic contour blocking (r=30)"]
for z in high:
    report.append("D=%2d, lambda=%.9f, fixed-slot blocking %.6f +/- %.6f, analytical %.6f, difference %+0.4f pp."%
        (z["D"],z["lambda_per_ms"],z["physical_blocking"],z["physical_blocking_ci95"],
         z["analytical_det_blocking"],z["blocking_error_percentage_points"]))
(OUT/"revision_second_round_report.md").write_text("\n".join(report)+"\n",encoding="utf8")
print("\n".join(report))
