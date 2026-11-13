#!/usr/bin/env python3
"""Publication-ready corrected DECT-2020 scheduled-access figures.

Unmodified source: phase4_dimensioning.py's classical finite-buffer
stationary/occupation-time solver. This revision is isolated: no writes to
the submitted manuscript, published phase4_output, or old simulation data.

Main corrected dimensional plots use B=10/24ms deterministic slots and
F=10-L*(10/24)ms. Both service laws are retained in the companion CSV;
the old exponential F=10-10/D runs remain historically labeled.
"""
from pathlib import Path
from functools import lru_cache
import csv
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np
import phase4_dimensioning as legacy

HERE = Path(__file__).resolve().parent
OUT = HERE / "revision_output"
DATA = HERE.parent / "dect2020_scheduled_access_omnetpp" / "ci_results"
OUT.mkdir(exist_ok=True)
MB = 10.0 / 24.0
R_MAP = 30
DS = list(range(2,25))
TARGETS=(0.01,0.05,0.10,0.50)
SERVICE_MODES=("deterministic","exponential")

def write_csv(name, rows):
    if not rows:raise RuntimeError("Empty output: "+name)
    with (OUT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

def read_csv(name):
    with (DATA/name).open("r",encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

@lru_cache(maxsize=20000)
def metrics(L,r,rho,mode):
    """Return (mean delay, blocking, mean number) at offered rho.
    Exactly one complete time-quantized slot per scheduled opportunity.
    """
    if rho == 0.0:
        return 0.,0.,0.
    lam = rho/MB
    f = 10.-L*MB
    nmax=r+4
    if mode=="deterministic":
        beta,bt=legacy.det_counts(lam,MB,nmax)
    elif mode=="exponential":
        beta,bt=legacy.exp_counts(lam,nmax)
    else:
        raise ValueError(mode)
    phi,pt=legacy.det_counts(lam,f,nmax)
    P=legacy.transition_matrix(r,L,beta,phi,bt,pt)
    if np.max(abs(P.sum(axis=1)-1))>1e-8:
        raise RuntimeError("Transition matrix normalization failed")
    q=legacy.stationary(P)
    N,pi,delay=legacy.reward_metrics(lam,r,L,f,q,bt,pt)
    if not 0<=pi<=1 or not np.isfinite(delay):
        raise RuntimeError("Nonphysical queue result")
    return delay,pi,N

def rho_at_pi(L,r,target,mode):
    lo=0.0
    hi=max(.1,2*(L*MB/10.0))
    for _ in range(40):
        mid=.5*(hi+lo)
        if metrics(L,r,mid,mode)[1] < target:
            lo=mid
        else:
            hi=mid
    return (lo+hi)/2.

def plot_operating_map():
    """Replacement Figure B: r=30, deterministic scheduled slot baseline."""
    load_grid=np.linspace(0,0.55,151)
    byL=sorted(set(24//D for D in DS))
    computed={}
    for L in byL:
        values=np.array([metrics(L,R_MAP,float(rho),"deterministic")[1]
                         if rho>0 else 0.0 for rho in load_grid],dtype=float)
        computed[L]=values
    Z=np.stack([computed[24//D] for D in DS],axis=1)
    maprows=[]
    for j,D in enumerate(DS):
        for k,rho in enumerate(load_grid):
            maprows.append({
                "D":D,"L":24//D,"r":R_MAP,"rho":float(rho),
                "lambda_per_ms":float(rho)/MB,
                "blocking_probability":float(Z[k,j]),
                "mF_frame_aligned_ms":10.-(24//D)*MB,
                "service_distribution":"deterministic"})
    write_csv("revision_corrected_operating_map.csv",maprows)

    thresholds=[]
    curves={t:[] for t in TARGETS}
    for D in DS:
        L=24//D
        row={"D":D,"L":L,"r":R_MAP,"mB_ms":MB,
             "mF_frame_aligned_ms":10.-L*MB,
             "lambda_sat_per_ms":L/10.,"rho_sat":L*MB/10.}
        for mode in SERVICE_MODES:
            for t in TARGETS:
                rho=rho_at_pi(L,R_MAP,t,mode)
                row["rho_"+mode+"_at_pi_"+str(int(t*100))+"pct"]=rho
                row["lambda_"+mode+"_at_pi_"+str(int(t*100))+"pct"]=rho/MB
                if mode=="deterministic":
                    curves[t].append(rho)
        thresholds.append(row)
    write_csv("revision_corrected_dimensioning_thresholds.csv",thresholds)
    write_csv("revision_corrected_selected_table4.csv",
              [x for x in thresholds if x["D"] in [2,6,10,13,20,24]])
    dr=float(load_grid[1]-load_grid[0])
    y_edges=np.concatenate(([0.0], load_grid+dr/2.0))
    fig,ax=plt.subplots(figsize=(8.4,5.5))
    mesh=ax.pcolormesh(np.arange(1.5,25.5,1.0),
                       y_edges,Z,shading="flat",cmap="viridis",vmin=0,vmax=1)
    bar=fig.colorbar(mesh,ax=ax,pad=.02)
    bar.set_label("Blocking probability π")
    for t in TARGETS:
        ax.plot(DS,curves[t],drawstyle="steps-mid",lw=1.5,
                label=f"π={100*t:.0f}%")
    ax.plot(DS,[24//D*MB/10. for D in DS],drawstyle="steps-mid",
            ls="--",lw=2.0,label="Frame-aligned saturation")
    ax.set_xlim(1.5,24.5);ax.set_ylim(0,.55)
    ax.set_xticks([2,4,6,8,10,12,14,16,18,20,22,24])
    ax.set_xlabel("Number of PT devices D")
    ax.set_ylabel("Offered load ρ = λmB")
    ax.set_title("Frame-aligned deterministic-slot dimensioning (r = 30)")
    ax.legend(loc="upper right",fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/"revision_corrected_figure_B_operating_map.pdf")
    fig.savefig(OUT/"revision_corrected_figure_B_operating_map.png",dpi=280)
    plt.close(fig)
    return thresholds

def plot_delay_loss():
    """Replacement Figure C: D10, corrected F=9.1667ms, deterministic B."""
    L=2;D=10
    rvals=range(1,51)
    factors=[.8,1.0,1.2]
    rows=[]
    fig,ax=plt.subplots(figsize=(7.9,5.3))
    for fac in factors:
        rr=[]
        for r in rvals:
            delay,pi,N=metrics(L,r,fac*L*MB/10.,"deterministic")
            rr.append({"D":D,"L":L,"r":r,"load_factor":fac,
                       "rho":fac*L*MB/10.,"lambda_per_ms":fac*L/10.,
                       "blocking_probability":pi,"mean_delay_ms":delay,
                       "mean_number":N,"mF_ms":10.-L*MB,
                       "service_distribution":"deterministic"})
        rows+=rr
        ax.plot([x["blocking_probability"] for x in rr],
                [x["mean_delay_ms"] for x in rr],
                marker="o",markersize=2.0,lw=1.55,
                label=f"ρ/ρsat = {fac:.1f}")
        # Label only TWO r values on one curve, not every point;
        # resolves reviewer concern about overlapping original r labels.
        if fac==1.0:
            for rv,delta in [(10,(7,7)),(40,(7,-10))]:
                point=rr[rv-1]
                if 1e-4<=point["blocking_probability"]<=0.6:
                    ax.annotate(f"r={rv}",
                     xy=(point["blocking_probability"],point["mean_delay_ms"]),
                     xytext=delta,textcoords="offset points",fontsize=8)
    write_csv("revision_corrected_delay_loss_tradeoff.csv",rows)
    ax.set_xscale("log")
    ax.set_xlim(1e-4,.6)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("Blocking probability π (logarithmic)")
    ax.set_ylabel("Mean admitted-packet sojourn time [ms]")
    ax.set_title("Frame-aligned deterministic-slot queue (D = 10)")
    ax.legend(loc="upper left",fontsize=8)
    ax.grid(True,alpha=.3,lw=.5)
    fig.tight_layout()
    fig.savefig(OUT/"revision_corrected_figure_C_delay_loss.pdf")
    fig.savefig(OUT/"revision_corrected_figure_C_delay_loss.png",dpi=280)
    plt.close(fig)

def plot_fixed_slot_tail():
    """Main replacement Figure D: independent fixed-clock OMNeT++ mean/P95/P99."""
    records=read_csv("revision-tail_summary.csv")
    data=sorted([z for z in records if int(z["D"])==10 and int(z["r"])==30
                 and int(z["available_slots"])==24
                 and int(z["slot_layout_code"])==0
                 and int(z["traffic_model_code"])==0],
                key=lambda x:float(x["physical_load_factor"]))
    if len(data)!=10:
        raise RuntimeError("Expected 10 fixed-slot tail-latency grid points")
    x=[float(z["physical_load_factor"]) for z in data]
    fig,ax=plt.subplots(figsize=(8.1,5.0))
    specs=[
       ("mean_delay_direct_ms","Mean sojourn","o"),
       ("delay_p95_ms","P95","s"),
       ("delay_p99_ms","P99","^"),
    ]
    for key,label,marker in specs:
        ax.errorbar(x,[float(z[key]) for z in data],
            yerr=[float(z[key+"_ci95"]) for z in data],
            label=label,marker=marker,capsize=2.5,markersize=4,lw=1.65)
    ax.axvline(1.0,color="gray",lw=1.1,ls="--",label="Fixed-slot capacity")
    ax.set_xscale("log")
    ax.set_xticks([.5,.7,.8,.9,1.,1.1,1.2,1.5,2.,5.])
    ax.set_xticklabels(["0.5","0.7","0.8","0.9","1.0",
                        "1.1","1.2","1.5","2.0","5.0"],fontsize=8)
    ax.set_xlim(.48,5.15)
    ax.set_xlabel("λ / (L/10 ms), logarithmic axis")
    ax.set_ylabel("Admitted-packet sojourn [ms]")
    ax.set_title("Fixed-slot mean, P95 and P99 (D=10, r=30)")
    ax.grid(alpha=.28,lw=.45)
    ax.legend(loc="lower right",fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/"revision_fixed_slot_figure_D_tail_latency.pdf")
    fig.savefig(OUT/"revision_fixed_slot_figure_D_tail_latency.png",dpi=280)
    plt.close(fig)

def plot_traffic_sensitivity():
    r=read_csv("revision-traffic_summary.csv")
    labels={0:"Poisson",1:"Periodic (random phase)",
            2:"Synchronized periodic",3:"Compound-Poisson bursty"}
    fig,ax=plt.subplots(figsize=(7.7,4.9))
    for code in (0,1,2,3):
        p=sorted([z for z in r if int(z["traffic_model_code"])==code],
                 key=lambda x:float(x["lambda_per_ms"]))
        ax.errorbar([float(z["lambda_per_ms"]) for z in p],
                    [100*float(z["blocking_probability"]) for z in p],
                    yerr=[100*float(z["blocking_probability_ci95"]) for z in p],
                    marker="o",capsize=2.5,lw=1.5,label=labels[code])
    ax.axvline(.2,ls="--",color="gray",lw=1)
    ax.set_xlabel("Mean offered packet rate [packets/ms]")
    ax.set_ylabel("Fixed-slot blocking probability [%]")
    ax.set_title("Equal-rate arrival-process sensitivity (D=10, r=30)")
    ax.grid(alpha=.3);ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/"revision_traffic_sensitivity_blocking.pdf")
    fig.savefig(OUT/"revision_traffic_sensitivity_blocking.png",dpi=280)
    plt.close(fig)

def plot_geometry():
    geom=read_csv("revision-geometry_summary.csv")
    tail=read_csv("revision-tail_summary.csv")
    # A matched D10/r30/24-slot contiguous-versus-distributed comparison;
    # check rate, slots and device count for every matched pair.
    a={(round(float(z["lambda_per_ms"]),8)):z for z in tail
        if int(z["D"])==10 and int(z["r"])==30
        and int(z["available_slots"])==24 and int(z["slot_layout_code"])==0}
    b={(round(float(z["lambda_per_ms"]),8)):z for z in geom
        if int(z["D"])==10 and int(z["r"])==30
        and int(z["available_slots"])==24 and int(z["slot_layout_code"])==1}
    rates=sorted(set(a)&set(b))
    if len(rates)<4:raise RuntimeError("Not enough matched geometry points")
    fig,ax=plt.subplots(figsize=(7.7,4.9))
    for dataset,label,marker in ((a,"Contiguous slots","o"),
                                 (b,"Distributed slots","s")):
        ax.errorbar(rates,[float(dataset[k]["delay_p99_ms"]) for k in rates],
                    yerr=[float(dataset[k]["delay_p99_ms_ci95"]) for k in rates],
                    marker=marker,capsize=2,lw=1.5,label=label)
    ax.set_xlabel("Mean offered packet rate [packets/ms]")
    ax.set_ylabel("Fixed-slot P99 sojourn time [ms]")
    ax.set_title("Slot-placement sensitivity (D=10, r=30)")
    ax.grid(alpha=.3);ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT/"revision_slot_position_sensitivity_p99.pdf")
    fig.savefig(OUT/"revision_slot_position_sensitivity_p99.png",dpi=280)
    plt.close(fig)

    # FT resource reservation: theoretical change in saturated packet rate.
    caps=[]
    for D in range(2,25):
        row={"D":D}
        for S in (24,22):
            L=S//D
            row[f"available_{S}_L"]=L
            row[f"available_{S}_capacity_packets_ms"]=L/10. if L>=1 else ""
        caps.append(row)
    write_csv("revision_FT_slot_reservation_capacity.csv",caps)
    fig,ax=plt.subplots(figsize=(7.7,4.5))
    for S,marker in ((24,"o"),(22,"s")):
        xs=[z["D"] for z in caps if z[f"available_{S}_L"]>=1]
        ys=[z[f"available_{S}_capacity_packets_ms"] for z in caps if z[f"available_{S}_L"]>=1]
        ax.step(xs,ys,where="mid",label=f"{S} PT-eligible slots",lw=1.6)
        ax.scatter(xs,ys,s=12,marker=marker)
    ax.set_xlabel("Number of PT devices D")
    ax.set_ylabel("Theoretical saturated rate [packets/ms]")
    ax.set_title("Effect of reserving two slots for FT/control")
    ax.legend(fontsize=8);ax.grid(alpha=.25)
    fig.tight_layout()
    fig.savefig(OUT/"revision_FT_slot_reservation_capacity.pdf")
    fig.savefig(OUT/"revision_FT_slot_reservation_capacity.png",dpi=280)
    plt.close(fig)

def make_manifest(thresholds):
    d10=next(z for z in thresholds if z["D"]==10)
    lines=[
        "# Supplementary publication assets for the MDPI Sensors major revision",
        "",
        "All generated assets are **new**. No original manuscript, original",
        "Phase-2...Phase-6 figure or raw experiment data is modified.",
        "Corrected mapping: L=floor(24/D), B=10/24ms and F=10-L*B.",
        "",
        "## New/replacement figures",
        "",
        "| Role | Figure source | Recommended placement |",
        "|---|---|---|",
        "| Replace submitted operating-regime Figure B | revision_corrected_figure_B_operating_map.pdf | Main Section 5.1 |",
        "| Replace submitted delay-loss Figure C | revision_corrected_figure_C_delay_loss.pdf | Main Section 5.2 |",
        "| Replace submitted Figure D (old vacation queue tail) | revision_fixed_slot_figure_D_tail_latency.pdf | Main Section 6 |
        "| 27-case physical vs abstract analytical model | revision_27case_mean_delay_comparison.pdf | Main Section 4 |",
        "| Six-D physical blocking validation | revision_final_sixD_blocking_validation.pdf | Main Section 5 |",
        "| Physical vs original P99 comparison | revision_physical_vs_original_tail_p99.pdf | Main Section 6; optional if space limited |",
        "| Three-distribution corrected service variability P99 | revision_corrected_service_variability_p99.pdf | Supplementary (optional by author preference) |",
        "| Five-case original CI convergence | revision_final_saturation_convergence.pdf | Supplementary |",
        "| Six-D deterministic approximation error | revision_final_sixD_delay_approximation_error.pdf | Supplementary |",
        "| Arrival-process blocking sensitivity | revision_traffic_sensitivity_blocking.pdf | Supplementary |",
        "| Slot placement P99 sensitivity | revision_slot_position_sensitivity_p99.pdf | Supplementary |",
        "| Reserved FT slot capacity sensitivity | revision_FT_slot_reservation_capacity.pdf | Supplementary |",
        "",
        "## Numeric source files",
        "",
        "- revision_corrected_dimensioning_thresholds.csv: 23 D-values, r=30,",
        "  corrected deterministic AND exponential 1/5/10/50% contours.",
        "- revision_corrected_selected_table4.csv: six selected D-values.",
        "- revision_corrected_operating_map.csv: every map grid point.",
        "- revision_corrected_delay_loss_tradeoff.csv: 150 corrected trade-off points.",
        "- revision_FT_slot_reservation_capacity.csv: exact effective capacities for S=24,22.",
        "- revision_final_sixD_dimensioning.csv: empirical 18-point blocking/mean/P99.",
        "- revision_final_saturation_five_cases.csv: five long-run CI checks.",
        "",
        "## Consistency rules",
        "",
        "1. Leave Section 4's legacy validation Table 1 and its original F=10-10/D",
        "   values unchanged as a historical stochastic-model verification.",
        "2. Cite the corrected mapping for ALL revised Section-5 figures and table",
        "   read-outs. Do NOT quote the legacy D=10 0.08335/0.08895/0.09414",
        "   blocking thresholds for the corrected cycle.",
        "3. Distinguish deterministic service baseline (new map/trade-off) from",
        "   exponential service (original 27-run analytical verification).",
        "4. Physical fixed-slot percentages at the EXPONENTIAL analytical",
        "   contour design rates are not exactly nominal: e.g. D=2 ~0.6723%",
        "   at the nominal 1% rate. The deterministic baseline is closer;",
        "   the two contour definitions must never be silently conflated.",
        "5. The corrected capacity is constant within D ranges sharing the",
        "   same integer L; the original paper's within-band slopes caused",
        "   by F=10-10/D must be deleted from Section 5.1.",
        "6. The idealized tagged PT has fixed slots, not a detailed DECT radio",
        "   implementation. Coexistence, FT signaling and interference",
        "   are not represented at PHY level.",
        "7. Maintain explicit fixed normalized-load definitions on all figures.",
        "",
        "## D=10 corrected deterministic blocking thresholds",
        "",
        f"- 1%: rho={d10['rho_deterministic_at_pi_1pct']:.10f}",
        f"- 5%: rho={d10['rho_deterministic_at_pi_5pct']:.10f}",
        f"- 10%: rho={d10['rho_deterministic_at_pi_10pct']:.10f}",
        "",
        "The companion revised-manuscript checklist will handle",
        "the exact reviewer-by-reviewer text replacements; the manuscript",
        "itself remains unedited.",
    ]
    (OUT/"revision_corrected_assets_manifest.md").write_text("\n".join(lines)+"\n",
        encoding="utf-8")
    print("\n".join(lines))

def main():
    thresholds=plot_operating_map()
    plot_delay_loss()
    plot_fixed_slot_tail()
    plot_traffic_sensitivity()
    plot_geometry()
    make_manifest(thresholds)

if __name__=="__main__":
    main()
