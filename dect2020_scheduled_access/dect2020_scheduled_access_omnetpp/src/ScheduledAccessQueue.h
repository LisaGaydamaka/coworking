#ifndef __DECT2020SCHEDULEDACCESS_SCHEDULEDACCESSQUEUE_H
#define __DECT2020SCHEDULEDACCESS_SCHEDULEDACCESSQUEUE_H

#include <omnetpp.h>
#include <cstdint>
#include <deque>
#include <vector>

class ScheduledAccessQueue : public omnetpp::cSimpleModule
{
  private:
    enum class ServiceMode { TYPE1, TYPE2 };

    struct PacketMeta {
        omnetpp::simtime_t arrivalTime = SIMTIME_ZERO;
        bool measured = false;
    };

    omnetpp::cMessage *arrivalEvent = nullptr;
    omnetpp::cMessage *serviceCompletionEvent = nullptr;

    std::deque<PacketMeta> waitingQueue;
    PacketMeta currentPacket;
    bool hasCurrentPacket = false;
    ServiceMode serviceMode = ServiceMode::TYPE2;

    int D = 0;
    int r = 0;
    int effectiveL = 0;
    int servedSinceType2 = 0;
    int rngIndex = 0;
    bool recordVectors = false;
    bool recordTailStatistics = false;

    omnetpp::simtime_t frameDuration;
    omnetpp::simtime_t meanType1ServiceTime;
    omnetpp::simtime_t type2ServiceTime;
    double rho = 0.0;
    double lambdaPerMs = 0.0;
    double lambdaSatPerMs = 0.0;
    double rhoSat = 0.0;

    std::int64_t warmupCompletedPackets = 0;
    std::int64_t targetCompletedPackets = 0;
    std::int64_t totalType1Completions = 0;

    bool collecting = false;
    omnetpp::simtime_t collectionStart;
    omnetpp::simtime_t lastAreaUpdate;
    double systemSizeAreaSeconds = 0.0;
    double type1ServiceAreaSeconds = 0.0;
    double type2ServiceAreaSeconds = 0.0;
    double fullType1AreaSeconds = 0.0;
    double fullType2AreaSeconds = 0.0;
    double nonFullAreaSeconds = 0.0;
    std::vector<double> fullType1PhaseAreaSeconds;

    std::int64_t measuredArrivals = 0;
    std::int64_t measuredBlockedArrivals = 0;
    std::int64_t measuredAcceptedArrivals = 0;
    std::int64_t measuredCompletedPackets = 0;
    double measuredDelaySumSeconds = 0.0;
    std::vector<double> measuredDelaySamplesMs;

    omnetpp::cOutVector queueLengthVector;
    omnetpp::cOutVector systemSizeVector;
    omnetpp::cOutVector sojournTimeVectorMs;

  protected:
    virtual void initialize() override;
    virtual void handleMessage(omnetpp::cMessage *msg) override;
    virtual void finish() override;

  private:
    void handleArrival();
    void handleServiceCompletion();
    void startType1Service();
    void startType2Service();
    void scheduleNextArrival();
    void beginCollection();
    void updateSystemSizeArea();
    void recordStateVectors();
    long currentType1SystemSize() const;
    omnetpp::simtime_t drawType1ServiceTime();
    omnetpp::simtime_t drawInterarrivalTime();
    static double empiricalQuantile(std::vector<double> values, double p);

  public:
    ScheduledAccessQueue() = default;
    virtual ~ScheduledAccessQueue();
};

#endif
