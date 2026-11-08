#include <omnetpp.h>

#include <algorithm>
#include <deque>
#include <limits>


#include <string>
#include <vector>

using namespace omnetpp;

class RandomAccessModel : public cSimpleModule
{
  private:
    enum PtState { IDLE, BACKOFF, LBT, DATA, WAIT_ACK };
    enum FtState { FT_IDLE, FT_RECEIVING, FT_PROCESSING, FT_ACK };

    struct Packet {
        long id = -1;
        simtime_t generatedAt;
        simtime_t lastDeliveredAt;
        bool hasDelivery = false;
    };

    struct Pt {
        std::deque<Packet> queue;
        PtState state = IDLE;
        int attempt = 0;
        int backoffRemaining = 0;
        int lbtRemaining = 0;
        bool lbtWasBusy = false;
        int dataRemaining = 0;
        bool dataDataCollision = false;
        bool dataAckCollision = false;
        bool receiverRejected = false;

        int waitRemaining = 0;
        bool ackReceived = false;
    };

    std::vector<Pt> pts;
    cMessage *tick = nullptr;

    int ptCount = 0;
    int generationIntervalSymbols = 0;
  
    bool resetBackoffAfterNoAck = false;
    int lbtSymbols = 0;

    int cMin = 0;

    int cMax = 0;

    int dataSymbols = 0;
    int procSymbols = 0;
    int ackSymbols = 0;



    simtime_t symbolTime;


    long simulationSymbols = 0;

    long warmupSymbols = 0;
    long currentSymbol = 0;





    FtState ftState = FT_IDLE;
    int ftRemaining = 0;
    int ftPt = -1;



    long ftPacketId = -1;
    bool ftAckCollided = false;



    bool ftDataSucceeded = false;

    long nextPacketId = 0;
    long generatedPackets = 0;
    long completedPackets = 0;


    long measuredCompletedPackets = 0;

    long uniqueDeliveredPackets = 0;
    long measuredDeliveredPackets = 0;
    long successfulDataDeliveries = 0;
    long dataTransmissionAttempts = 0;


    long failedDataTransmissionAttempts = 0;
    long ackTimeoutCount = 0;
    long retransmissions = 0;


    long busyLbtCount = 0;
    long dataDataCollisionAttempts = 0;
    long dataAckCollisionAttempts = 0;

    long ackCollisionCount = 0;

    long receiverBusyFailures = 0;
    double delaySumSeconds = 0;
    double delaySumSymbols = 0;

    double confirmedDelaySumSeconds = 0;
    double confirmedDelaySumSymbols = 0;

  protected:


    virtual void initialize() override;


    virtual void handleMessage(cMessage *message) override;


    virtual void finish() override;

  private:

    void generatePackets();


    void prepareStatesForSymbol();
    void runOneSymbol();

    int contentionWindow(int attempt) const;
    void startBackoff(int ptIndex);


    void retryPacket(int ptIndex, bool ackMissing);


    void finishProcessing();
    void recordDelivery(Packet& packet);
    void completePacket(int ptIndex, long packetId);

      void updateDisplay();

  public:
    virtual ~RandomAccessModel();
};

Define_Module(RandomAccessModel);

RandomAccessModel::~RandomAccessModel()
{
    cancelAndDelete(tick);
}

void RandomAccessModel::initialize()
{
    ptCount = par("ptCount");


    generationIntervalSymbols = par("generationIntervalSymbols");
    
    resetBackoffAfterNoAck = par("resetBackoffAfterNoAck");
    
     lbtSymbols = par("lbtSymbols");
    dataSymbols = par("dataSymbols");
    procSymbols = par("procSymbols");
    ackSymbols = par("ackSymbols");

    symbolTime = par("symbolTime");

    cMin = par("cMin");

    cMax = par("cMax");

    simulationSymbols = par("simulationSymbols");
    warmupSymbols = par("warmupSymbols");

    if (ptCount <= 0)
        throw cRuntimeError("ptCount must be positive");
    if (generationIntervalSymbols < 1)
        throw cRuntimeError("generationIntervalSymbols must be at least 1");
   
        if (cMin < 0 || cMax < cMin)
        throw cRuntimeError("Backoff parameters must satisfy 0 <= cMin <= cMax");
    if (lbtSymbols <= 0 || dataSymbols <= 0 || procSymbols < 0 || ackSymbols <= 0)
        throw cRuntimeError("Invalid LBT, DATA, processing, or ACK duration");
    if (cMax > std::numeric_limits<int>::max() / lbtSymbols
            || procSymbols > std::numeric_limits<int>::max() - ackSymbols)
        throw cRuntimeError("Backoff or ACK waiting duration is too large");
    if (symbolTime <= SIMTIME_ZERO || simulationSymbols <= 0)
        throw cRuntimeError("symbolTime and simulationSymbols must be positive");
    if (warmupSymbols < 0 || warmupSymbols >= simulationSymbols)
        throw cRuntimeError("warmupSymbols must be in [0, simulationSymbols)");

    pts.resize(ptCount);

    tick = new cMessage("symbolTick");
    scheduleAt(SIMTIME_ZERO, tick);
    updateDisplay();
}

