# Increased simulation horizon: 30,000 symbols

Independent Python `random` and OMNeT++ PRNGs; no shared-randomness overrides. All settings are the same as the original `../figures/independent_rng` 3,000-symbol study except duration: 2 PTs, 1 cluster, 9 arrival probabilities 0.01–0.09, and 10 independent seeds per point.

Run `bash run.sh` with Docker. Results are saved exclusively inside this folder: `results/` (90 .sca), `raw_metrics.csv` (180 rows), `summary_metrics.csv` (18 grouped rows), `figures/` (4 individual charts + combined panel and CSV/JSON error reports), `comparison_horizons.csv` (MAPE 3,000 vs 30,000). No changes to the original 3,000-symbol results.

Metrics:
- Physical DATA collision probability: collided DATA attempts / all DATA attempts.
- LBT busy: busy LBT / completed LBT.
- Attempts per delivered: all DATA attempts / uniquely delivered packets. **Window efficiency ratio**, not the mean attempts for exclusively delivered packets.
- Delivery intensity: uniquely delivered packets / 30,000 symbols.
- MAPE: mean across 9 arrival probabilities of |OMNeT++ mean − Python mean| / Python mean × 100.
- Bands show ±1 sample standard deviation across 10 independent runs, not confidence intervals.

**Important**: because arrival probabilities 0.03–0.09 overload the service capacity, queues accumulate. A longer horizon reduces short-run noise but it does not imply that packet waiting time or backlog will reach stationary conditions.
