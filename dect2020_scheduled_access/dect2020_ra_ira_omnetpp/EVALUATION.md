# DECT-2020 RA: assessment of Ira's prototype (2026-10-26)

## Reproducible run

GitHub Actions run: [successful OMNeT++ 6.3 smoke test](https://github.com/LisaGaydamaka/coworking/actions/runs/40361757670).

Configuration: one cluster, `2 PT -> Medium -> 1 FT`, 3000 simulated symbols,
Bernoulli arrival probability `0.01` per symbol and PT, `cMin=1`, `cMax=16`,
`lbtTime=2`, `transTime=10`, `procTime=10`, `ackTime=5`, seed set 1.
The original model represents one symbol with one OMNeT++ second.

| Observed metric | Value |
| --- | ---: |
| Generated packets (PT0 + PT1) | 66 |
| Confirmed packets at PT (PT0 + PT1) | 57 |
| Distinct packets delivered to FT | 57 |
| PT packets still queued at end | 9 |
| DATA transmission attempts | 130 |
| Collided DATA attempts | 39 (30% of attempts) |
| Busy LBT responses | 70 |
| Mean delay to processing completion at FT | 433.456 symbols |
| Minimum / maximum such delay | 22 / 1020 symbols |

The 57/66 ratio is a **finite-horizon delivery fraction**, not an independently
validated reliability estimate. Mean delay is averaged over uniquely delivered
packets, using generation time and FT processing completion (without ACK time).
All raw scalar results and an event-log excerpt are in `results/`.

## Problems found in the supplied source

1. In `Medium.cc`, `destination` was printed before its declaration. This
   prevents C++ compilation. The runnable copy moves the declaration above
   its first use.
2. In `FT.cc`, packet fields were accessed in an `EV_INFO` statement **after
   `delete packet`**, causing a segmentation fault on the first successful
   delivery. The runnable copy moves the deletion below the statement.

The unchanged files are in `original/`; these two safety fixes are present only
in `src/`. The initial build/run failures and the successful retry remain
visible in the GitHub Actions history.

## How complete is it?

This is a functioning **single-cluster prototype**, not yet the random-access
simulator required to reproduce all thesis figures.

| Feature | Assessment |
| --- | --- |
| Bernoulli packet generation, FIFO queue | Present |
| Random backoff and LBT | Present |
| Overlap/collision detection | Present |
| ACK, timeout, contention-window growth, retry | Present |
| Network topology | Partial: one cluster only |
| Metrics | Partial: mean end-to-end delay and counters, but no peak AoI |
| FT relay/multihop forwarding | Absent |
| Python equivalence and thesis sweeps/plots | Not validated/absent |

The status labels describe source-code coverage and a smoke run; they do **not**
certify that event ordering and protocol constants match the Python reference.
The next useful step is to run a handful of deterministic one-PT/two-PT cases,
compare event traces and scalar definitions with the cleaned Python model,
then add FT forwarding and peak AoI before recreating Figures 3.1a/b, 3.2, 3.3.
