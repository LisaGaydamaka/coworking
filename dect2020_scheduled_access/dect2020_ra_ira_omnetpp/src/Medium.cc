#include <omnetpp.h>
#include <algorithm>
#include <map>
#include <vector>
#include <set>
#include <utility>
#include <cstring>

#include "DectPacket_m.h"
#include "DectTypes.h"

using namespace omnetpp;


class Medium : public cSimpleModule
{
  private:
    struct ActiveTransmission {
        DectPacket *packet;
        cMessage *endEvent;
        bool isAck;
    };

    int numPTs = 0;
    simtime_t transTime = SIMTIME_ZERO;
    simtime_t lbtTime = SIMTIME_ZERO;
    simtime_t ackTime = SIMTIME_ZERO;

    std::vector<ActiveTransmission> active;        // идущие передачи
    std::map<int, bool> lbtBusy;                   // состояние LBT по PT
    std::map<int, cMessage *> lbtEndEvents;        // таймеры окончания LBT

    simsignal_t collisionSignal;
    simsignal_t busyLbtSignal;
    long collisionEvents = 0;
    long dataTransmissionAttempts = 0;
    long collidedDataAttempts = 0;
    // Audit physical overlaps by other transmission type; a single attempt may
    // appear in both categories, but each category counts that attempt once.
    using AttemptKey = std::pair<uint64_t, int>;
    std::set<AttemptKey> dataOverlappedWithData;
    std::set<AttemptKey> dataOverlappedWithAck;
    long busyLbtResponses = 0;

  protected:
    void initialize() override;
    void handleMessage(cMessage *msg) override;
    void finish() override;

  private:
    void startLbt(DectPacket *request);
    void startTransmission(DectPacket *packet, bool isAck);
    void markListenWindowsBusy();
    void finishTransmission(cMessage *event);
};

Define_Module(Medium);

void Medium::initialize()
{
    numPTs = par("numPTs").intValue();
    transTime = par("transTime").doubleValueInUnit("s");
    lbtTime = par("lbtTime").doubleValueInUnit("s");
    ackTime = par("ackTime").doubleValueInUnit("s");

    collisionSignal = registerSignal("collisionEvent");
    busyLbtSignal = registerSignal("busyLbtResponse");
}

void Medium::handleMessage(cMessage *msg)
{
    // ---- Служебные события ----
    if (msg->isSelfMessage()) {
        if (std::strcmp(msg->getName(), "lbtEnd") == 0) {
            const int sourceId = msg->getKind();
            auto it = lbtBusy.find(sourceId);
            const bool busy = (it == lbtBusy.end()) ? true : it->second;
            if (it != lbtBusy.end()) lbtBusy.erase(it);
            lbtEndEvents.erase(sourceId);
            EV_INFO << "Завершено прослушивание (LBT) для PT[" << sourceId << "]. Результат: " << (busy ? "КАНАЛ ЗАНЯТ" : "КАНАЛ СВОБОДЕН") << "\n";
            delete msg;

            auto *response = new DectPacket("lbtResponse");
            response->setType(MSG_LBT_RESPONSE);
            response->setSrcId(-1);
            response->setDstId(sourceId);
            response->setChannelBusy(busy);
            if (busy) {
                ++busyLbtResponses;
                emit(busyLbtSignal, 1L);
            }
            if (sourceId >= 0 && sourceId < numPTs)
                send(response, "ptOut", sourceId);
            else
                delete response;
            return;
        }

        finishTransmission(msg);
        return;
    }

    // ---- Сообщения от PT/FT ----
    DectPacket *packet = check_and_cast<DectPacket *>(msg);

    if (packet->arrivedOn("ptIn")) {
        if (packet->getType() == MSG_LBT_REQUEST) {
            startLbt(packet);
            return;
        }
        if (packet->getType() == MSG_DATA) {
            ++dataTransmissionAttempts;
            startTransmission(packet, /*isAck=*/false);
            return;
        }
    }
    else if (packet->arrivedOn("ftIn")) {
        if (packet->getType() == MSG_ACK) {
            startTransmission(packet, /*isAck=*/true);
            return;
        }
    }

    delete packet;
}

void Medium::startLbt(DectPacket *request)
{
    const int sourceId = request->getSrcId();
    delete request;

    if (sourceId < 0 || sourceId >= numPTs) return;
    if (lbtBusy.find(sourceId) != lbtBusy.end()) return; // LBT уже идёт

    // Канал занят сейчас — если есть активная передача.
    lbtBusy[sourceId] = !active.empty();

    auto *end = new cMessage("lbtEnd");
    end->setKind(sourceId);
    lbtEndEvents[sourceId] = end;
    scheduleAt(simTime() + lbtTime, end);
}

