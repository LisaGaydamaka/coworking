"""Exact 9x10 paired Python/OMNeT++ sweep using identical per-PT random draws.
The integer checks reveal true algorithm/event-order divergence, not sampling noise.
"""
import csv
import contextlib
import importlib.util
import io
import json
import random
from pathlib import Path
ROOT=Path(__file__).resolve().parent
src=ROOT/'4_random_access_shared_rng.py'
spec=importlib.util.spec_from_file_location('shared90',src)
sim=importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
sim.cluster_count=1
sim.devices_in_cluster_count=2
sim.c_min=1;sim.c_max=16
sim.model_time=3000
sim.arrival_type='arrprob'
sim.ack_delivery_always_succ=False
sim.lbt_always_succ=False
sim.c_min_for_retry=False
sim.parity_random_mode=True
gen=[0,0]
orig_generate=sim.DevicePT.generate_packet
def hook_generate(pt,t):
    gen[pt.id]+=1
    return orig_generate(pt,t)
sim.DevicePT.generate_packet=hook_generate
physical=set()
orig_check=sim.Operation.check
def hook_check(op):
    if op.type=='Trans':
        for other in op.A.cluster.transmissions:
            if other is not op and op.start_time<other.end_time and other.start_time<op.end_time:
                physical.add(op)
    elif op.type=='Ack':
        for other in op.B.cluster.transmissions:
            if other.type=='Trans' and other.start_time<op.end_time and op.start_time<other.end_time:
                physical.add(other)
    return orig_check(op)
sim.Operation.check=hook_check

def get_python(p,seed):
    gen[:]=[0,0]
    physical.clear()
    sim.arrprob=p
    sim.parity_seed=seed
    random.seed(seed)
    sim.setup()
    with contextlib.redirect_stdout(io.StringIO()):
        sim.main()
    c=sim.clusters[0]
    return dict(generated=sum(gen),
                pt0_generated=gen[0],pt1_generated=gen[1],
                attempts=c.all,
                busy_lbt=c.LBTall-c.LBTsucc,
                all_lbt=c.LBTall,
                delivered=sim.delivered_num(c),
                acknowledged=sum(gen)-sum(len(pt.queue) for pt in c.PT_devices),
                radio_collisions=len(physical))

def get_omnet(vals):
    def g(k):return round(vals['Cluster.'+k])
    return dict(generated=g('pt[0].generatedPackets')+g('pt[1].generatedPackets'),
                pt0_generated=g('pt[0].generatedPackets'),
                pt1_generated=g('pt[1].generatedPackets'),
                attempts=g('medium.dataTransmissionAttempts'),
                busy_lbt=g('medium.busyLbtResponses'),
                all_lbt=g('medium.busyLbtResponses')+g('medium.dataTransmissionAttempts'),
                delivered=g('ft.deliveredUniquePackets'),
                acknowledged=g('pt[0].acknowledgedPackets')+g('pt[1].acknowledgedPackets'),
                radio_collisions=g('medium.collidedDataAttempts'))

checks=[]
observed=set()
for path in sorted((ROOT/'omnet_new/shared_rng_grid').glob('run_*.sca')):
    vals={}
    for line in path.read_text().splitlines():
        v=line.split()
        if len(v)>=3 and v[0]=='itervar':
            vals[v[1]]=v[2].strip('"')
        if len(v)>=4 and v[0]=='scalar':
            vals[v[1]+'.'+v[2]]=float(v[3])
    p=float(vals['arrProb']);seed=int(vals['paritySeed'])
    key=(round(p,2),seed)
    assert key not in observed,('repeated',key)
    observed.add(key)
    py=get_python(p,seed)
    om=get_omnet(vals)
    for name in py:
        checks.append(dict(arrprob=p,seed=seed,metric=name,
                           python=py[name],omnet=om[name],
                           difference=om[name]-py[name]))
expected={(round(i/100,2),j) for i in range(1,10) for j in range(1,11)}
assert observed==expected,('wrong 90-case grid',len(observed),
                          sorted(expected-observed)[:5])
csv_path=ROOT/'omnet_new/shared_rng_grid_comparison.csv'
with csv_path.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(checks[0]))
    w.writeheader()
    w.writerows(checks)
bad=[c for c in checks if c['difference']!=0]
report=dict(runs=len(observed),metrics_per_run=len(checks)//len(observed),
            total_metric_checks=len(checks),mismatched_checks=len(bad),
            mismatched_runs=len(set((x['arrprob'],x['seed']) for x in bad)),
            example_mismatches=bad[:30])
(ROOT/'omnet_new/shared_rng_grid_report.json').write_text(
    json.dumps(report,indent=2)+'\n')
print('Shared-random grid result:',json.dumps(report))