void RandomAccessModel::handleMessage(cMessage *message)

{
    if (message != tick)
        throw cRuntimeError("Unexpected message");

    if (currentSymbol >= simulationSymbols) {
        endSimulation();
        return;
    }

    runOneSymbol();
    currentSymbol++;
    updateDisplay();
    scheduleAt(simTime() + symbolTime, tick);
}

void RandomAccessModel::generatePackets()
{
    if (currentSymbol % generationIntervalSymbols != 0)
        return;

    for (int i = 0; i < ptCount; i++) {
        bool wasEmpty = pts[i].queue.empty();

        Packet packet;
        packet.id = nextPacketId++;
        packet.generatedAt = simTime();
        pts[i].queue.push_back(packet);
        generatedPackets++;

        if (wasEmpty) {
            pts[i].attempt = 0;
            startBackoff(i);
        }
    }
}

int RandomAccessModel::contentionWindow(int attempt) const
{
    if (cMin == 0)
        return 0;
    int window = cMin;
    for (int i = 0; i < attempt && window < cMax; i++) {
        if (window > cMax / 2)
            window = cMax;
        else
            window *= 2;
    }
    return std::min(window, cMax);
}





void RandomAccessModel::startBackoff(int ptIndex)
{
    Pt& pt = pts[ptIndex];
    int window = contentionWindow(pt.attempt);
    int randomValue = intuniform(0, window);

    pt.state = BACKOFF;
    pt.backoffRemaining = lbtSymbols * randomValue;
    pt.ackReceived = false;
}

void RandomAccessModel::retryPacket(int ptIndex, bool ackMissing)
{
    if (ackMissing)
        ackTimeoutCount++;
    if (ackMissing && resetBackoffAfterNoAck)
        pts[ptIndex].attempt = 0;
    else
        pts[ptIndex].attempt++;
    retransmissions++;
    startBackoff(ptIndex);
}

void RandomAccessModel::prepareStatesForSymbol()
{
    for (Pt& pt : pts) {
        if (pt.state == BACKOFF && pt.backoffRemaining == 0) {
            pt.state = LBT;
            pt.lbtRemaining = lbtSymbols;
            pt.lbtWasBusy = false;
        }
    }
}


















