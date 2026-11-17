# Second-round fixed-slot numerical audit

All 22 points use 5 independent replications, 100,000 warm-up and
400,000 measured admitted completions per run.
Physical data: ci_results/revision-second-round_summary.csv
Analytical independent solver: analysis/phase4_dimensioning.py

## D2 low-load comparison
lambda=0.240000, load=0.2, layout=contiguous: fixed-slot mean 2.166686 +/- 0.003351 ms, analytical 2.939821 ms, relative analytical error +35.683%.
lambda=0.600000, load=0.5, layout=contiguous: fixed-slot mean 2.560655 +/- 0.006417 ms, analytical 3.009329 ms, relative analytical error +17.522%.
lambda=0.240000, load=0.2, layout=distributed: fixed-slot mean 0.938017 +/- 0.001748 ms, analytical 2.939821 ms, relative analytical error +213.408%.
lambda=0.600000, load=0.5, layout=distributed: fixed-slot mean 1.252145 +/- 0.003661 ms, analytical 3.009329 ms, relative analytical error +140.334%.

## Deterministic contour blocking (r=30)
D= 2, lambda=1.175827371, fixed-slot blocking 0.010166 +/- 0.000725, analytical 0.010000, difference +0.0166 pp.
D= 2, lambda=1.258426609, fixed-slot blocking 0.050329 +/- 0.001732, analytical 0.050000, difference +0.0329 pp.
D= 2, lambda=1.332922484, fixed-slot blocking 0.100092 +/- 0.001650, analytical 0.100000, difference +0.0092 pp.
D= 6, lambda=0.392955260, fixed-slot blocking 0.010081 +/- 0.000783, analytical 0.010000, difference +0.0081 pp.
D= 6, lambda=0.419726950, fixed-slot blocking 0.050264 +/- 0.001776, analytical 0.050000, difference +0.0264 pp.
D= 6, lambda=0.444344681, fixed-slot blocking 0.100074 +/- 0.001655, analytical 0.100000, difference +0.0074 pp.
D=10, lambda=0.196764560, fixed-slot blocking 0.010041 +/- 0.000812, analytical 0.010000, difference +0.0041 pp.
D=10, lambda=0.209930945, fixed-slot blocking 0.050261 +/- 0.001799, analytical 0.050000, difference +0.0261 pp.
D=10, lambda=0.222181270, fixed-slot blocking 0.100073 +/- 0.001657, analytical 0.100000, difference +0.0073 pp.
D=13, lambda=0.098451304, fixed-slot blocking 0.010042 +/- 0.000830, analytical 0.010000, difference +0.0042 pp.
D=13, lambda=0.104981209, fixed-slot blocking 0.050253 +/- 0.001819, analytical 0.050000, difference +0.0253 pp.
D=13, lambda=0.111092590, fixed-slot blocking 0.100074 +/- 0.001653, analytical 0.100000, difference +0.0074 pp.
D=20, lambda=0.098451304, fixed-slot blocking 0.010042 +/- 0.000830, analytical 0.010000, difference +0.0042 pp.
D=20, lambda=0.104981209, fixed-slot blocking 0.050253 +/- 0.001819, analytical 0.050000, difference +0.0253 pp.
D=20, lambda=0.111092590, fixed-slot blocking 0.100074 +/- 0.001653, analytical 0.100000, difference +0.0074 pp.
D=24, lambda=0.098451304, fixed-slot blocking 0.010042 +/- 0.000830, analytical 0.010000, difference +0.0042 pp.
D=24, lambda=0.104981209, fixed-slot blocking 0.050253 +/- 0.001819, analytical 0.050000, difference +0.0253 pp.
D=24, lambda=0.111092590, fixed-slot blocking 0.100074 +/- 0.001653, analytical 0.100000, difference +0.0074 pp.
