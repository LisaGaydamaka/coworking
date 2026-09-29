# DECT-2020 NR Scheduled Access

This top-level folder contains all repository work for the DECT-2020 NR scheduled-access queueing project.

## Active components

- `analysis/` — analytical model post-processing, reproducible dimensioning data, and manuscript figures.
- `dect2020_scheduled_access_omnetpp/` — C++/NED OMNeT++ simulator, CI runners, and all simulation-validation outputs used by the manuscript.

All simulation results referenced by the manuscript are generated with OMNeT++. Analytical figures are generated from the frozen finite-capacity queueing model. Runnable components keep their own `run.sh` and `.run` trigger.
