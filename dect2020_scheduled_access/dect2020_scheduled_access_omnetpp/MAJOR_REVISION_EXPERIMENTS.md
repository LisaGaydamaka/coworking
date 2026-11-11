# MDPI Sensors major-revision experiment suite

All new experiments live in this existing OMNeT++ project, under the
`revision-*` run modes. The original `ScheduledAccessQueue` and
published Phase 2–6 outputs remain unchanged.

## Physical reference and scope
- `FixedSlotQueue.cc` models one tagged PT with a fixed 10-ms clock and
  24 discrete slots. A tagged PT obtains `floor(availableSlots/D)`
  assigned one-packet opportunities per frame.
- `slotLayout=contiguous` assigns adjacent opportunities;
  `slotLayout=distributed` separates them.
- Any non-PT-eligible slots are reserved at the beginning of each frame.
  `availableSlots < D` is rejected as an infeasible one-slot-per-PT-per-frame
  allocation, rather than artificially assigning `L=1`.
- Service completion uses absolute slot endpoints; empty opportunities
  do not resynchronize the schedule.
- Packet arrival processes: Poisson, randomized-phase periodic,
  synchronized periodic batches and compound-Poisson geometric bursts.
  Matched experiments use identical *mean offered packet rates*.
- The scheduler is a controlled slot-synchronous MAC abstraction, **not**
  a radio-channel, PHY/CRC, retransmission or ETSI conformance simulator.
- Original queue buffer convention: `r` waiting positions plus at most
  one in-service type-1 packet. An exact-boundary arrival is processed
  **after** the slot-start event.

## Commands and experiment-to-reviewer mapping

| Experiment | GitHub Actions mode | Configs |
|---|---|---|
| 1: Build and validate fixed-frame simulator | `revision-smoke` | Smoke |
| 2: Physical 27-case grid | `revision-grid` | Revision_D6/D10/D20 |
| 3: Original vs corrected frame mapping | Every mode, especially `revision-grid` | Analytic model comparison |
| 4: Type-1 variability | Historical Phase 6, existing source and results | Phase6_Deterministic/Exponential/Hyperexponential |
| 5: Slot geometry and reserved slots | `revision-geometry` | Revision_Distributed/Overhead |
| 6: Arrival-process sensitivity | `revision-traffic` | Revision_Traffic |
| 7: P95/P99 physical validation | `revision-tail` | Revision_Tail |
| 8: All 27 original 95% CI checks | Every mode | Frozen Phase-2 CSV plus analytical solver |
| 9: Dimensioning cross-check | `revision-dimensioning` | Revision_DimensioningD6/D10/D20/Trade |

`run.sh` dispatches `revision-*` to `run_revision.sh`. The
shared `.github/workflows/run-project.yml` is activated by changing
**this component's** `.run` trigger on `main`.

## Measurement and comparisons
- Each main grid group uses ten independent seed-set repetitions,
  200,000 warm-up completions and 1,000,000 measured completions.
- The comparison CSVs evaluate original exponential queue, 10-ms
  frame-aligned exponential queue, 10-ms frame-aligned deterministic
  queue and physical slot scheduling at a **common absolute lambda**.
- `revision_analysis.py` exports, per Actions run mode:
  `<mode>_summary.csv`, `<mode>_model_comparison.csv`,
  `<mode>_frame_mapping.csv`, `<mode>_blocking_thresholds.csv`,
  `<mode>_phase2_ci_audit.csv` and `<mode>_report.md`.
- Analytic metrics are computed by the existing frozen
  `../analysis/phase4_dimensioning.py` stationary solver, not inferred
  from the slot scheduler.
- Uncertainty is based on replication-level 95% Student-t intervals.
  The reported original worst-case near-saturation analytic estimate
  is not inside its recomputed 95% interval; that discrepancy must be
  reported, not hidden.

## Reproducibility safeguards
- Do not overwrite `ci_results/phase2_*.csv`, `phase3_*.csv`,
  `phase4_*.csv`, `phase5_*.csv` or `phase6_*.csv`.
- Do not claim validation or publication-readiness based on *triggered*
  runs. The reports and status files must exist and the simulation logs
  must show successful completion before numerical conclusions are drawn.
- Original Phase 6 was measured under `m_F=9` ms at `D=10`; it is
  not a direct substitute for a corrected `m_F=9.166667` ms baseline.
