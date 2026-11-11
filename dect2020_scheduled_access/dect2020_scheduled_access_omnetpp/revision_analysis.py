#!/usr/bin/env python3
"""Reproducible major-revision fixed-slot results and original-grid CI audit.

This script never edits submitted/published Phase-2...Phase-6 outputs.
It records 95%-t intervals for independent simulation replications and
compares at common absolute Poisson arrival rates.
"""
import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODE = sys.argv[1] if len(sys.argv) > 1 else "revision-smoke"
SOURCE = HERE / "ci_results" / (MODE + "_scalars.csv")
OUT = HERE / "ci_results"
TCRIT = {1: 12.706204736, 2: 4.30265273, 3: 3.1824463,
         4: 2.776445105, 9: 2.262157163}
NUMERIC = ("D","r","L_effective","available_slots","slot_layout_code",
    "traffic_model_code","traffic_batch_size","lambda_per_ms",
    "lambda_sat_per_ms","load_factor_rho_over_rho_sat","blocking_probability",
    "mean_delay_direct_ms","mean_type1_number",
    "effective_throughput_departures_per_ms","mean_delay_little_ms",
    "delay_p95_ms","delay_p99_ms","slot_utilization","measured_arrivals")

def load(path):
    d = defaultdict(dict)
    with path.open(newline="") as f:
        for row in csv.DictReader(f):
            if row.get("type") != "scalar" or not row.get("module","").endswith(".queue"):
                continue
            try:
                d[row["run"]][row["name"]] = float(row["value"])
            except (ValueError, TypeError):
                pass
    return list(d.values())

def mean(x):
    return sum(x)/len(x)

def ci(x):
    n = len(x)
    if n < 2: return 0.0
    mu = mean(x)
    s = math.sqrt(sum((v-mu)**2 for v in x)/(n-1))
    t = TCRIT.get(n-1, 1.96 if n>30 else 2.3)
    return t*s/math.sqrt(n)

def save(path,rows):
    if not rows:return
    names = list(rows[0])
    with path.open("w",newline="") as f:
        w = csv.DictWriter(f,fieldnames=names)
        w.writeheader()
        w.writerows(rows)

runs = load(SOURCE)
if not runs:
    raise RuntimeError("No scalar runs in "+str(SOURCE))
groups = defaultdict(list)
for r in runs:
    key = tuple(r.get(k,-1) for k in ("D","r","available_slots",
                "slot_layout_code","traffic_model_code","lambda_per_ms"))
    groups[key].append(r)
rows = []
for key, samples in sorted(groups.items()):
    g = {"D":int(key[0]),"r":int(key[1]),"available_slots":int(key[2]),
         "slot_layout_code":int(key[3]),"traffic_model_code":int(key[4]),
         "lambda_per_ms":key[5],"repetitions":len(samples)}
    g["L"] = int(samples[0].get("L_effective",0))
    g["physical_lambda_sat_per_ms"] = samples[0].get("lambda_sat_per_ms",0)
    g["physical_load_factor"] = samples[0].get("load_factor_rho_over_rho_sat",0)
    for metric in ("blocking_probability","mean_delay_direct_ms",
        "mean_type1_number","effective_throughput_departures_per_ms",
        "mean_delay_little_ms","delay_p95_ms","delay_p99_ms","slot_utilization"):
        values = [s[metric] for s in samples if metric in s and math.isfinite(s[metric])]
        g[metric] = mean(values) if values else ""
        g[metric+"_ci95"] = ci(values) if len(values)>1 else ""
    rows.append(g)
summary = OUT/(MODE+"_summary.csv")
save(summary,rows)

mapping = []
for D in range(2,25):
    L = 24//D
    b = 10/24
    old_f = 10-10/D
    corrected_f = 10-L*b
    old_lam = L/(L*b+old_f)
    new_lam = L/10
    mapping.append(dict(D=D,L=L,original_F_ms=old_f,corrected_F_ms=corrected_f,
         original_capacity_per_ms=old_lam,physical_capacity_per_ms=new_lam,
         relative_capacity_overestimate_pct=100*(old_lam/new_lam-1)))
save(OUT/"revision_frame_mapping.csv",mapping)

# Original 270 independent runs; exact analytical values from frozen Phase-4 solver.
audit = []
legacy = HERE/"ci_results"/"phase2_metrics.csv"
if legacy.exists():
    oldruns=load(legacy)
    try:
        sys.path.insert(0,str(HERE.parent/"analysis"))
        import phase4_dimensioning as analytical
        bykey=defaultdict(list)
        for s in oldruns:
            if all(k in s for k in ("D","r","rho","mean_delay_direct_ms")):
                key=(int(s["D"]),int(s["r"]),round(s["rho"],12))
                bykey[key].append(s)
        for (D,r,rho),ss in sorted(bykey.items()):
            predicted=analytical.analytic_metrics(D,r,rho)
            row={"D":D,"r":r,"rho":rho,"repetitions":len(ss)}
            for simkey,analyticvalue in [
                ("mean_delay_direct_ms",predicted["mean_delay_ms"]),
                ("blocking_probability",predicted["blocking_probability"]),
                ("mean_type1_number",predicted["mean_number"]),
            ]:
                vals=[s[simkey] for s in ss]
                avg=mean(vals)
                half=ci(vals)
                row[simkey+"_sim"]=avg
                row[simkey+"_ci95"]=half
                row[simkey+"_analytical"]=analyticvalue
                row[simkey+"_covered"]=int(abs(analyticalvalue-avg)<=half)
            audit.append(row)
        save(OUT/"revision_phase2_ci_audit.csv",audit)
    except (ImportError,ModuleNotFoundError) as exc:
        print("WARNING: Phase-2 analytical CI audit unavailable:",exc)

