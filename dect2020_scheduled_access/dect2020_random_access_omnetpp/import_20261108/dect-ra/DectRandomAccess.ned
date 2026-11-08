simple RandomAccessModel
{
    parameters:
        int ptCount = default(2);
        int generationIntervalSymbols = default(500);

        int cMin = default(5);
        int cMax = default(40);
        bool resetBackoffAfterNoAck = default(false);

        int lbtSymbols = default(2);
        int dataSymbols = default(10);
        int procSymbols = default(10);
        int ackSymbols = default(5);

        double symbolTime @unit(s) = default(41.666666667us);
        int simulationSymbols = default(100000);
        int warmupSymbols = default(0);

        @display("i=block/process");
}

network DectRandomAccess
{
    submodules:
        model: RandomAccessModel {
            @display("p=180,100");
        }
}
