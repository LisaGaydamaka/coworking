# DECT-2020 random access — Python / OMNeT++ metrics comparison

Independent comparison component. **Do not modify** the separate `dect2020_random_access_omnetpp/` student starter or the scheduled-access simulator.

## Contents

- `4_random_access_final.py` — corrected Python source from the supplied `DECT-2020.rar`. `sim_delay()` measures time from generation to **first** delivery (multiple receipts count once).
- `inputs/DECT-2020.rar` — original uploaded archive; includes 90 archived pre-fix OMNeT++ `.sca` outputs, original comparison code and data.
- `raw_metrics.csv` — 180 individual observations (90 newly re-run Python + 90 NEW OMNeT++ after receiver-state fix); includes underlying counters.
- `summary_metrics.csv` — per-parameter means and standard deviations over 10 runs.
- `plot_metrics.py` — plots four requested metrics, plus a diagnostic Python failed-DATA series on the collision plot.
- `run.sh` / `.run` — repository-compliant entrypoint; compiles corrected OMNeT++, runs all 90 cases, re-runs Python and regenerates plots.\n- `omnet_new/results/` — 90 new OMNeT++ `.sca` files generated from the current sibling `dect2020_ra_ira_omnetpp/src` sources.

## Scenario

`arrprob = 0.01,0.02,...,0.09`, independent generation per PT per symbol; `seed = 1..10` (different frameworks use different PRNGs); 2 PT devices, one cluster, duration 3000 symbols; `c_min=1`, `c_max=16`; transmission 10 symbols, processing 10, ACK 5, LBT 2. All model outputs are measured at the end of each finite-horizon run. Original comparison used archived OMNeT++ scalar files. The updated comparison compiles the current sibling OMNeT++ source and performs **90 new runs**. Both models are run again at the same settings, though Python and OMNeT++ have different RNG streams.

## Metric definitions

| Metric | Python numerator/denominator | OMNeT++ source |
| --- | --- | --- |
| **Physical collision** | All DATA operations overlapping another DATA **or ACK**, even when previously rejected at FT, divided by started DATA attempts | `Cluster.medium.collidedDataAttempts / dataTransmissionAttempts` |
| LBT busy | `(Cluster.LBTall - Cluster.LBTsucc) / Cluster.LBTall` | `medium.busyLbtResponses / (busyLbtResponses + dataTransmissionAttempts)` |
| Attempts per delivered packet | `Cluster.all / delivered_num(cluster)` | `medium.dataTransmissionAttempts / ft.deliveredUniquePackets` |
| Delivery intensity | `delivered_num(cluster) / 3000` | `ft.deliveredUniquePackets / 3000` (matches recorded `packetDeliveryRate`) |

**Collision probability audit (2026-11-02)**

The original Python `error_rate(cluster)` computes `(all-succ)/all`: this is the rate of failed DATA attempts (including FT-busy refusal), **not** exclusively physical collision probability.

An earlier comparison incorrectly labeled `Operation.check()` **first transition to failure** as a radio collision: that excludes DATA attempts which were already marked unsuccessful at the busy receiver before a subsequent radio overlap. The true physical collision numerator must count all DATA attempts **whose radio interval overlaps another DATA or ACK**, regardless of prior `is_successful`. It can be measured in Python by observing `cluster.transmissions` on every `Operation.check()` and counting every overlapping DATA operation once, even when `is_successful == False`; in OMNeT++ the appropriate native counter is `medium.collidedDataAttempts`, with one increment per DATA attempt. The physical collision metric is now the **primary** `collision` series in `summary_metrics.csv` and `collision.png`.

The earlier `ft.pythonEquivalentDataCollisions` is retained for diagnosis and renamed `first_failure_collision` in CSV. It is *not* the complete physical collision probability. Likewise `failed_data_fraction` remains distinct. To explain discrepancies, `medium.dataOverlappedWithData` and `medium.dataOverlappedWithAck` separately count distinct DATA attempts overlapping each transmission type; these categories may overlap, so their sum need not equal `collidedDataAttempts`. `collision_diagnostics.png` compares all definitions. `busy_ft_at_start` records what proportion of DATA attempts encountered a busy receiver at transmission start.

The previous Python first-failure series at `arrprob=0.05` was **0.10344**, while its properly measured physical collision probability is **0.23526**. A saved prior OMNeT++ physical collision rate was **0.32630**. This gap represents different simulated behaviors, not a normalization adjustment. Any further protocol changes must be separately validated; do **not** set or multiply counters to force numerical agreement.


The attempts-per-delivered ratio includes transmissions initiated for undelivered packets still in the finite-horizon system. It is a **window-wide efficiency ratio**, not the exact sample mean of attempts associated only with eventually delivered packets. To compute the latter, instrument per-packet attempts in both implementations. The LBT denominator assumes every non-busy completed LBT leads to a DATA transmission, consistent with the provided aggregated OMNeT++ counters.

## Run plots

```bash
bash run.sh
```

`bash run.sh` uses Docker with OMNeT++ 6.3, compiles a copy of the current Ira source, produces new .sca files, re-runs the corrected Python simulator, and generates CSV and PNG plots. The shared GitHub Actions workflow runs this on a `.run` change. Figures appear in `figures/`; new OMNeT++ scalar files in `omnet_new/results/`.

The original comparison archive must be extracted separately if you intend to re-run the Python-to-OMNeT++ scalar parsing or create a new experiment grid. The original Python source was re-run using 10 seeds, and the comparison means are given in `summary_metrics.csv`. 
