# Phase 5 Tail-Latency Audit

Status: **PASS**

OMNeT++ simulation run: GitHub Actions #77  
Figure/summary pipeline: GitHub Actions #78

## Configuration

Representative DECT configuration:

- D = 10;
- L = 2;
- r = 30;
- mean type-1 service time = 10/24 ms;
- deterministic type-2 service time = 9 ms.

Normalized-load grid:

`rho/rho_sat = {0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.5, 2.0, 5.0}`.

Each load point uses:

- 10 repetitions with distinct seed sets;
- 200,000 completed type-1 requests for warm-up per repetition;
- 1,000,000 measured admitted type-1 completions per repetition;
- 10,000,000 measured admitted-packet delays per load point.

Empirical P50, P95, P99 and P99.9 are computed inside the OMNeT++ C++ module from the measured admitted-packet sojourn times. Vector output is disabled in the publication grid.

## Main results

| rho/rho_sat | Mean [ms] | P95 [ms] | P99 [ms] | Blocking |
|---:|---:|---:|---:|---:|
| 0.5 | 6.6721 | 14.9881 | 21.2864 | 0.000000 |
| 0.7 | 9.8067 | 24.6259 | 36.4741 | 0.000000 |
| 0.8 | 13.8337 | 36.8390 | 55.2376 | 0.000001 |
| 0.9 | 25.6977 | 72.2382 | 106.6167 | 0.000233 |
| 1.0 | 74.0718 | 139.6065 | 146.4382 | 0.016668 |
| 1.1 | 121.6356 | 146.5711 | 149.5909 | 0.090872 |
| 1.2 | 133.6747 | 147.8882 | 150.4907 | 0.166550 |
| 1.5 | 141.2957 | 149.1581 | 151.4573 | 0.333063 |
| 2.0 | 144.0236 | 149.9050 | 152.0842 | 0.499863 |
| 5.0 | 146.5930 | 150.9800 | 153.0070 | 0.799966 |

For the mean delay, Theorem 2 gives the high-load limit 147.9167 ms. At normalized load 5 the OMNeT++ mean is 146.5930 ms, approximately 0.895% below this limit.

P95 and P99 increase sharply as the load approaches saturation and then flatten in the overloaded finite-buffer regime. These percentile plateaus are simulation results; they are not claimed as direct analytical consequences of Theorem 2.

## Statistical reliability

The figure uses the mean of the 10 replication-level estimates at each load. Error bars are 95% Student-t intervals across the 10 repetitions.

Largest confidence half-width over the grid:

- P95: about 0.77 ms;
- P99: about 1.38 ms.

The source data also retain P99.9. With 1,000,000 measured completions per repetition, each run contains approximately 1,000 observations beyond the empirical P99.9 threshold.

## Reproducible artifacts

OMNeT++:

- `simulations/omnetpp.ini` config `Phase5_Tail`;
- `ci_results/phase5_metrics.csv`;
- `ci_results/phase5_scalars.csv`;
- `ci_results/phase5_tail_run.log`.

Figure pipeline:

- `../analysis/phase5_tail_latency.py`;
- `../analysis/phase5_output/phase5_tail_summary.csv`;
- `../analysis/phase5_output/figure_D_tail_latency.pdf`.

The manuscript Figure D and all reported tail-latency values are sourced from these OMNeT++ runs.
