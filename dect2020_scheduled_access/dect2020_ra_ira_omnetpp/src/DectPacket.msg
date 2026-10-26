
packet DectPacket
{
    int     type        = 0;
    int     srcId       = -1;   // исходное устройство (для статистики)
    int     dstId       = -1;   // кому адресовано
    int     pktId       = -1;   // уникальный id пакета у источника
    int     attempt     = 0;    // номер попытки (1, 2, ...)
    simtime_t genTime;          // время генерации пакета у PT
    bool    collided    = false;
    bool    channelBusy = false;
}