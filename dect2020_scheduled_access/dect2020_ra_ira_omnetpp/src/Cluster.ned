network Cluster
{
    parameters:
        int    numPTs   = default(2);
        double arrProb  = default(0.01);
        int    cMin     = default(1);
        int    cMax     = default(16);
        bool   forceZeroBackoff = default(false);
        bool   useParityRandom = default(false);
        int    paritySeed = default(1); // deterministic parity test only
        double transTime @unit(s) = default(10s);
        double lbtTime   @unit(s) = default(2s);
        double procTime  @unit(s) = default(10s);
        double ackTime   @unit(s) = default(5s);
        // Exact Python wait_end()/ack_end() timing: Tdata + Tproc + Tack.
        // The ACK timeout event has lower execution precedence in PT.cc,
        // so a valid ACK arriving at this exact time cancels the timer.
        double ackTimeout @unit(s) = default(transTime + procTime + ackTime);

    submodules:
        pt[numPTs]: PT {
            parameters:
                id         = index;
                arrProb    = parent.arrProb;
                cMin       = parent.cMin;
                cMax       = parent.cMax;
                forceZeroBackoff = parent.forceZeroBackoff;
                useParityRandom = parent.useParityRandom;
                paritySeed = parent.paritySeed;
                lbtTime    = parent.lbtTime;
                ackTimeout = parent.ackTimeout;
            @display("p=100,80,row,120;i=device/pc");
        }
        medium: Medium {
            parameters:
                numPTs    = parent.numPTs;
                transTime = parent.transTime;
                lbtTime   = parent.lbtTime;
                ackTime   = parent.ackTime;
            @display("p=300,180;i=block/cloud");
        }
        ft: FT {
            parameters:
                procTime = parent.procTime;
                ackTime  = parent.ackTime;
            @display("p=480,180;i=device/server");
        }

    connections:
        for i = 0..numPTs-1 {
            pt[i].out --> { @display("ls=blue,2"); } --> medium.ptIn[i];
            medium.ptOut[i] --> { @display("ls=blue,2"); } --> pt[i].in;
        }
        medium.ftOut --> { @display("ls=green,2"); } --> ft.in;
        ft.out --> { @display("ls=green,2"); } --> medium.ftIn;
}