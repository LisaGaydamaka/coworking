#include "ScheduledAccessQueue.h"

#include <algorithm>
#include <cmath>
#include <limits>

using namespace omnetpp;

Define_Module(ScheduledAccessQueue);

ScheduledAccessQueue::~ScheduledAccessQueue()
{
    if (arrivalEvent != nullptr)
        cancelAndDelete(arrivalEvent);
    if (serviceCompletionEvent != nullptr)
        cancelAndDelete(serviceCompletionEvent);
}

void ScheduledAccessQueue::initialize()
{
    D = par("D").intValue();
    r = par("r").intValue();
    rngIndex = par("rngIndex").intValue();
    recordVectors = par("recordVectors").boolValue();

    if (D <= 0)
        throw cRuntimeError("D must be positive");
    if (r < 1)
        throw cRuntimeError("r must be at least 1");

    frameDuration = SimTime(par("frameDuration").doubleValueInUnit("s"));
    meanType1ServiceTime = SimTime(par("meanType1ServiceTime").doubleValueInUnit("s"));
    if (meanType1ServiceTime <= SIMTIME_ZERO)
        throw cRuntimeError("meanType1ServiceTime must be positive");

    if (par("deriveDectParametersFromD").boolValue()) {
        const double allocationSeconds = frameDuration.dbl() / D;
        type2ServiceTime = SimTime(frameDuration.dbl() - allocationSeconds);
        const double serviceSlotsPerAllocation = allocationSeconds / meanType1ServiceTime.dbl();
        effectiveL = static_cast<int>(std::floor(serviceSlotsPerAllocation + 1e-9));
        effectiveL = std::max(1, effectiveL);
    }
    else {
        effectiveL = par("L").intValue();
        type2ServiceTime = SimTime(par("type2ServiceTime").doubleValueInUnit("s"));
    }

    if (effectiveL <= 0)
        throw cRuntimeError("L must be positive");
    if (type2ServiceTime < SIMTIME_ZERO)
        throw cRuntimeError("type2ServiceTime cannot be negative");

    rho = par("rho").doubleValue();
    if (par("deriveLambdaFromRho").boolValue()) {
        const double meanBms = meanType1ServiceTime.dbl() * 1000.0;
        lambdaPerMs = rho / meanBms;
    }
    else {
        lambdaPerMs = par("lambdaPerMs").doubleValue();
        rho = lambdaPerMs * meanType1ServiceTime.dbl() * 1000.0;
    }

    if (lambdaPerMs <= 0.0)
        throw cRuntimeError("Arrival rate must be positive");

    const double meanBms = meanType1ServiceTime.dbl() * 1000.0;
    const double meanFms = type2ServiceTime.dbl() * 1000.0;
    lambdaSatPerMs = effectiveL / (effectiveL * meanBms + meanFms);
    rhoSat = lambdaSatPerMs * meanBms;

    warmupCompletedPackets = par("warmupCompletedPackets").intValue();
    targetCompletedPackets = par("targetCompletedPackets").intValue();
    if (warmupCompletedPackets < 0 || targetCompletedPackets <= 0)
        throw cRuntimeError("warmupCompletedPackets must be >=0 and targetCompletedPackets must be >0");

    arrivalEvent = new cMessage("type1Arrival");
    serviceCompletionEvent = new cMessage("serviceCompletion");

    queueLengthVector.setName("queueLength");
    systemSizeVector.setName("type1SystemSize");
    sojournTimeVectorMs.setName("type1SojournTime_ms");

    serviceMode = ServiceMode::TYPE2;
    servedSinceType2 = effectiveL;
    hasCurrentPacket = false;

    if (warmupCompletedPackets == 0)
        beginCollection();

    scheduleNextArrival();
    startType2Service();
    recordStateVectors();
}

void ScheduledAccessQueue::handleMessage(cMessage *msg)
{
    updateSystemSizeArea();

    if (msg == arrivalEvent)
        handleArrival();
    else if (msg == serviceCompletionEvent)
        handleServiceCompletion();
    else
        throw cRuntimeError("Unknown self-message received");

    recordStateVectors();
}

void ScheduledAccessQueue::handleArrival()
{
    if (collecting)
        measuredArrivals++;

    PacketMeta packet;
    packet.arrivalTime = simTime();
    packet.measured = collecting;

    if (static_cast<int>(waitingQueue.size()) < r) {
        waitingQueue.push_back(packet);
        if (collecting)
            measuredAcceptedArrivals++;
    }
    else if (collecting) {
        measuredBlockedArrivals++;
    }

    scheduleNextArrival();
}

void ScheduledAccessQueue::handleServiceCompletion()
{
    if (serviceMode == ServiceMode::TYPE2) {
        servedSinceType2 = 0;
        if (waitingQueue.empty())
            startType2Service();
        else
            startType1Service();
        return;
    }

    if (!hasCurrentPacket)
        throw cRuntimeError("TYPE1 completion without a packet in service");

    totalType1Completions++;

    if (currentPacket.measured) {
        const simtime_t delay = simTime() - currentPacket.arrivalTime;
        measuredDelaySumSeconds += delay.dbl();
        measuredCompletedPackets++;
        if (recordVectors)
            sojournTimeVectorMs.record(delay.dbl() * 1000.0);
    }

    hasCurrentPacket = false;
    servedSinceType2++;

    if (!collecting && totalType1Completions >= warmupCompletedPackets)
        beginCollection();

    if (collecting && measuredCompletedPackets >= targetCompletedPackets) {
        endSimulation();
        return;
    }

    if (waitingQueue.empty() || servedSinceType2 >= effectiveL)
        startType2Service();
    else
        startType1Service();
}

