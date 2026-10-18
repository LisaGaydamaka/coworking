# DECT-2020 random-access simulator — starter exercise

This folder is an **unfinished OMNeT++ 6.x project** for implementing the random-access mode studied in the supplied graduation thesis. It intentionally contains **no completed simulator, reference outputs, numerical results, or solution walkthrough**.

The assignment is to implement and validate the model yourself, using the thesis and the original Python simulator as the behavioral specification. Do not assume that the draft classes or parameters cover every detail.

## Where to start

1. Read `IMPLEMENTATION_PLAN.md` and the random-access sections of the thesis.
2. Complete the C++ event logic in `src/RandomAccess.cc`.
3. Decide whether to keep one centralized module (the provided starting design) or divide the model into separate OMNeT++ modules.
4. Fill in the experiments in `omnetpp.ini`.
5. Implement metric extraction and plotting in `plot.py`.
6. Validate basic scenarios and then compare the resulting curves with the thesis.

## Files

- `src/RandomAccess.ned`: initial network and parameter declaration.
- `src/RandomAccess.cc`: **compilable skeleton only**; all protocol mechanics are TODOs.
- `omnetpp.ini`: draft experiment configurations, without completed sweeps.
- `plot.py`: plotting skeleton, not an implemented plotting solution.
- `IMPLEMENTATION_PLAN.md`: design guidance and test checklist, not executable logic.
- `run.sh`: builds the skeleton using OMNeT++ 6.x in Docker; it deliberately does not run experimental sweeps.
- `.run`: trigger for the shared GitHub Actions workflow; update it only when intentionally requesting a build.

## Build

From this folder, with Docker installed:

```bash
bash run.sh
```

With OMNeT++ 6.x already installed and its environment activated:

```bash
cd src
opp_makemake -f -o ra
make -j2
```

A successful build **does not mean the simulator has been implemented**. The draft has no real packet progression or graph generation.

All generated files should remain inside this project folder. The `.gitignore` excludes temporary binaries, logs, results, and figures until you explicitly decide which validated outputs to share.
