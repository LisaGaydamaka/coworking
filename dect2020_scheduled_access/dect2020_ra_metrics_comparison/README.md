# DECT-2020 random access — Python / OMNeT++ metrics comparison

Independent comparison component. **Do not modify** the separate `dect2020_random_access_omnetpp/` student starter or the scheduled-access simulator.

## Contents

- `4_random_access_final.py` — corrected Python source from the supplied `DECT-2020.rar`. `sim_delay()` measures time from generation to **first** delivery (multiple receipts count once).
- `inputs/DECT-2020.rar` — original uploaded archive; includes 90 OMNeT++ `.sca` outputs, original comparison code and data.
- `raw_metrics.csv` — 180 individual observations (90 newly re-run Python + 90 archived OMNeT++); includes underlying counters.
- `summary_metrics.csv` — per-parameter means and standard deviations over 10 runs.
- `plot_metrics.py` — plots four requested metrics, plus a diagnostic Python failed-DATA series on the collision plot.
- `run.sh` / `.run` — repository-compliant entrypoint and GitHub Actions trigger (plot regeneration only).

## Scenario

`arrprob = 0.01,0.02,...,0.09`, independent generation per PT per symbol; `seed = 1..10` (different frameworks use different PRNGs); 2 PT devices, one cluster, duration 3000 symbols; `c_min=1`, `c_max=16`; transmission 10 symbols, processing 10, ACK 5, LBT 2. All model outputs are measured at the end of each finite-horizon run. Data were extracted from **already supplied** OMNeT++ scalar files; the archive contains **no OMNeT++ source code** and no new OMNeT++ runs were made.

## Metric definitions

| Metric | Python numerator/denominator | OMNeT++ source |
| --- | --- | --- |
| Collision | Count unique DATA operations marked unsuccessful during `Operation.check()` (overlapping transmissions), divided by all started DATA attempts | `Cluster.medium.collidedDataAttempts / dataTransmissionAttempts` |
| LBT busy | `(Cluster.LBTall - Cluster.LBTsucc) / Cluster.LBTall` | `medium.busyLbtResponses / (busyLbtResponses + dataTransmissionAttempts)` |
| Attempts per delivered packet | `Cluster.all / delivered_num(cluster)` | `medium.dataTransmissionAttempts / ft.deliveredUniquePackets` |
| Delivery intensity | `delivered_num(cluster) / 3000` | `ft.deliveredUniquePackets / 3000` (matches recorded `packetDeliveryRate`) |

**Important interpretation:** Python's strict overlapping-DATA collision probability is about 0.08–0.12, while its **all-failed-DATA** fraction (`(Cluster.all-Cluster.succ)/Cluster.all`) is about 0.32–0.35. The OMNeT++ scalar called `collidedDataAttempts` is about 0.30–0.33, far closer to the latter. This strongly suggests that the counters are **not semantically equivalent**. Do not equate all failed transmissions to actual radio collisions; inspect the omitted OMNeT++ Medium/FT implementation before making such a claim.

The attempts-per-delivered ratio includes transmissions initiated for undelivered packets still in the finite-horizon system. It is a **window-wide efficiency ratio**, not the exact sample mean of attempts associated only with eventually delivered packets. To compute the latter, instrument per-packet attempts in both implementations. The LBT denominator assumes every non-busy completed LBT leads to a DATA transmission, consistent with the provided aggregated OMNeT++ counters.

## Run plots

```bash
bash run.sh
```

This regenerates the PNG figures from `summary_metrics.csv` inside an OMNeT++ Docker image, without executing the full model or changing saved statistics. A push changing `.run` triggers the repository's shared GitHub Actions workflow. The resulting PNGs appear in `figures/`.

The original comparison archive must be extracted separately if you intend to re-run the Python-to-OMNeT++ scalar parsing or create a new experiment grid. The original Python source was re-run using 10 seeds, and the comparison means are given in `summary_metrics.csv`. 
