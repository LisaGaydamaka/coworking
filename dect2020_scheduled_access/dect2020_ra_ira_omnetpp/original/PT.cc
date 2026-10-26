#include <omnetpp.h>
#include <algorithm>
#include <deque>

#include "DectPacket_m.h"
#include "DectTypes.h"

using namespace omnetpp;


class PT : public cSimpleModule
{
  private:
    int id = -1;
    int cMin = 1;
    int cMax = 16;
    int currentCW = 1;         // текущее значение C_i
    double arrProb = 0.01;
    simtime_t lbtTime = SIMTIME_ZERO;
    simtime_t ackTimeout = SIMTIME_ZERO;

    std::deque<DectPacket *> queue;   // пакеты, ожидающие отправки
    cMessage *arrivalTimer = nullptr;
    cMessage *backoffTimer = nullptr;
    cMessage *ackTimer = nullptr;
    bool waitingForAck = false;

    // статистика
    long generatedPackets = 0;
    long dataAttempts = 0;
    long busyLbtResponses = 0;
    long acknowledgedPackets = 0;
    long retransmissions = 0;

  protected:
    void initialize() override;
    void handleMessage(cMessage *msg) override;
    void finish() override;

  private:
    void generatePacket();
    void startBackoff();
    void sendLbtRequest();
    void transmitCurrentPacket();
    void handleAck(DectPacket *ack);
    void handleAckTimeout();
    void increaseCW();
};

Define_Module(PT);

void PT::initialize()
{
    id = par("id").intValue();
    arrProb = par("arrProb").doubleValue();
    cMin = par("cMin").intValue();
    cMax = par("cMax").intValue();
    lbtTime = par("lbtTime").doubleValueInUnit("s");
    ackTimeout = par("ackTimeout").doubleValueInUnit("s");

    if (arrProb < 0.0 || arrProb > 1.0)
        throw cRuntimeError("arrProb must be in [0,1], got %g", arrProb);
    if (cMin < 1 || cMax < cMin)
        throw cRuntimeError("Require 1 <= cMin <= cMax");

    currentCW = cMin;

    //первая проверка - в момент t=0
    arrivalTimer = new cMessage("arrivalTimer");
    scheduleAt(SIMTIME_ZERO, arrivalTimer);
}

void PT::handleMessage(cMessage *msg)
{
    //таймеры
    if (msg->isSelfMessage()) {
        if (msg == arrivalTimer) {
            if (uniform(0, 1) < arrProb)
                generatePacket();
            scheduleAt(simTime() + 1.0, arrivalTimer); // 1 символ
            return;
        }
        if (msg == backoffTimer) {
            backoffTimer = nullptr;
            delete msg;
            sendLbtRequest();
            return;
        }
        if (msg == ackTimer) {
            ackTimer = nullptr;
            delete msg;
            handleAckTimeout();
            return;
        }
        delete msg;
        return;
    }

    //входящее сообщение от Medium
    DectPacket *packet = check_and_cast<DectPacket *>(msg);

    if (packet->getType() == MSG_LBT_RESPONSE) {
        if (packet->getChannelBusy()) {
            ++busyLbtResponses;
            EV_INFO << "LBT не пройден: канал ЗАНЯТ. Удваиваем CW.\n";
            increaseCW();
            if (!queue.empty() && !waitingForAck)
                startBackoff();
        }
        else if (!queue.empty() && !waitingForAck) {
            EV_INFO << "LBT пройден: канал СВОБОДЕН. Начинаем передачу.\n";
            transmitCurrentPacket();
        }
        delete packet;
        return;
    }

    if (packet->getType() == MSG_ACK_END) {
        handleAck(packet);
        delete packet;
        return;
    }

    delete packet;
}

void PT::generatePacket()
{
    auto *packet = new DectPacket("data");
    packet->setType(MSG_DATA);
    packet->setSrcId(id);
    packet->setPktId(static_cast<int>(generatedPackets));
    packet->setAttempt(0);
    packet->setGenTime(simTime());
    packet->setCollided(false);
    queue.push_back(packet);
    ++generatedPackets;
    EV_INFO << "Сгенерирован новый пакет #" << packet->getPktId() << ". Размер очереди: " << queue.size() << "\n";

    if (queue.size() == 1 && !waitingForAck && backoffTimer == nullptr)
        startBackoff();
}

