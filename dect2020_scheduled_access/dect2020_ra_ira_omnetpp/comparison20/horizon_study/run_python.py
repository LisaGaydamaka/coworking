"""Python DECT-2020 RA, extended-horizon comparison, no protocol changes."""
import argparse, contextlib, csv, importlib.util, io, random, statistics
from pathlib import Path
import numpy as np

BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("dect_ref", BASE.parent.parent/"comparison"/"4_random_access_final.py")
sim=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

parser=argparse.ArgumentParser()
parser.add_argument("--horizon",type=int,required=True)
parser.add_argument("--repetitions",type=int,default=5)
args=parser.parse_args()
sim.cluster_count=1
sim.devices_in_cluster_count=20
sim.c_min=1
sim.c_max=16
sim.model_time=args.horizon
sim.trans_time=10
sim.proc_time=10
sim.ack_time=5
sim.lbt_time=2
sim.arrival_type="arrprob"
sim.lbt_always_succ=False
sim.ack_delivery_always_succ=False
sim.c_min_for_retry=False

out=BASE/"results"/f"h{args.horizon}"
out.mkdir(parents=True,exist_ok=True)
runs=[]
for p_int in range(1,10):
    p=p_int/100
    for seed in range(1,args.repetitions+1):
        random.seed(seed)
        np.random.seed(seed)
        sim.arrprob=p
        sim.setup()
        with contextlib.redirect_stdout(io.StringIO()):
            sim.main()
        d=sim.sim_delay(sim.clusters[0])
        delivered=sum(len(pt.delivered_packets) for pt in sim.clusters[0].PT_devices)
        generated=sim.devices_in_cluster_count*p*args.horizon
        runs.append([p,seed, "" if d is None else d,delivered,generated])
    valid=[float(r[2]) for r in runs if r[0]==p and r[2]!=""]
    print(f"Python horizon={args.horizon}, p={p:.2f}: mean={statistics.mean(valid) if valid else None}, delivered={sum(r[3] for r in runs if r[0]==p)/args.repetitions:.1f}",flush=True)
with (out/"python_runs.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["arrProb","seed","meanDelay","deliveredUniquePackets","expectedGeneratedPackets"]);w.writerows(runs)
