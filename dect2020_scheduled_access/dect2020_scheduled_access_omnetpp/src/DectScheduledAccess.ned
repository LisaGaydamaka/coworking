package dect2020scheduledaccess;

simple ScheduledAccessQueue
{
    parameters:
        int D = default(10);                         // PT devices in the DECT leaf cluster
        double frameDuration @unit(s) = default(10ms);
        double meanType1ServiceTime @unit(s) = default(0.4166666667ms);

        bool deriveDectParametersFromD = default(true);
        int L = default(2);                          // used when deriveDectParametersFromD=false
        double type2ServiceTime @unit(s) = default(9ms); // used when deriveDectParametersFromD=false

        bool deriveLambdaFromRho = default(true);
        double rho = default(0.05);                 // rho = lambda * E[B]
        double lambdaPerMs = default(0.12);         // used when deriveLambdaFromRho=false

        int r = default(30);                         // waiting-buffer capacity
        int warmupCompletedPackets = default(200000);
        int targetCompletedPackets = default(1000000);
        int rngIndex = default(0);
        bool recordVectors = default(false);
        bool recordTailStatistics = default(false);       // retain measured delays and record P50/P95/P99/P99.9

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
