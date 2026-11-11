#!/usr/bin/env python3
"""Final publication tables and figures after two GitHub Actions completion checks.

Source: original frozen Phase-2 results, full revision physical simulations,
and the final 90+100 OMNeT++ runs. No input data is rewritten.

Output figures and CSV are explicitly conditioned on:
(1) all nine final D=2/13/24 physical points with ten repetitions each;
(2) all five extended original near-saturation points with twenty repetitions.
"""
import csv
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import phase4_dimensioning as a

ROOT=Path(__file__).resolve().parent
SRC=ROOT.parent/"dect2020_scheduled_access_omnetpp"/"ci_results"
OUT=ROOT/"revision_output"
OUT.mkdir(exist_ok=True)
B=10.0/24.0

def load(path):
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write(filename, rows):
    if not rows:raise RuntimeError("No rows for "+filename)
    with (OUT/filename).open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def aligned_queue(D,r,lam,det=False):
    L=24//D
    mF=10-L*B
    p,bt=(a.det_counts(lam,B,r+4) if det else a.exp_counts(lam,r+4))
    phi,pt=a.det_counts(lam,mF,r+4)
    P=a.transition_matrix(r,L,p,phi,bt,pt)
    q=a.stationary(P)
    N,pi,v=a.reward_metrics(lam,r,L,mF,q,bt,pt)
    return N,pi,v

def find_threshold(D,target):
    L=24//D
    lo,hi=0.,2*L/10.
    for _ in range(36):
        mid=(lo+hi)/2
        if aligned_queue(D,30,mid)[1]<target:lo=mid
        else:hi=mid
    return (lo+hi)/2

# 1, 5, 10% contours: new exact points for D=2,13,24 and existing
# 5-rep points for D=6,10,20. Rates matched to earlier planned grids.
rates={
 2:(1.160952429723,1.254030294175,1.332014486309),
 6:(0.39245,0.4196,0.4443),
 10:(0.19670,0.20992,0.22218),
 13:(0.098443918923,0.104979509711,0.111092379637),
 20:(0.09844,0.10498,0.11109),
 24:(0.098443918923,0.104979509711,0.111092379637),
}
allr=load(SRC/"revision-dimensioning_summary.csv")+load(SRC/"revision-final-physical_summary.csv")
physical={}
for row in allr:
    if int(row["r"])!=30 or int(row["available_slots"])!=24:continue
    key=(int(row["D"]),round(float(row["lambda_per_ms"]),10))
    physical[key]=row
dimensioning=[]
for D in sorted(rates):
    for i,lam in enumerate(rates[D]):
        key=(D,round(lam,10))
        if key not in physical:
            raise RuntimeError("Missing physical experiment "+str(key))
        z=physical[key]
        reps=int(z["repetitions"])
        if reps!=(10 if D in (2,13,24) else 5):
            raise RuntimeError("Unexpected replication count "+str(key)+" "+str(reps))
        target=(0.01,0.05,0.10)[i]
        _,exp_pi,exp_v=aligned_queue(D,30,lam,det=False)
        _,det_pi,det_v=aligned_queue(D,30,lam,det=True)
        mu=float(z["mean_delay_direct_ms"])
        pi=float(z["blocking_probability"])
        p99=float(z["delay_p99_ms"])
        dimensioning.append({
         "D":D,"r":30,"L":24//D,"target_blocking":target,
         "lambda_per_ms":lam,"physical_load_factor":float(z["physical_load_factor"]),
         "replications":reps,
         "physical_blocking":pi,"physical_blocking_ci95":float(z["blocking_probability_ci95"]),
         "physical_mean_delay_ms":mu,"physical_mean_delay_ci95":float(z["mean_delay_direct_ms_ci95"]),
         "physical_p99_ms":p99,"physical_p99_ci95":float(z["delay_p99_ms_ci95"]),
         "aligned_exp_blocking":exp_pi,"aligned_exp_mean_delay_ms":exp_v,
         "aligned_det_blocking":det_pi,"aligned_det_mean_delay_ms":det_v,
         "physical_minus_aligned_det_delay_ms":mu-det_v,
         "relative_aligned_det_delay_error_pct":100*(det_v/mu-1),
         "corrected_contour_lambda_per_ms":find_threshold(D,target)
        })