# Controlled decomposition: original exponential queue, 10-ms-aligned
# exponential queue, 10-ms-aligned deterministic queue, and physical slots.
# Each is evaluated at the SAME absolute lambda, not at its own saturation.
comparisons = []
thresholds = []
try:
    sys.path.insert(0,str(HERE.parent/"analysis"))
    import phase4_dimensioning as a
    def queue_metrics(D,r,lam,aligned,deterministic):
        L=24//D
        b=10/24
        f=(10-L*b) if aligned else (10-10/D)
        nmax=r+4
        beta,bt=(a.det_counts(lam,b,nmax) if deterministic
                 else a.exp_counts(lam,nmax))
        phi,pt=a.det_counts(lam,f,nmax)
        P=a.transition_matrix(r,L,beta,phi,bt,pt)
        q=a.stationary(P)
        N,pi,v=a.reward_metrics(lam,r,L,f,q,bt,pt)
        return N,pi,v
    for g in rows:
        if g["traffic_model_code"] != 0 or g["available_slots"] != 24:
            continue
        D,r,lam=g["D"],g["r"],g["lambda_per_ms"]
        old=queue_metrics(D,r,lam,False,False)
        aligned=queue_metrics(D,r,lam,True,False)
        determ=queue_metrics(D,r,lam,True,True)
        row={"D":D,"r":r,"lambda_per_ms":lam,
             "load_factor_physical":g["physical_load_factor"],
             "fixed_slot_delay_ms":g["mean_delay_direct_ms"],
             "fixed_slot_delay_ci95":g["mean_delay_direct_ms_ci95"],
             "fixed_slot_blocking":g["blocking_probability"],
             "old_exponential_delay_ms":old[2],
             "aligned_exponential_delay_ms":aligned[2],
             "aligned_deterministic_delay_ms":determ[2],
             "old_exponential_blocking":old[1],
             "aligned_exponential_blocking":aligned[1],
             "aligned_deterministic_blocking":determ[1],
             "physical_minus_aligned_deterministic_delay_ms":g["mean_delay_direct_ms"]-determ[2],
             "physical_minus_aligned_deterministic_blocking":g["blocking_probability"]-determ[1]}
        comparisons.append(row)
    save(OUT/(MODE+"_model_comparison.csv"),comparisons)
    # Readouts for the three table configurations with original-vs-aligned
    # 1%, 5%, 10% blocking contours, evaluated at r=30.
    def threshold(D,aligned,target):
        b=10/24
        cap=(24//D)/10 if aligned else (24//D)/((24//D)*b+10-10/D)
        lo,hi=1e-10,2*cap
        for _ in range(40):
            m=queue_metrics(D,30,(lo+hi)/2,aligned,False)
            if m[1]<target:lo=(lo+hi)/2
            else:hi=(lo+hi)/2
        return (lo+hi)/2*b
    for D in (6,10,20):
        for target in (0.01,0.05,0.10):
            thresholds.append({"D":D,"r":30,"blocking_target":target,
                "original_rho_threshold":threshold(D,False,target),
                "aligned_rho_threshold":threshold(D,True,target)})
    save(OUT/"revision_blocking_thresholds.csv",thresholds)
except (ImportError,ModuleNotFoundError) as exc:
    print("WARNING: Analytical comparison requires numpy/matplotlib:",exc)

report=[
    "# Major-revision simulation: "+MODE,
    "",
    "Runs observed: "+str(len(runs)),
    "Independent configuration groups: "+str(len(rows)),
    "Summary: ci_results/"+MODE+"_summary.csv",
    "Full-frame correction: ci_results/revision_frame_mapping.csv",
    "Original model preserved: yes",
    "",
    "All physical metrics refer to one tagged PT with an explicit repeated",
    "10-ms / 24-slot allocation. This is an idealized slot-synchronous MAC",
    "benchmark, not a full radio PHY or ETSI conformance implementation.",
]
if comparisons:
    report += ["", "Physical vs queue-model comparisons: ci_results/"+MODE+"_model_comparison.csv",
               "Original/aligned blocking thresholds: ci_results/revision_blocking_thresholds.csv"]
if audit:
    hit=sum(x["mean_delay_direct_ms_covered"] for x in audit)
    report += ["","Original Phase-2 analytical delay within 95% replication CI:",
             str(hit)+"/"+str(len(audit)),
             "Audit: ci_results/revision_phase2_ci_audit.csv"]
for row in rows[:12]:
    report.append("D={D} r={r} lambda={lambda_per_ms:.6g}: delay={mean_delay_direct_ms:.5f}ms, blocking={blocking_probability:.6g}".format(**row))
(OUT/(MODE+"_report.md")).write_text("\n".join(report)+"\n")
print("\n".join(report))
