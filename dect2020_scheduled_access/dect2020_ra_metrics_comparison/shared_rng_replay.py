"""Shared-random replay: identical Bernoulli arrivals and per-PT backoff draws.
Uses portable parityHash in both models; differences imply protocol/event ordering,
not random-stream differences. Writes observed counters and first DATA start times.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

spec=importlib.util.spec_from_file_location('shared',ROOT/'4_random_access_shared_rng.py')
s=importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
s.cluster_count=1;s.devices_in_cluster_count=2;s.c_min=1;s.c_max=16
s.model_time=3000;s.arrival_type='arrprob';s.arrprob=.05
s.ack_delivery_always_succ=False;s.lbt_always_succ=False;s.c_min_for_retry=False
s.parity_random_mode=True;s.parity_seed=1
generated=[0,0]
orig_generate=s.DevicePT.generate_packet
def generated_hook(pt,t):
    generated[pt.id]+=1
    return orig_generate(pt,t)
s.DevicePT.generate_packet=generated_hook
physical=set()
check=s.Operation.check
def collision_hook(op):
    if op.type=='Trans':
        for other in op.A.cluster.transmissions:
            if other is not op and op.start_time<other.end_time and other.start_time<op.end_time:
                physical.add(op)
    elif op.type=='Ack':
        for d in op.B.cluster.transmissions:
            if d.type=='Trans' and d.start_time<op.end_time and op.start_time<d.end_time:
                physical.add(d)
    return check(op)
s.Operation.check=collision_hook
s.setup()
with contextlib.redirect_stdout(io.StringIO()): s.main()
c=s.clusters[0]
py=dict(generated=sum(generated),
        generated_by_pt=generated,
        data_attempts=c.all,
        lbt_busy=c.LBTall-c.LBTsucc,
        lbt_total=c.LBTall,
        delivered=s.delivered_num(c),
        acknowledged=sum(generated)-sum(len(pt.queue) for pt in c.PT_devices),
        physical_collisions=len(physical))
py_times=[[ev.ttime for ev in pt.timeline if ev.content=='transmission'][:20]
          for pt in c.PT_devices]
vals={}
for line in (ROOT/'omnet_new/SharedRandomParity.sca').read_text().splitlines():
    v=line.split()
    if len(v)>=4 and v[0]=='scalar':
        vals[v[1]+'.'+v[2]]=float(v[3])
g=lambda key:round(vals['Cluster.'+key])
om=dict(generated=sum(g(f'pt[{i}].generatedPackets') for i in range(2)),
    generated_by_pt=[g(f'pt[{i}].generatedPackets') for i in range(2)],
    data_attempts=g('medium.dataTransmissionAttempts'),
    lbt_busy=g('medium.busyLbtResponses'),
    lbt_total=g('medium.busyLbtResponses')+g('medium.dataTransmissionAttempts'),
    delivered=g('ft.deliveredUniquePackets'),
    acknowledged=sum(g(f'pt[{i}].acknowledgedPackets') for i in range(2)),
    physical_collisions=g('medium.collidedDataAttempts'))
om_times=[]
for i in range(2):
    times=[]
    for k in range(20):
        name=f'Cluster.pt[{i}].txStart{k}'
        if name not in vals: break
        times.append(round(vals[name]))
    om_times.append(times)
report=dict(scenario='2 PT, shared-random seed 1, arrprob=.05, 3000 symbols',
            python=py,omnet=om,
            differences={k:om[k]-py[k] for k in py if k!='generated_by_pt'},
            identical_arrival_counts=om['generated_by_pt']==py['generated_by_pt'],
            first_python_data_starts=py_times,
            first_omnet_data_starts=om_times,
            first_start_divergence_by_pt=[
                next((j for j,(a,b) in enumerate(zip(py_times[i],om_times[i])) if a!=b),
                     None if py_times[i]==om_times[i] else min(len(py_times[i]),len(om_times[i])))
                for i in range(2)])
outfile=ROOT/'omnet_new/shared_rng_replay.json'
outfile.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('Shared-random replay:',json.dumps(report,ensure_ascii=False))
