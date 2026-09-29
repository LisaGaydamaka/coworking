# MONETEC PAoI plot reproduction (isolated OMNeT++ experiment)

## Coordination / ownership

This directory was added for the MONETEC conference-paper plot reproduction requested on 2026-09-29.

**Do not modify the canonical simulator in**
`../dect2020_scheduled_access_omnetpp/`
**for this experiment.** This component only reads that simulator and copies its source/configuration into a temporary local scratch directory during CI. It never writes into the canonical simulator folder.

This isolation is intentional because another agent is maintaining the canonical OMNeT++ implementation. Future agents should treat this directory as a self-contained experiment and the sibling `dect2020_scheduled_access_omnetpp/` directory as the authoritative simulator.

## Purpose

Recreate the MONETEC paper's PAoI-vs-load sweep using the independently validated OMNeT++ simulator rather than the legacy/incorrect simulator that produced the paper's current numerical curve.

The experiment uses the same plotting grid as the paper:

- `D = 10`;
- buffer capacities `r = 5, 10, 20, 30, 40, 50`;
- `rho = 0.01, 0.093, ..., 2.583` (step 0.083);
- 3 independent repetitions per point;
- 5,000 completed type-1 packets for warm-up;
- 20,000 measured type-1 completions per repetition.

The canonical OMNeT++ implementation is used **as-is**. In particular, its current model uses exponential type-1 service with mean `m_B` and deterministic type-2 service.

## PAoI calculation

The simulator already records direct mean type-1 sojourn time and successful-departure throughput. For FIFO service with no replacement, where blocked arrivals are excluded from the delivered-packet sequence, packet-average peak AoI is evaluated per run as

```
PAoI = mean_sojourn_time + 1 / successful_departure_throughput
```

where throughput is measured in successful packets per millisecond.

This corresponds to averaging the generation-time gap between consecutive successfully delivered packets plus the current packet's sojourn time. The result is then averaged over repetitions for each `(r, rho)` point.

## Files

- `run.sh` — CI entry point; copies the canonical simulator into temporary scratch space, builds it, runs the sweep, exports scalars, and deletes scratch space.
- `analyze.py` — aggregates OMNeT++ scalars and creates the CSV/SVG outputs.
- `.run` — trigger for the repository's shared GitHub Actions runner.
- `paper_plot_data.csv` — generated aggregated data.
- `paper_plot.svg` — generated replacement plot.
- `scalars.csv` — generated raw scalar export for audit/recalculation.
- `run.log` — generated OMNeT++ log.
- `SIMULATOR_SOURCE_COMMIT.txt` — exact repository commit used by the run.
- `status.txt` — run status.

If the canonical simulator changes later, rerun this component by updating only this directory's `.run` trigger. Do not copy changes back into the canonical simulator unless the user explicitly requests that work.
