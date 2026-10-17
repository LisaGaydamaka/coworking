# Random access (ВКР, раздел 3.1)

Independent **OMNeT++ 6.x** C++/NED model of the random-access DECT-2020 scenario; no INET dependency. Located under the existing DECT-2020 project, without changing the scheduled-access components.

## Files

- `src/RandomAccess.cc` — event-driven PT/FT/root logic, exponential backoff, LBT, collisions, ACK retries, per-cluster delay and peak AoI.
- `src/RandomAccess.ned` — the single OMNeT++ network module.
- `omnetpp.ini` — reproducing the parameter sweeps for thesis figures 3.1a, 3.1b, 3.2, 3.3.
- `plot.py` — figures from OMNeT++ scalar outputs.
- `run.sh` — complete Docker-based build and run entry point; `.run` — CI trigger.

## Run

In this folder, using Docker:

```bash
bash run.sh
```

The file `.run` selects `smoke` (quick sanity run) or `full` (all four figure grids). In GitHub Actions, to run again, **modify only this component's `.run` file**. Figures go into `figures/Fig31a.png`, `Fig31b.png`, `Fig32.png`, `Fig33.png` and OMNeT++ scalars into `results/`.

## Model conventions

All internal times are integer DECT symbols (represented as OMNeT++ seconds purely for convenient tick scheduling). Every PT periodically generates a packet at t=0,d,2d,...; packets are FIFO. The contention window starts at Cmin, doubles on unsuccessful LBT or ACK and is capped by Cmax. Backoff is Uniform{0,...,C} multiplied by 2 symbols. LBT lasts 2 symbols; DATA 10 symbols; processing 10 symbols; ACK 5 symbols. Packet transmissions and ACKs sharing a cluster channel collide. An FT forwards packets toward the root, and pauses its outbound backoff while receiving.

Recorded scalars are `delay_0`, `paoi_0`, `delivered_0`; for a two-cluster network the `_1` metrics record packets originating in the far cluster. Delay = root processing completion minus generation. Peak AoI for two successive **delivered** updates of the same source = current delivery time minus previous update generation time.

**Model limitations:** This is a compact independent implementation, not a line-by-line transcription. OMNeT++ uses a different pseudorandom-number stream than Python and small event-ordering differences may change numeric results. The reference Python includes additional arrival modes (`qnempty`, `arrprob`) and analytical utilities that are not implemented. Only the periodic-generation configurations underlying figures 3.1–3.3 are covered. A numerical regression against the thesis values is still required before claiming exact reproduction. The current figure grids may take considerable execution time.
