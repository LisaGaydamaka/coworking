# DECT-2020 random access — Python / OMNeT++ metrics comparison

## Final protocol parity finding — 2026-11-02

**Exactly identical paired statistics have been demonstrated in the shared-randomness regression:** 9 `arrprob` values × 10 common `paritySeed` values = **90 pairs of simulations** (180 executions). We compared **9 exact integer counters per pair** — 810 comparisons — and obtained **0 mismatches in 0 runs**. The [full CI run succeeded](https://github.com/LisaGaydamaka/coworking/actions/runs/41517590704). See:

- `omnet_new/shared_rng_grid_report.json`: authoritative machine-checkable summary (`runs=90`, `total_metric_checks=810`, `mismatched_checks=0`).
- `omnet_new/shared_rng_grid_comparison.csv`: all 810 pairs and their exact integer differences.
- `omnet_new/shared_rng_grid/run_*.sca`: all 90 OMNeT++ raw scalar outputs.
- `shared_rng_grid.py`: repeated-run Python comparison using the same counter-based pseudo-random schedule.
- `omnet_new/shared_rng_replay.json`: one detailed run with exact first 20 DATA start times for each PT (both languages identical).
- `4_random_access_shared_rng.py`: source with opt-in shared PRNG matching opt-in `PT.cc` C++ `parityHash` implementation.
- `regression_ack_lbt.py`: deterministic demonstration of the original Python ACK/LBT bug.
- `4_random_access_protocol_corrected.py`: Python protocol-fixed version, retaining the separate `4_random_access_final.py` for reference.

**Root causes of prior apparent disagreement:**

1. The default PRNGs **do not deliver the same arrival events/backoff draws**, even when their numeric seeds match. Example at `arrprob=.05`, seed 1, 3000 symbols: the independent-stream runs generated 285 Python packets versus 307 OMNeT++ packets. A per-run value-to-value comparison of those traces is therefore not an algorithm parity test.
2. OMNeT++ originally had `ackTimeout = 10 + 10 + 5 + 1 = 26` symbol times, versus Python's 25. It now uses 25, and the PT timeout self-message has lower precedence than a simultaneous ACK arrival.
3. Original Python `RootDevice.proc_end()` creates an ACK, but its `main()` rechecks the *dummy root cluster* instead of active PT LBT windows. Therefore LBT [10,12) was incorrectly successful when ACK [11,16) started at 11. The separate protocol-corrected Python version explicitly invalidates overlapping LBT windows on ACK creation (also for intermediate `DeviceFT`). Ordinary OMNeT++ `Medium.markListenWindowsBusy()` already handles this correctly.

**Evidence under fully shared randomness:** At `arrprob=.05`, shared seed 1: both produced 296 packets (PT counts 161/135), 138 DATA attempts, 88 busy LBT out of 226, 65 uniquely delivered packets, 64 acknowledged packets, and 40 radio-collided DATA attempts. All seven agree exactly. The 90-case grid additionally checks separately generated packets on each PT, DATA attempts, LBT total and busy, unique delivery, ACKed packets and radio collisions for a total of nine counts per case.

**Interpretation:** Both models agree exactly for the tested configurations **once they are given identical random events and the two protocol differences are corrected**. The roughly 3–5% MAPE from plots produced using *independent* random streams is Monte Carlo sample mismatch, not evidence of a protocol discrepancy in these tested configurations. The parity proof does not establish identical behavior for arbitrary topologies, other numerologies, multihop paths or arbitrary parameter choices; test those separately.

---

Independent comparison component. **Do not modify** the separate `dect2020_random_access_omnetpp/` student starter or the scheduled-access simulator.

## Contents

- `4_random_access_final.py` — corrected Python source from the supplied `DECT-2020.rar`. `sim_delay()` measures time from generation to **first** delivery (multiple receipts count once).
- `inputs/DECT-2020.rar` — original uploaded archive; includes 90 archived pre-fix OMNeT++ `.sca` outputs, original comparison code and data.
- `raw_metrics.csv` — 180 individual observations (90 newly re-run Python + 90 NEW OMNeT++ after receiver-state fix); includes underlying counters.
- `summary_metrics.csv` — per-parameter means and standard deviations over 10 runs.
- `plot_metrics.py` — four requested metrics plus a separate `collision_diagnostics.png` comparing physical radio overlap with first-failure-only statistics.
- `run.sh` / `.run` — repository-compliant entrypoint; compiles corrected OMNeT++, runs all 90 cases, re-runs Python and regenerates plots.
- `omnet_new/results/` — 90 new OMNeT++ `.sca` files generated from the current sibling `dect2020_ra_ira_omnetpp/src` sources.

## Scenario

`arrprob = 0.01,0.02,...,0.09`, independent generation per PT per symbol; `seed = 1..10` (different frameworks use different PRNGs); 2 PT devices, one cluster, duration 3000 symbols; `c_min=1`, `c_max=16`; transmission 10 symbols, processing 10, ACK 5, LBT 2. All model outputs are measured at the end of each finite-horizon run. Original comparison used archived OMNeT++ scalar files. The updated comparison compiles the current sibling OMNeT++ source and performs **90 new runs**. Both models are run again at the same settings, though Python and OMNeT++ have different RNG streams.

## Metric definitions

| Metric | Python numerator/denominator | OMNeT++ source |
| --- | --- | --- |
| **Physical collision** | All DATA operations overlapping another DATA **or ACK**, even when previously rejected at FT, divided by started DATA attempts | `Cluster.medium.collidedDataAttempts / dataTransmissionAttempts` |
| LBT busy | `(Cluster.LBTall - Cluster.LBTsucc) / Cluster.LBTall` | `medium.busyLbtResponses / (busyLbtResponses + dataTransmissionAttempts)` |
| Attempts per delivered packet | `Cluster.all / delivered_num(cluster)` | `medium.dataTransmissionAttempts / ft.deliveredUniquePackets` |
| Delivery intensity | `delivered_num(cluster) / 3000` | `ft.deliveredUniquePackets / 3000` (matches recorded `packetDeliveryRate`) |

## Verified Python DATA/ACK collision accounting defect (2026-11-02)

**Diagnosis.** The original Python script had no separate physical-collision counter. The first comparison instrumented only `Operation.check()` for DATA operations and registered radio overlaps whenever an active `Trans` encountered another transmission. That observer **under-counts physical DATA/ACK overlaps** because ACK creation is done by `RootDevice.proc_end()`. During the root's `AAA_proc_end` event, `main()` adds `event.subject.cluster` to `clusters_to_check`, but `RootDevice` was constructed with **the dummy `Cluster(-1)`** while PT operations belong to `clusters[0]`. Thus the active DATA operations are **not rechecked automatically** when ACK starts. The new ACK's own `Operation.check()` *is* called immediately by `DevicePT.wait_end()`, and it sees the active DATA operations; therefore the observer can count every DATA/ACK overlap at the moment of ACK creation even if the DATA itself never gets rechecked.

**Correction.** `compare_metrics.py` now adds an **observation-only** hook for an ACK's `Operation.check()`: when ACK starts, count every still-transmitting DATA operation whose time interval overlaps the ACK. Physical interval overlap uses strict bounds `a.start_time < b.end_time and b.start_time < a.end_time`. `Operation.check()` and the simulator's outcomes are unchanged. A DATA attempt is counted only once per category. The original check-only measurement remains traceable via `unobserved_by_original_data_check`; `first_failure_collision` is a separate diagnostic and `error_rate()=(all-succ)/all` is the *DATA failure* rate, not the physical collision probability.

**New verified results** ([GitHub Actions run: 90 Python + 90 OMNeT++ simulations](https://github.com/LisaGaydamaka/coworking/actions/runs/41513102790)):

| `arrprob=0.05`, 2 PT, 3000 symbols | Python | OMNeT++ |
| --- | ---: | ---: |
| Physical DATA collision (DATA/DATA or DATA/ACK) | **0.33109** | **0.32630** |
| DATA/DATA overlap probability | 0.05568 | 0.05784 |
| DATA/ACK overlap probability | 0.27542 | 0.26846 |
| DATA first transitions to unsuccessful | 0.10344 | 0.07758 |
| Fraction invisible to the former Python DATA-only observer | **0.09584** | n/a |

The former Python 'physical collision' result `0.23526` was missing `0.09584` of DATA attempts (approximately 9.58 percentage points), exactly explaining the corrected value `0.33109`.

**Overall physical-collision error (9 parameter values, mean over 10 runs each):** **MAPE 4.29%**; mean absolute probability error **0.01453** (1.45 percentage points), compared with the former apparent MAPE 36.44% based on the incomplete Python observer. For the DATA/ACK component alone, MAPE is 3.80%. The gap is not exactly zero because the models use different random streams and can differ in event ordering and dynamics; this investigation does **not** establish that timing order caused the former nine-point gap. The Python radio-overlap observer now has the same physical definition as `medium.collidedDataAttempts`.

**Important:** The protocol behavior in `4_random_access_final.py` was **not changed** by this accounting repair. The existing OMNeT++ FT busy-timing patch and the separate raw radio-overlap counters remain in place. If a change is desired to the Python *protocol-state updates* on ACK start, validate it independently; it is not needed to fix the metric.


The attempts-per-delivered ratio includes transmissions initiated for undelivered packets still in the finite-horizon system. It is a **window-wide efficiency ratio**, not the exact sample mean of attempts associated only with eventually delivered packets. To compute the latter, instrument per-packet attempts in both implementations. The LBT denominator assumes every non-busy completed LBT leads to a DATA transmission, consistent with the provided aggregated OMNeT++ counters.

## Run plots

```bash
bash run.sh
```

`bash run.sh` uses Docker with OMNeT++ 6.3, compiles a copy of the current Ira source, produces new .sca files, re-runs the corrected Python simulator, and generates CSV and PNG plots. The shared GitHub Actions workflow runs this on a `.run` change. Figures appear in `figures/`; new OMNeT++ scalar files in `omnet_new/results/`.

The original comparison archive must be extracted separately if you intend to re-run the Python-to-OMNeT++ scalar parsing or create a new experiment grid. The original Python source was re-run using 10 seeds, and the comparison means are given in `summary_metrics.csv`. 
