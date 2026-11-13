# Supplementary publication assets for the MDPI Sensors major revision

All generated assets are **new**. No original manuscript, original
Phase-2...Phase-6 figure or raw experiment data is modified.
Corrected mapping: L=floor(24/D), B=10/24ms and F=10-L*B.

## New/replacement figures

| Role | Figure source | Recommended placement |
|---|---|---|
| Replace submitted operating-regime Figure B | revision_corrected_figure_B_operating_map.pdf | Main Section 5.1 |
| Replace submitted delay-loss Figure C | revision_corrected_figure_C_delay_loss.pdf | Main Section 5.2 |
| 27-case physical vs abstract analytical model | revision_27case_mean_delay_comparison.pdf | Main Section 4 |
| Six-D physical blocking validation | revision_final_sixD_blocking_validation.pdf | Main Section 5 |
| Physical vs original P99 comparison | revision_physical_vs_original_tail_p99.pdf | Main Section 6; optional if space limited |
| Three-distribution corrected service variability P99 | revision_corrected_service_variability_p99.pdf | Supplementary (optional by author preference) |
| Five-case original CI convergence | revision_final_saturation_convergence.pdf | Supplementary |
| Six-D deterministic approximation error | revision_final_sixD_delay_approximation_error.pdf | Supplementary |
| Arrival-process blocking sensitivity | revision_traffic_sensitivity_blocking.pdf | Supplementary |
| Slot placement P99 sensitivity | revision_slot_position_sensitivity_p99.pdf | Supplementary |
| Reserved FT slot capacity sensitivity | revision_FT_slot_reservation_capacity.pdf | Supplementary |

## Numeric source files

- revision_corrected_dimensioning_thresholds.csv: 23 D-values, r=30,
  corrected deterministic AND exponential 1/5/10/50% contours.
- revision_corrected_selected_table4.csv: six selected D-values.
- revision_corrected_operating_map.csv: every map grid point.
- revision_corrected_delay_loss_tradeoff.csv: 150 corrected trade-off points.
- revision_FT_slot_reservation_capacity.csv: exact effective capacities for S=24,22.
- revision_final_sixD_dimensioning.csv: empirical 18-point blocking/mean/P99.
- revision_final_saturation_five_cases.csv: five long-run CI checks.

## Consistency rules

1. Leave Section 4's legacy validation Table 1 and its original F=10-10/D
   values unchanged as a historical stochastic-model verification.
2. Cite the corrected mapping for ALL revised Section-5 figures and table
   read-outs. Do NOT quote the legacy D=10 0.08335/0.08895/0.09414
   blocking thresholds for the corrected cycle.
3. Distinguish deterministic service baseline (new map/trade-off) from
   exponential service (original 27-run analytical verification).
4. Physical fixed-slot percentages at the EXPONENTIAL analytical
   contour design rates are not exactly nominal: e.g. D=2 ~0.6723%
   at the nominal 1% rate. The deterministic baseline is closer;
   the two contour definitions must never be silently conflated.
5. The corrected capacity is constant within D ranges sharing the
   same integer L; the original paper's within-band slopes caused
   by F=10-10/D must be deleted from Section 5.1.
6. The idealized tagged PT has fixed slots, not a detailed DECT radio
   implementation. Coexistence, FT signaling and interference
   are not represented at PHY level.
7. Maintain explicit fixed normalized-load definitions on all figures.

## D=10 corrected deterministic blocking thresholds

- 1%: rho=0.0819852333
- 5%: rho=0.0874712270
- 10%: rho=0.0925755292

The companion revised-manuscript checklist will handle
the exact reviewer-by-reviewer text replacements; the manuscript
itself remains unedited.
