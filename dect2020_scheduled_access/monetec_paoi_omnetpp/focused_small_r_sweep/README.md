# Focused small-buffer PAoI sweep

This is an isolated MONETEC follow-up experiment requested on 2026-09-30.

## Coordination

Do not modify the canonical simulator in `../../dect2020_scheduled_access_omnetpp/` from this component.
The canonical simulator is copied into temporary scratch space during CI and used as-is.
This folder owns only its own trigger, runner, analysis script, logs, tables, and plot.

The paper is not edited by this experiment.

## Grid

- `D = 10`
- `r = {1, 4, 7, 10, 13, 16}`
- `rho = 0.005, 0.010, ..., 0.300`
- 3 independent repetitions per point
- 5,000 warm-up type-1 completions
- 30,000 measured type-1 completions per repetition

The x-axis is the paper's offered-load parameter `rho = lambda*m_B`. No normalization by saturation load is introduced.

## PAoI

Per run:
```
PAoI = mean_sojourn_time + 1 / successful_departure_throughput
```
with throughput measured in successful packets/ms.

Outputs:
- `focused_paoi_plot.svg`
- `focused_paoi_data.csv`
- `focused_paoi_runs.csv`
- `summary.txt`
- `scalars.csv`
- `run.log`
- `SIMULATOR_SOURCE_COMMIT.txt`
- `status.txt`
