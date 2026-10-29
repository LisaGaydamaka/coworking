"""Read OMNeT++ scalars; save complete per-horizon comparisons and trend."""
import argparse,csv,re,statistics
from collections import defaultdict
from pathlib import Path
BASE=Path(__file__).resolve().parent
pa=argparse.ArgumentParser();pa.add_argument("--horizon",type=int,required=True);args=pa.parse_args()
folder=BASE/"results"/f"h{args.horizon}"
py=list(csv.DictReader((folder/"python_runs.csv").open()))
pym=defaultdict(list);pyd=defaultdict(list)
for x in py:
    p=float(x["arrProb"])
    if x["meanDelay"]:pym[p].append(float(x["meanDelay"]))
    pyd[p].append(int(x["deliveredUniquePackets"]))
omm=defaultdict(list);omd=defaultdict(list);oruns=[]
for sca in sorted((folder/"omnet").glob("p*_s*.sca")):
    found=re.fullmatch(r"p([0-8])_s(\d+)\.sca",sca.name)
    if not found:continue
    p=(int(found.group(1))+1)/100
    content=sca.read_text()
    rx=re.search(r"^scalar Cluster\.ft meanEndToEndDelay ([0-9.eE+-]+)",content,re.M)
    dx=re.search(r"^scalar Cluster\.ft deliveredUniquePackets (\d+)",content,re.M)
    if rx:omm[p].append(float(rx.group(1)))
    if dx:omd[p].append(int(dx.group(1)))
    oruns.append([p,int(found.group(2)),float(rx.group(1)) if rx else "",int(dx.group(1)) if dx else ""])
with (folder/"omnet_runs.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["arrProb","seed","meanDelay","deliveredUniquePackets"]);w.writerows(oruns)
rows=[]
for idx in range(1,10):
    p=idx/100
    if not (pym[p] and omm[p]):raise SystemExit(f"No delivered delay in both models for p={p}")
    pmean=statistics.mean(pym[p]);omean=statistics.mean(omm[p])
    pct=(omean-pmean)/pmean*100
    rows.append([args.horizon,p,len(pym[p]),pmean,statistics.stdev(pym[p]) if len(pym[p])>1 else 0,statistics.mean(pyd[p]),len(omm[p]),omean,statistics.stdev(omm[p]) if len(omm[p])>1 else 0,statistics.mean(omd[p]),pct])
    print(f"H={args.horizon}, arrProb={p:.2f}: Python={pmean:.1f}, OMNeT++={omean:.1f}, diff={pct:+.1f}%, delivered={statistics.mean(pyd[p]):.1f}/{statistics.mean(omd[p]):.1f}",flush=True)
with (folder/"comparison.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["horizon","arrProb","pythonRuns","pythonMean","pythonSD","pythonDelivered","omnetRuns","omnetMean","omnetSD","omnetDelivered","differencePct"]);w.writerows(rows)
mape=statistics.mean(abs(r[-1]) for r in rows)
maxerr=max(abs(r[-1]) for r in rows)
print(f"STUDY_SUMMARY horizon={args.horizon} MAPE={mape:.3f} MAX_ABS={maxerr:.3f}",flush=True)
with (folder/"summary.txt").open("w") as f:f.write(f"horizon={args.horizon}\nMAPE={mape}\nMAX_ABS={maxerr}\n")
try:
    import matplotlib;matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(8,4.5))
    ax.plot([r[1] for r in rows],[r[3] for r in rows],marker="o",label="Python")
    ax.plot([r[1] for r in rows],[r[7] for r in rows],marker="s",label="OMNeT++")
    ax.set(title=f"20 PT: horizon={args.horizon} symbols",xlabel="arrProb",ylabel="Mean delay to first delivery (symbols)")
    ax.grid(alpha=.3);ax.legend();fig.tight_layout();fig.savefig(folder/"comparison.png",dpi=150);plt.close(fig)
except ImportError:pass