write("revision_final_sixD_dimensioning.csv",dimensioning)
write("revision_final_missing_D_points.csv",
      [z for z in dimensioning if z["D"] in (2,13,24)])

# Long-run original exact analytical predictions; original 270-run data are frozen.
newrows=load(SRC/"revision-final-saturation_summary.csv")
if len(newrows)!=5:raise RuntimeError("Expected exactly five long-run saturation cases")
audits=[]
for z in sorted(newrows,key=lambda z:(int(z["D"]),int(z["r"]))):
    D,r=int(z["D"]),int(z["r"])
    rho=float(z["rho"])
    analytic=a.analytic_metrics(D,r,rho)
    rec={"D":D,"r":r,"rho":rho,
      "repetitions_original":int(z["old_repetitions"]),
      "repetitions_longrun":int(z["new_repetitions"]),
      "warmup_completions_longrun":int(z["warmup_new"]),
      "measured_completions_per_rep_longrun":int(z["measured_completed_new_per_rep"]),
    }
    for col,expected in (
       ("mean_delay_direct_ms",analytic["mean_delay_ms"]),
       ("blocking_probability",analytic["blocking_probability"]),
       ("mean_type1_number",analytic["mean_number"])
    ):
        oldmu=float(z[col+"_old_mean"])
        oldhw=float(z[col+"_old_ci95_halfwidth"])
        newmu=float(z[col+"_new_mean"])
        newhw=float(z[col+"_new_ci95_halfwidth"])
        rec.update({
         col+"_analytical":expected,
         col+"_original_mean":oldmu,
         col+"_original_ci95":oldhw,
         col+"_original_covered":int(abs(oldmu-expected)<=oldhw),
         col+"_longrun_mean":newmu,
         col+"_longrun_ci95":newhw,
         col+"_longrun_covered":int(abs(newmu-expected)<=newhw),
         col+"_longrun_relerror_pct":100*(newmu/expected-1) if expected!=0 else 0.0,
        })
    audits.append(rec)
write("revision_final_saturation_five_cases.csv",audits)

# Graph A: actual blocking probabilities versus device count for 1/5/10%
# rate-based contour targets, with replicate-level errorbars.
fig,ax=plt.subplots(figsize=(7.7,5.1))
for target,marker in ((0.01,"o"),(0.05,"s"),(0.10,"^")):
    rr=[z for z in dimensioning if z["target_blocking"]==target]
    ax.errorbar([z["D"] for z in rr],[z["physical_blocking"] for z in rr],
                yerr=[z["physical_blocking_ci95"] for z in rr],
                marker=marker,linewidth=1.6,capsize=2.5,
                label="Nominal %.0f%% blocking contour"%(100*target))
    ax.axhline(target,linestyle=":",linewidth=.7,color="gray")
ax.set_xticks(sorted(rates))
ax.set_xlabel("PT device count D")
ax.set_ylabel("Fixed-slot blocking probability")
ax.legend(fontsize=8);ax.grid(alpha=.24)
fig.tight_layout()
fig.savefig(OUT/"revision_final_sixD_blocking_validation.pdf")
fig.savefig(OUT/"revision_final_sixD_blocking_validation.png",dpi=260)
plt.close(fig)

# Graph B: original 5 simulations at old sampling effort vs 20 longer
# original-queue runs, with EXACT analytical predictions at each case.
fig,ax=plt.subplots(figsize=(8,5))
x=np.arange(len(audits))
orig=[100*(r["mean_delay_direct_ms_original_mean"]/r["mean_delay_direct_ms_analytical"]-1) for r in audits]
long=[r["mean_delay_direct_ms_longrun_relerror_pct"] for r in audits]
origerr=[100*r["mean_delay_direct_ms_original_ci95"]/r["mean_delay_direct_ms_analytical"] for r in audits]
longerr=[100*r["mean_delay_direct_ms_longrun_ci95"]/r["mean_delay_direct_ms_analytical"] for r in audits]
ax.errorbar(x-.12,orig,yerr=origerr,fmt="o",capsize=3,label="Original: 10 × 1 million")
ax.errorbar(x+.12,long,yerr=longerr,fmt="s",capsize=3,label="Long-run: 20 × 5 million")
ax.axhline(0,linestyle="--",linewidth=1,color="black",label="Exact analytical prediction")
ax.set_xticks(x,["D%d, r%d"%(r["D"],r["r"]) for r in audits])
ax.set_ylabel("Simulation minus analytical delay / analytical delay [%]")
ax.legend(fontsize=8);ax.grid(alpha=.25)
fig.tight_layout()
fig.savefig(OUT/"revision_final_saturation_convergence.pdf")
fig.savefig(OUT/"revision_final_saturation_convergence.png",dpi=260)
plt.close(fig)

