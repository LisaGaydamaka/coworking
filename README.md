# Coworking

This repository is a shared remote execution workspace for multiple independent projects.

## Rules for agents

1. Each project must live entirely inside its own top-level folder.
2. Project code, dependencies, inputs, generated results, plots, logs, and documentation must stay inside that project folder.
3. Do not place project-specific files in the repository root.
4. The only shared infrastructure outside project folders is:
   - `.github/workflows/run-project.yml`
   - this root `README.md`
5. Every runnable project should contain:
   - `run.sh` — the complete project entry point;
   - `.run` — a trigger file used to request a GitHub Actions run.
6. To run a project, update only that project's `.run` file. The shared workflow detects the changed trigger, enters that folder, and executes `bash run.sh`.
7. A project's `run.sh` must install or prepare everything it needs and must write all generated outputs back into the same project folder.
8. The workflow commits generated changes only from the selected project folder.
9. Projects are independent. Never import files from, write into, rename, or modify another project folder unless the user explicitly requests it.
10. Do not create additional project folders unless the user explicitly asks for them.

## Current project

- `dect2020_scheduled_access_simulator/` — analytical vs. discrete-event Monte Carlo validation for the DECT-2020 NR scheduled-access queueing model.
