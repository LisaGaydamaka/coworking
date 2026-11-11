#include "FixedSlotQueue.h"
#include <algorithm>
#include <cmath>
#include <limits>

using namespace omnetpp;
Define_Module(FixedSlotQueue);

FixedSlotQueue::~FixedSlotQueue() {
    if (arrivalEvent) cancelAndDelete(arrivalEvent);
    if (slotEvent) cancelAndDelete(slotEvent);
    if (completionEvent) cancelAndDelete(completionEvent);
}

void FixedSlotQueue::initialize() {
    D = par("D").intValue();
    r = par("r").intValue();
    totalSlots = par("totalSlots").intValue();
    availableSlots = par("availableSlots").intValue();
    rngIndex = par("rngIndex").intValue();
    batchSize = par("trafficBatchSize").intValue();
    slotLayout = par("slotLayout").stdstringValue();
    trafficModel = par("trafficModel").stdstringValue();
    recordTail = par("recordTailStatistics").boolValue();
    frameSeconds = par("frameDuration").doubleValueInUnit("s");
    const double meanBms = par("meanType1ServiceTime").doubleValueInUnit("s") * 1000.0;
    if (D < 1 || r < 1 || totalSlots < 1 || availableSlots > totalSlots ||
        availableSlots < D || frameSeconds <= 0.0 || batchSize < 1)
        throw cRuntimeError("Infeasible frame, devices, buffer or batch configuration");
    if (slotLayout != "contiguous" && slotLayout != "distributed")
        throw cRuntimeError("slotLayout must be contiguous or distributed");
    if (trafficModel != "poisson" && trafficModel != "periodic" &&
        trafficModel != "synchronized" && trafficModel != "bursty")
        throw cRuntimeError("Unknown trafficModel: %s", trafficModel.c_str());

    slotSeconds = frameSeconds / totalSlots;
    L = availableSlots / D; // floor; no artificial L>=1 if insufficient slots
    const int offset = totalSlots - availableSlots; // reserved FT slots occupy frame prefix
    for (int j = 0; j < L; ++j) {
        const int idx = (slotLayout == "contiguous") ? (offset+j)
                        : (offset + (j*availableSlots)/L);
        if (idx < 0 || idx >= totalSlots)
            throw cRuntimeError("Assigned slot index out of range");
        assignedSlots.push_back(idx);
    }
    if (std::adjacent_find(assignedSlots.begin(), assignedSlots.end()) != assignedSlots.end())
        throw cRuntimeError("Duplicate slot allocation");

    lambdaSatPerMs = L / (frameSeconds * 1000.0);
    if (par("deriveLambdaFromRho").boolValue()) {
        rho = par("rho").doubleValue();
        lambdaPerMs = rho / meanBms;
    } else {
        lambdaPerMs = par("lambdaPerMs").doubleValue();
        rho = lambdaPerMs * meanBms;
    }
    if (lambdaPerMs <= 0.0)
        throw cRuntimeError("lambdaPerMs must be positive");

    warmupCompletions = par("warmupCompletedPackets").intValue();
    targetCompletions = par("targetCompletedPackets").intValue();
    if (warmupCompletions < 0 || targetCompletions < 1)
        throw cRuntimeError("Invalid warm-up/target completion counts");

    arrivalEvent = new cMessage("arrival");
    slotEvent = new cMessage("assignedSlotStart");
    completionEvent = new cMessage("slotCompletion");
    // At a shared timestamp, finish the previous slot before the next slot starts,
    // and process exact-boundary arrivals after the slot begins.
    completionEvent->setSchedulingPriority(-1);
    slotEvent->setSchedulingPriority(0);
    arrivalEvent->setSchedulingPriority(1);

    if (warmupCompletions == 0) beginCollection();
    nextArrival(true);
    nextSlot();
}

void FixedSlotQueue::handleMessage(cMessage *msg) {
    updateArea();
    if (msg == arrivalEvent) processArrival();
    else if (msg == slotEvent) processSlot();
    else if (msg == completionEvent) processCompletion();
    else throw cRuntimeError("Unrecognized event in FixedSlotQueue");
}

