# используемые пакеты
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rc
import statistics as stt
import random
from operator import attrgetter
import math


# pip install numpy
# pip install matplotlib
# pip install statistics
# pip install random
# pip install operator
# pip install math

# apt install python3-numpy
# apt install python3-matplotlib
# apt install python3-statistics
# apt install python3-random
# apt install python3-operator
# apt install python3-math


# модель режим 1, свободный RA
# с новым классом Transmission

# подключения ввода LaTex для подписей графика
plt.rcParams['text.usetex'] = True
rc('text.latex',preamble=r'\usepackage[utf8]{inputenc}')
rc('text.latex',preamble=r'\usepackage[russian]{babel}')


# ОБЪЯВЛЕНИЕ КЛАССОВ

class DevicePT:
    def __init__(self, id, cluster):
        self.id = id
        self.cluster = cluster

        self.c_current = c_min
        self.queue = []
        self.operation = None
        self.delivered_packets = []
        self.timeline = [Event(0,"idle",None,None)]
        self.qnemptyall = 0 # Число раз очередь была непуста на момент окончания обслуживания
        self.qnemptysucc = 0 # Число раз очередь была непуста на момент окончания обслуживания

    def schedule_arrival(self, ttime):
        global events
        match arrival_type:
            case "none":
                betw_arr_time = Lmb
                events.append(Event(ttime+betw_arr_time, "schedule_arrival", self, None))
                self.generate_packet(ttime)

            case "qnempty": # ЗАЙЦЕВА
                self.cluster.qnemptyall += 1
                if random.random()<qnempty: # если в очереди ТИПА есть пакет
                    self.cluster.qnemptysucc += 1
                    self.generate_packet(ttime)
                else:
                    self.empty_cycle_count +=1
                    events.append(Event(ttime+1, "schedule_arrival", self, None))
                    self.timeline.append(Event(ttime, "idle",None,None))
                    
            case "arrprob": # МОРОЗОВА
                if random.random()<arrprob: # если в систему поступает новый пакет
                    self.generate_packet(ttime)
                else:
                    self.timeline.append(Event(ttime, "idle",None,None))
                events.append(Event(ttime+1, "schedule_arrival", self, None)) # на каждом такте проверяется, пришел ли пакет

            case _:
                print("erm.. this shouldnt happen...")

    def generate_packet(self, ttime):
        packet = Packet(ttime, self)
        self.queue.append(packet)
        if self.queue == [packet]:
            self.backoff_start(ttime)

    def backoff_start(self, ttime):
        global events
        self.timeline.append(Event(ttime, "backoff",None,None)) # для статистики
        packet = self.queue[0] # достается пакет из очереди
        packet.journey.append(Event(ttime, "backoff", self, None)) # для статистики
        bo_time = random.randint(0,self.c_current)*lbt_time # рассчитывается время backoff
        events.append(Event(ttime+bo_time, "LBT_start_PT", self, packet)) # добавляется событие окончание backoff, т.е. начала LBT
    
    def LBT_start(self, ttime, packet):
        global events
        self.timeline.append(Event(ttime, "LBT",None,None))
        packet.journey.append(Event(ttime, "LBT", self, None))
        self.operation = Operation("LBT", self, None, packet, ttime, ttime+lbt_time, True)
        self.cluster.LBTs.append(self.operation)
        self.operation.check()
        events.append(Event(ttime+lbt_time, "A_LBT_end", self, packet))

    def LBT_end(self, ttime, packet):
        self.cluster.LBTall += 1
        if lbt_always_succ: self.operation.is_successful = True
        if self.operation.is_successful:
            self.timeline[-1].content = "posLBT"
            self.cluster.LBTsucc += 1
            self.end_operation()
            self.send_start(ttime, packet)
        else:
            self.timeline[-1].content = "negLBT"
            self.end_operation()
            self.c_current = min(c_max, 2 * self.c_current)
            self.backoff_start(ttime)
            
    def send_start(self, ttime, packet):
        global events
        self.timeline.append(Event(ttime, "transmission",None,None))
        packet.journey.append(Event(ttime, "transmission", self, None))
        self.operation = Operation("Trans", self, self.cluster.FT, packet, ttime, ttime+trans_time, True)
        self.cluster.transmissions.append(self.operation)
        self.operation.check()
        events.append(Event(ttime+proc_time//2, "trans_check",self,self.operation))
        self.cluster.all += 1
        self.cluster.FT.receive_start(ttime, self.operation)
    
    def send_end(self, ttime, packet): # завершить передачу, которую FT не слушал
        self.timeline.append(Event(ttime, "waiting",None,None))
        packet.journey.append(Event(ttime, "wait",self,None))
        self.end_operation()
    
    def wait_end(self, ttime, transmission, ack_trans):
        global events
        if transmission.is_successful:
            self.operation = ack_trans
            # if ack_trans != None and ack_delivery_always_succ:
            if ack_trans != None:
                self.cluster.transmissions.append(ack_trans)
                ack_trans.check()
            self.timeline.append(Event(ttime, "failACK",None,None))
            events.append(Event(ttime+ack_time, "A_ack_end", self, ack_trans))
            self.cluster.succ += 1
            self.cluster.ACKsucc += 1
        else:
            self.timeline.append(Event(ttime, "noACK",None,None))
            events.append(Event(ttime+ack_time, "A_ack_end", self, None))

    def ack_end(self, ttime, ack_trans):
        if ack_trans != None and ack_delivery_always_succ: ack_trans.is_successful = True
        if self.operation != None: self.end_operation()
        if ack_trans != None and ack_trans.is_successful == True: # усли была передача ack, и она была успешной
            self.timeline[-1].content = "posACK"
            self.c_current = c_min
            self.queue.pop(0)
            if arrival_type == "qnempty":
                self.schedule_arrival(ttime)
            else:
                self.cluster.qnemptyall += 1
                if self.queue != []:
                    self.cluster.qnemptysucc += 1
                    self.backoff_start(ttime)
                else:
                    self.timeline.append(Event(ttime, "idle",None,None))
        else:
            if c_min_for_retry:
                self.c_current = c_min
            else:
                self.c_current = min(c_max, 2 * self.c_current)
            self.backoff_start(ttime)
        if ack_trans != None:
            ack_trans.A.backoff_continue(ttime)

    def end_operation(self):
        if self.operation in self.cluster.transmissions:
            self.cluster.transmissions.remove(self.operation)
        else:
            self.cluster.LBTs.remove(self.operation)
        self.operation = None
    
    def clearr(self):
        self.c_current = c_min
        self.queue = []
        self.operation = None
        self.delivered_packets = []
        self.timeline = [Event(0,"idle",None,None)]
        self.empty_cycle_count = 0 # Число пустых циклов


class DeviceFT():
    def __init__(self, id, cluster):
        self.id = id
        self.cluster = cluster

        self.c_current = c_min
        self.queue = []
        self.delivered_packets = [] # rudimentary
        self.operation = None # uplink or downlink transmission or LBT
        self.is_free = True
        self.LBT_start_event = None
        self.backoff_timer_stop_time = -1
        self.timeline = [Event(0,"idle",None,None)]

    def receive_start(self, ttime, transmission):
        global events
        if self.is_free:
            self.is_free = False
            self.timeline.append(Event(ttime, "receive",None,None))
            if self.LBT_start_event != None: # если идет backoff
                events.remove(self.LBT_start_event) # убираем событие начала LBT
                self.backoff_timer_stop_time = ttime # запоминаем, когда поставили таймер на паузу
            events.append(Event(ttime+trans_time, "A_receive_end", self, transmission))
        else:
            transmission.is_successful = False
            events.append(Event(ttime+trans_time, "A_send_end", transmission.A, transmission.packet))
            events.append(Event(ttime+trans_time+proc_time, "wait_end", transmission.A, transmission))

    def receive_end(self, ttime, transmission): # в случае, если FT вообще слушает передачу
        global events
        self.timeline.append(Event(ttime, "proc",None,None))
        events.append(Event(ttime+proc_time, "AAA_proc_end", self, transmission))
        transmission.A.send_end(ttime, transmission.packet)
        transmission.packet.journey[-1] = Event(ttime, "proc", self, None)
    
    def proc_end(self, ttime, transmission):
        if transmission.is_successful:
            self.queue.append(transmission.packet)
            self.timeline.append(Event(ttime, "sendACK",None,None))
            ack_trans = Operation("Ack", self, transmission.A, None, ttime, ttime+ack_time, True) # transmission.A - отправитель предыдущей передачи, т.е. получатель этой передачи
            transmission.A.cluster.ACKall +=1
            transmission.A.wait_end(ttime, transmission, ack_trans)
        else:
            transmission.packet.journey[-1] = Event(ttime-proc_time, "wait", self, None)
            transmission.A.wait_end(ttime, transmission, None)
            self.backoff_continue(ttime)
    
    def backoff_continue(self, ttime):
        global events
        if self.LBT_start_event == None:
            if self.queue == []:
                self.is_free = True
                self.timeline.append(Event(ttime, "idle",None,None))
            else:
                self.backoff_start(ttime)
        else:
            self.timeline.append(Event(ttime, "backoff",None,None))
            uebrige_time = self.LBT_start_event.ttime - self.backoff_timer_stop_time
            self.LBT_start_event.ttime = ttime + uebrige_time
            self.is_free = True
            events.append(self.LBT_start_event)

    def backoff_start(self, ttime):
        global events
        self.timeline.append(Event(ttime, "backoff",None,None))
        self.is_free = True
        packet = self.queue[0]
        # bo_time = random.randint(0,self.c_current+1)*lbt_time
        bo_time = random.randint(0,self.c_current)*lbt_time
        # bo_time = random.randint(1,self.c_current+1)*lbt_time
        self.LBT_start_event = Event(ttime+bo_time, "AA_LBT_start_FT", self, packet)
        events.append(self.LBT_start_event)

    def LBT_start(self, ttime, packet):
        global events
        self.timeline.append(Event(ttime, "LBT",None,None))
        self.is_free = False
        self.LBT_start_event = None
        self.backoff_timer_stop_time = -1
        self.operation = Operation("LBT", self, None, packet, ttime, ttime+lbt_time, True)
        self.cluster.LBTs.append(self.operation)
        self.operation.check()
        events.append(Event(ttime+lbt_time, "A_LBT_end", self, packet))

    def LBT_end(self, ttime, packet):
        self.cluster.LBTall += 1
        if lbt_always_succ: self.operation.is_successful = True
        if self.operation.is_successful:
            self.timeline[-1].content = "posLBT"
            self.cluster.LBTsucc += 1
            self.end_operation()
            self.send_start(ttime, packet)
        else:
            self.timeline[-1].content = "negLBT"
            self.end_operation()
            self.c_current = min(c_max, 2 * self.c_current)
            self.backoff_start(ttime)

    def send_start(self, ttime, packet):
        global events
        self.timeline.append(Event(ttime, "transmission",None,None))
        self.operation = Operation("Trans", self, self.cluster.FT, packet, ttime, ttime+trans_time, True)
        self.cluster.transmissions.append(self.operation)
        self.operation.check()
        events.append(Event(ttime+proc_time//2, "trans_check",self,self.operation))
        self.cluster.all += 1
        self.cluster.FT.receive_start(ttime, self.operation)

    def send_end(self, ttime, packet):
        self.timeline.append(Event(ttime, "waiting",None,None))
        packet.journey.append(Event(ttime, "wait", self, None))
        self.end_operation()

    def wait_end(self, ttime, transmission, ack_trans):
        global events
        if transmission.is_successful:
            self.operation = ack_trans
            # if ack_trans != None and ack_delivery_always_succ:
            if ack_trans != None:
                self.cluster.transmissions.append(ack_trans)
                ack_trans.check()
            self.timeline.append(Event(ttime, "failACK",None,None))
            events.append(Event(ttime+ack_time, "A_ack_end", self, ack_trans))
            self.cluster.succ += 1
            self.cluster.ACKsucc += 1
        else:
            self.timeline.append(Event(ttime, "noACK",None,None))
            events.append(Event(ttime+ack_time, "A_ack_end", self, None))

    def ack_end(self, ttime, ack_trans):
        if ack_delivery_always_succ: ack_trans.is_successful = True
        if self.operation != None: self.end_operation()
        if ack_trans != None and ack_trans.is_successful == True: # усли была передача ack, и она была успешной
            self.timeline[-1].content = "posACK"
            self.c_current = c_min
            self.queue.pop(0)
            self.cluster.qnemptyall += 1
            if self.queue != []:
                self.cluster.qnemptysucc += 1
                self.backoff_start(ttime)
            else:
                self.timeline.append(Event(ttime, "idle",None,None))
        else:
            if c_min_for_retry:
                self.c_current = c_min
            else:
                self.c_current = min(c_max, 2 * self.c_current)
            self.backoff_start(ttime)
        if ack_trans != None:
            ack_trans.A.backoff_continue(ttime)

    def end_operation(self):
        if self.operation in self.cluster.transmissions:        
            self.cluster.transmissions.remove(self.operation)
        else:
            self.cluster.LBTs.remove(self.operation)
        self.operation = None
    
    def clearr(self):
        self.c_current = c_min
        self.queue = []
        self.delivered_packets = [] # rudimentary
        self.operation = None # uplink or downlink transmission or LBT

        self.is_free = True
        self.LBT_start_event = None
        self.backoff_timer_stop_time = -1

        self.timeline = [Event(0,"idle",None,None)]


class RootDevice():
    def __init__(self, id, cluster):
        self.id = id
        self.cluster = cluster

        self.operation = None # uplink or downlink transmission or LBT
        self.is_free = True
        self.timeline = [Event(0,"idle",None,None)]

    def receive_start(self, ttime, transmission):
        global events
        if self.is_free:
            self.is_free = False
            self.timeline.append(Event(ttime, "receive",None,None))
            events.append(Event(ttime+trans_time, "A_receive_end", self, transmission))
        else:
            transmission.is_successful = False
            events.append(Event(ttime+trans_time, "A_send_end", transmission.A, transmission.packet))
            events.append(Event(ttime+trans_time+proc_time, "wait_end", transmission.A, transmission))

    def receive_end(self, ttime, transmission):
        global events
        self.timeline.append(Event(ttime, "proc",None,None))
        events.append(Event(ttime+proc_time, "AAA_proc_end", self, transmission))
        transmission.A.send_end(ttime, transmission.packet)
        transmission.packet.journey[-1] = Event(ttime, "proc", self, None)

    def proc_end(self, ttime, transmission):
        if transmission.is_successful:
            transmission.packet.journey.append(Event(ttime, "delivered", self, None))
            transmission.packet.device.delivered_packets.append(transmission.packet)
            self.timeline.append(Event(ttime, "sendACK",None,None))
            ack_trans = Operation("Ack", self, transmission.A, None, ttime, ttime+ack_time, True) # transmission.A - отправитель предыдущей передачи, т.е. получатель этой передачи
            transmission.A.cluster.ACKall +=1
            transmission.A.wait_end(ttime, transmission, ack_trans)

        else:
            transmission.packet.journey[-1] = Event(ttime-proc_time, "wait", self, None)
            transmission.A.wait_end(ttime, transmission, None)
            self.backoff_continue(ttime)
    
    def backoff_continue(self, ttime):
        self.timeline.append(Event(ttime, "idle",None,None))
        self.is_free = True
    
    def clearr(self):
        self.operation = None # uplink or downlink transmission or LBT
        self.is_free = True
        self.timeline = [Event(0,"idle",None,None)]


class Cluster:
    def __init__(self, id):
        self.id = id
        self.devices = []
        self.PT_devices = []
        self.FT = None # тот, к которому подключается весь кластер

        self.transmissions = []
        self.LBTs = []
        self.succ = 0 # число успешно переданных пакетов (пришел ACK) в канале (не надо заново передавать пакет)
        self.all = 0 # число переданных пакетов в канале
        self.LBTsucc = 0 # число успешных LBT в канале
        self.LBTall = 0 # число LBT в канале
        self.ACKsucc = 0
        self.ACKall = 0
        self.qnemptysucc = 0 # Число раз очередь была непуста на момент окончания обслуживания
        self.qnemptyall = 0 # число моментов окончания обслуживания
    
    def clearr(self):
        self.transmissions = []
        self.LBTs = []
        self.succ = 0 # число успешно переданных сообщений в канале
        self.all = 0 # число переданных сообщений в канале
        self.LBTsucc = 0 # число успешных LBT в канале
        self.LBTall = 0 # число LBT в канале
        self.ACKsucc = 0
        self.ACKall = 0
        self.qnemptysucc = 0
        self.qnemptyall = 0

class Event:
    # Инициализация (когда, что, кто, кого)
    def __init__(self, ttime, content, subject, object) -> None:
        self.ttime = ttime # Время события
        self.content = content # Содержание - что сделал
        self.subject = subject # Субъект - кто сделал
        self.object = object # Объект - кого сделал

class Packet:
    def __init__(self, gen_time, device):
        self.device = device
        self.journey = [Event(gen_time, "created", None, None)] # created, (backoff, LBT), transmission, proc, delivered
                                                                # created, (backoff, LBT), transmission, wait=15 / proc=10, delivered

class Operation:
    def __init__(self, type, A, B, packet, start_time, end_time, is_successful):
        self.type = type
        self.A = A
        self.B = B
        self.packet = packet
        self.start_time = start_time
        self.end_time = end_time
        self.is_successful = is_successful
    
    def check(self):
        match self.type:
            case "LBT":
                if self.A.cluster.transmissions != []:
                    self.is_successful = False
            case "Ack":
                if self.B.cluster.transmissions != [self]:
                    self.is_successful = False
            case "Trans":
                if self.A.cluster.transmissions != [self]:
                    self.is_successful = False


#----------------------------------------------------------------

def setup(): # для топологии типа: кластеры один за другим в цепочке, нулевое устройство это FT предыдущего. первый кл, т.е. который с root - 0, последний - (-1)
    global topology
    global clusters
    global root_device
    topology = []
    clusters = []
    root_device = RootDevice(0, Cluster(-1))
    for c in range(cluster_count-1):
        cluster = Cluster(c)
        clusters.append(cluster)
        topology.append([DeviceFT(0, cluster)])
        for d in range(1, devices_in_cluster_count):
            device = DevicePT(d, cluster)
            topology[-1].append(device)
        cluster.devices = topology[-1]
        cluster.PT_devices = topology[-1][1:]
    
    # последний кластер
    cluster = Cluster(cluster_count-1)
    clusters.append(cluster)
    topology.append([])
    for d in range(devices_in_cluster_count):
        device = DevicePT(d, cluster)
        topology[-1].append(device)
    cluster.devices = topology[-1]
    cluster.PT_devices = topology[-1]

    clusters[0].FT = root_device
    for c in range(1, cluster_count):
        clusters[c].FT = topology[c-1][0]

def main():
    global events # массив предстоящих событий
    events = []
    time=0

    for cluster in clusters:
        for pt_device in cluster.PT_devices:
            pt_device.schedule_arrival(time)

    while time<=model_time:
        if events == []: break
        n_events = next_events() # получаем следующее событие
        sorted_events = sorted(n_events, key=attrgetter("content"))
        time = n_events[0].ttime
        if time>model_time: break

        clusters_to_check = []
        for event in sorted_events:

#------------------- Die Reihenfolge----------
# "proc_end": # в начало, чтобы смог сразу принимать receive

# "LBT_start_FT":

# "LBT_end_FT":
# "LBT_end_PT":
# "ack_end":
# "receive_end": # если FT услышал передачу
# "send_end":

# "LBT_start_PT":
# "schedule_arrival":
# "end_operation":
# "wait_end"
# "trans_check"
#----------------------------------------------

            match event.content: # обрабатываем событие в соответствии с содержанием
                case "schedule_arrival":
                    event.subject.schedule_arrival(time)
                case "LBT_start_PT":
                    event.subject.LBT_start(time, event.object)
                case "AA_LBT_start_FT":
                    event.subject.LBT_start(time, event.object)
                case "A_LBT_end":
                    event.subject.LBT_end(time, event.object)
                    clusters_to_check.append(event.subject.cluster)
                case "AAA_proc_end":
                    event.subject.proc_end(time, event.object)
                    clusters_to_check.append(event.subject.cluster)
                case "A_ack_end":
                    event.subject.ack_end(time, event.object)
                case "end_operation":
                    event.subject.end_operation()
                case "A_receive_end": # если FT услышал передачу
                    event.subject.receive_end(time, event.object)
                case "A_send_end": # завершить передачу, которую FT не слушал
                    event.subject.send_end(time,event.object)
                case "wait_end": # если FT занят, когда PT передает
                    event.subject.wait_end(time, event.object, None)
                case "trans_check":
                    clusters_to_check.append(event.subject.cluster)
                # case "check_packet": # only used if arrival_type != none
                #     event.subject.check_packet(time)
        if clusters_to_check != []:
            for cluster in clusters_to_check:
                for operation in cluster.LBTs+cluster.transmissions:
                    operation.check()
    for cluster in clusters: # когда всемя закончилось
        for pt_device in cluster.PT_devices:
            # Делаем так, чтобы все пакеты были в переданных по одному разу
            # Они там по несколько раз, потому что устройство не получает ACK и начинает еще раз слать
            pt_device.delivered_packets = list(dict.fromkeys(pt_device.delivered_packets))
    
# Функция "следующее событие", возвращающая из списка событий то, которое по времени должно случится следующим
def next_event():
    global events
    min_time = np.inf
    for event in events: # поиск события с минимальным временем
        if event.ttime<min_time:
            res = event
            min_time = event.ttime
    events.remove(res) # удаление найденного события (т.к. сейчас оно случится)
    return res

# Функция "следующее событие", возвращающая из списка событий то, которое по времени должно случится следующим
def next_events():
    global events
    res = []
    min_time = np.inf
    for event in events: # поиск события с минимальным временем
        if event.ttime == min_time:
            res.append(event)
        elif event.ttime<min_time:
            min_time = event.ttime
            res = [event]
    for event in res:
        events.remove(event) # удаление найденного события (т.к. сейчас оно случится)
    return res

def print_event(event):
    print(event.ttime, event.content, event.subject)
    # print(event.ttime, event.content, event.subject.cluster.id, event.subject.id)
    # print(event.ttime, event.content)

def print_events(event_list):
    for event in event_list:
        # print(event.content, end=' ')
        print(str(event.ttime)+":"+event.content, end=' ')
    print()

# for graphana
def print_timeline(timeline):
    for e in range(len(timeline)-1):
        for i in range(timeline[e+1].ttime-timeline[e].ttime):
            print(timeline[e].content, end=',')
    
    for i in range(model_time-timeline[-1].ttime):
            print(timeline[-1].content, end=',')

# for graphana
def print_for_diagram():
    print("FT 1")
    print_timeline(root_device.timeline)
    for cluster in clusters:
        for device in cluster.devices:
            print()
            print()
            print(str(type(device))[-4:-2], str(cluster.id+1),str(device.id+1))
            print_timeline(device.timeline)

def device_state_at(ttime, timeline=None, device=None, mark_exact=False):
    if timeline == None:
        timeline = device.timeline
    for event in reversed(timeline):
        if event.ttime <= ttime:
            if event.ttime == ttime and mark_exact: return "exact "+event.content
            else: return event.content
    return None

def device_timeline_AB(A,B, timeline=None, device=None):
    if A>B:
        # return
        A,B = B, A
    if timeline == None:
        timeline = device.timeline
    for event in timeline:
        if event.ttime>=A:
            if event.ttime>B: return
            print(event.ttime,":",device_state_at(event.ttime, timeline=timeline, mark_exact=False))

def clean():
    for cluster in clusters:
        cluster.clearr()
        for device in cluster.devices:
            device.clearr()
    root_device.clearr()




def sim_delay(cluster):
    """Mean generation-to-first-delivery delay of uniquely delivered PT packets."""
    tmp = []
    for device in cluster.PT_devices:
        for packet in device.delivered_packets:
            delivery_times = [e.ttime for e in packet.journey
                              if e.content == "delivered"]
            if delivery_times:
                tmp.append(min(delivery_times) - packet.journey[0].ttime)
    return stt.mean(tmp) if tmp else None


# works only for cluster_count=1
# длина сессии
# как sim_delay(), но исключая ожидание в очереди, т.е. просто время обслуж.
def sim_service(cluster, add_idle):
    tmp = []
    for device in cluster.devices: # во всех устройствах кластера
        for packet in device.delivered_packets: # все пакеты устройства
            # print_events(packet.journey)
            # print()
            service = packet.journey[-1].ttime - packet.journey[1].ttime # исключая ожидание в очереди
            tmp.append(service)
    if tmp == []:
        return None
    idle_time=1
    if add_idle: return stt.mean(tmp)+ack_time+idle_time
    else: return stt.mean(tmp)+ack_time

def anl_service(lbt_succ_rate, error_rate, count_zero_cycles, add_idle):
    states = ['backoff', 'LBT', 'upd', 'out', 'proc+ack']
    res = 0
    for state in states:
        tmp = anl_state(lbt_succ_rate, error_rate, count_zero_cycles, state)
        res += tmp
    idle_time=1
    if add_idle: return res+idle_time
    else: return res+ack_time

def sim_batch_service(cluster, B):
    tmp = []
    for device in cluster.devices: # во всех устройствах кластера
        short_delivered_packets = device.delivered_packets[0::B]
        for i in range(1, len(short_delivered_packets)): # каждый B-й пакет устройства
            prev_packet = short_delivered_packets[i-1]
            packet = short_delivered_packets[i]
            batch_service = packet.journey[-1].ttime - prev_packet.journey[1].ttime # исключая ожидание в очереди
            tmp.append(batch_service)
    if tmp == []:
        return None
    return stt.mean(tmp)


# суммарное время нахождения в состоянии, среднее по пакетам и устройствам 
def sim_state(cluster, state, count_zero_cycles, print_out=False): # state = backoff / LBT / transmission / proc
    if state == "proc+ack":
        if count_zero_cycles: return sim_state(cluster, "proc", count_zero_cycles, print_out) + ack_time*qnempty
        else: return sim_state(cluster, "proc", count_zero_cycles, print_out) + ack_time
    if state == "upd": return sim_state(cluster, "transmission", count_zero_cycles, print_out)
    if state == "out": return sim_state(cluster, "wait", count_zero_cycles, print_out)
    tmp = []
    for device in cluster.devices: # во всех устройствах кластера
        tmp1 = []
        pkt_count = 0
        for packet in device.delivered_packets: # все доставленные пакеты устройства
            pkt_count+=1
            if print_out: print("pkt"+str(pkt_count)+":", end=" [ ") # в [] длительности пребываения в состоянии за сессию
            tmp2 = [] # массив времен, проведенных в состоянии
            i_count = 0 # сколько раз передавал
            for e in range(len(packet.journey)-1): # -1 потому что delivered не всегда последний (потому что повторная передача того же пакета)
                event = packet.journey[e]
                if event.content == "transmission":
                    i_count+=1
                    if print_out: print(".", end=" ") # типа была передача
                if event.content == state: # если находим интересующее состояние
                    state_time = packet.journey[e+1].ttime - packet.journey[e].ttime # считаем время от начала интерес. события 
                                                                                    # до начала следующего за ним события
                    if print_out: print(state_time, end=" ")
                    tmp2.append(state_time)
            if print_out: print("] i_count="+str(i_count), "D_"+str(state)+"="+str(sum(tmp2))) # D - суммарное время, проведенное в состоянии
            if print_out and i_count>10:
                i_count = 0
                print("-----------------------------------------------------------")
                for e in range(len(packet.journey)-1):
                    event = packet.journey[e]
                    if event.content == "transmission":
                        i_count+=1
                        print(str(i_count)+")", event.ttime, ":", device_state_at(device=cluster.FT, ttime=event.ttime, mark_exact=True), ",", device_state_at(device=cluster.FT, ttime=event.ttime+trans_time+proc_time, mark_exact=True)) # номер попытки передачи, время, состояние FT, состояние FT через proc_time
                print("-----------------------------------------------------------")
                device_timeline_AB(0, np.inf, packet.journey)
                print("-----------------------------------------------------------")

            tmp1.append(sum(tmp2))  # добавляем в массив по пакетам суммарное время, проведенное в состоянии за пакет (за сессию)
        
        if count_zero_cycles:
            tmp1 = tmp1 + [0 for i in range(device.empty_cycle_count)] # МОЖЕТ НЕ РАБОТАТЬ ДЛЯ cluster_count>1 
        # print(tmp1)
        tmp.append(stt.mean(tmp1))  # добавляем в массив среднее по пакетам (по сессиям) время
        # print(tmp)
    if tmp == []:
        return None
    # print(stt.mean(tmp))
    return stt.mean(tmp) # возвращаем среднее
# число раз, когда пакет находился в состоянии, среднее по пакетам и устройствам 
def sim_state_count(cluster, state, count_zero_cycles):
    if state == "proc+ack":
        if count_zero_cycles: return sim_state_count(cluster, "proc", count_zero_cycles) + ack_time*qnempty
        else: return sim_state_count(cluster, "proc", count_zero_cycles) + ack_time
    if state == "upd": return sim_state_count(cluster, "transmission", count_zero_cycles)
    if state == "out": return sim_state_count(cluster, "wait", count_zero_cycles)
    tmp = []
    for device in cluster.devices: # во всех устройствах кластера
        tmp1 = []
        for packet in device.delivered_packets: # все доставленные пакеты (сессии) устройства
            state_count = 0 # сколько раз
            for e in range(len(packet.journey)-1): # -1 потому что delivered не всегда последний (потому что повторная передача того же пакета)
                event = packet.journey[e]
                if event.content == state: # если находим интересующее состояние
                    state_count+=1
            tmp1.append(state_count)  # добавляем в массив по пакетам суммарное время, проведенное в состоянии за пакет (за сессию)
        
        if count_zero_cycles:
            tmp1 = tmp1 + [0 for i in range(device.empty_cycle_count)] # МОЖЕТ НЕ РАБОТАТЬ ДЛЯ cluster_count>1 
        tmp.append(stt.mean(tmp1))  # добавляем в массив среднее по пакетам (по сессиям) число
    if tmp == []:
        return None
    return stt.mean(tmp) # возвращаем среднее

def sim_state_pi(cluster, state, count_zero_cycles):
    D_state = sim_state(cluster, state, count_zero_cycles)
    D_session = sim_service(cluster, add_idle=False)
    if count_zero_cycles: return "ADD CODE"
    else: return D_state/D_session

def anl_state(lbt_succ_rate, error_rate, count_zero_cycles, state):
    pf = lbt_succ_rate
    p = error_rate
    if arrival_type == "qnempty": pa = qnempty
    else: return "set pa!!"
    # imax = int(math.log(int(c_max/c_min), 2)) + 1
    imax = int(math.log(c_max/c_min, 2)) + 1
    taubo = 2
    tauLBT = 2
    tauupd = 10
    tauout = 15
    tauprocack = 15
    match state:
        case "backoff":
            tmp = sum([(min(2**(i-1)*c_min,c_max))*((1-pf+pf*p)**(i-1))/(2) for i in range(2,imax+1)])
            if count_zero_cycles: return pa*(c_min/2 + (c_max*((1-pf+pf*p)**imax))/(2*(pf*(1-p))) + tmp)*taubo
            else: return 1*(c_min/2 + (c_max*((1-pf+pf*p)**imax))/(2*(pf*(1-p))) + tmp)*taubo
        case "LBT":
            if count_zero_cycles: return pa/(pf*(1-p))*tauLBT
            else: return 1/(pf*(1-p))*tauLBT
        case "upd":
            if count_zero_cycles: return pa/(1-p)*tauupd
            else: return 1/(1-p)*tauupd
        case "out":
            if count_zero_cycles: return pa*p/(1-p)*tauout
            else: return p/(1-p)*tauout
        case "proc+ack":
            if count_zero_cycles: return pa*tauprocack
            else: return tauprocack

def sim_aoi(cluster):
    tmp = []
    for device in cluster.devices: # во всех устройствах кластера
        for i in range(1, len(device.delivered_packets)): # все пакеты устройства
            prev_packet = device.delivered_packets[i-1]
            packet = device.delivered_packets[i]
            aoi = packet.journey[-1].ttime - prev_packet.journey[0].ttime
            tmp.append(aoi)
    if tmp == []:
        return None
    return stt.mean(tmp)

def anl_aoi(lbt_succ_rate, error_rate):
    p_a=qnempty
    D_session = anl_service(lbt_succ_rate, error_rate, count_zero_cycles=False, add_idle=False)
    D_cycle = 1 + p_a*D_session
    # D_cycle = 1 + D_session
    # return 1/p_a + D_cycle
    return 1/p_a + 2*D_session
    # return D_session

# вероятность необходимости повторной передачи
def error_rate(cluster):
    return (cluster.all-cluster.succ)/cluster.all

def lbt_succ_rate(cluster):
    return cluster.LBTsucc/cluster.LBTall

def nonempty_queue_rate(cluster):
    return cluster.qnemptysucc/cluster.qnemptyall

# вероятность того, что ACK не дойдет
def ack_fail_rate(cluster):
    return 1-(cluster.ACKsucc/cluster.ACKall)

def throughput(cluster):
    return trans_time*cluster.all/model_time

def throughput_succ(cluster):
    return trans_time*cluster.succ/model_time

def delivered_num(cluster):
    tmp = 0
    for device in cluster.devices:
        tmp += len(device.delivered_packets)
    return tmp

#-----------------------------------------------------------------


global devices_in_cluster_count
global cluster_count
global trans_time # сколько символов занимает передача
global proc_time # сколько символов занимает обработка
global ack_time # сколько символов занимает передача ack
global lbt_time # сколько символов занимает LBT

global c_min
global c_max

global topology
global clusters
global root_device

global Lmb

global model_time
global events

# global generate_new # if False, generates a packet at each PT and no more packets
global ack_delivery_allways_succ # ACK delivery is allways successful, even if another transmission was underway
global lbt_always_succ # LBT always returns "channel is clear" 
global c_min_for_retry 
# global use_qnempty 
global arrival_type
global arrprob

# DEFAULTS
ack_delivery_always_succ = False
lbt_always_succ = False
c_min_for_retry = False # после неуспешной передачи c_current = c_min
arrival_type = "none" # none / qnempty / arrprob
# generate_new = True # ЕСЛИ arrival_type != none, ПОСТАВИТЬ generate_new = False БОЛЬШЕ НЕ ИСПОЛЬЗУЕТСЯ
qnempty = None
arrprob = None
trans_time = 10
proc_time = 10
ack_time = 5
lbt_time = 2
# DEFAULTS






cluster_count = 1
devices_in_cluster_count = 20

c_min = 1
c_max = 1

model_time = 3000
# ack_delivery_always_succ = True 
ack_delivery_always_succ = False

arrival_type = "arrprob" # none / qnempty / arrprob
arrprob = 0.01


