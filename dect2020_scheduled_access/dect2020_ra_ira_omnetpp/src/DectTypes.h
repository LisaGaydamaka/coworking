#ifndef DECT_TYPES_H
#define DECT_TYPES_H

#include <cstdint>

// Тип сообщения DectPacket. Служебные таймеры — это cMessage.
enum DectMessageType {
    MSG_LBT_REQUEST = 1,
    MSG_LBT_RESPONSE = 2,
    MSG_DATA = 3,
    MSG_DATA_START = 4,
    MSG_DATA_END = 5,
    MSG_ACK = 6,
    MSG_ACK_END = 7,
    MSG_PROCESS_END = 8
};

// Ключ (srcId, pktId), уникальный для логического пакета,
// даже если он передаётся несколько раз (retry).
inline uint64_t dectPacketKey(int srcId, int pktId)
{
    return (static_cast<uint64_t>(static_cast<uint32_t>(srcId)) << 32)
           | static_cast<uint32_t>(pktId);
}

#endif
