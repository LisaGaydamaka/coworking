# DECT-2020 analytical dimensioning

This component generates the Phase-4 analytical dimensioning artifacts for the DECT-2020 scheduled-access manuscript.

It uses the frozen finite-capacity analytical model to generate:

- Figure B: operating-regime map over physical DECT mappings `D=2,...,24` with `r=30`;
- blocking contours at 1%, 5%, 10%, and 50%;
- the saturation boundary `rho_sat(D)`;
- Figure C: delay-loss trade-off for `D=10`, `r=1,...,50`, and normalized loads 0.8, 1.0, and 1.2;
- source CSV files for all plotted data.

This is analytical post-processing, not a simulation implementation. Simulation validation in the manuscript is performed with OMNeT++.

Run:

```bash
bash run.sh
```

Outputs are written to `phase4_output/`.