void Medium::markListenWindowsBusy()
{
    // Передача началась — все активные LBT-окна её «слышат» и становятся неуспешными.
    for (auto &entry : lbtBusy)
        entry.second = true;
}

void Medium::startTransmission(DectPacket *packet, bool isAck)
{
    markListenWindowsBusy();

    // Коллизия при любом перекрытии двух радиопередач.
    if (!active.empty()) {
        // Count all actual overlapping DATA transmissions independently of
        // FT acceptance and of any earlier failure flag (radio collision).
        const auto currentKey = std::make_pair(
            dectPacketKey(packet->getSrcId(), packet->getPktId()),
            packet->getAttempt());
        for (const auto &tx : active) {
            const auto activeKey = std::make_pair(
                dectPacketKey(tx.packet->getSrcId(), tx.packet->getPktId()),
                tx.packet->getAttempt());
            if (!isAck) {
                if (tx.isAck) dataOverlappedWithAck.insert(currentKey);
                else dataOverlappedWithData.insert(currentKey);
            }
            if (!tx.isAck) {
                if (isAck) dataOverlappedWithAck.insert(activeKey);
                else dataOverlappedWithData.insert(activeKey);
            }
        }
        EV_WARN << "!!! КОЛЛИЗИЯ !!! Передача от PT[" << packet->getSrcId() << "] наложилась на другую передачу.\n";
        if (!isAck && !packet->getCollided())
            ++collidedDataAttempts;
        packet->setCollided(true);
        for (auto &tx : active) {
            if (!tx.packet->getCollided()) {
                if (!tx.isAck)
                    ++collidedDataAttempts;
                tx.packet->setCollided(true);
            }
        }
        ++collisionEvents;
        emit(collisionSignal, 1L);
    }

    // Уведомляем FT о начале передачи данных (не ACK).
    if (!isAck) {
        EV_INFO << "Начало передачи DATA от PT[" << packet->getSrcId() << "] (длительность " << transTime << "s)\n";
        auto *notice = packet->dup();
        notice->setType(MSG_DATA_START);
        send(notice, "ftOut");
    }else {
        EV_INFO << "Начало передачи ACK для PT[" << packet->getDstId() << "]\n";
    }

    auto *end = new cMessage(isAck ? "ackTxEnd" : "dataTxEnd");
    end->setContextPointer(packet);
    const simtime_t duration = isAck ? ackTime : transTime;
    active.push_back({packet, end, isAck});
    scheduleAt(simTime() + duration, end);
}

void Medium::finishTransmission(cMessage *event)
{
    DectPacket *packet = static_cast<DectPacket *>(event->getContextPointer());
    size_t foundIndex = active.size();
    for (size_t i = 0; i < active.size(); ++i) {
        if (active[i].packet == packet) {
            foundIndex = i;
            break;
        }
    }
    if (foundIndex == active.size()) {
        delete event;
        return;
    }

    const bool isAck = active[foundIndex].isAck;
    active.erase(active.begin() + foundIndex);
    delete event;

    if (isAck) {
        const int destination = packet->getDstId();
        EV_INFO << "Передача ACK завершена. Отправка в PT[" << destination << "]\n";
        packet->setType(MSG_ACK_END);
        if (destination >= 0 && destination < numPTs)
            send(packet, "ptOut", destination);
        else
            delete packet;
    }
    else {
        EV_INFO << "Передача DATA от PT[" << packet->getSrcId() << "] завершена.\n";
        packet->setType(MSG_DATA_END);
        send(packet, "ftOut");
    }
}

void Medium::finish()
{
    for (auto &tx : active) {
        cancelAndDelete(tx.endEvent);
        delete tx.packet;
    }
    active.clear();

    for (auto &entry : lbtEndEvents)
        cancelAndDelete(entry.second);
    lbtEndEvents.clear();
    lbtBusy.clear();

    recordScalar("collisionEvents",           collisionEvents);
    recordScalar("dataTransmissionAttempts",  dataTransmissionAttempts);
    recordScalar("collidedDataAttempts",      collidedDataAttempts);
    recordScalar("dataOverlappedWithData",    static_cast<long>(dataOverlappedWithData.size()));
    recordScalar("dataOverlappedWithAck",     static_cast<long>(dataOverlappedWithAck.size()));
    recordScalar("dataCollisionProbability",
                 dataTransmissionAttempts > 0
                     ? static_cast<double>(collidedDataAttempts) / dataTransmissionAttempts
                     : 0.0);
    recordScalar("busyLbtResponses",          busyLbtResponses);
}
