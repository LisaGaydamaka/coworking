// Starter network: extend the topology if you choose per-device OMNeT++ modules.
simple RandomAccess
{
    parameters:
        int clusters = default(1);
        int devices = default(2);
        int period = default(500);
        int cwMin = default(5);
        int cwMax = default(40);
        int duration = default(800000);
        @display("i=block/network");
}
network RandomAccessNetwork
{
    submodules:
        ra: RandomAccess;
}