void RandomAccessModel::runOneSymbol()
{
    generatePackets();
    prepareStatesForSymbol();

    std::vector<PtState> oldStates(ptCount);
    int transmittingDataCount = 0;
    for (int i = 0; i < ptCount; i++) {
        oldStates[i] = pts[i].state;
        if (pts[i].state == DATA)
            transmittingDataCount++;
    }

    bool ackIsTransmitting = (ftState == FT_ACK);
    bool channelIsBusy = transmittingDataCount > 0 || ackIsTransmitting;

    for (int i = 0; i < ptCount; i++) {
        Pt& pt = pts[i];
        if (pt.state == LBT && channelIsBusy)
            pt.lbtWasBusy = true;

        if (pt.state == DATA) {
            if (transmittingDataCount > 1)
                pt.dataDataCollision = true;
            if (ackIsTransmitting)
                pt.dataAckCollision = true;
        }
    }

    if (ackIsTransmitting && transmittingDataCount > 0)
        ftAckCollided = true;

    
    for (int i = 0; i < ptCount; i++) {
        Pt& pt = pts[i];
        if (pt.state == DATA && pt.dataRemaining == dataSymbols) {
            dataTransmissionAttempts++;
            pt.receiverRejected = (ftState != FT_IDLE);
            if (!pt.receiverRejected) {
                ftState = FT_RECEIVING;
                ftRemaining = dataSymbols;
                ftPt = i;
                ftPacketId = pt.queue.front().id;
            }
            else {
                receiverBusyFailures++;
            }
        }
    }

    FtState oldFtState = ftState;


    bool ackFinished = false;

    bool ackSucceeded = false;
    int ackPt = -1;

    long ackPacketId = -1;

    if (oldFtState == FT_RECEIVING) {

              ftRemaining--;
        if (ftRemaining == 0) {
            Pt& pt = pts[ftPt];
            ftDataSucceeded = !pt.dataDataCollision && !pt.dataAckCollision;
            ftState = FT_PROCESSING;
            ftRemaining = procSymbols;
            if (procSymbols == 0)
                finishProcessing();
        }
    }
    else if (oldFtState == FT_PROCESSING) {
        ftRemaining--;
        if (ftRemaining == 0) {
            finishProcessing();
        }
    }
    else if (oldFtState == FT_ACK) {
        ftRemaining--;
        if (ftRemaining == 0) {
            ackFinished = true;
            ackSucceeded = !ftAckCollided;
            ackPt = ftPt;
            ackPacketId = ftPacketId;
            if (!ackSucceeded)
                ackCollisionCount++;

            ftState = FT_IDLE;
            ftPt = -1;
            ftPacketId = -1;
        }
    }

    for (int i = 0; i < ptCount; i++) {
        Pt& pt = pts[i];

        if (oldStates[i] == BACKOFF) {
            if (pt.backoffRemaining > 0)
                pt.backoffRemaining--;
        }
        else if (oldStates[i] == LBT) {
            pt.lbtRemaining--;
            if (pt.lbtRemaining == 0) {
                if (pt.lbtWasBusy) {
                    busyLbtCount++;
                    retryPacket(i, false);
                }
                else {
                    pt.state = DATA;
                    pt.dataRemaining = dataSymbols;
                    pt.dataDataCollision = false;
                    pt.dataAckCollision = false;
                }
            }
        }
        else if (oldStates[i] == DATA) {
            pt.dataRemaining--;
            if (pt.dataRemaining == 0) {
                if (pt.dataDataCollision)
                    dataDataCollisionAttempts++;
                if (pt.dataAckCollision)
                    dataAckCollisionAttempts++;

                if (pt.dataDataCollision || pt.dataAckCollision || pt.receiverRejected)
                    failedDataTransmissionAttempts++;

                pt.state = WAIT_ACK;
                pt.waitRemaining = procSymbols + ackSymbols;
                pt.ackReceived = false;
            }
        }
    }

    if (ackFinished && ackSucceeded && ackPt >= 0 && ackPt < ptCount) {
        Pt& pt = pts[ackPt];
        if (pt.state == WAIT_ACK && !pt.queue.empty() && pt.queue.front().id == ackPacketId)
            pt.ackReceived = true;
    }

    for (int i = 0; i < ptCount; i++) {
        Pt& pt = pts[i];
        if (oldStates[i] == WAIT_ACK) {
            pt.waitRemaining--;
            if (pt.waitRemaining == 0) {
                long packetId = pt.queue.front().id;
                if (pt.ackReceived)
                    completePacket(i, packetId);
                else
                    retryPacket(i, true);
            }
        }
    }
}

void RandomAccessModel::finishProcessing()
{
    Pt& pt = pts[ftPt];
    if (pt.queue.empty() || pt.queue.front().id != ftPacketId)
        throw cRuntimeError("FT processing does not match the PT packet");



    if (ftDataSucceeded) {
        recordDelivery(pt.queue.front());
        ftState = FT_ACK;
        ftRemaining = ackSymbols;
        ftAckCollided = false;
    }
    else {
    
        ftState = FT_IDLE;
        ftPt = -1;
        ftPacketId = -1;
    }
}

