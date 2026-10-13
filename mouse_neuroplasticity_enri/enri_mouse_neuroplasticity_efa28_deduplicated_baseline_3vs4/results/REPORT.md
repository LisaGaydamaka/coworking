# Repeat EFA on 28 features after removing exact baseline duplicates

Original data cleaning and seven removed mouse-week states are unchanged.
Excluded columns: Learning_T1sum, Learning_T2sum, Learning_T3sum.
All three mean/sum pairs were identical on each of 54 baseline mice.

Parallel analysis: 3 factors pass observed eigenvalue > random 95th percentile.

## Old 31-feature vs new 28-feature parallel analysis

| Component | Old eig | Old null q95 | New eig | New null q95 | Margin new |
|---|---:|---:|---:|---:|---:|
| 1 | 9.661 | 3.078 | 9.291 | 2.931 | +6.360 |
| 2 | 6.430 | 2.687 | 4.645 | 2.544 | +2.102 |
| 3 | 2.604 | 2.439 | 2.550 | 2.301 | +0.249 |
| 4 | 2.248 | 2.234 | 2.024 | 2.114 | -0.090 |
| 5 | 1.457 | 2.069 | 1.441 | 1.931 | -0.490 |
| 6 | 1.262 | 1.911 | 1.128 | 1.794 | -0.667 |
| 7 | 1.060 | 1.773 | 0.976 | 1.658 | -0.682 |
| 8 | 0.944 | 1.650 | 0.895 | 1.530 | -0.635 |

## k=3, MINRES oblimin / bootstrap 500

Offdiagonal residual RMSE: 0.1385. Bootstrap valid: 500.
- D1: bootstrap cosine median=0.941, q10=0.837, q90=0.974.
  - Members: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport
  - Stable core: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport
- D2: bootstrap cosine median=0.923, q10=0.673, q90=0.972.
  - Members: Total_distance_travelled_NOR1, Average_speed_NOR1, Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1, Total_distance_travelled_NOR2, Average_speed_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2
  - Stable core: Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1, Total_distance_travelled_NOR2, Average_speed_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2
- D3: bootstrap cosine median=0.965, q10=0.925, q90=0.981.
  - Members: Learning_T1mean, Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT
  - Stable core: Learning_T1mean, Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT

## k=4, MINRES oblimin / bootstrap 500

Offdiagonal residual RMSE: 0.0557. Bootstrap valid: 500.
- D1: bootstrap cosine median=0.961, q10=0.929, q90=0.979.
  - Members: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport
  - Stable core: OFT_distance, Average_speed_OFT, Total_time_mobile_OFT, Absolute_turn_angle_OFT, rear_support, rear_nosupport
- D2: bootstrap cosine median=0.967, q10=0.936, q90=0.980.
  - Members: Learning_T1mean, Learning_T1max, Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT
  - Stable core: Learning_T2mean, Learning_T2max, Learning_T3mean, Learning_T3max, EnduranceT
- D3: bootstrap cosine median=0.912, q10=0.672, q90=0.965.
  - Members: Total_distance_travelled_NOR1, Average_speed_NOR1, Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1, Latency_to_first_investigation_Stakan_NOR1, Weight
  - Stable core: Time_investigating_Piramidka_NOR1, Time_investigating_Stakan_NOR1
- D4: bootstrap cosine median=0.889, q10=0.658, q90=0.957.
  - Members: Total_distance_travelled_NOR2, Average_speed_NOR2, Time_investigating_Piramidka_zone_NOR2, Time_investigating_Stakan_zone_NOR2, Latency_to_first_investigation_Stakan_zone_NOR2
  - Stable core: Total_distance_travelled_NOR2, Average_speed_NOR2, Time_investigating_Piramidka_zone_NOR2

## Matched factors vs old 31-feature EFA

- k=3: old D1 -> new D3, absolute loading cosine=0.996.
- k=3: old D2 -> new D1, absolute loading cosine=0.991.
- k=3: old D3 -> new D2, absolute loading cosine=0.988.
- k=4: old D1 -> new D2, absolute loading cosine=0.982.
- k=4: old D2 -> new D1, absolute loading cosine=0.996.
- k=4: old D3 -> new D3, absolute loading cosine=0.953.
- k=4: old D4 -> new D4, absolute loading cosine=0.909.

## Caveats

The new PCA/eigenvalue retention is not the same thing as the EFA factor loadings.
Small baseline sample, multiple correlated behavioral measures, and near-threshold factors require caution.
Frozen factor scores at week 16 and 24 are descriptive only.
All previous experiment files are left untouched.
