"""Re-run the corrected original Python simulator and compare the supplied OMNeT++ .sca runs.
Reads newly generated OMNeT++ scalar files from omnet_new/results/.
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
keys=['collision','lbt_busy','attempts_per_delivered','delivery_rate','failed_data_fraction',
      'first_failure_collision','busy_ft_at_start','collision_with_data','collision_with_ack',
      'missed_at_ack_start','boundary_contacts']

spec=importlib.util.spec_from_file_location('dect',root/'4_random_access_final.py')
sim=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
# True physical collision: ANY overlap, even if a prior FT-busy refusal
# already made the DATA unsuccessful. Compare like-for-like with Medium.cc.
physical=set()
first_transition=set()
data_data=set()
data_ack=set()
ft_busy_at_start=set()
# Diagnostic: a DATA/Ack overlap that the original Python 'Trans.check'
# observer misses because RootDevice belongs to dummy Cluster(-1).
missed_at_ack_start=set()
boundary_contacts=set()
check=sim.Operation.check
receive_start=sim.RootDevice.receive_start
def overlap(a,b):
    # Strict radio interval overlap, not merely sharing a boundary instant.
    return a.start_time < b.end_time and b.start_time < a.end_time
def record_data_overlap(data,other):
    if overlap(data,other):
        physical.add(data)
        if other.type=='Trans': data_data.add(data)
        if other.type=='Ack': data_ack.add(data)
    elif data.start_time==other.end_time or other.start_time==data.end_time:
        boundary_contacts.add(data)
def track(op):
    if op.type=='Trans':
        for other in op.A.cluster.transmissions:
            if other is not op and other.type in ('Trans','Ack'):
                record_data_overlap(op,other)
    elif op.type=='Ack':
        # Python's original RootDevice.proc_end() does not run check() again
        # for the real cluster: the FT is attached to Cluster(-1). The ACK's
        # own check() DOES run at creation and sees the active DATA operations.
        # Record them here, WITHOUT modifying the simulated model.
        for data in op.B.cluster.transmissions:
            if data is not op and data.type=='Trans' and overlap(data,op):
                if data not in data_ack: missed_at_ack_start.add(data)
                record_data_overlap(data,op)
    before=op.is_successful
    check(op)
    if op.type=='Trans' and before and not op.is_successful:
        first_transition.add(op)
def track_receiver(ft, ttime, transmission):
    if not ft.is_free: ft_busy_at_start.add(transmission)
    return receive_start(ft, ttime, transmission)
sim.Operation.check=track
sim.RootDevice.receive_start=track_receiver
rows=[]
for p in probs:
    for seed in seeds:
        for observed in (physical,first_transition,data_data,data_ack,ft_busy_at_start,
                         missed_at_ack_start,boundary_contacts):
            observed.clear()
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
          collision=len(physical)/attempts if attempts else float('nan'),
          lbt_busy=(c.LBTall-c.LBTsucc)/c.LBTall if c.LBTall else float('nan'),
          attempts_per_delivered=attempts/delivered if delivered else float('nan'),
          delivery_rate=delivered/T,
          data_attempts=attempts,collided_data_attempts=len(physical),
          busy_lbt=c.LBTall-c.LBTsucc,lbt_checks=c.LBTall,delivered_unique=delivered,
          failed_data_fraction=(c.all-c.succ)/attempts if attempts else float('nan'),
          first_failure_collision=len(first_transition)/attempts if attempts else float('nan'),
          busy_ft_at_start=len(ft_busy_at_start)/attempts if attempts else float('nan'),
          collision_with_data=len(data_data)/attempts if attempts else float('nan'),
          collision_with_ack=len(data_ack)/attempts if attempts else float('nan'),
          missed_at_ack_start=len(missed_at_ack_start)/attempts if attempts else float('nan'),
          boundary_contacts=len(boundary_contacts)/attempts if attempts else float('nan')))

for path in sorted((root/'omnet_new/results').glob('*.sca')):
    vals={}
    for line in path.read_text().splitlines():
        parts=line.split()
        if len(parts)>=3 and parts[0]=='itervar': vals[parts[1]]=parts[2]
        if len(parts)>=4 and parts[0]=='scalar': vals[parts[1]+'.'+parts[2]]=float(parts[3])
    if 'arrProb' not in vals: raise ValueError(f'Unknown run in {path}')
    p=float(vals['arrProb']); seed=int(vals.get('seed',path.stem.split('_s')[-1]))
    get=lambda name:vals['Cluster.'+name]
    attempts=get('medium.dataTransmissionAttempts')
    first_failed=get('ft.pythonEquivalentDataCollisions')
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
       first_failure_collision=first_failed/attempts if attempts else float('nan'),
       busy_ft_at_start=get('ft.rejectedAtStartWhileBusy')/attempts if attempts else float('nan'),
       collision_with_data=get('medium.dataOverlappedWithData')/attempts if attempts else float('nan'),
       collision_with_ack=get('medium.dataOverlappedWithAck')/attempts if attempts else float('nan'),
       missed_at_ack_start=float('nan'), boundary_contacts=float('nan'),
       failed_data_fraction=(attempts-get('ft.receivedDataAttempts')+collided+get('ft.droppedWhileFTBusy'))/attempts if attempts else float('nan')))

expected={(round(p,2),seed) for p in probs for seed in seeds}
for model in ['Python','OMNeT++']:
    present={(round(r['arrprob'],2),r['seed']) for r in rows if r['model']==model}
    assert present==expected and len([r for r in rows if r['model']==model])==90,(model,len(present))

def write(filename,data):
    with (root/filename).open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(dict.fromkeys(k for row in data for k in row)))
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
