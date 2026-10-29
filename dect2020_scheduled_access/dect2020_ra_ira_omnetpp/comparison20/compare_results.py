"""Aggregate OMNeT++ .sca scalars and compare to matched Python means."""
from pathlib import Path
import csv,re,statistics
from collections import defaultdict
HERE=Path(__file__).resolve().parent; OUT=HERE/"results"
py={float(x["arrProb"]):x for x in csv.DictReader((OUT/"python_aggregate.csv").open())}
by=defaultdict(list);per=[]
for path in sorted((OUT/"omnet").glob("p*_s*.sca")):
    m=re.fullmatch(r"p([0-8])_s(\d+)\.sca",path.name)
    if m is None:continue
    p=(int(m.group(1))+1)/100
    text=path.read_text()
    d=re.search(r"^scalar Cluster\.ft meanEndToEndDelay ([0-9.eE+-]+)",text,re.M)
    count=re.search(r"^scalar Cluster\.ft deliveredUniquePackets (\d+)",text,re.M)
    v=float(d.group(1)) if d else None
    per.append([p,int(m.group(2)),v if v is not None else "",int(count.group(1)) if count else ""])
    if v is not None:by[p].append(v)
if not per:raise SystemExit("No OMNeT++ sweeps found")
with (OUT/"omnet_runs.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["arrProb","seed","meanDelay","deliveredUniquePackets"]);w.writerows(per)
rows=[]
for p in sorted(py):
    vs=by[p]
    pv=float(py[p]["meanDelay"]) if py[p]["meanDelay"] else None
    om=statistics.mean(vs) if vs else None
    sd=statistics.stdev(vs) if len(vs)>1 else None
    delta=(om-pv) if om is not None and pv is not None else None
    percent=(100*delta/pv) if delta is not None and pv else None
    rows.append([p,int(py[p]["validRuns"]),pv,py[p]["sdBetweenRuns"],len(vs),om,sd,delta,percent])
    print(f"p={p:.2f}: Python={pv:.2f}; OMNeT++={om:.2f}; difference={percent:+.1f}%",flush=True)
with (OUT/"comparison.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["arrProb","pythonRuns","pythonMean","pythonSD","omnetRuns","omnetMean","omnetSD","omnetMinusPython","differencePct"]);w.writerows(rows)
try:
    import matplotlib;matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,5))
    ax.plot([r[0] for r in rows],[r[2] for r in rows],"o-",label="Python: first delivery")
    ax.plot([r[0] for r in rows],[r[5] for r in rows],"s--",label="OMNeT++: first delivery")
    ax.set(title="DECT-2020 RA: 20 PT, CW=1..16, 3000 symbols",xlabel="arrProb",ylabel="Mean end-to-end delay (symbols)")
    ax.grid(alpha=.25);ax.legend();fig.tight_layout();fig.savefig(OUT/"comparison.png",dpi=160)
except ImportError:pass
