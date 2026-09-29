# Coworking

This repository is a shared remote execution workspace for multiple independent projects.

## Rules for agents

1. Each logical project must live entirely inside its own top-level folder.
2. If one logical project has multiple implementations, simulators, components, experiments, or subprojects, keep them as subfolders inside that same top-level project folder. Do not create multiple sibling top-level folders for parts of the same project.
3. Project code, dependencies, inputs, generated results, plots, logs, and documentation must stay inside that project folder.
4. Do not place project-specific files in the repository root.
5. The only shared infrastructure outside project folders is:
   - `.github/workflows/run-project.yml`
   - this root `README.md`
6. Every runnable project component should contain:
   - `run.sh` — the complete entry point for that component;
   - `.run` — a trigger file used to request a GitHub Actions run.
7. To run a component, update only that component's `.run` file. The shared workflow detects the changed trigger, enters that folder, and executes `bash run.sh`.
8. A component's `run.sh` must install or prepare everything it needs and must write all generated outputs back inside the same logical project's top-level folder.
9. The workflow commits generated changes only from the selected runnable component folder.
10. Projects are independent. Never import files from, write into, rename, or modify another project folder unless the user explicitly requests it.
11. Do not create additional top-level project folders unless the user explicitly asks for them. Before creating a new top-level folder, check whether the work belongs to an existing logical project and, if so, place it there instead.

## Current project

- `dect2020_scheduled_access/` — DECT-2020 NR scheduled-access queueing project.
  - `dect2020_scheduled_access_simulator/` — analytical/reference and Python validation tools.
  - `dect2020_scheduled_access_omnetpp/` — independent OMNeT++ discrete-event simulator and validation results.
