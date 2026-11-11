# Major-revision independent analytical audit

Analytical source: frozen analysis/phase4_dimensioning.py
Physical source: newly committed ci_results/revision-*_summary.csv
All physical-to-analytical comparisons use identical absolute Poisson lambda.
Physical model: fixed 10 ms/24-slot calendar, not full radio PHY.

## Completed experimental groups
- revision-grid: 27 pooled configurations
- revision-tail: 10 pooled configurations
- revision-geometry: 17 pooled configurations
- revision-traffic: 16 pooled configurations
- revision-dimensioning: 27 pooled configurations

## Corrected 10-ms-frame service-time variability (90 runs)
- deterministic: P99 150.2195 +/- 0.0014 ms (95%)
- exponential: P99 152.9620 +/- 0.0218 ms (95%)
- hyperexponential_SCv4: P99 158.6321 +/- 0.0939 ms (95%)

## Original 27-case confidence-interval audit
- Available groups: 27
- Analytical mean delays contained in 95% simulation CI: 22/27
- Worst D10/r50 saturation: simulation 122.073566 +/- 1.155568 ms (95%); analytical 123.654645 ms.

## Fixed-slot D10/r30 at physical saturation
- mean admitted delay: 75.7636 ms
- P99 admitted delay: 148.4820 ms
- blocking: 0.016787

Outputs: revision_all_model_comparisons.csv, revision_original_27_confidence_intervals.csv,
revision_blocking_thresholds.csv, revision_tail_comparison.csv, revision_frame_mapping.csv.
Figures: revision_27case_mean_delay_comparison and revision_physical_vs_original_tail_p99.
The classical queue stability and finite-buffer limits are not claims of exact physical-slot fidelity.
