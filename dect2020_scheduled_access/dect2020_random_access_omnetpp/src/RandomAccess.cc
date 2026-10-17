#include <omnetpp.h>
#include <algorithm>
#include <cmath>
#include <deque>
#include <map>
#include <string>
#include <vector>
using namespace omnetpp;

// One OMNeT++ simulation second represents one DECT symbol.
class RandomAccess : public cSimpleModule {
    enum {PROC=0, START_FT, END_LBT, END_ACK, END_RX, END_TX, START_PT, GENERATE, WAIT};
    enum {LBT, DATA, ACK};
    struct Packet { long born; int origin, cluster; bool delivered=false; };
    struct Sender {
        int cluster, cw, op=-1, backoff=-1;
        long pause=-1;
        bool ft=false, free=true;
        std::deque<int> queue;
    };
    struct Op { int kind, cluster, from, packet; bool ok=true, active=true; };
    struct Event { long t; int type, from, op, packet, receiver; bool canceled=false; };
    std::vector<Sender> nodes;
    std::vector<Packet> packets;
    std::vector<Op> ops;
    std::vector<Event> events;
    std::multimap<long,int> timeline;
    std::vector<int> ft, currentLbt[2], currentTx[2];
    long horizon, interval;
    int minimum, maximum, trans=10, processing=10, ack=5, listen=2, nClusters;
    bool rootFree=true;
    double delay[2]={}, aoi[2]={};
    long delivered[2]={}, peaks[2]={};
    std::vector<long> previousGeneration;
    cMessage *tick=nullptr;