void FixedSlotQueue::nextArrival(bool first) {
    const double lambdaPerS = 1000.0 * lambdaPerMs;
    double delta = 0.0;
    if (trafficModel == "poisson") {
        delta = exponential(1.0 / lambdaPerS, rngIndex);
    } else if (trafficModel == "bursty") {
        delta = exponential(batchSize / lambdaPerS, rngIndex);
    } else if (trafficModel == "synchronized") {
        delta = first ? 0.0 : (batchSize / lambdaPerS);
    } else { // periodic with a randomized initial phase
        delta = first ? uniform(0.0, 1.0/lambdaPerS, rngIndex) : 1.0/lambdaPerS;
    }
    scheduleAt(simTime() + SimTime(delta), arrivalEvent);
}

void FixedSlotQueue::nextSlot() {
    if (nextSlotIndex == assignedSlots.size()) {
        nextSlotIndex = 0;
        ++frameIndex;
    }
    const int slot = assignedSlots[nextSlotIndex++];
    const double absoluteSeconds = frameIndex * frameSeconds + slot * slotSeconds;
    const simtime_t t = SimTime(absoluteSeconds);
    if (t < simTime())
        throw cRuntimeError("Fixed-slot clock moved backwards");
    scheduleAt(t, slotEvent);
}

void FixedSlotQueue::processArrival() {
    int arrivalsInEvent = 1;
    if (trafficModel == "synchronized") {
        arrivalsInEvent = batchSize;
    } else if (trafficModel == "bursty") {
        // Geometric size (mean=batchSize), compound-Poisson event rate=lambda/batchSize.
        const double u = uniform(0.0, 1.0, rngIndex);
        arrivalsInEvent = 1 + static_cast<int>(
            std::floor(std::log(std::max(1e-15, 1.0-u)) /
                       std::log(1.0 - 1.0/batchSize)));
    }
    for (int j = 0; j < arrivalsInEvent; ++j) {
        if (collecting) ++measuredArrivals;
        if (static_cast<int>(waiting.size()) >= r) {
            if (collecting) ++measuredBlocked;
        } else {
            waiting.push_back({simTime(), collecting});
            if (collecting) ++measuredAccepted;
        }
    }
    nextArrival();
}

void FixedSlotQueue::processSlot() {
    if (collecting) ++totalSlotOpportunities;
    if (inService)
        throw cRuntimeError("Service still active at next assigned slot");
    if (!waiting.empty()) {
        current = waiting.front();
        waiting.pop_front();
        inService = true;
        if (collecting) ++usedSlots;
        // Exactly one packet per assigned slot, independent of arrivals in the slot.
        // Frame clock remains fixed when slots are unused.
        // Use the same absolute frame/slot boundary computation for starts
        // and completions. Adding separately quantized slot durations would
        // otherwise introduce a 1-tick overlap after consecutive slots.
        const int activeSlot = assignedSlots[nextSlotIndex-1];
        const double completionAbsoluteSeconds =
            frameIndex * frameSeconds + (activeSlot+1) * slotSeconds;
        scheduleAt(SimTime(completionAbsoluteSeconds), completionEvent);
    }
    nextSlot();
}

void FixedSlotQueue::processCompletion() {
    if (!inService) throw cRuntimeError("Spurious slot completion");
    inService = false;
    ++totalCompletions;
    if (current.measured) {
        const double delay = (simTime()-current.arrival).dbl() * 1000.0;
        delaySum += delay;
        ++measuredCompletions;
        if (recordTail) delaysMs.push_back(delay);
    }
    if (!collecting && totalCompletions >= warmupCompletions)
        beginCollection();
    if (collecting && measuredCompletions >= targetCompletions)
        endSimulation();
}

void FixedSlotQueue::beginCollection() {
    collecting = true;
    collectionStart = simTime();
    lastAreaTime = simTime();
    systemSizeArea = delaySum = 0.0;
    measuredArrivals = measuredAccepted = measuredBlocked = measuredCompletions = 0;
    usedSlots = totalSlotOpportunities = 0;
    delaysMs.clear();
    if (recordTail) delaysMs.reserve(static_cast<std::size_t>(targetCompletions));
}

