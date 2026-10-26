"""Extract a concise and reproducible smoke-test summary from OMNeT++ files."""

import collections
import pathlib
import shlex
import sys

scalar_path = pathlib.Path(sys.argv[1])
console_path = pathlib.Path(sys.argv[2])
result_dir = scalar_path.parent

scalars = collections.defaultdict(dict)
for line in scalar_path.read_text(errors="replace").splitlines():
    if line.startswith("scalar "):
        fields = shlex.split(line)
        if len(fields) >= 4:
            _, module, metric, value = fields[:4]
            scalars[module][metric] = value

ordered_keys = [
    "generatedPackets",
    "dataTransmissionAttempts",
    "busyLbtResponses",
    "acknowledgedPackets",
    "dataRetransmissions",
    "queueLengthAtEnd",
    "receivedDataAttempts",
    "droppedByCollision",
    "droppedWhileFTBusy",
    "deliveredUniquePackets",
    "meanEndToEndDelay",
    "minEndToEndDelay",
    "maxEndToEndDelay",
    "packetDeliveryRate",
    "collisionEvents",
    "collidedDataAttempts",
    "dataCollisionProbability",
]
summary = ["Ira DECT-2020 RA: one cluster, 2 PTs, 1 FT, 3000 symbols, seed=1", ""]
for module in sorted(scalars):
    interesting = [(key, scalars[module][key]) for key in ordered_keys if key in scalars[module]]
    if not interesting:
        continue
    summary.append(module)
    summary += [f"  {key}: {value}" for key, value in interesting]
    summary.append("")

if not any("deliveredUniquePackets" in values for values in scalars.values()):
    raise RuntimeError("Run produced no FT delivery metric; cannot claim functional test")

(result_dir / "summary.txt").write_text("\n".join(summary) + "\n")

console = console_path.read_text(errors="replace").splitlines()
filters = ("Сгенерирован", "КОЛЛИЗИЯ", "LBT", "ACK", "Начата передача", "Simulation time limit", "Finished")
selected = [line for line in console if any(item in line for item in filters)]
sample = selected[:34] + (["... [trace shortened]"] if len(selected) > 34 else [])
if not sample:
    sample = console[-30:]
(result_dir / "console_excerpt.txt").write_text("\n".join(sample) + "\n")
