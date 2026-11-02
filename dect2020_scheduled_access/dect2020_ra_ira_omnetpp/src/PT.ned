simple PT
{
    parameters:
        int    id;
        double arrProb;
        int    cMin;
        int    cMax;
        bool   forceZeroBackoff = default(false);
        double lbtTime    @unit(s);   // длительность слота backoff
        double ackTimeout @unit(s);   // таймаут ожидания ACK
    gates:
        input  in;
        output out;
}