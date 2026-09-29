package dect2020scheduledaccess;

simple ScheduledAccessQueue
{
    parameters:
        int D = default(10);                         // PT devices in the DECT leaf cluster
        simtime_t frameDuration = default(10ms);
        simtime_t meanType1ServiceTime = default(0.4166666667ms);

        bool deriveDectParametersFromD = default(true);
        int L = default(2);                          // used when deriveDectParametersFromD=false
        simtime_t type2ServiceTime = default(9ms); // used when deriveDectParametersFromD=false

        bool deriveLambdaFromRho = default(true);
        double rho = default(0.05);                 // rho = lambda * E[B]
        double lambdaPerMs = default(0.12);         // used when deriveLambdaFromRho=false

        int r = default(30);                         // waiting-buffer capacity
        long warmupCompletedPackets = default(200000);
        long targetCompletedPackets = default(1000000);
        int rngIndex = default(0);
        bool recordVectors = default(false);

        @class(ScheduledAccessQueue);
        @display("i=block/queue");
}

network DectScheduledAccessNetwork
{
    submodules:
        queue: ScheduledAccessQueue {
            @display("p=200,120");
        }
}
