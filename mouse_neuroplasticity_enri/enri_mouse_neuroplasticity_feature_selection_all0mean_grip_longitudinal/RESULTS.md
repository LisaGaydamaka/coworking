# Longitudinal-only GRIP31 eNRI — production result

Workflow run: 37596130022

## Model change

Only six within-group longitudinal directional constraints are used:

- PBS^0 > PBS^16
- LPS^0 > LPS^16
- run^0 > run^16
- MCC^0 > MCC^16
- PBS^16 > PBS^24
- LPS^16 > LPS^24

No between-group directional inequality is included.

## Base model

- Selected QP hyperparameters: beta=1.0, lambda2=0.1, C=0.1, rho=0.1.
- 31 weighted features, including Grip.
- Living eNRI range: 0.83563–1.18698.
- Sum of slack: 3.77e-10.
- Development L1: lambda1*=0.03; full sparse fit has 13 active features.
- Development stability has one core feature: Absolute_turn_angle_OFT (pi=0.85, sign consistency=1.00).
- Development subset selection chooses k=8.

## Production nested validation

30 outer splits completed successfully. No validation errors.

Top outer selection frequencies:
- Absolute_turn_angle_OFT: 25/30 = 83.3%
- Average_speed_NOR1: 23/30 = 76.7%
- OFT_distance: 22/30 = 73.3%
- Time_investigating_Piramidka_NOR1: 21/30 = 70.0%
- Latency_to_first_investigation_Stakan_zone_NOR2: 19/30 = 63.3%
- Weight: 15/30 = 50.0%
- Grip: 7/30 = 23.3%

Reference block frequencies:
- B01 (OFT): 30/30 = 100%
- B02 (NOR1 distance/speed): 23/30 = 76.7%
- B04 (Rotarod T1): 9/30 = 30.0%
- B05 (Rotarod T2): 5/30 = 16.7%
- B06 (Rotarod T3): 4/30 = 13.3%
- B03 (NOR2 distance/speed): 0/30

Selected k ranges from 3 to 15; median=7, mean=8.

## Stopping rule

30 outer splits produced 30 distinct exact weighted subsets. The development k=8 subset was reproduced exactly in 0/30 outer splits.

**NO_STABLE_FIXED_SUBSET**

Therefore no post-hoc reduced weighted eNRI is fixed. The completed fixed index remains the full 31-feature longitudinal-only constrained eNRI.
