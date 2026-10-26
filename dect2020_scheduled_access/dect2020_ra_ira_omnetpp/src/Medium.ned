simple Medium
{
    parameters:
        int    numPTs;
        double transTime @unit(s);
        double lbtTime   @unit(s);
        double ackTime   @unit(s);
    gates:
        // Явно задаем размер массивов шлюзов
        input  ptIn[numPTs];
        output ptOut[numPTs];

        input  ftIn;
        output ftOut;
}