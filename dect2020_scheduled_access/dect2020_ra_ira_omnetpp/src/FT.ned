simple FT
{
    parameters:
        double procTime @unit(s);
        double ackTime  @unit(s);
    gates:
        input  in;
        output out;
}