void FixedSlotQueue::updateArea() {
    if (!collecting) return;
    const double dt = (simTime()-lastAreaTime).dbl();
    if (dt < 0.0) throw cRuntimeError("Negative time advance");
    systemSizeArea += (waiting.size() + (inService ? 1 : 0)) * dt;
    lastAreaTime = simTime();
}

double FixedSlotQueue::quantile(const std::vector<double>& x, double p) {
    if (x.empty()) return std::numeric_limits<double>::quiet_NaN();
    const double index = p*(x.size()-1);
    const std::size_t lo = static_cast<std::size_t>(std::floor(index));
    const std::size_t hi = static_cast<std::size_t>(std::ceil(index));
    return x[lo] + (index-lo)*(x[hi]-x[lo]);
}

void FixedSlotQueue::finish() {
    updateArea();
    const double obs = collecting ? (simTime()-collectionStart).dbl() : 0.0;
    const double N = obs>0.0 ? systemSizeArea/obs : 0.0;
    const double throughput = obs>0.0 ? measuredCompletions/(obs*1000.0) : 0.0;
    const double blocking = measuredArrivals>0.0
        ? static_cast<double>(measuredBlocked)/measuredArrivals : 0.0;
    const double delay = measuredCompletions>0
        ? delaySum/measuredCompletions : 0.0;
    recordScalar("D",D); recordScalar("r",r); recordScalar("L_effective",L);
    recordScalar("total_slots",totalSlots);
    recordScalar("available_slots",availableSlots);
    recordScalar("slot_layout_code",slotLayout=="contiguous" ? 0 : 1);
    recordScalar("traffic_model_code",trafficModel=="poisson" ? 0 :
        trafficModel=="periodic" ? 1 : trafficModel=="synchronized" ? 2 : 3);
    recordScalar("traffic_batch_size",batchSize);
    recordScalar("frame_ms",frameSeconds*1000.0);
    recordScalar("rho",rho);
    recordScalar("rho_sat",lambdaSatPerMs*(frameSeconds*1000.0/totalSlots));
    recordScalar("lambda_per_ms",lambdaPerMs);
    recordScalar("lambda_sat_per_ms",lambdaSatPerMs);
    recordScalar("load_factor_rho_over_rho_sat",lambdaPerMs/lambdaSatPerMs);
    recordScalar("warmup_type1_completions",static_cast<double>(warmupCompletions));
    recordScalar("measured_arrivals",static_cast<double>(measuredArrivals));
    recordScalar("measured_accepted_arrivals",static_cast<double>(measuredAccepted));
    recordScalar("measured_blocked_arrivals",static_cast<double>(measuredBlocked));
    recordScalar("measured_completed_packets",static_cast<double>(measuredCompletions));
    recordScalar("observation_time_s",obs);
    recordScalar("blocking_probability",blocking);
    recordScalar("mean_type1_number",N);
    recordScalar("mean_delay_direct_ms",delay);
    recordScalar("mean_delay_little_ms",throughput>0.0 ? N/throughput : 0.0);
    recordScalar("effective_throughput_departures_per_ms",throughput);
    recordScalar("effective_throughput_accepted_per_ms",
        obs>0.0 ? measuredAccepted/(obs*1000.0) : 0.0);
    recordScalar("slot_utilization",totalSlotOpportunities>0
        ? static_cast<double>(usedSlots)/totalSlotOpportunities : 0.0);
    if (recordTail) {
        std::sort(delaysMs.begin(),delaysMs.end());
        recordScalar("delay_p95_ms",quantile(delaysMs,0.95));
        recordScalar("delay_p99_ms",quantile(delaysMs,0.99));
        recordScalar("delay_p999_ms",quantile(delaysMs,0.999));
        recordScalar("tail_sample_count",static_cast<double>(delaysMs.size()));
    }
}