    int add(long t, int type, int from=-1, int op=-1, int packet=-1, int receiver=-1) {
        int i=events.size();
        events.push_back({t,type,from,op,packet,receiver});
        timeline.emplace(t,i);
        return i;
    }
    void next() {
        while (!timeline.empty() && events[timeline.begin()->second].canceled) timeline.erase(timeline.begin());
        if (!timeline.empty() && timeline.begin()->first<=horizon)
            scheduleAt(SimTime(timeline.begin()->first, SIMTIME_S),tick);
    }
    void startBackoff(int s,long t) {
        Sender &n=nodes[s];
        if(n.queue.empty()) return;
        n.free=true;
        n.backoff=add(t+intuniform(0,n.cw)*listen,n.ft?START_FT:START_PT,s);
    }
    void receiveFree(int receiver,long t) {
        if(receiver<0) { rootFree=true; return; }
        Sender &n=nodes[receiver];
        n.free=true;
        if(n.pause>=0) {
            n.backoff=add(t+n.pause,START_FT,receiver);
            n.pause=-1;
        } else if(!n.queue.empty() && n.backoff<0) startBackoff(receiver,t);
    }
    void removeOp(int i) {
        if(i<0 || !ops[i].active) return;
        Op &o=ops[i];
        auto &v=o.kind==LBT?currentLbt[o.cluster]:currentTx[o.cluster];
        v.erase(std::remove(v.begin(),v.end(),i),v.end());
        o.active=false;
    }
    int newOp(int kind,int sender,int pkt) {
        int i=ops.size();
        ops.push_back({kind,nodes[sender].cluster,sender,pkt});
        (kind==LBT?currentLbt[nodes[sender].cluster]:currentTx[nodes[sender].cluster]).push_back(i);
        return i;
    }
    void startData(int sender,long t) {
        Sender &n=nodes[sender];
        int pkt=n.queue.front(), op=newOp(DATA,sender,pkt);
        n.op=op;
        int receiver=n.cluster==0?-1:ft[n.cluster-1];
        bool available=receiver<0?rootFree:nodes[receiver].free;
        if(available) {
            if(receiver<0) rootFree=false;
            else {
                Sender &f=nodes[receiver];
                f.free=false;
                if(f.backoff>=0) {
                    events[f.backoff].canceled=true;
                    f.pause=std::max(0L,events[f.backoff].t-t);
                    f.backoff=-1;
                }
            }
            add(t+trans,END_RX,sender,op,pkt,receiver);
        } else {
            ops[op].ok=false;
            add(t+trans,END_TX,sender,op);
            add(t+trans+processing,WAIT,sender,op,pkt);
        }
    }
    void waitAck(int sender,int dataOp,int pkt,int receiver,long t) {
        int ackOp=-1;
        if(dataOp>=0 && ops[dataOp].ok) {
            int i=ops.size();
            ops.push_back({ACK,nodes[sender].cluster,receiver,pkt});
            currentTx[nodes[sender].cluster].push_back(i);
            ackOp=i;
        }
        add(t+ack,END_ACK,sender,ackOp,pkt,receiver);
    }
    void checkChannel() {
        for(int c=0;c<nClusters;c++) {
            if(!currentTx[c].empty()) for(int i:currentLbt[c]) ops[i].ok=false;
            if(currentTx[c].size()>1) for(int i:currentTx[c]) ops[i].ok=false;
        }
    }
    void dispatch(const Event &e,long t) {
        switch(e.type) {
        case GENERATE: {
            int pkt=packets.size();
            packets.push_back({t,e.from,nodes[e.from].cluster});
            Sender &n=nodes[e.from];
            bool empty=n.queue.empty();
            n.queue.push_back(pkt);
            if(empty && (!n.ft || n.free)) startBackoff(e.from,t);
            add(t+interval,GENERATE,e.from);
            break;
        }
        case START_PT: case START_FT: {
            Sender &n=nodes[e.from];
            n.backoff=-1;
            if(e.type==START_FT) n.free=false;
            int op=newOp(LBT,e.from,n.queue.front());
            n.op=op;
            add(t+listen,END_LBT,e.from,op);
            break;
        }
        case END_LBT: {
            bool ok=ops[e.op].ok;
            removeOp(e.op);
            Sender &n=nodes[e.from];
            if(ok) startData(e.from,t);
            else { n.cw=std::min(maximum,2*n.cw); startBackoff(e.from,t); }
            break;
        }
        case END_TX: removeOp(e.op); break;
        case END_RX:
            add(t+processing,PROC,e.from,e.op,e.packet,e.receiver);
            removeOp(e.op);
            break;
        case PROC: {
            if(ops[e.op].ok) {
                if(e.receiver<0) {
                    Packet &p=packets[e.packet];
                    if(!p.delivered) {
                        p.delivered=true;
                        int c=p.cluster;
                        delay[c]+=t-p.born;
                        delivered[c]++;
                        if(previousGeneration[p.origin]>=0) {
                            aoi[c]+=t-previousGeneration[p.origin];
                            peaks[c]++;
                        }
                        previousGeneration[p.origin]=p.born;
                    }
                } else nodes[e.receiver].queue.push_back(e.packet);
                waitAck(e.from,e.op,e.packet,e.receiver,t);
            } else {
                waitAck(e.from,-1,e.packet,e.receiver,t);
                receiveFree(e.receiver,t);
            }
            break;
        }
        case WAIT: waitAck(e.from,-1,e.packet,-1,t); break;
        case END_ACK: {
            Sender &n=nodes[e.from];
            bool ok=e.op>=0 && ops[e.op].ok;
            if(e.op>=0) removeOp(e.op);
            if(ok) {
                n.queue.pop_front();
                n.cw=minimum;
                if(!n.queue.empty()) startBackoff(e.from,t);
                else if(n.ft) n.free=true;
            } else {
                n.cw=std::min(maximum,2*n.cw);
                startBackoff(e.from,t);
            }
            if(e.op>=0) receiveFree(e.receiver,t);
            break;
        }
        }
    }
protected:
    void initialize() override {
        nClusters=par("clusters");
        int D=par("devices");
        interval=par("period"); minimum=par("cwMin"); maximum=par("cwMax"); horizon=par("duration");
        if(nClusters<1 || nClusters>2 || D<2 || interval<1 || minimum<1 || maximum<minimum)
            throw cRuntimeError("Require 1 or 2 clusters, D>=2, period>=1, 1<=cwMin<=cwMax");
        ft.assign(nClusters,-1);
        for(int c=0;c<nClusters;c++) {
            if(c<nClusters-1) { ft[c]=nodes.size(); nodes.push_back({c,minimum,-1,-1,-1,true,true,{}}); }
            for(int i=(c<nClusters-1?1:0);i<D;i++) nodes.push_back({c,minimum});
        }
        previousGeneration.assign(nodes.size(),-1);
        for(int i=0;i<(int)nodes.size();i++) if(!nodes[i].ft) add(0,GENERATE,i);
        tick=new cMessage("next-symbol");
        next();
    }
    void handleMessage(cMessage *msg) override {
        long t=simTime().inUnit(SIMTIME_S);
        std::vector<int> batch;
        auto range=timeline.equal_range(t);
        for(auto it=range.first;it!=range.second;++it) if(!events[it->second].canceled) batch.push_back(it->second);
        timeline.erase(range.first,range.second);
        std::stable_sort(batch.begin(),batch.end(),[&](int a,int b){return events[a].type<events[b].type;});
        for(int i:batch) { Event e=events[i]; dispatch(e,t); }
        checkChannel();
        next();
    }
    void finish() override {
        for(int c=0;c<nClusters;c++) {
            recordScalar(("delay_"+std::to_string(c)).c_str(),delivered[c]?delay[c]/delivered[c]:NAN);
            recordScalar(("paoi_"+std::to_string(c)).c_str(),peaks[c]?aoi[c]/peaks[c]:NAN);
            recordScalar(("delivered_"+std::to_string(c)).c_str(),delivered[c]);
        }
    }
    ~RandomAccess() override { cancelAndDelete(tick); }
};
Define_Module(RandomAccess);
