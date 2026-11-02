"""Deterministic 2-PT parity test (arrprob=1, backoff=0, 100 symbols).
Used alongside OMNeT++ [Config DeterministicParity]; no stochastic draws affect behavior.
Writes a JSON report containing both models' observable counters.
"""
import contextlib
import importlib.util
import io
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('reference', ROOT/'4_random_access_protocol_corrected.py')
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)
sim.cluster_count=1
sim.devices_in_cluster_count=2
sim.c_min=1
sim.c_max=16
sim.model_time=100
sim.arrival_type='arrprob'
sim.arrprob=1.
sim.lbt_always_succ=False
sim.ack_delivery_always_succ=False
sim.c_min_for_retry=False

gen=[0,0]
original=sim.DevicePT.generate_packet
def generate(pt,t):
    gen[pt.id]+=1
    return original(pt,t)
sim.DevicePT.generate_packet=generate
old_randint=random.randint
random.randint=lambda a,b:0
try:
    sim.setup()
    with contextlib.redirect_stdout(io.StringIO()):
        sim.main()
finally:
    random.randint=old_randint
c=sim.clusters[0]
py=dict(generated=sum(gen), data_attempts=c.all,
        lbt_busy=c.LBTall-c.LBTsucc,
        lbt_total=c.LBTall, delivered=sim.delivered_num(c),
        data_success=c.succ)
sca=ROOT/'omnet_new/deterministic_100.sca'
vals={}
for line in sca.read_text().splitlines():
    x=line.split()
    if len(x)>=4 and x[0]=='scalar':
        vals[x[1]+'.'+x[2]]=float(x[3])
get=lambda k:round(vals['Cluster.'+k])
om=dict(generated=sum(get('pt[%d].generatedPackets'%i) for i in range(2)),
        data_attempts=get('medium.dataTransmissionAttempts'),
        lbt_busy=get('medium.busyLbtResponses'),
        lbt_total=get('medium.busyLbtResponses')+get('medium.dataTransmissionAttempts'),
        delivered=get('ft.deliveredUniquePackets'),
        data_success=None)
report=dict(scenario='2 PT, arrprob=1, zero backoff, 100 symbol horizon',
            python=py,omnet=om,
            differences={k: om[k]-py[k] for k in om if k in py and om[k] is not None})
out=ROOT/'omnet_new/deterministic_parity.json'
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('Deterministic comparison:',json.dumps(report,ensure_ascii=False))
