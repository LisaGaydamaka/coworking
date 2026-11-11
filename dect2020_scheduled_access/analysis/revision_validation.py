#!/usr/bin/env python3
"""Major revision: independent analytical comparison of GitHub Actions OMNeT++ outputs.

Must run from the existing analysis/ component on a GitHub Actions host,
where both this folder and the sibling OMNeT++ ci_results are accessible.
The published Phase 2-6 data and original analytical figures remain frozen.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import phase4_dimensioning as a

ROOT=Path(__file__).resolve().parent
INPUT=ROOT.parent/"dect2020_scheduled_access_omnetpp"/"ci_results"
OUT=ROOT/"revision_output"
OUT.mkdir(exist_ok=True)
B=10.0/24.0
T={1:12.706204736,2:4.30265273,3:3.1824463,4:2.776445105,9:2.262157163}

def read_csv(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf8") as f:
        return list(csv.DictReader(f))
def write_csv(path,rows):
    if not rows:return
    with path.open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
def mean(xs):return sum(xs)/len(xs)
def ci95(xs):
    if len(xs)<2:return 0.0
    mu=mean(xs)
    sd=math.sqrt(sum((x-mu)**2 for x in xs)/(len(xs)-1))
    return T.get(len(xs)-1,2.1)*sd/math.sqrt(len(xs))
def queue(D,r,lam,aligned=False,det=False,available=24):
    L=available//D
    if L<1:raise ValueError("infeasible PT allocation")
    mF=(10-L*B) if aligned else 10-10/D
    nmax=r+4
    beta,bt=a.det_counts(lam,B,nmax) if det else a.exp_counts(lam,nmax)
    phi,pt=a.det_counts(lam,mF,nmax)
    P=a.transition_matrix(r,L,beta,phi,bt,pt)
    if abs(np.sum(a.stationary(P))-1)>1e-7:
        raise AssertionError("analytical stationary state failed normalization")
    q=a.stationary(P)
    N,pi,v=a.reward_metrics(lam,r,L,mF,q,bt,pt)
    return {"mean_delay_ms":v,"blocking_probability":pi,
            "mean_number":N,"lambda_sat":L/(L*B+mF),"L":L,"mF_ms":mF}

# Original queue verification: complete 27-group 95% Student-t CI audit.
oldrows=read_csv(INPUT/"phase2_metrics.csv")
byrun=defaultdict(dict)
for x in oldrows:
    if x.get("type")!="scalar" or x.get("module")!="DectScheduledAccessNetwork.queue":continue
    try:byrun[x["run"]][x["name"]]=float(x["value"])
    except (ValueError,KeyError):pass
bygroup=defaultdict(list)
for x in byrun.values():
    if all(k in x for k in ("D","r","rho","mean_delay_direct_ms")):
        bygroup[(int(x["D"]),int(x["r"]),round(x["rho"],12))].append(x)
audits=[]
for (D,r,rho),ss in sorted(bygroup.items()):
    ana=a.analytic_metrics(D,r,rho)
    v={"D":D,"r":r,"rho":rho,"repetitions":len(ss)}
    for name,pred in (("mean_delay_direct_ms",ana["mean_delay_ms"]),
                      ("blocking_probability",ana["blocking_probability"]),
                      ("mean_type1_number",ana["mean_number"])):
        xs=[s[name] for s in ss]
        est=mean(xs);err=ci95(xs)
        v[name+"_analytical"]=pred
        v[name+"_simulated"]=est
        v[name+"_ci95_halfwidth"]=err
        v[name+"_ci95_covers_analytical"]=int(abs(pred-est)<=err)
    audits.append(v)
write_csv(OUT/"revision_original_27_confidence_intervals.csv",audits)

# The fixed-slot summaries are already pooled across independent replications.
# Each comparison uses the EXACT SAME external Poisson packet rate lambda.
modes=("revision-grid","revision-tail","revision-geometry",
       "revision-traffic","revision-dimensioning")
comparisons=[]
mode_counts={}
for mode in modes:
    physical=read_csv(INPUT/(mode+"_summary.csv"))
    mode_counts[mode]=len(physical)
    for x in physical:
        D,r,S=int(x["D"]),int(x["r"]),int(x["available_slots"])
        lam=float(x["lambda_per_ms"])
        kind=int(x["traffic_model_code"])
        row={"experiment":mode,"D":D,"r":r,"available_slots":S,
             "slot_layout_code":int(x["slot_layout_code"]),
             "traffic_model_code":kind,"lambda_per_ms":lam,
             "physical_load_factor":float(x["physical_load_factor"]),
             "physical_delay_ms":float(x["mean_delay_direct_ms"]),
             "physical_delay_ci95":float(x["mean_delay_direct_ms_ci95"]),
             "physical_blocking":float(x["blocking_probability"]),
             "physical_blocking_ci95":float(x["blocking_probability_ci95"]),
             "physical_throughput_per_ms":float(x["effective_throughput_departures_per_ms"]),
             "physical_p95_ms":x.get("delay_p95_ms",""),
             "physical_p99_ms":x.get("delay_p99_ms","")}
        if kind==0:
            old=queue(D,r,lam,aligned=False,det=False) if S==24 else None
            aln=queue(D,r,lam,aligned=True,det=False,available=S)
            det=queue(D,r,lam,aligned=True,det=True,available=S)
            row.update({
                "original_queue_delay_ms":old["mean_delay_ms"] if old else "",
                "aligned_exp_queue_delay_ms":aln["mean_delay_ms"],
                "aligned_det_queue_delay_ms":det["mean_delay_ms"],
                "original_queue_blocking":old["blocking_probability"] if old else "",
                "aligned_exp_queue_blocking":aln["blocking_probability"],
                "aligned_det_queue_blocking":det["blocking_probability"],
                "physical_minus_aligned_det_delay_ms":
                    row["physical_delay_ms"]-det["mean_delay_ms"],
                "physical_minus_aligned_det_blocking":
                    row["physical_blocking"]-det["blocking_probability"],
            })
        else:
            row.update({
                "original_queue_delay_ms":"","aligned_exp_queue_delay_ms":"",
                "aligned_det_queue_delay_ms":"","original_queue_blocking":"",
                "aligned_exp_queue_blocking":"","aligned_det_queue_blocking":"",
                "physical_minus_aligned_det_delay_ms":"",
                "physical_minus_aligned_det_blocking":""})
        comparisons.append(row)
write_csv(OUT/"revision_all_model_comparisons.csv",comparisons)
write_csv(OUT/"revision_grid_model_comparisons.csv",
          [x for x in comparisons if x["experiment"]=="revision-grid"])

# Recompute dimensioning contour thresholds with the exact stationary solver.
def blocking_threshold(D,aligned,target):
    L=24//D
    cap=L/10 if aligned else L/(L*B+10-10/D)
    lo,hi=1e-10,2*cap
    for _ in range(36):
        mid=(lo+hi)/2
        if queue(D,30,mid,aligned,False)["blocking_probability"]<target:lo=mid
        else:hi=mid
    return B*(lo+hi)/2
thresholds=[]
for D in (6,10,20):
    for target in (0.01,0.05,0.10):
        thresholds.append({
            "D":D,"r":30,"blocking_target":target,
            "original_rho_threshold":blocking_threshold(D,False,target),
            "frame_aligned_rho_threshold":blocking_threshold(D,True,target)})
write_csv(OUT/"revision_blocking_thresholds.csv",thresholds)

mapping=[]
for D in range(2,25):
    L=24//D
    lo=L/(L*B+10-10/D)
    ph=L/10
    mapping.append(dict(D=D,L=L,original_capacity_per_ms=lo,
        corrected_capacity_per_ms=ph,
        overestimate_pct=(lo/ph-1)*100,
        original_F_ms=10-10/D,frame_aligned_F_ms=10-L*B))
write_csv(OUT/"revision_frame_mapping.csv",mapping)

# Tail-latency comparison: label physical vs original queue; x is common
# lambda/0.2 rather than treating the two distinct saturation rates as equal.
physical_tail=[x for x in comparisons if x["experiment"]=="revision-tail"]
historical_tail=read_csv(ROOT/"phase5_output"/"phase5_tail_summary.csv")
tail_table=[]
original_capacity=2/(2*B+9)
for physical in physical_tail:
    lam=physical["lambda_per_ms"]
    old_factor=lam/original_capacity
    closest=min(historical_tail,key=lambda h:abs(float(h["rho_over_rho_sat"])-old_factor)) if historical_tail else None
    tail_table.append({
      "lambda_per_ms":lam,"physical_load_factor":physical["physical_load_factor"],
      "physical_delay_ms":physical["physical_delay_ms"],
      "physical_p95_ms":physical["physical_p95_ms"],
      "physical_p99_ms":physical["physical_p99_ms"],
      "physical_blocking":physical["physical_blocking"],
      "original_queue_mean_at_same_lambda_ms":physical["original_queue_delay_ms"],
      "aligned_exp_mean_at_same_lambda_ms":physical["aligned_exp_queue_delay_ms"],
      "aligned_det_mean_at_same_lambda_ms":physical["aligned_det_queue_delay_ms"]})
write_csv(OUT/"revision_tail_comparison.csv",tail_table)

if physical_tail:
    x=[z["physical_load_factor"] for z in physical_tail]
    fig,ax=plt.subplots(figsize=(7.8,4.8))
    ax.plot(x,[float(z["physical_p95_ms"]) for z in physical_tail],"o-",label="Fixed-slot P95")
    ax.plot(x,[float(z["physical_p99_ms"]) for z in physical_tail],"s-",label="Fixed-slot P99")
    if historical_tail:
        xold=[float(z["rho_over_rho_sat"])*original_capacity/0.2 for z in historical_tail]
        ax.plot(xold,[float(z["p99_ms"]) for z in historical_tail],"^--",label="Original queue OMNeT++ P99")
    ax.set_xlabel("Offered rate / fixed-slot saturation capacity")
    ax.set_ylabel("Admitted-packet sojourn [ms]")
    ax.set_xlim(0.45,5.15)
    ax.legend();ax.grid(alpha=.3);fig.tight_layout()
    fig.savefig(OUT/"revision_physical_vs_original_tail_p99.pdf")
    fig.savefig(OUT/"revision_physical_vs_original_tail_p99.png",dpi=250)
    plt.close(fig)

grid=[x for x in comparisons if x["experiment"]=="revision-grid"]
if grid:
    fig,ax=plt.subplots(figsize=(6.5,5.8))
    xp=[x["physical_delay_ms"] for x in grid]
    for name,marker,label in (("original_queue_delay_ms","o","Original exponential"),
                              ("aligned_exp_queue_delay_ms","s","Frame-aligned exponential"),
                              ("aligned_det_queue_delay_ms","^","Frame-aligned deterministic")):
        ax.scatter(xp,[float(x[name]) for x in grid],s=26,marker=marker,label=label,alpha=.7)
    mx=max(xp+[float(x["original_queue_delay_ms"]) for x in grid])
    ax.plot([0,mx],[0,mx],"k--",lw=1,label="Perfect agreement")
    ax.set_xlabel("Fixed-slot mean delay [ms]")
    ax.set_ylabel("Vacation-queue mean delay [ms]")
    ax.legend(fontsize=8);ax.grid(alpha=.25);fig.tight_layout()
    fig.savefig(OUT/"revision_27case_mean_delay_comparison.pdf")
    fig.savefig(OUT/"revision_27case_mean_delay_comparison.png",dpi=250)
    plt.close(fig)

traffic=[x for x in comparisons if x["experiment"]=="revision-traffic"]
if traffic:
    labels={0:"Poisson",1:"Periodic phase-randomized",2:"Synchronized periodic",3:"Compound-Poisson bursty"}
    fig,ax=plt.subplots(figsize=(7.2,4.7))
    for code in sorted({x["traffic_model_code"] for x in traffic}):
        rr=sorted([x for x in traffic if x["traffic_model_code"]==code],key=lambda x:x["lambda_per_ms"])
        ax.plot([x["lambda_per_ms"] for x in rr],
                [x["physical_blocking"] for x in rr],"o-",label=labels[code])
    ax.set_xlabel("Mean offered packet rate [packets/ms]")
    ax.set_ylabel("Blocking probability")
    ax.legend(fontsize=8);ax.grid(alpha=.25);fig.tight_layout()
    fig.savefig(OUT/"revision_traffic_blocking.pdf")
    fig.savefig(OUT/"revision_traffic_blocking.png",dpi=250)
    plt.close(fig)

# Corrected 10-ms-cycle Phase 6: original M/G/1 vacation queue with fixed
# mF=10-L*10/24, no physical slot synchronization.
variability=read_csv(INPUT/"revision-variability-aligned_summary.csv")
if variability:
    fig,ax=plt.subplots(figsize=(7.6,4.8))
    distnames={0:"Deterministic (SCV=0)",1:"Exponential (SCV=1)",
               2:"Hyperexponential (SCV=4)"}
    for code in (0,1,2):
        rr=sorted([v for v in variability if int(v["distribution_code"])==code],
                  key=lambda v:float(v["physical_load_factor"]))
        ax.errorbar([float(v["physical_load_factor"]) for v in rr],
                    [float(v["delay_p99_ms"]) for v in rr],
                    yerr=[float(v["delay_p99_ms_ci95"]) for v in rr],
                    marker="o",capsize=3,label=distnames[code])
    ax.set_xlabel("Load relative to frame-aligned saturation")
    ax.set_ylabel("Admitted-packet P99 [ms]")
    ax.legend();ax.grid(alpha=.25);fig.tight_layout()
    fig.savefig(OUT/"revision_corrected_service_variability_p99.pdf")
    fig.savefig(OUT/"revision_corrected_service_variability_p99.png",dpi=250)
    plt.close(fig)

hits=sum(row["mean_delay_direct_ms_ci95_covers_analytical"] for row in audits)
worst=next((r for r in audits if r["D"]==10 and r["r"]==50 and
              abs(r["rho"]-0.084745762712)<1e-7),None)
report=["# Major-revision independent analytical audit","",
    "Analytical source: frozen analysis/phase4_dimensioning.py",
    "Physical source: newly committed ci_results/revision-*_summary.csv",
    "All physical-to-analytical comparisons use identical absolute Poisson lambda.",
    "Physical model: fixed 10 ms/24-slot calendar, not full radio PHY.",
    "",
    "## Completed experimental groups",
]
report += ["- "+mode+": "+str(n)+" pooled configurations" for mode,n in mode_counts.items()]
if variability:
    report += ["", "## Corrected 10-ms-frame service-time variability (90 runs)"]
    for v in variability:
        if abs(float(v["physical_load_factor"])-1.2)<0.0001:
            report.append("- %s: P99 %.4f +/- %.4f ms (95%%)"%
                (v["distribution"],float(v["delay_p99_ms"]),
                 float(v["delay_p99_ms_ci95"])))
report += ["","## Original 27-case confidence-interval audit",
    "- Available groups: "+str(len(audits)),
    "- Analytical mean delays contained in 95% simulation CI: "+str(hits)+"/"+str(len(audits))]
if worst:
    report.append("- Worst D10/r50 saturation: simulation %.6f +/- %.6f ms (95%%); analytical %.6f ms."%
                  (worst["mean_delay_direct_ms_simulated"],
                   worst["mean_delay_direct_ms_ci95_halfwidth"],
                   worst["mean_delay_direct_ms_analytical"]))
if physical_tail:
    atsat=min(physical_tail,key=lambda z:abs(z["physical_load_factor"]-1))
    report += ["","## Fixed-slot D10/r30 at physical saturation",
        "- mean admitted delay: %.4f ms"%atsat["physical_delay_ms"],
        "- P99 admitted delay: %.4f ms"%float(atsat["physical_p99_ms"]),
        "- blocking: %.6f"%atsat["physical_blocking"]]
report += ["","Outputs: revision_all_model_comparisons.csv, revision_original_27_confidence_intervals.csv,",
    "revision_blocking_thresholds.csv, revision_tail_comparison.csv, revision_frame_mapping.csv.",
    "Figures: revision_27case_mean_delay_comparison and revision_physical_vs_original_tail_p99.",
    "The classical queue stability and finite-buffer limits are not claims of exact physical-slot fidelity."]
(OUT/"revision_master_summary.md").write_text("\n".join(report)+"\n")
print("\n".join(report))
