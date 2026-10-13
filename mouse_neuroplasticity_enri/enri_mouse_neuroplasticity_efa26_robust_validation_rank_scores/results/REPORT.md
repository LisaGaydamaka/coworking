# Independent EFA26 robustness and frozen-rank scoring

## Data

Clean 133 mouse-weeks, full 140, baseline 54 (52 with status=observed); all seven prior outlier-state removals were postbaseline.
Removed Learning T1/T2/T3 sum (exact baseline duplicates) and NOR1/NOR2 average speed (Spearman r>0.997 with respective distance).

## Parallel analysis

| Component | 28 old eig | 26 eig | 26 Gaussian q95 | 26 perm q95 | 26 common eig | 26 common perm q95 |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 9.291 | 7.967 | 2.822 | 2.846 | 7.798 | 2.377 |
| 2 | 4.645 | 4.612 | 2.460 | 2.478 | 4.481 | 1.990 |
| 3 | 2.550 | 2.480 | 2.221 | 2.226 | 2.287 | 1.737 |
| 4 | 2.024 | 1.900 | 2.035 | 2.026 | 1.642 | 1.534 |
| 5 | 1.441 | 1.420 | 1.860 | 1.858 | 1.066 | 1.366 |
| 6 | 1.128 | 1.123 | 1.719 | 1.710 | 0.823 | 1.217 |
| 7 | 0.976 | 0.965 | 1.585 | 1.588 | 0.635 | 1.076 |
| 8 | 0.895 | 0.805 | 1.461 | 1.465 | 0.563 | 0.961 |

Factor counts: {"perm_standard": {"retained_leading_positive_factors": 3, "raw_all_positions_threshold_crossings": 3, "first_nonpassing_position": 4, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}, "perm_common": {"retained_leading_positive_factors": 4, "raw_all_positions_threshold_crossings": 11, "first_nonpassing_position": 5, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}, "normal_standard": {"retained_leading_positive_factors": 3, "raw_all_positions_threshold_crossings": 3, "first_nonpassing_position": 4, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}, "normal_common": {"retained_leading_positive_factors": 4, "raw_all_positions_threshold_crossings": 11, "first_nonpassing_position": 5, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}}

Observed-only sensitivity factor counts: {"perm_standard": {"retained_leading_positive_factors": 3, "raw_all_positions_threshold_crossings": 3, "first_nonpassing_position": 4, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}, "perm_common": {"retained_leading_positive_factors": 4, "raw_all_positions_threshold_crossings": 11, "first_nonpassing_position": 5, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}, "normal_standard": {"retained_leading_positive_factors": 3, "raw_all_positions_threshold_crossings": 3, "first_nonpassing_position": 4, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}, "normal_common": {"retained_leading_positive_factors": 4, "raw_all_positions_threshold_crossings": 11, "first_nonpassing_position": 5, "note": "Only consecutive positive eigenvalues starting at component 1 count; negative tail passes ignored."}}

## main26: k=3
- RMSE of off-diagonal correlations: 0.0763; pairs |residual|>0.2: 6.
- Bootstrap valid: 500, failures: 0.
- D1: median cosine=0.959; q10=0.904; assigned: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport.
- D2: median cosine=0.969; q10=0.935; assigned: Learning_T1mean, Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT.
- D3: median cosine=0.922; q10=0.739; assigned: Total_distance_travelled_NOR1, Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1, Total_distance_travelled_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2.

## main26: k=4
- RMSE of off-diagonal correlations: 0.0550; pairs |residual|>0.2: 2.
- Bootstrap valid: 500, failures: 0.
- D1: median cosine=0.968; q10=0.941; assigned: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport.
- D2: median cosine=0.963; q10=0.925; assigned: Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT.
- D3: median cosine=0.925; q10=0.798; assigned: Total_distance_travelled_NOR1, Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1.
- D4: median cosine=0.838; q10=0.540; assigned: Total_distance_travelled_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2, Latency_to_first_investigation_Stakan_zone_NOR2, Learning_T1mean.

## observed52: k=3
- RMSE of off-diagonal correlations: 0.0773; pairs |residual|>0.2: 6.
- Bootstrap valid: 250, failures: 0.
- D1: median cosine=0.954; q10=0.882; assigned: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport.
- D2: median cosine=0.967; q10=0.933; assigned: Learning_T1mean, Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT.
- D3: median cosine=0.929; q10=0.676; assigned: Total_distance_travelled_NOR1, Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1, Total_distance_travelled_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2.

## observed52: k=4
- RMSE of off-diagonal correlations: 0.0543; pairs |residual|>0.2: 2.
- Bootstrap valid: 250, failures: 0.
- D1: median cosine=0.968; q10=0.943; assigned: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport.
- D2: median cosine=0.965; q10=0.933; assigned: Learning_T1mean, Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT.
- D3: median cosine=0.918; q10=0.805; assigned: Total_distance_travelled_NOR1, Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1, Latency_to_first_investigation_Stakan_NOR1.
- D4: median cosine=0.839; q10=0.586; assigned: Total_distance_travelled_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2, Latency_to_first_investigation_Stakan_zone_NOR2.

## Consistent domain-score calculation

The previous model computed regression scores using raw-scale standardized values but a Spearman-derived correlation matrix. This model replaces those with frozen baseline midrank-standardized scores. The baseline transformed values reproduce the Spearman R exactly.
The same baseline midrank transformation and factor-regression weights are used for week 0, 16, and 24 without refitting.
Full 140-state score projection is a descriptive sensitivity analysis of the seven exclusions. It does not validate or repair implausible raw measurements.
See k3/k4 clean133 vs full140 impact tables and raw vs rank score correlations.

## Outstanding validation limitations

- Actual raw source Excel readings for the seven outliers must still be audited before editing the source.
- Historical imputation pipeline used all-week fitting; strict prospective modeling would require baseline-only imputation fitting.
- n=54 (or 52) is modest relative to 26 variables; treat factor counts as tentative.
- Domain scores are descriptive and are not inference of causal treatments or aging effects.
