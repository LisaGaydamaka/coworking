"""Deterministic 100-symbol parity: same generated traffic and zero backoff.
Three cases: synchronized 2PT, isolated 1PT (ACK), phased 2PT (DATA/ACK).
No random outcomes affect these scenarios. Execute after OMNeT++ deterministic .sca files.
"""
import contextlib
import importlib.util
import io
import json
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SCENARIOS=[
    ('DeterministicParity',2,0),
    ('DeterministicOnePT',1,0),
    ('DeterministicPhase',2,15),
]

def python_reference(npt,offset):
    spec=importlib.util.spec_from_file_location('reference',ROOT/'4_random_access_protocol_corrected.py')
    sim=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    sim.cluster_count=1
    sim.devices_in_cluster_count=npt
    sim.c_min=1
    sim.c_max=16
    sim.model_time=100
    sim.arrival_type='arrprob'
    sim.arrprob=1.
    sim.lbt_always_succ=False
    sim.ack_delivery_always_succ=False
    sim.c_min_for_retry=False
    generated=[0]*npt
    original=sim.DevicePT.generate_packet
    def tracked_generate(pt,t):
        generated[pt.id]+=1
        return original(pt,t)
    sim.DevicePT.generate_packet=tracked_generate
    original_arrival=sim.DevicePT.schedule_arrival
    def shifted_arrival(pt,t):
        if offset>0 and pt.id==1 and t==0:
            sim.events.append(sim.Event(offset,'schedule_arrival',pt,None))
            return
        return original_arrival(pt,t)
    sim.DevicePT.schedule_arrival=shifted_arrival
    randint=random.randint
    random.randint=lambda a,b:0
    try:
        sim.setup()
        with contextlib.redirect_stdout(io.StringIO()):
            sim.main()
    finally:
        random.randint=randint
    c=sim.clusters[0]
    return dict(generated=sum(generated),data_attempts=c.all,
        lbt_busy=c.LBTall-c.LBTsucc,lbt_total=c.LBTall,
        delivered=sim.delivered_num(c),
        acknowledged=sum(generated)-sum(len(pt.queue) for pt in c.PT_devices))

def omnet_counters(name,npt):
    path=ROOT/f'omnet_new/{name}.sca'
    vals={}
    for line in path.read_text().splitlines():
        x=line.split()
        if len(x)>=4 and x[0]=='scalar':
            vals[x[1]+'.'+x[2]]=float(x[3])
    get=lambda k:round(vals['Cluster.'+k])
    return dict(generated=sum(get('pt[%d].generatedPackets'%i) for i in range(npt)),
        data_attempts=get('medium.dataTransmissionAttempts'),
        lbt_busy=get('medium.busyLbtResponses'),
        lbt_total=get('medium.busyLbtResponses')+get('medium.dataTransmissionAttempts'),
        delivered=get('ft.deliveredUniquePackets'),
        acknowledged=sum(get('pt[%d].acknowledgedPackets'%i) for i in range(npt)))

report={'test':'same traffic arrivals and zero backoff, time horizon 100 symbols','scenarios':[]}
for name,npt,offset in SCENARIOS:
    py=python_reference(npt,offset)
    om=omnet_counters(name,npt)
    diffs={k:om[k]-py[k] for k in py}
    scenario=dict(name=name,numPTs=npt,pt1Offset=offset,python=py,omnet=om,differences=diffs)
    report['scenarios'].append(scenario)
    print(name, json.dumps(scenario,ensure_ascii=False))
out=ROOT/'omnet_new/deterministic_parity.json'
out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('Saved',out)
