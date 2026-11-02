#include <omnetpp.h>
#include <set>
#include <map>

#include "DectPacket_m.h"
#include "DectTypes.h"

using namespace omnetpp;


class FT : public cSimpleModule
{
  private:
    simtime_t procTime = SIMTIME_ZERO;
    simtime_t ackTime = SIMTIME_ZERO;
    bool isBusy = false;

    DectPacket *processingPacket = nullptr;
    cMessage *busyReleaseTimer = nullptr;

    // Python RootDevice.receive_start() reserves the FT immediately at DATA_START.
    // A failed DATA still occupies the receiver until its processing interval ends.
    struct RxState {
        bool acceptedAtStart = false;
        bool alreadyCollidedAtStart = false;
    };
    std::map<uint64_t, RxState> activeReceives;
    std::set<uint64_t> deliveredPacketKeys;
    cMessage *failedProcessingTimer = nullptr;

    cStdDev endToEndDelayStats;

    long receivedAttempts = 0;
    long droppedByCollision = 0;
    long droppedWhileBusy = 0;
    long rejectedAtStartWhileBusy = 0;
    long pythonEquivalentDataCollisions = 0;
    long deliveredPackets = 0;

  protected:
    void initialize() override;
    void handleMessage(cMessage *msg) override;
    void finish() override;

  private:
    void startProcessing(DectPacket *packet);
    void completeProcessing(DectPacket *packet);
};

Define_Module(FT);

void FT::initialize()
{
    procTime = par("procTime").doubleValueInUnit("s");
    ackTime = par("ackTime").doubleValueInUnit("s");
}

void FT::handleMessage(cMessage *msg)
{
    // ---- Служебные таймеры ----
    if (msg->isSelfMessage()) {
        if (msg == busyReleaseTimer) {
            busyReleaseTimer = nullptr;
            isBusy = false;
            delete msg;
            return;
        }
        if (msg == processingPacket) {
            processingPacket = nullptr;
            completeProcessing(check_and_cast<DectPacket *>(msg));
            return;
        }
        if (msg == failedProcessingTimer) {
            failedProcessingTimer = nullptr;
            isBusy = false;
            delete msg;
            return;
        }
        delete msg;
        return;
    }

    // ---- DectPacket от Medium ----
    DectPacket *packet = check_and_cast<DectPacket *>(msg);
    const uint64_t key = dectPacketKey(packet->getSrcId(), packet->getPktId());

    if (packet->getType() == MSG_DATA_START) {
        // Python reserves the receiver when DATA starts, not at the end of reception.
        // Even a collided accepted DATA will keep the FT busy for DATA + PROC.
        const bool accepted = !isBusy;
        activeReceives[key] = {accepted, packet->getCollided()};
        if (accepted)
            isBusy = true;
        else
            ++rejectedAtStartWhileBusy;
        delete packet;
        return;
    }

    if (packet->getType() == MSG_DATA_END) {
        ++receivedAttempts;
        const auto found = activeReceives.find(key);
        if (found == activeReceives.end())
            throw cRuntimeError("DATA_END without DATA_START for PT[%d] packet %d",
                                packet->getSrcId(), packet->getPktId());
        const RxState rx = found->second;
        activeReceives.erase(found);

        // Equivalent to Python Operation.check(): a DATA is counted only if
        // overlap changed its state from successful to failed. In Python the
        // receiver-busy refusal may have already made the DATA unsuccessful.
        //
        // Case 1: FT was free at DATA_START -> any overlap is a collision.
        // Case 2: FT was busy, but DATA already overlapped another radio signal
        //         at its START -> Operation.check() ran before FT rejection.
        // Case 3: FT was busy, initially no overlap, and another radio signal
        //         started later -> NOT counted by Python's transition counter.
        if (packet->getCollided() &&
            (rx.acceptedAtStart || rx.alreadyCollidedAtStart))
            ++pythonEquivalentDataCollisions;

        if (packet->getCollided()) {
            ++droppedByCollision;  // Raw radio overlaps, preserved separately.
            EV_WARN << "DATA PT[" << packet->getSrcId() << "] radio overlap.\n";
            delete packet;
            if (rx.acceptedAtStart) {
                // Python RootDevice.receive_end() always schedules PROC, even
                // for a reception that was corrupted during transmission.
                if (failedProcessingTimer != nullptr)
                    throw cRuntimeError("Concurrent processing after collided DATA");
                failedProcessingTimer = new cMessage("failedProcEnd");
                scheduleAt(simTime() + procTime, failedProcessingTimer);
            }
            return;
        }

        if (!rx.acceptedAtStart) {
            ++droppedWhileBusy;
            EV_WARN << "DATA PT[" << packet->getSrcId() << "] FT was busy.\n";
            delete packet;
            return;
        }

        startProcessing(packet);
        return;
    }

    delete packet;
}

