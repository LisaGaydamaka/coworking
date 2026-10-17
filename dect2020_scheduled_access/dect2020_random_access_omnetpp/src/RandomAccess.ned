simple RandomAccess
{
    parameters:
        int clusters = default(1);
        int devices = default(2);
        int period = default(500); // symbols between packet generations
        int cwMin = default(5);
        int cwMax = default(40);
        int duration = default(800000); // in symbols
        @display("i=block/network");
}
network RandomAccessNetwork
{
    submodules:
        ra: RandomAccess;
}