void RandomAccessModel::recordDelivery(Packet& packet)
{
    simtime_t deliveredAt = simTime() + symbolTime;

    successfulDataDeliveries++;
    if (!packet.hasDelivery)
        uniqueDeliveredPackets++;




    if (packet.generatedAt >= warmupSymbols * symbolTime) {
        // A repeat replaces the old delivery time, without adding another packet.
        if (packet.hasDelivery) {
            simtime_t oldDelay = packet.lastDeliveredAt - packet.generatedAt;
            delaySumSeconds -= oldDelay.dbl();
            delaySumSymbols -= oldDelay.dbl() / symbolTime.dbl();
        }
        else {
            measuredDeliveredPackets++;
        }
        simtime_t delay = deliveredAt - packet.generatedAt;
        delaySumSeconds += delay.dbl();
        delaySumSymbols += delay.dbl() / symbolTime.dbl();
    }
    packet.lastDeliveredAt = deliveredAt;
    packet.hasDelivery = true;
}

void RandomAccessModel::completePacket(int ptIndex, long packetId)
{
    Pt& pt = pts[ptIndex];
    if (pt.queue.empty() || pt.queue.front().id != packetId)
        throw cRuntimeError("ACK does not match the first packet in the PT queue");

    Packet packet = pt.queue.front();
    pt.queue.pop_front();

    if (!packet.hasDelivery)
        throw cRuntimeError("A packet with no successful DATA delivery received an ACK");

    completedPackets++;

    if (packet.generatedAt >= warmupSymbols * symbolTime) {



        simtime_t delay = packet.lastDeliveredAt - packet.generatedAt;
                           double delaySeconds = delay.dbl();
        double delaySymbols = delaySeconds / symbolTime.dbl();

        measuredCompletedPackets++;
        confirmedDelaySumSeconds += delaySeconds;
        confirmedDelaySumSymbols += delaySymbols;
    }

    if (pt.queue.empty()) {
        pt.state = IDLE;
        pt.attempt = 0;
    }
    else {
        pt.attempt = 0;
        startBackoff(ptIndex);
    }
}

void RandomAccessModel::updateDisplay()
{
    if (!getEnvir()->isGUI())
        return;

    long queued = 0;
    for (const Pt& pt : pts)
        queued += pt.queue.size();

    std::string text = "symbol: " + std::to_string(currentSymbol)
            + "\ncompleted: " + std::to_string(completedPackets)
            + "\nqueued: " + std::to_string(queued);
    getDisplayString().setTagArg("t", 0, text.c_str());
}

void RandomAccessModel::finish()
{
    long queuedPackets = 0;
    for (const Pt& pt : pts)
        queuedPackets += pt.queue.size();

    recordScalar("generatedPackets", generatedPackets);
    recordScalar("completedPackets", completedPackets);
    recordScalar("measuredCompletedPackets", measuredCompletedPackets);


    recordScalar("uniqueDeliveredPackets", uniqueDeliveredPackets);
    recordScalar("measuredDeliveredPackets", measuredDeliveredPackets);

    recordScalar("successfulDataDeliveries", successfulDataDeliveries);
    recordScalar("deliveredPacketsAwaitingAck", uniqueDeliveredPackets - completedPackets);
    recordScalar("dataTransmissionAttempts", dataTransmissionAttempts);
    recordScalar("failedDataTransmissionAttempts", failedDataTransmissionAttempts);



    recordScalar("ackTimeoutCount", ackTimeoutCount);
    recordScalar("packetsLeftInQueues", queuedPackets);
    recordScalar("retransmissions", retransmissions);
    recordScalar("accessRetries", retransmissions);



    recordScalar("busyLbtCount", busyLbtCount);
    recordScalar("dataDataCollisionAttempts", dataDataCollisionAttempts);
    recordScalar("dataAckCollisionAttempts", dataAckCollisionAttempts);



    recordScalar("ackCollisionCount", ackCollisionCount);
    recordScalar("receiverBusyFailures", receiverBusyFailures);

    if (measuredDeliveredPackets > 0) {


        recordScalar("meanEndToEndDelaySeconds", delaySumSeconds / measuredDeliveredPackets, "s");
        recordScalar("meanEndToEndDelaySymbols", delaySumSymbols / measuredDeliveredPackets);
    }
    if (measuredCompletedPackets > 0) {

        
        recordScalar("meanConfirmedPacketDelaySeconds", confirmedDelaySumSeconds / measuredCompletedPackets, "s");
        recordScalar("meanConfirmedPacketDelaySymbols", confirmedDelaySumSymbols / measuredCompletedPackets);
    }
}