void ScheduledAccessQueue::startType1Service()
{
    if (waitingQueue.empty())
        throw cRuntimeError("Cannot start TYPE1 service with an empty waiting queue");

    currentPacket = waitingQueue.front();
    waitingQueue.pop_front();
    hasCurrentPacket = true;
    serviceMode = ServiceMode::TYPE1;
    scheduleAt(simTime() + drawType1ServiceTime(), serviceCompletionEvent);
}

void ScheduledAccessQueue::startType2Service()
{
    hasCurrentPacket = false;
    serviceMode = ServiceMode::TYPE2;
    scheduleAt(simTime() + type2ServiceTime, serviceCompletionEvent);
}

void ScheduledAccessQueue::scheduleNextArrival()
{
    scheduleAt(simTime() + drawInterarrivalTime(), arrivalEvent);
}

void ScheduledAccessQueue::beginCollection()
{
    collecting = true;
    collectionStart = simTime();
    lastAreaUpdate = simTime();
    systemSizeAreaSeconds = 0.0;

    measuredArrivals = 0;
    measuredBlockedArrivals = 0;
    measuredAcceptedArrivals = 0;
    measuredCompletedPackets = 0;
    measuredDelaySumSeconds = 0.0;
}

void ScheduledAccessQueue::updateSystemSizeArea()
{
    if (!collecting)
        return;

    const simtime_t dt = simTime() - lastAreaUpdate;
    systemSizeAreaSeconds += currentType1SystemSize() * dt.dbl();
    lastAreaUpdate = simTime();
}

void ScheduledAccessQueue::recordStateVectors()
{
    if (!recordVectors)
        return;

    queueLengthVector.record(static_cast<long>(waitingQueue.size()));
    systemSizeVector.record(currentType1SystemSize());
}

long ScheduledAccessQueue::currentType1SystemSize() const
{
    return static_cast<long>(waitingQueue.size()) + (serviceMode == ServiceMode::TYPE1 && hasCurrentPacket ? 1L : 0L);
}

simtime_t ScheduledAccessQueue::drawType1ServiceTime()
{
    return SimTime(exponential(meanType1ServiceTime.dbl(), rngIndex));
}

simtime_t ScheduledAccessQueue::drawInterarrivalTime()
{
    const double lambdaPerSecond = lambdaPerMs * 1000.0;
    return SimTime(exponential(1.0 / lambdaPerSecond, rngIndex));
}

void ScheduledAccessQueue::finish()
{
    updateSystemSizeArea();

    recordScalar("D", D);
    recordScalar("r", r);
    recordScalar("L_effective", effectiveL);
    recordScalar("rho", rho);
    recordScalar("lambda_per_ms", lambdaPerMs);
    recordScalar("lambda_sat_per_ms", lambdaSatPerMs);
    recordScalar("rho_sat", rhoSat);
    recordScalar("mean_type1_service_ms", meanType1ServiceTime.dbl() * 1000.0);
    recordScalar("type2_service_ms", type2ServiceTime.dbl() * 1000.0);
    recordScalar("warmup_type1_completions", static_cast<double>(warmupCompletedPackets));
    recordScalar("measured_arrivals", static_cast<double>(measuredArrivals));
    recordScalar("measured_accepted_arrivals", static_cast<double>(measuredAcceptedArrivals));
    recordScalar("measured_blocked_arrivals", static_cast<double>(measuredBlockedArrivals));
    recordScalar("measured_completed_packets", static_cast<double>(measuredCompletedPackets));

    if (!collecting)
        return;

    const double observationSeconds = (simTime() - collectionStart).dbl();
    recordScalar("observation_time_s", observationSeconds);
    if (observationSeconds <= 0.0)
        return;

    const double meanNumber = systemSizeAreaSeconds / observationSeconds;
    const double blockingProbability = measuredArrivals > 0
        ? static_cast<double>(measuredBlockedArrivals) / measuredArrivals
        : std::numeric_limits<double>::quiet_NaN();
    const double meanDelayMs = measuredCompletedPackets > 0
        ? (measuredDelaySumSeconds / measuredCompletedPackets) * 1000.0
        : std::numeric_limits<double>::quiet_NaN();
    const double throughputDeparturesPerMs = measuredCompletedPackets / observationSeconds / 1000.0;
    const double throughputAcceptedPerMs = measuredAcceptedArrivals / observationSeconds / 1000.0;
    const double littleDelayMs = throughputDeparturesPerMs > 0.0
        ? meanNumber / throughputDeparturesPerMs
        : std::numeric_limits<double>::quiet_NaN();

    recordScalar("blocking_probability", blockingProbability);
    recordScalar("mean_type1_number", meanNumber);
    recordScalar("mean_delay_direct_ms", meanDelayMs);
    recordScalar("effective_throughput_departures_per_ms", throughputDeparturesPerMs);
    recordScalar("effective_throughput_accepted_per_ms", throughputAcceptedPerMs);
    recordScalar("mean_delay_little_ms", littleDelayMs);
    recordScalar("little_vs_direct_relative_error", meanDelayMs > 0.0
        ? std::fabs(littleDelayMs / meanDelayMs - 1.0)
        : std::numeric_limits<double>::quiet_NaN());
}
