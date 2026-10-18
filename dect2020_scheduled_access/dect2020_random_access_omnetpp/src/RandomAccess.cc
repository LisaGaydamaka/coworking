#include <omnetpp.h>
#include <deque>
#include <vector>

using namespace omnetpp;

// DRAFT ONLY. Fill in the protocol rules using the thesis and Python reference.
class RandomAccess : public cSimpleModule {
    enum class Action {
        Generate, BackoffComplete, LbtComplete, TxComplete,
        ProcessingComplete, AckComplete
    };

    struct Packet {
        int source = -1;
        int sourceCluster = -1;
        simtime_t generationTime = SIMTIME_ZERO;
        // TODO: Add the information needed for forwarding and AoI.
    };

    struct Device {
        int cluster = -1;
        bool isRelay = false;
        int contentionWindow = 0;
        std::deque<int> queue;    // Indices of packets
        // TODO: Add radio state, timers and any pending operation.
    };

    struct RadioOperation {
        int sender = -1;
        int receiver = -1;
        int packet = -1;
        simtime_t start = SIMTIME_ZERO;
        simtime_t end = SIMTIME_ZERO;
        // TODO: Add channel, operation type and outcome.
    };

    std::vector<Packet> packets;
    std::vector<Device> devices;
    std::vector<RadioOperation> operations;

    int clusters = 0;
    int devicesPerCluster = 0;
    int cwMin = 0;
    int cwMax = 0;
    int generationPeriod = 0;

    void createTopology() {
        // TODO: Construct PTs, FTs, the root and cluster relationships.
    }

    void generatePacket(int deviceId) {
        // TODO: Create a timestamped update, queue it and schedule the next one.
        (void)deviceId;
    }

    void beginBackoff(int deviceId) {
        // TODO: Schedule a backoff based on the device's contention window.
        (void)deviceId;
    }

    void completeLbt(int deviceId) {
        // TODO: Decide whether channel access succeeds or a retry is required.
        (void)deviceId;
    }

    void beginTransmission(int deviceId) {
        // TODO: Schedule data transmission and check receiver availability.
        (void)deviceId;
    }

    void updateChannelState() {
        // TODO: Detect overlapping LBT, data and ACK operations.
    }

    void completeReception(int packetId, int receiverId) {
        // TODO: Process a received packet and forward or deliver it.
        (void)packetId;
        (void)receiverId;
    }

    void completeAck(int deviceId, bool acknowledged) {
        // TODO: Remove an acknowledged packet or arrange retransmission.
        (void)deviceId;
        (void)acknowledged;
    }

    void recordDelivery(int packetId) {
        // TODO: Update end-to-end delay and peak AoI statistics.
        (void)packetId;
    }

protected:
    void initialize() override {
        clusters = par("clusters");
        devicesPerCluster = par("devices");
        cwMin = par("cwMin");
        cwMax = par("cwMax");
        generationPeriod = par("period");
        // TODO: Validate inputs, call createTopology(), schedule first events.
    }

    void handleMessage(cMessage *message) override {
        // TODO: Decode events and call the appropriate methods above.
        // Decide how to order events that occur at the same simulation time.
        delete message;
    }

    void finish() override {
        // TODO: recordScalar(...) for average delay, PAoI and delivery count.
    }
};

Define_Module(RandomAccess);
