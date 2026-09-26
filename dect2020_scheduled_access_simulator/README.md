# DECT-2020 scheduled-access simulator

Minimal independent validation of the finite-capacity queueing model.

## Model used

- Poisson type-1 arrivals.
- Type-1 service: exponential, mean `1/MU = 10/24 ms`.
- Type-2 service: deterministic, `F = 9 ms`.
- Baseline Figure-7 parameters: `D=10`, `L=2`, `r=30`.
- A type-2 service starts when the type-1 system becomes empty or after `L` type-1 completions.
- Buffer capacity is `r` waiting type-1 packets.

## Run

```bash
bash run.sh
```

Outputs:
- `results.csv`
- `comparison.svg`

The analytical calculation in `compare.py` uses the stated model consistently: every state with `l=L` is followed by the deterministic type-2 service distribution `F`, including overflow-tail probabilities. This differs from the old plotting code used for the manuscript Figure 7, where some `l=L` transition rows used the type-1 distribution instead.
