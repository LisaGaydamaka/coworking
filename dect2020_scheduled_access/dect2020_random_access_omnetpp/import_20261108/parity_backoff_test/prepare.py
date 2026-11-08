"""Prepare an INSTRUMENTED COPY of the uploaded OMNeT++ model.
The repository's original RandomAccessModel.cc and default intuniform RNG are not changed.
"""
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "dect-ra"
BUILD = HERE / "build"
BUILD.mkdir(exist_ok=True)

def replace_one(s, old, new, label):
    matches = s.count(old)
    if matches != 1:
        raise RuntimeError(f"Needle {label}: expected 1 occurrence, got {matches}")
    return s.replace(old, new, 1)

code = (SRC / "RandomAccessModel.cc").read_text()
code = replace_one(code, "#include <omnetpp.h>",
"""#include <omnetpp.h>
#include <cstdint>
#include <cmath>
#include <fstream>
""", "includes")
code = replace_one(code, "class RandomAccessModel : public cSimpleModule",
"""// Counter-indexed diagnostic backoff generator; byte-for-byte same arithmetic in Python.
// This function exists only in the isolated testing build.
static uint32_t parityHash(int kind, int ptId, uint32_t index, int seed) {
    uint32_t x = uint32_t(seed) * 0x9e3779b9u
               + uint32_t(ptId + 1) * 0x85ebca6bu
               + (index + 1u) * 0xc2b2ae35u
               + uint32_t(kind) * 0x27d4eb2fu;
    x ^= x >> 16; x *= 0x7feb352du;
    x ^= x >> 15; x *= 0x846ca68bu;
    x ^= x >> 16;
    return x;
}
class RandomAccessModel : public cSimpleModule""", "hash")
code = replace_one(code, "    std::vector<Pt> pts;",
"""    std::vector<Pt> pts;
    std::vector<uint32_t> parityBackoffCounts;
    int paritySeed = 17;
    std::ofstream parityTrace;""", "members")
code = replace_one(code, "    pts.resize(ptCount);",
"""    pts.resize(ptCount);
    paritySeed = par("paritySeed").intValue();
    parityBackoffCounts.assign(ptCount, 0);
    parityTrace.open(par("parityTraceFile").stringValue());
    if (!parityTrace.is_open()) throw cRuntimeError("Cannot open parity trace file");
    parityTrace << "kind,pt,t,a,b\\n";""", "initialize")
code = replace_one(code, "    int randomValue = intuniform(0, window);",
"""    uint32_t index = parityBackoffCounts[ptIndex]++;
    int randomValue = int(parityHash(1, ptIndex, index, paritySeed) % uint32_t(window + 1));
    parityTrace << "backoff," << ptIndex << ","
                << (pt.state == IDLE ? currentSymbol : currentSymbol + 1)
                << "," << window << "," << randomValue << "\\n";""".replace('"\\\\n"', '"\\n"'), "draw")
# add data-start trace before attempt counter
code = replace_one(code, """        if (pt.state == DATA && pt.dataRemaining == dataSymbols) {
            dataTransmissionAttempts++;""",
"""        if (pt.state == DATA && pt.dataRemaining == dataSymbols) {
            parityTrace << "data," << i << "," << currentSymbol << ","
                        << std::llround(pt.queue.front().generatedAt.dbl() / symbolTime.dbl())
                        << ",0\\n";
            dataTransmissionAttempts++;""", "DATA trace")
code = replace_one(code, """            pt.lbtRemaining--;
            if (pt.lbtRemaining == 0) {
                if (pt.lbtWasBusy) {""",
"""            pt.lbtRemaining--;
            if (pt.lbtRemaining == 0) {
                parityTrace << "lbt," << i << "," << currentSymbol + 1 << ","
                            << (pt.lbtWasBusy ? 0 : 1) << ",0\\n";
                if (pt.lbtWasBusy) {""", "LBT trace")
code = replace_one(code, """    successfulDataDeliveries++;
    if (!packet.hasDelivery)""",
"""    parityTrace << "delivery," << ftPt << "," << currentSymbol + 1 << ","
                << std::llround(packet.generatedAt.dbl() / symbolTime.dbl())
                << ",0\\n";
    successfulDataDeliveries++;
    if (!packet.hasDelivery)""", "delivery trace")
# Keep trace fully flushed at simulation finish.
code = replace_one(code, """void RandomAccessModel::finish()
{
    long queuedPackets""",
"""void RandomAccessModel::finish()
{
    parityTrace.flush();
    long queuedPackets""", "finish")
(BUILD / "RandomAccessModel.cc").write_text(code)

ned = (SRC / "DectRandomAccess.ned").read_text()
ned = replace_one(ned, "        int ptCount = default(2);",
"""        int ptCount = default(2);
        int paritySeed = default(17);
        string parityTraceFile = default("results/trace_omnet.csv");""", "NED params")
(BUILD / "DectRandomAccess.ned").write_text(ned)
print("Prepared isolated C++/NED diagnostic sources; originals untouched.")