# Graph C: 18 fixed-slot dimensions vs frame-aligned deterministic model.
fig,ax=plt.subplots(figsize=(7,5.1))
for target,marker in ((0.01,"o"),(0.05,"s"),(0.10,"^")):
    rr=[z for z in dimensioning if z["target_blocking"]==target]
    ax.plot([z["D"] for z in rr],[z["relative_aligned_det_delay_error_pct"] for z in rr],
            marker+"-",linewidth=1.3,label="Nominal %.0f%% blocking"%(target*100))
ax.axhline(0,color="black",linestyle="--",linewidth=1)
ax.set_xticks(sorted(rates))
ax.set_xlabel("PT device count D")
ax.set_ylabel("Frame-aligned deterministic mean-delay error [%]")
ax.grid(alpha=.25);ax.legend(fontsize=8);fig.tight_layout()
fig.savefig(OUT/"revision_final_sixD_delay_approximation_error.pdf")
fig.savefig(OUT/"revision_final_sixD_delay_approximation_error.png",dpi=260)
plt.close(fig)

# Summary is designed to be concise and directly translatable to Results.
full_coverage=sum(r["mean_delay_direct_ms_longrun_covered"] for r in audits)
worst=max(audits,key=lambda r:abs(r["mean_delay_direct_ms_longrun_relerror_pct"]))
lines=[
 "# Final pre-manuscript experiment audit (GitHub Actions)",
 "",
 "## Experimental scope",
 "- New physical-slot Table-4 checks: 3 D values x 3 rates x 10 replications = 90 runs.",
 "- Extended original-simulator audit: 5 cases x 20 replications = 100 runs.",
 "- Original model: 1 million warm-up and 5 million measured admitted completions/run.",
 "- Source code: original vacation-queue C++ unchanged; physical model idealized 10-ms/24-slot MAC.",
 "",
 "## Five exact finite-load original-queue checks",
 "- Analytical mean within long-run 95% CI: %d/5 cases."%full_coverage,
 "- Largest absolute long-run relative mean-delay error: D=%d, r=%d, %.5f%%."%
     (worst["D"],worst["r"],abs(worst["mean_delay_direct_ms_longrun_relerror_pct"])),
 ]
for z in audits:
    lines.append("- D=%d, r=%d: analytical %.6f ms; long-run %.6f +/- %.6f ms (95%%); covered=%s."%
     (z["D"],z["r"],z["mean_delay_direct_ms_analytical"],
      z["mean_delay_direct_ms_longrun_mean"],z["mean_delay_direct_ms_longrun_ci95"],
      bool(z["mean_delay_direct_ms_longrun_covered"])))
lines+=["","## Fixed-slot six-D dimensioning"]
for D in sorted(rates):
    rr=[z for z in dimensioning if z["D"]==D]
    lines.append("- D=%d, L=%d; fixed-slot blocking at nominal 1%%,5%%,10%%: %s."%
     (D,24//D,", ".join("%.4f%%"%(100*z["physical_blocking"]) for z in rr)))
lines+=["","## Manuscript-ready items",
"- Table: revision_final_saturation_five_cases.csv",
"- Table: revision_final_sixD_dimensioning.csv",
"- Figure: revision_final_saturation_convergence.pdf",
"- Figure: revision_final_sixD_blocking_validation.pdf",
"- Figure: revision_final_sixD_delay_approximation_error.pdf",
"",
"Interpretation caveat: nominal 1/5/10% targets are analytical design points; empirical fixed-slot probabilities are separately shown.",
"Do not claim full ETSI PHY conformance or independent in-network multi-user scheduling based on the tagged-PT scheduler."]
(OUT/"revision_final_publication_report.md").write_text("\n".join(lines)+"\n")
print("\n".join(lines))
