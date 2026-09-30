# Focused PAoI sweep with deterministic B and deterministic F

This is an isolated MONETEC follow-up experiment using the same grid as the preceding focused plot:

- `D = 10`
- `r = {1, 3, 7, 12, 16, 20}`
- `rho = 0.005, 0.010, ..., 0.300`
- 3 independent repetitions per point
- 5,000 warm-up type-1 completions
- 30,000 measured type-1 completions per repetition

## Service-time distributions

For this experiment only:

- type-1 service `B` is deterministic with duration `m_B = 0.4166666667 ms`;
- type-2 service `F` is deterministic with duration `m_F = 9 ms` for `D=10`.

Poisson type-1 arrivals are unchanged.

## Coordination / isolation

The canonical simulator in `../../dect2020_scheduled_access_omnetpp/` is **not modified**.

The runner copies the canonical source into this experiment's temporary scratch directory and changes only the scratch copy of `drawType1ServiceTime()` from exponential sampling to returning `meanType1ServiceTime` directly. Type-2 service is already deterministic in the canonical implementation. Scratch files are deleted after the run.

Future agents should not copy this deterministic-B patch back into the canonical simulator unless the user explicitly requests that change.

The MONETEC paper is not edited by this experiment.

## PAoI

Per run:
```
PAoI = mean_sojourn_time + 1 / successful_departure_throughput
```

All outputs remain local to this directory so they do not overwrite the exponential-B experiment.
