package dect2020scheduledaccess;

// Fixed 10ms frame with 24 slots: independent packet-slot benchmark.
simple FixedSlotQueue
{
    parameters:
        int D = default(10);
        int r = default(30);
        int totalSlots = default(24);
        int availableSlots = default(24);
        double frameDuration @unit(s) = default(10ms);
        double meanType1ServiceTime @unit(s) = default(0.4166666667ms);
        string slotLayout = default("contiguous");
        string trafficModel = default("poisson");
        int trafficBatchSize = default(4);
        bool deriveLambdaFromRho = default(false);
        double rho = default(0.08);
        double lambdaPerMs = default(0.2);
        int warmupCompletedPackets = default(200000);
        int targetCompletedPackets = default(1000000);
        bool recordTailStatistics = default(false);
        int rngIndex = default(0);
        @class(FixedSlotQueue);
        @display("i=block/queue");
}
network FixedSlotNetwork
{
    submodules:
        queue: FixedSlotQueue { @display("p=200,120"); }
}
