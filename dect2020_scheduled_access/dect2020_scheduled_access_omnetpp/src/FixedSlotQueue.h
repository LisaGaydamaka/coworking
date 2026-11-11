#ifndef DECT_FIXED_SLOT_QUEUE_H
#define DECT_FIXED_SLOT_QUEUE_H

#include <omnetpp.h>
#include <cstdint>
#include <deque>
#include <string>
#include <vector>

class FixedSlotQueue : public omnetpp::cSimpleModule {
  private:
    struct Packet {
        omnetpp::simtime_t arrival = SIMTIME_ZERO;
        bool measured = false;
    };
    omnetpp::cMessage *arrivalEvent = nullptr;
    omnetpp::cMessage *slotEvent = nullptr;
    omnetpp::cMessage *completionEvent = nullptr;
    std::deque<Packet> waiting;
    Packet current;
    bool inService = false;
    int D = 10, r = 30, L = 2, availableSlots = 24, totalSlots = 24;
    int rngIndex = 0, batchSize = 4;
    std::string slotLayout, trafficModel;
    std::vector<int> assignedSlots;
    std::size_t nextSlotIndex = 0;
    std::int64_t frameIndex = 0;
    double frameSeconds = 0.01, slotSeconds = 0.01/24.0;
    double lambdaPerMs = 0.2, rho = 0.0, lambdaSatPerMs = 0.2;
    std::int64_t warmupCompletions = 0, targetCompletions = 0;
    std::int64_t totalCompletions = 0, measuredCompletions = 0;
    std::int64_t measuredArrivals = 0, measuredAccepted = 0, measuredBlocked = 0;
    std::int64_t usedSlots = 0, totalSlotOpportunities = 0;
    bool collecting = false, recordTail = false;
    omnetpp::simtime_t collectionStart, lastAreaTime;
    double systemSizeArea = 0.0, delaySum = 0.0;
    std::vector<double> delaysMs;
  protected:
    void initialize() override;
    void handleMessage(omnetpp::cMessage *msg) override;
    void finish() override;
  private:
    void nextArrival(bool first = false);
    void nextSlot();
    void processArrival();
    void processSlot();
    void processCompletion();
    void beginCollection();
    void updateArea();
    static double quantile(const std::vector<double>& sorted, double p);
  public:
    ~FixedSlotQueue() override;
};
#endif
