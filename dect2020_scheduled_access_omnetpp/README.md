# DECT-2020 NR scheduled-access simulator for OMNeT++

This directory contains an independent discrete-event implementation of the canonical scheduled-access queueing model used in the DECT-2020 NR manuscript. It is intentionally implemented in C++/NED rather than by translating the analytical transition matrix, so it can be used as an independent validation model.

## Model implemented

Type-1 requests arrive according to a Poisson process. The waiting buffer has capacity `r`. Type-1 service times are exponentially distributed with mean `m_B`. Type-2 service has duration `m_F` and is non-preemptive. A type-2 service starts after a service completion when either the type-1 waiting queue is empty or `L` type-1 requests have been completed since the previous type-2 completion. If type-2 service completes while no type-1 request is waiting, another type-2 service starts immediately.

The implementation preserves the capacity convention used by the paper: during type-1 service there can be one type-1 request in service plus `r` waiting requests, while during type-2 service at most `r` type-1 requests wait.

With `deriveDectParametersFromD=true`, the simulator derives

- `m_F = T_frame - T_frame/D`,
- `L = floor((T_frame/D)/m_B)`, with a lower bound of 1.

With `deriveLambdaFromRho=true`, it uses `rho = lambda*m_B` to obtain the Poisson arrival rate.

## Recorded validation metrics

At the end of each run the module records scalars for:

- direct mean type-1 sojourn time;
- blocking probability;
- mean number of type-1 requests in the system;
- effective throughput from departures;
- accepted-arrival throughput;
- Little-law delay `E[N]/lambda_eff`;
- relative difference between direct and Little-law delay;
- effective `L`, `rho_sat`, and `lambda_sat`.

Warm-up is controlled by `warmupCompletedPackets`. Packets arriving before the end of warm-up are not used in the direct delay statistic. Measurement stops after `targetCompletedPackets` measured type-1 completions.

## OMNeT++ version and dependencies

The project uses only the OMNeT++ simulation kernel; INET is not required. The source is written for the OMNeT++ 6.x API and standard `opp_makemake` workflow.

## Build

After entering an OMNeT++ shell/environment:

```bash
bash build.sh
```

This runs `opp_makemake -f --deep` in `src/` and then `make`.

## Run the Phase-2 validation grid

```bash
bash run_phase2_grid.sh
```

The `omnetpp.ini` file contains three configurations (`Phase2_D6`, `Phase2_D10`, and `Phase2_D20`). Together they cover:

- `D = 6, 10, 20`;
- `r = 5, 20, 50`;
- load at `0.5`, `1.0`, and `1.5` times the corresponding saturation threshold;
- 10 independent repetitions per parameter point.

Each run uses 200,000 completed type-1 packets for warm-up and then collects 1,000,000 measured type-1 completions.

## Export scalar results

```bash
bash export_results.sh
```

This uses `opp_scavetool` to create `simulations/exported/phase2_scalars.csv` from OMNeT++ scalar files.

## Tail-latency data

The `TailExample` configuration enables vector output for packet sojourn times. It is separate from the Phase-2 grid because vector recording substantially increases result-file size. It can later be used for P95/P99/P99.9 analysis.

## Important distinction from the old Python simulator

This OMNeT++ implementation follows the frozen canonical model from the mathematical audit. It is not a line-by-line port of the original `sim.py`, whose transition logic was one of the reasons for re-validating the model.

## Current verification status

The project has been compiled and executed successfully in GitHub Actions with the official `ghcr.io/omnetpp/omnetpp:u24.04-6.3.0` image.

Verified run:

- GitHub Actions run #36;
- build completed successfully;
- Baseline: 10 independent repetitions completed;
- full Phase-2 grid: 270 runs completed (90 runs for each of `D=6`, `D=10`, and `D=20`);
- each Phase-2 run uses 200,000 completed type-1 packets for warm-up and 1,000,000 measured type-1 completions;
- compact scalar outputs are committed under `ci_results/baseline_metrics.csv` and `ci_results/phase2_metrics.csv`.

During CI verification, the DECT-derived `L` calculation was corrected to use the unquantized NED parameter values before converting them to `SimTime`. This prevents an integer ratio such as `D=6 -> L=4` from being rounded down because of simulation-time quantization.
