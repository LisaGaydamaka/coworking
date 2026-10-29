"""Reproducible Python random-access sweep under Ira's OMNeT++ settings."""
import argparse, contextlib, csv, importlib.util, io, random, statistics
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("dect_ref", HERE/"4_random_access_final.py")
sim=importlib.util.module_from_spec(spec);spec.loader.exec_module(sim)
ps=[round(n/100,2) for n in range(1,10)]
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repetitions",type=int,default=10)
    a=ap.parse_args()
    sim.cluster_count=1;sim.devices_in_cluster_count=2
    sim.c_min=1;sim.c_max=16;sim.model_time=3000
    sim.trans_time=10;sim.proc_time=10;sim.ack_time=5;sim.lbt_time=2
    sim.arrival_type="arrprob";sim.lbt_always_succ=False
    sim.ack_delivery_always_succ=False;sim.c_min_for_retry=False
    results=[];runs=[]
    for p in ps:
        values=[]
        for seed in range(1,a.repetitions+1):
            random.seed(seed);np.random.seed(seed)
            sim.arrprob=p;sim.setup()
            with contextlib.redirect_stdout(io.StringIO()):sim.main()
            d=sim.sim_delay(sim.clusters[0])
            count=sum(len(pt.delivered_packets) for pt in sim.clusters[0].PT_devices)
            runs.append([p,seed, "" if d is None else d,count])
            if d is not None:values.append(d)
        results.append([p,len(values),statistics.mean(values) if values else "",statistics.stdev(values) if len(values)>1 else ""])
        print("PY p=%.2f mean=%s valid=%d"%(p,results[-1][2],len(values)),flush=True)
    out=HERE/"results";out.mkdir(exist_ok=True)
    for name,header,rows in [("python_runs.csv",["arrProb","seed","meanDelay","deliveredUniquePackets"],runs),("python_aggregate.csv",["arrProb","validRuns","meanDelay","sdBetweenRuns"],results)]:
        with (out/name).open("w",newline="") as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
if __name__=="__main__":main()