void FT::startProcessing(DectPacket *packet)
{
    isBusy = true;
    packet->setType(MSG_PROCESS_END);
    processingPacket = packet;
    scheduleAt(simTime() + procTime, processingPacket);
    EV_INFO << "Начата обработка пакета #" << packet->getPktId()<< " от PT[" << packet->getSrcId() << "] (время " << procTime << "s)\n";
}

void FT::completeProcessing(DectPacket *packet)
{
    // Статистика сквозной задержки: только по первой успешной доставке.
    const uint64_t key = dectPacketKey(packet->getSrcId(), packet->getPktId());
    if (deliveredPacketKeys.insert(key).second) {
        endToEndDelayStats.collect((simTime() - packet->getGenTime()).dbl());
        ++deliveredPackets;
    }

    // Отправляем ACK в обратном направлении через Medium.
    auto *ack = new DectPacket("ack");
    ack->setType(MSG_ACK);
    ack->setSrcId(packet->getSrcId());
    ack->setDstId(packet->getSrcId());
    ack->setPktId(packet->getPktId());
    ack->setAttempt(packet->getAttempt());
    ack->setGenTime(packet->getGenTime());
    ack->setCollided(false);
    send(ack, "out");
    EV_INFO << "Обработка пакета #" << packet->getPktId()<< " завершена. Отправка ACK в PT[" << packet->getSrcId() << "]\n";
    delete packet;

    // FT остаётся занятым на время передачи ACK — как в модели на Python.
    busyReleaseTimer = new cMessage("busyReleaseTimer");
    scheduleAt(simTime() + ackTime, busyReleaseTimer);
}

void FT::finish()
{
    if (processingPacket != nullptr) cancelAndDelete(processingPacket);
    if (busyReleaseTimer != nullptr) cancelAndDelete(busyReleaseTimer);
    if (failedProcessingTimer != nullptr) cancelAndDelete(failedProcessingTimer);

    recordScalar("receivedDataAttempts",     receivedAttempts);
    recordScalar("droppedByCollision",       droppedByCollision);
    recordScalar("droppedWhileFTBusy",       droppedWhileBusy);
    recordScalar("rejectedAtStartWhileBusy", rejectedAtStartWhileBusy);
    recordScalar("pythonEquivalentDataCollisions", pythonEquivalentDataCollisions);
    recordScalar("pythonEquivalentCollisionProbabilityCompleted",
        receivedAttempts > 0
            ? static_cast<double>(pythonEquivalentDataCollisions) / receivedAttempts
            : 0.0);
    recordScalar("deliveredUniquePackets",   deliveredPackets);
    if (endToEndDelayStats.getCount() > 0) {
        recordScalar("meanEndToEndDelay", endToEndDelayStats.getMean());
        recordScalar("minEndToEndDelay",  endToEndDelayStats.getMin());
        recordScalar("maxEndToEndDelay",  endToEndDelayStats.getMax());
    }
    recordScalar("packetDeliveryRate",
                 simTime() > SIMTIME_ZERO ? deliveredPackets / simTime().dbl() : 0.0);
}