void PT::startBackoff()
{
    if (queue.empty() || waitingForAck || backoffTimer != nullptr)
        return;

    // C_i = currentCW. Отсрочка x = U[0, C_i] * lbtTime.
    const int slots = intuniform(0, currentCW);
    backoffTimer = new cMessage("backoffTimer");
    scheduleAt(simTime() + slots * lbtTime, backoffTimer);
    EV_INFO << "Разыгрывается отсрочка (Backoff): CW = " << currentCW
            << ", выбрано слотов: " << slots
            << ", время ожидания: " << (slots * lbtTime) << "s\n";
}

void PT::sendLbtRequest()
{
    if (queue.empty() || waitingForAck)
        return;

    auto *request = new DectPacket("lbtRequest");
    request->setType(MSG_LBT_REQUEST);
    request->setSrcId(id);
    EV_INFO << "Отправка LBT-запроса (прослушивание канала на " << lbtTime << "s)\n";
    send(request, "out");
}

void PT::transmitCurrentPacket()
{
    if (queue.empty() || waitingForAck)
        return;

    DectPacket *packet = queue.front();
    packet->setAttempt(packet->getAttempt() + 1);
    packet->setCollided(false);

    auto *copy = packet->dup();
    copy->setType(MSG_DATA);
    ++dataAttempts;
    send(copy, "out");

    EV_INFO << "Начата передача пакета #" << packet->getPktId()<< " (попытка " << packet->getAttempt() << ")\n";

    waitingForAck = true;
    ackTimer = new cMessage("ackTimer");
    scheduleAt(simTime() + ackTimeout, ackTimer);
}

void PT::handleAck(DectPacket *ack)
{
    // отбрасываем «чужие», устаревшие и коллидированные ACK
    if (ack->getDstId() != id || ack->getCollided() || queue.empty() || !waitingForAck)
        return;

    DectPacket *current = queue.front();
    if (ack->getPktId() != current->getPktId()
        || ack->getSrcId() != id
        || ack->getAttempt() != current->getAttempt())
        return;
    EV_INFO << "Получен ACK для пакета #" << ack->getPktId() << ". Успех! CW сброшен до " << cMin << "\n";
    waitingForAck = false;
    if (ackTimer != nullptr) {
        cancelAndDelete(ackTimer);
        ackTimer = nullptr;
    }

    retransmissions += std::max(0, current->getAttempt() - 1);
    ++acknowledgedPackets;
    delete queue.front();
    queue.pop_front();

    //успешная передача - CW сбрасывается
    currentCW = cMin;

    if (!queue.empty())
        startBackoff();
}

void PT::handleAckTimeout()
{
    if (!waitingForAck)
        return;// ACK уже пришёл, таймер просто «просрочен»
    waitingForAck = false;

    if (queue.empty())
        return;//на всякий случай

    // Неуспех: увеличиваем CW и снова backoff
    EV_WARN << "ТАЙМАУТ ACK для пакета #" << queue.front()->getPktId()<< ". ACK не пришел, удваиваем CW и повторяем.\n";
    increaseCW();
    startBackoff();
}

void PT::increaseCW()
{
    currentCW = std::min(cMax, std::max(cMin, 2 * currentCW));
}

void PT::finish()
{
    cancelAndDelete(arrivalTimer);
    if (backoffTimer != nullptr) cancelAndDelete(backoffTimer);
    if (ackTimer != nullptr)     cancelAndDelete(ackTimer);

    recordScalar("generatedPackets",        generatedPackets);
    recordScalar("dataTransmissionAttempts", dataAttempts);
    recordScalar("busyLbtResponses",         busyLbtResponses);
    recordScalar("acknowledgedPackets",      acknowledgedPackets);
    recordScalar("dataRetransmissions",      retransmissions);
    recordScalar("queueLengthAtEnd",         static_cast<double>(queue.size()));

    for (auto *p : queue) delete p;
    queue.clear();
}
