"""Re-run the corrected original Python simulator and compare the supplied OMNeT++ .sca runs.
Extract inputs/DECT-2020.rar (all .sca files) to results/ before executing.
Requires Python 3.10+, numpy and matplotlib, as the original simulator imports both.
"""
import csv, importlib.util, io, contextlib, math, random, statistics
from collections import defaultdict
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parent
probs=[k/100 for k in range(1,10)]
seeds=range(1,11)
T=3000
keys=['collision','lbt_busy','attempts_per_delivered','delivery_rate','failed_data_fraction']

spec=importlib.util.spec_from_file_location('dect',root/'4_random_access_final.py')
sim=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
collisions=set()
check=sim.Operation.check
def track(op):
    before=op.is_successful
    check(op)
    if op.type=='Trans' and before and not op.is_successful:
        collisions.add(op)  # hold references: id(op) is NOT safe due to address reuse
sim.Operation.check=track
rows=[]
for p in probs:
    for seed in seeds:
        collisions.clear()
        random.seed(seed); np.random.seed(seed)
        sim.arrprob=p; sim.arrival_type='arrprob'
        sim.c_min=1; sim.c_max=16; sim.model_time=T
        sim.cluster_count=1; sim.devices_in_cluster_count=2
        sim.trans_time=10; sim.proc_time=10; sim.ack_time=5; sim.lbt_time=2
        sim.ack_delivery_always_succ=False
        sim.lbt_always_succ=False
        sim.c_min_for_retry=False
        sim.setup()
        with contextlib.redirect_stdout(io.StringIO()): sim.main()
        c=sim.clusters[0]
        attempts=c.all; delivered=sim.delivered_num(c)
        rows.append(dict(model='Python',arrprob=p,seed=seed,
          collision=len(collisions)/attempts if attempts else float('nan'),
          lbt_busy=(c.LBTall-c.LBTsucc)/c.LBTall if c.LBTall else float('nan'),
          attempts_per_delivered=attempts/delivered if delivered else float('nan'),
          delivery_rate=delivered/T,
          data_attempts=attempts,collided_data_attempts=len(collisions),
          busy_lbt=c.LBTall-c.LBTsucc,lbt_checks=c.LBTall,delivered_unique=delivered,
          failed_data_fraction=(c.all-c.succ)/attempts if attempts else float('nan')))

for path in sorted((root/'results').glob('*.sca')):
    vals={}
    for line in path.read_text().splitlines():
        parts=line.split()
        if len(parts)>=3 and parts[0]=='itervar': vals[parts[1]]=parts[2]
        if len(parts)>=4 and parts[0]=='scalar': vals[parts[1]+'.'+parts[2]]=float(parts[3])
    if not {'arrProb','seed'}<=vals.keys(): raise ValueError(f'Unknown run in {path}')
    p=float(vals['arrProb']); seed=int(vals['seed'])
    get=lambda name:vals['Cluster.'+name]
    attempts=get('medium.dataTransmissionAttempts')
    collided=get('medium.collidedDataAttempts')
    busy=get('medium.busyLbtResponses')
    delivered=get('ft.deliveredUniquePackets')
    rows.append(dict(model='OMNeT++',arrprob=p,seed=seed,
       collision=collided/attempts if attempts else float('nan'),
       lbt_busy=busy/(busy+attempts) if busy+attempts else float('nan'),
       attempts_per_delivered=attempts/delivered if delivered else float('nan'),
       delivery_rate=delivered/T,
       data_attempts=attempts,collided_data_attempts=collided,
       busy_lbt=busy,lbt_checks=busy+attempts,delivered_unique=delivered,
       failed_data_fraction=(collided+get('ft.droppedWhileFTBusy'))/attempts if attempts else float('nan')))

expected={(round(p,2),seed) for p in probs for seed in seeds}
for model in ['Python','OMNeT++']:
    present={(round(r['arrprob'],2),r['seed']) for r in rows if r['model']==model}
    assert present==expected and len([r for r in rows if r['model']==model])==90,(model,len(present))

def write(filename,data):
    with (root/filename).open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(data[0]))
        w.writeheader();w.writerows(data)
write('raw_metrics.csv',rows)
grouped=defaultdict(list)
for r in rows:grouped[(r['model'],r['arrprob'])].append(r)
summary=[]
for (model,p),group in sorted(grouped.items()):
    entry=dict(model=model,arrprob=p,runs=len(group))
    for metric in keys:
        values=[r[metric] for r in group if math.isfinite(r[metric])]
        entry[metric]=statistics.mean(values) if values else float('nan')
        entry[metric+'_sd']=statistics.stdev(values) if len(values)>1 else 0
    summary.append(entry)
write('summary_metrics.csv',summary)
print('Saved 90 Python + 90 OMNeT++ measurements and 18 summary rows')
