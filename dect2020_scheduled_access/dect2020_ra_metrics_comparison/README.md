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
| Collision | Count unique DATA operations marked unsuccessful during `Operation.check()` (overlapping transmissions), divided by all started DATA attempts | `Cluster.ft.pythonEquivalentDataCollisions / Cluster.medium.dataTransmissionAttempts` (new) |
| LBT busy | `(Cluster.LBTall - Cluster.LBTsucc) / Cluster.LBTall` | `medium.busyLbtResponses / (busyLbtResponses + dataTransmissionAttempts)` |
| Attempts per delivered packet | `Cluster.all / delivered_num(cluster)` | `medium.dataTransmissionAttempts / ft.deliveredUniquePackets` |
| Delivery intensity | `delivered_num(cluster) / 3000` | `ft.deliveredUniquePackets / 3000` (matches recorded `packetDeliveryRate`) |

**Collision interpretation and exact patch:**

The Python metric counts *only a transition from successful to unsuccessful* in `Operation.check()` for DATA (`type == "Trans"`). A DATA may have been rejected earlier because the FT was busy. Later overlaps do not retroactively count as an additional Python collision.

OMNeT++ was materially different: it only made `FT.isBusy=true` when **processing begins** at DATA_END. Python `RootDevice.receive_start()` makes FT busy immediately at DATA_START, then processes for `procTime` even if the reception was corrupted. The patch in `../dect2020_ra_ira_omnetpp/src/FT.cc` corrects both timing behaviors and adds `ft.pythonEquivalentDataCollisions`:

- For each DATA, remember whether FT was free at DATA_START and whether the DATA was already collided when its start notification arrived.
- On DATA_END with radio overlap, count a Python-equivalent collision if the receiver was initially free **or** the transmission was already collided at start (Python runs `check()` before `receive_start()`).
- Otherwise an attempt already marked failed due to FT busy is **not** counted again as a Python collision, although it remains a physical radio overlap.

Raw physical overlaps remain available in `medium.collidedDataAttempts`. The new metric is `ft.pythonEquivalentDataCollisions / medium.dataTransmissionAttempts` and is compared to the Python `Operation.check()` transition-based metric. The `FT` additionally records `rejectedAtStartWhileBusy`. The two curves should be close **because their semantics now match**, not because of a tuned multiplier. Different RNGs and event ordering can still cause differences. Verify using the new .sca results.


The attempts-per-delivered ratio includes transmissions initiated for undelivered packets still in the finite-horizon system. It is a **window-wide efficiency ratio**, not the exact sample mean of attempts associated only with eventually delivered packets. To compute the latter, instrument per-packet attempts in both implementations. The LBT denominator assumes every non-busy completed LBT leads to a DATA transmission, consistent with the provided aggregated OMNeT++ counters.

## Run plots

```bash
bash run.sh
```

`bash run.sh` uses Docker with OMNeT++ 6.3, compiles a copy of the current Ira source, produces new .sca files, re-runs the corrected Python simulator, and generates CSV and PNG plots. The shared GitHub Actions workflow runs this on a `.run` change. Figures appear in `figures/`; new OMNeT++ scalar files in `omnet_new/results/`.

The original comparison archive must be extracted separately if you intend to re-run the Python-to-OMNeT++ scalar parsing or create a new experiment grid. The original Python source was re-run using 10 seeds, and the comparison means are given in `summary_metrics.csv`. 
