# Implementation roadmap (no solutions)

## Goal and scope

Construct a discrete-event model of the **random-access** DECT-2020 network described in the graduation thesis. Your model should support the topology and experiments needed for the thesis's random-access delay and peak age-of-information plots. This task is not to invent a new MAC protocol: extract precise rules, constants, and arrival assumptions from the thesis and the Python reference.

## Recommended architecture

A compact implementation may use **one OMNeT++ `cSimpleModule`** with in-memory PT and FT device states. The supplied C++ file follows that layout, but it contains only types and unimplemented method stubs.

Keep these concepts separate:

- **Packet:** generation timestamp, source identity, source cluster, progression toward the root.
- **Device:** PT/FT role, FIFO waiting queue, contention window, active action and receiving/transmitting state.
- **Radio operation:** transmitter/receiver, time interval, channel, operation kind (LBT, data or ACK), success/failure.
- **Scheduled event:** timestamp, event kind, associated packet and device.
- **Cluster/channel:** which operations overlap and which receiver can listen.

You may use OMNeT++ self-messages for each event, or a local time-ordered event container driven by one self-message. Document the event-ordering policy, especially for simultaneous starts and completions.

## Mechanics to implement

1. **Topology:** one-cluster route to the root; optional two-cluster chain with an intermediate FT. Specify which devices share each radio channel.
2. **Traffic:** generate packets according to the selected arrival mode; record their actual generation times and enqueue them in the correct PT.
3. **Channel acquisition:** model contention/backoff, listen-before-talk (LBT), and the channel-busy outcome.
4. **Transmission:** model the data-transmission interval, receiver availability, overlapping transmissions and collisions.
5. **Acknowledgements:** model processing and the outcome of ACK transmission, including missing or collided ACKs.
6. **Retries:** define how the contention window changes after a failure and resets after a confirmed success; check the original rules.
7. **Forwarding:** FT reception, buffering and transmission toward the next hop; ensure its half-duplex behavior is consistent with the reference.
8. **Statistics:** record root delivery time, end-to-end delay, age-of-information samples, delivery counts and any additional quantities required by the thesis.
9. **Experiments:** create the parameter sweeps for the relevant thesis figures, run multiple seeds if needed, and produce labelled plots.

The order above describes **responsibilities**, not a complete protocol state machine. Derive the actual transitions, overlap rules, and numerical durations from the reference material.

## Suggested decomposition in C++

The function names in `RandomAccess.cc` are placeholders:

- `createTopology()`, `generatePacket()`, `beginBackoff()`, `completeLbt()`;
- `beginTransmission()`, `completeReception()`, `completeAck()`;
- `updateChannelState()`, `recordDelivery()`.

Connect them through `initialize()` and `handleMessage()` after choosing your event representation.

## Self-checks before comparing graphs

- One device and one packet: no unintended collisions.
- Two devices choosing overlapping transmission intervals: verify collision behavior.
- Failed LBT and failed ACK: ensure packets are not silently removed.
- Successful ACK: verify that the correct queue entry leaves and its window resets.
- Relay topology: packets from the far cluster traverse the intermediate FT once.
- Boundary events: confirm deterministic handling when operations have the same timestamp.
- Confirm that statistics use the same start/end instants and averaging definitions as the thesis.

## Deliverables

A working OMNeT++ model, a reproducible run command, documented parameters and assumptions, scalar results, the requested curves, and a short comparison with the Python/thesis baseline. Explain all deviations rather than tuning parameters solely to match a graph.
