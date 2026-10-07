# eNRI GRIP31 — longitudinal-only production rerun

Production workflow run: `37596130022` — **success**.  
Final artifact: `longitudinal-grip31-final-results` (artifact id `11471792849`).

## Scientific change

Only the directional order set was changed. The model now uses six within-group longitudinal inequalities:

- PBS^0 > PBS^16
- LPS^0 > LPS^16
- run^0 > run^16
- MCC^0 > MCC^16
- PBS^16 > PBS^24
- LPS^16 > LPS^24

No same-week between-group directional inequality is included.

## Full 31-feature eNRI

The base QP re-selected its hyperparameters from scratch under the six-constraint model:

- beta = 1.0
- lambda2 = 0.1
- C = 0.1
- rho = 0.1
- epsilon = 0.001
- solver status = optimal
- pooled week-0 mouse mean eNRI = 1.0000000000000002
- living eNRI range = 0.83563 to 1.18698
- total order slack = 3.77e-10

All six longitudinal relations meet the requested margin to numerical tolerance. The two 16→24 PBS/LPS differences sit essentially exactly at 0.1.

Because between-group relations are no longer imposed, they are descriptive model outputs. In the full fit:

- week 16: PBS=0.795686, LPS=0.822349, PBS-LPS=-0.026663
- week 24: PBS=0.695686, LPS=0.722349, PBS-LPS=-0.026663
- week 24: run-LPS=+0.057020
- week 24: MCC-LPS=+0.048695

## Development feature selection

The L1 development step again selected lambda1*=0.03, but the sparse structure changed materially. The full sparse fit contains 13 active features. In 200 stability resamples, only `Absolute_turn_angle_OFT` satisfies the core rule (pi=0.85, sign consistency=1.00).

The development candidates are:

- `Latency_to_first_investigation_Stakan_zone_NOR2`
- `rear_support`
- `Weight`
- `Latency_to_first_investigation_Piramidka_NOR1`

Grip is no longer stable: pi=0.165 and sign consistency=0.788.

The development one-SE subset is S8:

`Average_speed_NOR1, OFT_distance, Absolute_turn_angle_OFT, Time_investigating_Piramidka_NOR1, Latency_to_first_investigation_Stakan_zone_NOR2, rear_support, Weight, Latency_to_first_investigation_Piramidka_NOR1`.

## Production nested validation

The full adaptive procedure was repeated inside 30 fixed outer 80/20 splits; each outer-train used 20 inner splits and 100 stability resamples.

Selected k varies from 3 to 15 (median 7, mean 8.0). Top outer selection frequencies:

| Feature | Count | Frequency |
|---|---:|---:|
| Absolute_turn_angle_OFT | 25/30 | 83.3% |
| Average_speed_NOR1 | 23/30 | 76.7% |
| OFT_distance | 22/30 | 73.3% |
| Time_investigating_Piramidka_NOR1 | 21/30 | 70.0% |
| Latency_to_first_investigation_Stakan_zone_NOR2 | 19/30 | 63.3% |
| Weight | 15/30 | 50.0% |
| Grip | 7/30 | 23.3% |

## Stopping rule

The pre-specified stopping rule fires:

- 30 outer splits produced 30 distinct exact weighted subsets;
- no exact subset recurred more than once;
- the development S8 subset recurred exactly 0/30 times.

Final status: **NO_STABLE_FIXED_SUBSET**.

Therefore the reduced final refit remains blocked. The fixed model for this formulation is the full 31-feature eNRI; nested results characterize information stability/substitution rather than define a post-hoc reduced index.

## Audit

Base Stage 9 passed 25/25 checks; max order violation=0, max positivity violation=0, and model.json reproduces eNRI with max absolute error 2.22e-16.

One cosmetic issue was found in the successful artifact: the Stage-A informational JSON retained the historical beta=0.1 label. It did not feed any solver. The actual base model, Stage 0, Stage B and reduced/nested fits used beta=1.0. The new experiment source has been corrected so future reruns emit aligned Stage-A metadata.
