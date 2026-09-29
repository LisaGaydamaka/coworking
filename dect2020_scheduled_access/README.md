# DECT-2020 NR Scheduled Access

This top-level folder contains all repository work for the DECT-2020 NR scheduled-access queueing project.

## Implementations

- `dect2020_scheduled_access_simulator/` — analytical/reference code and the Python validation implementation used during the model audit and Phase 2 work.
- `dect2020_scheduled_access_omnetpp/` — independent C++/NED OMNeT++ simulator, CI runner, and OMNeT++ validation outputs.

The two implementations are kept together because they validate the same canonical queueing model. Each runnable implementation retains its own `run.sh` and `.run` trigger.
