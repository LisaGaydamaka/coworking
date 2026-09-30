# Focused PAoI sweep: r = {1, 3, 7, 12, 16, 20}

This is a second isolated MONETEC follow-up experiment. The previous focused sweep is preserved unchanged.

## Coordination

Do not modify the canonical simulator in `../../dect2020_scheduled_access_omnetpp/` from this component.
The canonical OMNeT++ simulator is copied into temporary scratch space and used as-is.
This folder owns only its own runner, trigger, analysis files, logs, tables, and plot.

The MONETEC paper is not edited by this experiment.

## Grid

- `D = 10`
- `r = {1, 3, 7, 12, 16, 20}`
- `rho = 0.005, 0.010, ..., 0.300`
- 3 independent repetitions per point
- 5,000 warm-up type-1 completions
- 30,000 measured type-1 completions per repetition

The x-axis remains the paper's offered-load parameter `rho = lambda*m_B`; no normalized load is introduced.

## PAoI

Per run:
```
PAoI = mean_sojourn_time + 1 / successful_departure_throughput
```

Outputs are local to this directory and do not overwrite the earlier focused sweep.
