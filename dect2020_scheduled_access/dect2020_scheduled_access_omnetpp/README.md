# DECT-2020 NR scheduled-access simulator for OMNeT++

This directory contains the OMNeT++ discrete-event implementation of the canonical scheduled-access queueing model used in the DECT-2020 NR manuscript. It is implemented in C++/NED and is the simulation source used for all manuscript validation results.

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
- 10 separate repetitions per parameter point.

Each run uses 200,000 completed type-1 packets for warm-up and then collects 1,000,000 measured type-1 completions.

## Export scalar results

```bash
bash export_results.sh
```

This uses `opp_scavetool` to create `simulations/exported/phase2_scalars.csv` from OMNeT++ scalar files.

## Tail-latency data

The final Phase-5 configuration `Phase5_Tail` computes empirical P50, P95, P99, and P99.9 directly inside the OMNeT++ C++ model from measured admitted-packet sojourn times. The publication grid uses 10 repetitions per load point, 200,000 warm-up type-1 completions, and 1,000,000 measured completions per repetition. Vector output is disabled for this grid because only the percentile scalars are required for the manuscript figure.

## Current verification status

The project has been compiled and executed successfully in GitHub Actions with the official `ghcr.io/omnetpp/omnetpp:u24.04-6.3.0` image.

Verified run:

- GitHub Actions run #36;
- build completed successfully;
- Baseline: 10 separate repetitions completed;
- full Phase-2 grid: 270 runs completed (90 runs for each of `D=6`, `D=10`, and `D=20`);
- each Phase-2 run uses 200,000 completed type-1 packets for warm-up and 1,000,000 measured type-1 completions;
- compact scalar outputs are committed under `ci_results/baseline_metrics.csv` and `ci_results/phase2_metrics.csv`.

During CI verification, the DECT-derived `L` calculation was corrected to use the unquantized NED parameter values before converting them to `SimTime`. This prevents an integer ratio such as `D=6 -> L=4` from being rounded down because of simulation-time quantization.


## Phase 3 high-load audit

The high-load theorem and Corollary 1 were separately checked in OMNeT++ in GitHub Actions run #38.

Audit grid:

- (D = 6,10,20);
- (r = 5,30,50);
- (ho/ho_{sat} = 5,10,20,50);
- 3 repetitions per point;
- 20,000 warm-up type-1 completions;
- 50,000 measured type-1 completions.

At normalized load 50, the mean/max absolute relative errors against the analytical high-load limits were 0.171%/0.413% for mean delay and 0.176%/0.429% for mean type-1 population. Mean/max throughput-limit errors were 0.063%/0.116%.

The complete audit and reproducible files are in:

- `PHASE3_HIGHLOAD_AUDIT.md`;
- `ci_results/phase3_highload_metrics.csv`;
- `ci_results/phase3_highload_scalars.csv`;
- `run_phase3_highload.sh`.



## Phase 5 tail-latency audit

The final tail-latency experiment was completed in GitHub Actions run #77 and the publication figure/summary pipeline in run #78. The audit report is in `PHASE5_TAIL_LATENCY_AUDIT.md`, with source scalars in `ci_results/phase5_metrics.csv` and the publication figure generated from those OMNeT++ results.


## Phase 6 service-time variability

The Phase-6 robustness grid uses the same mean type-1 service time, 10/24 ms, with three service-time families:

- deterministic (SCV=0);
- exponential (SCV=1);
- balanced two-phase hyperexponential (SCV=4).

The representative configuration is D=10, L=2, r=30 with normalized loads 0.8, 1.0, and 1.2. Each distribution/load point uses 10 repetitions, 200,000 warm-up type-1 completions, and 1,000,000 measured admitted completions. The C++ model records mean delay, blocking, P95, P99, and P99.9.

GitHub Actions run #81 completed the 90-run OMNeT++ grid successfully. At normalized load 1.2, the P99 values were approximately 147.72 ms (deterministic), 150.49 ms (exponential), and 156.14 ms (hyperexponential SCV=4), while mean delay and blocking remained close across the three cases. Figure E is generated from these OMNeT++ scalars by the analysis component.
