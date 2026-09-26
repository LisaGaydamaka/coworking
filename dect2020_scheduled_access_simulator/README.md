# DECT-2020 scheduled-access simulator

Minimal validation of the analytical queueing model against a discrete-event Monte Carlo simulation.

## Run

```bash
pip install numpy matplotlib
python compare.py
```

The script prints analytical and simulation mean delays and creates `comparison.svg`.

Parameters are the manuscript baseline: `m_B=10/24 ms`, `m_F=9 ms`, `r=30`, `L=2`.
All simulator files and generated outputs must stay inside this directory.
