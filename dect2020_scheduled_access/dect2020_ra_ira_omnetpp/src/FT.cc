#include <omnetpp.h>
#include <set>

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

    std::set<uint64_t> activeReceives;   // ключи передач, стартовавших и не закончившихся
    std::set<uint64_t> deniedWhileBusy;  // ключи, для которых FT был занят на MSG_DATA_START
    std::set<uint64_t> deliveredPacketKeys;

    cStdDev endToEndDelayStats;

    long receivedAttempts = 0;
    long droppedByCollision = 0;
    long droppedWhileBusy = 0;
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
        delete msg;
        return;
    }

    // ---- DectPacket от Medium ----
    DectPacket *packet = check_and_cast<DectPacket *>(msg);
    const uint64_t key = dectPacketKey(packet->getSrcId(), packet->getPktId());

    if (packet->getType() == MSG_DATA_START) {
        // Начало передачи. Запоминаем, что она идёт; если FT уже занят
        // (обрабатывает предыдущий пакет или передаёт ACK), помечаем
        // «отказано с самого начала» — пакет потом будет отброшен.
        activeReceives.insert(key);
        if (isBusy)
            deniedWhileBusy.insert(key);
        delete packet;
        return;
    }

    if (packet->getType() == MSG_DATA_END) {
        // Конец передачи. Проверяем, можно ли было её принять.
        ++receivedAttempts;
        activeReceives.erase(key);

        // Коллизия — сразу отбрасываем.
        if (packet->getCollided()) {
            ++droppedByCollision;
            deniedWhileBusy.erase(key);
            EV_WARN << "Пакет от PT[" << packet->getSrcId() << "] отброшен из-за КОЛЛИЗИИ.\n";
            delete packet;
            return;
        }

        // FT не мог принять передачу с самого её начала.
        if (isBusy || deniedWhileBusy.erase(key) > 0) {
            ++droppedWhileBusy;
            EV_WARN << "Пакет от PT[" << packet->getSrcId() << "] отброшен: FT был занят.\n";
            delete packet;
            return;
        }

        // Успех: начинаем обработку.
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
    delete packet;
    EV_INFO << "Обработка пакета #" << packet->getPktId()<< " завершена. Отправка ACK в PT[" << packet->getSrcId() << "]\n";

    // FT остаётся занятым на время передачи ACK — как в модели на Python.
    busyReleaseTimer = new cMessage("busyReleaseTimer");
    scheduleAt(simTime() + ackTime, busyReleaseTimer);
}

void FT::finish()
{
    if (processingPacket != nullptr) cancelAndDelete(processingPacket);
    if (busyReleaseTimer != nullptr) cancelAndDelete(busyReleaseTimer);

    recordScalar("receivedDataAttempts",     receivedAttempts);
    recordScalar("droppedByCollision",       droppedByCollision);
    recordScalar("droppedWhileFTBusy",       droppedWhileBusy);
    recordScalar("deliveredUniquePackets",   deliveredPackets);
    if (endToEndDelayStats.getCount() > 0) {
        recordScalar("meanEndToEndDelay", endToEndDelayStats.getMean());
        recordScalar("minEndToEndDelay",  endToEndDelayStats.getMin());
        recordScalar("maxEndToEndDelay",  endToEndDelayStats.getMax());
    }
    recordScalar("packetDeliveryRate",
                 simTime() > SIMTIME_ZERO ? deliveredPackets / simTime().dbl() : 0.0);
}
