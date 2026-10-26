# Ira's DECT-2020 random-access OMNeT++ prototype

This is a **separate contribution**, placed alongside (not inside) the previous
`dect2020_random_access_omnetpp` starter folder.

## Preservation and layout

- `original/` contains the 10 files exactly as received in `DECT2020-RA.rar`.
- `src/` contains a runnable copy with **two minimal safety fixes**:
  `Medium.cc` now declares `destination` before using it (C++ compile error);
  `FT.cc` logs packet information before deleting the packet (use-after-free
  caused a segmentation fault on the first successful reception).
  Neither fix intentionally changes the model's protocol decisions.
- `run.sh` builds and runs the supplied one-cluster configuration in OMNeT++ 6.3.
- `summarize.py` extracts a concise metrics table and console trace into `results/`.
- `EVALUATION.md` reviews the [successful GitHub Actions run](https://github.com/LisaGaydamaka/coworking/actions/runs/40361757670),
  the two observed source bugs, numerical counters, and remaining gaps.

## Run

```bash
bash run.sh
```

Requires Docker with access to `ghcr.io/omnetpp/omnetpp:u24.04-6.3.0`.
The repository workflow runs this automatically when `.run` changes.

## Scope and important limitations

The implementation has one shared medium, two PT nodes and one FT sink.
It generates Bernoulli traffic once per simulated symbol, uses a random
backoff/LBT mechanism, models packet overlaps and ACK-based retry, and records
per-source counters plus FT mean end-to-end delay.

It **does not** implement a two-cluster/multihop route, relay forwarding, peak
age of information, or the four thesis-figure parameter sweeps. Numeric agreement
with the reference Python simulator has **not** been established.

The model's behavior is measured at the FT when processing finishes, before
ACK reception at PT. Interpret its delivery metrics accordingly.
