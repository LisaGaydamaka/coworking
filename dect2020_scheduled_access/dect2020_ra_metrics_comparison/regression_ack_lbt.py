"""Reproduce the same deterministic DATA/ACK/LBT timeline in both Python sources.
Run: python3 regression_ack_lbt.py
No RNG or entire simulation sweep is involved.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent

def verify(filename):
    spec = importlib.util.spec_from_file_location('dect_'+filename.replace('.','_'), HERE / filename)
    model = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    model.cluster_count = 1
    model.devices_in_cluster_count = 2
    model.c_min = 1
    model.c_max = 16
    model.lbt_time = 2
    model.ack_time = 5
    model.setup()
    model.events = []
    cluster = model.clusters[0]
    p0, p1 = cluster.PT_devices
    receiver = model.root_device
    receiver.is_free = False
    # PT1 listens [10,12), while an ACK for PT0 starts at 11.
    packet = model.Packet(10, p1)
    p1.queue.append(packet)  # failed LBT schedules retry for this queued packet
    lbt = model.Operation('LBT',p1,None,packet,10,12,True)
    p1.operation = lbt
    cluster.LBTs.append(lbt)
    data = model.Operation('Trans',p0,receiver,model.Packet(0,p0),1,11,True)
    receiver.proc_end(11,data)
    ack = next(x for x in cluster.transmissions if x.type == 'Ack')
    assert ack.start_time == 11 and ack.end_time == 16
    assert lbt.start_time < ack.end_time and ack.start_time < lbt.end_time
    value = lbt.is_successful
    p1.LBT_end(12,packet)
    return value,cluster.LBTsucc,cluster.all

original = verify('4_random_access_final.py')
corrected = verify('4_random_access_protocol_corrected.py')
print('LBT [10,12), ACK [11,16): strict radio overlap')
print('Original Python: LBT success =',original[0],'; started DATA =',original[2])
print('Corrected Python: LBT success =',corrected[0],'; started DATA =',corrected[2])
assert original == (True,1,1), original
assert corrected == (False,0,0), corrected
print('PASS: original Python missed ACK-start LBT busy; fixed version rejects correctly')
