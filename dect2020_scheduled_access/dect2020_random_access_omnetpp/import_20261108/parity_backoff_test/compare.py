"""Run matched-backoff diagnostics against unchanged production model sources.

This harness uses Python monkeypatches and an isolated C++ build: production
random.randint/intuniform remain untouched. It compares actual *event times*
(not just aggregate means) and stores a machine-checkable report.
"""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import random
import statistics
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
REFERENCE = ROOT.parent / "comparison_mean_delay" / "4_random_access_corrected.py"
EXECUTABLE = ROOT / "build" / "ra_parity"
CASES = [(110, 300000, 17), (110, 2000000, 17),
         (120, 2000000, 17), (150, 2000000, 17),
         (250, 2000000, 17), (390, 2000000, 17),
         (500, 2000000, 17)]
EVENTS = ("backoff", "lbt", "data", "delivery")
assert REFERENCE.exists() and EXECUTABLE.exists()

def parity_hash(kind, pt, index, seed):
    x = (seed * 0x9e3779b9 + (pt + 1) * 0x85ebca6b
         + (index + 1) * 0xc2b2ae35 + kind * 0x27d4eb2f) & 0xffffffff
    x = ((x ^ (x >> 16)) * 0x7feb352d) & 0xffffffff
    x = ((x ^ (x >> 15)) * 0x846ca68b) & 0xffffffff
    return (x ^ (x >> 16)) & 0xffffffff

def run_python(d, symbols, seed, trace_path):
    spec = importlib.util.spec_from_file_location("ra_corrected", REFERENCE)
    sim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sim)
    sim.cluster_count = 1
    sim.devices_in_cluster_count = 2
    sim.arrival_type = "none"
    sim.Lmb = d
    sim.c_min = 5
    sim.c_max = 40
    sim.lbt_time = 2
    sim.trans_time = 10
    sim.proc_time = 10
    sim.ack_time = 5
    sim.model_time = symbols
    sim.ack_delivery_always_succ = False
    sim.lbt_always_succ = False
    sim.c_min_for_retry = False
    random.seed(seed)

    counters = [0, 0]
    with trace_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(("kind", "pt", "t", "a", "b"))
        original_backoff = sim.DevicePT.backoff_start
        original_lbt_end = sim.DevicePT.LBT_end
        original_send_start = sim.DevicePT.send_start
        original_proc_end = sim.RootDevice.proc_end

        def deterministic_backoff(self, t):
            window = self.c_current
            index = counters[self.id]
            counters[self.id] += 1
            slots = parity_hash(1, self.id, index, seed) % (window + 1)
            writer.writerow(("backoff", self.id, t, window, slots))
            old_randint = sim.random.randint
            def draw(a, b):
                assert (a, b) == (0, window), (a, b, window)
                return slots
            sim.random.randint = draw
            try:
                return original_backoff(self, t)
            finally:
                sim.random.randint = old_randint

        def lbt_end(self, t, packet):
            writer.writerow(("lbt", self.id, t, int(self.operation.is_successful), 0))
            return original_lbt_end(self, t, packet)

        def send_start(self, t, packet):
            writer.writerow(("data", self.id, t, packet.journey[0].ttime, 0))
            return original_send_start(self, t, packet)

        def proc_end(self, t, transmission):
            success = transmission.is_successful
            result = original_proc_end(self, t, transmission)
            if success:
                writer.writerow(("delivery", transmission.A.id, t,
                                 transmission.packet.journey[0].ttime, 0))
            return result

        sim.DevicePT.backoff_start = deterministic_backoff
        sim.DevicePT.LBT_end = lbt_end
        sim.DevicePT.send_start = send_start
        sim.RootDevice.proc_end = proc_end
        sim.setup()
        with contextlib.redirect_stdout(io.StringIO()):
            sim.main()
        delivered = sim.delivered_num(sim.clusters[0])
        delay = sim.sim_delay(sim.clusters[0])
        attempts = sim.clusters[0].all
        busy_lbt = sim.clusters[0].LBTall - sim.clusters[0].LBTsucc

    return dict(mean_delay=delay, delivered_unique=delivered,
                data_attempts=attempts, busy_lbt=busy_lbt,
                backoff_draws=counters)

def scalar(path, key):
    for line in path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[0] == "scalar" and parts[2] == key:
            return float(parts[3])
    raise RuntimeError(f"Scalar not found: {key} in {path}")

def run_omnet(d, symbols, seed, trace_path):
    ini = RESULTS / f"parity_d{d}_n{symbols}_s{seed}.ini"
    ini.write_text(f"""[General]
network = DectRandomAccess
simtime-resolution = ps
seed-set = {seed}
*.model.paritySeed = {seed}
*.model.parityTraceFile = "{trace_path}"
*.model.ptCount = 2
*.model.generationIntervalSymbols = {d}
*.model.cMin = 5
*.model.cMax = 40
*.model.resetBackoffAfterNoAck = false
*.model.lbtSymbols = 2
*.model.dataSymbols = 10
*.model.procSymbols = 10
*.model.ackSymbols = 5
*.model.symbolTime = 41.666666667us
*.model.simulationSymbols = {symbols}
*.model.warmupSymbols = 0
**.vector-recording = false
""")
    sca = RESULTS / f"parity_d{d}_n{symbols}_s{seed}.sca"
    cmd = [str(EXECUTABLE), "-u", "Cmdenv", "-n", str(ROOT / "build"),
           "-f", str(ini), f"--output-scalar-file={sca}",
           "--cmdenv-express-mode=true"]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    (RESULTS / f"omnet_d{d}_n{symbols}_s{seed}.log").write_text(proc.stdout + "\n" + proc.stderr)
    if proc.returncode:
        raise RuntimeError(f"OMNeT++ exit={proc.returncode}\n{proc.stderr[-2000:]}\n{proc.stdout[-2000:]}")
    return dict(mean_delay=scalar(sca, "meanEndToEndDelaySymbols"),
                delivered_unique=int(scalar(sca, "measuredDeliveredPackets")),
                data_attempts=int(scalar(sca, "dataTransmissionAttempts")),
                busy_lbt=int(scalar(sca, "busyLbtCount")))

def load_trace(path):
    grouped = {key: [] for key in EVENTS}
    with path.open(newline="") as f:
        for r in csv.DictReader(f):
            grouped[r["kind"]].append((int(r["pt"]), int(r["t"]),
                                      int(r["a"]), int(r["b"])))
    return grouped

def comparison(py, om, kind):
    p = py[kind]
    o = om[kind]
    # Canonical time/pt ordering removes nonphysical same-timestamp insertion order.
    ps = sorted(p)
    os_ = sorted(o)
    first = next((i for i in range(min(len(ps), len(os_))) if ps[i] != os_[i]),
                 min(len(ps), len(os_)) if len(ps) != len(os_) else None)
    draw_prefix = None
    if kind == "backoff":
        draw_prefix = {}
        for pt in range(2):
            # Compare (window, slots) sequence independently for each PT.
            a = [(r[2], r[3]) for r in p if r[0] == pt]
            b = [(r[2], r[3]) for r in o if r[0] == pt]
            draw_prefix[str(pt)] = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]),
                                       min(len(a), len(b)))
    canonical = lambda rows: hashlib.sha256(
        "".join(",".join(map(str, r)) + "\n" for r in rows).encode()).hexdigest()
    return dict(python_count=len(ps), omnet_count=len(os_), matched=(ps == os_),
                python_sha256=canonical(ps), omnet_sha256=canonical(os_),
                first_mismatch_index=first,
                python_at_mismatch=ps[first] if first is not None and first < len(ps) else None,
                omnet_at_mismatch=os_[first] if first is not None and first < len(os_) else None,
                matching_draw_prefix_per_pt=draw_prefix)

report = {"method": "independent per-PT counter-based hash PRNG, same seeds",
          "original_sources_modified": False,
          "reference_file": str(REFERENCE.relative_to(ROOT.parent)),
          "scenarios": []}
rows = []
for d, symbols, seed in CASES:
    stem = f"d{d}_n{symbols}_s{seed}"
    py_trace = RESULTS / f"trace_python_{stem}.csv"
    om_trace = RESULTS / f"trace_omnet_{stem}.csv"
    print("Running", stem, flush=True)
    py = run_python(d, symbols, seed, py_trace)
    om = run_omnet(d, symbols, seed, om_trace)
    traces = {"python": load_trace(py_trace), "omnet": load_trace(om_trace)}
    events = {kind: comparison(traces["python"], traces["omnet"], kind) for kind in EVENTS}
    # Python includes events at t==symbols, OMNeT++ stops before the tick at t==symbols.
    # Preserve raw events and compare starts within the common observation window.
    in_window = {
        side: {"backoff": [ev for ev in traces[side]["backoff"] if ev[1] < symbols]}
        for side in ("python", "omnet")
    }
    events["backoff_within_horizon"] = comparison(
        in_window["python"], in_window["omnet"], "backoff")
    events["terminal_backoff_counts"] = {
        side: len(traces[side]["backoff"]) - len(in_window[side]["backoff"])
        for side in ("python", "omnet")
    }
    diff = om["mean_delay"] - py["mean_delay"]
    row = dict(d=d, symbols=symbols, seed=seed,
               python_mean_symbols=py["mean_delay"], omnet_mean_symbols=om["mean_delay"],
               mean_difference_symbols=diff,
               relative_difference_pct=diff / py["mean_delay"] * 100,
               python_delivered=py["delivered_unique"], omnet_delivered=om["delivered_unique"],
               python_attempts=py["data_attempts"], omnet_attempts=om["data_attempts"],
               python_busy_lbt=py["busy_lbt"], omnet_busy_lbt=om["busy_lbt"],
               backoff_events_match=events["backoff"]["matched"],
               lbt_events_match=events["lbt"]["matched"],
               data_events_match=events["data"]["matched"],
               delivery_events_match=events["delivery"]["matched"])
    rows.append(row)
    report["scenarios"].append(dict(config=dict(d=d, symbols=symbols, seed=seed),
                                    python=py, omnet=om, delay_diff=diff,
                                    event_comparisons=events))
    for kind in EVENTS:
        e = events[kind]
        print(f"  {kind}: {e['python_count']} / {e['omnet_count']} | "
              f"exact_match={e['matched']} first_diff={e['first_mismatch_index']}", flush=True)
    print(f"  Mean delay: PY={py['mean_delay']:.9f}, OM={om['mean_delay']:.9f}, "
          f"delta={diff:.9f}; delivered={py['delivered_unique']}/{om['delivered_unique']}",
          flush=True)
    # Raw traces exceed several megabytes for long runs and are intentionally not committed.
    py_trace.unlink()
    om_trace.unlink()

report["all_event_traces_match"] = all(
    all(sc["event_comparisons"][kind]["matched"] for kind in EVENTS)
    for sc in report["scenarios"]
)
report["all_event_traces_match_within_observation_window"] = all(
    all(sc["event_comparisons"][kind]["matched"] for kind in (
        "backoff_within_horizon", "lbt", "data", "delivery"))
    for sc in report["scenarios"]
)
report["boundary_note"] = (
    "Python processes events at time == horizon, whereas OMNeT++ does not "
    "run a symbol tick at t==horizon. Extra terminal backoffs are filtered "
    "only for the observation-window comparison. Raw counts are retained."
)
report["all_numeric_metrics_match"] = all(
    abs(r["mean_difference_symbols"]) < 1e-6
    and r["python_delivered"] == r["omnet_delivered"]
    and r["python_attempts"] == r["omnet_attempts"]
    and r["python_busy_lbt"] == r["omnet_busy_lbt"] for r in rows
)
(RESULTS / "report.json").write_text(json.dumps(report, indent=2) + "\n")
with (RESULTS / "summary.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)

# The supplied Python source enables Matplotlib usetex at import.
# This plot does not require LaTeX.
plt.rcParams["text.usetex"] = False
# For the 2-million-symbol scenarios, chart absolute delays side by side.
full = [r for r in rows if r["symbols"] == 2000000]
fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=180)
ax.plot([r["d"] for r in full], [r["python_mean_symbols"] for r in full],
        "o-", label="Python, shared diagnostic backoff")
ax.plot([r["d"] for r in full], [r["omnet_mean_symbols"] for r in full],
        "s--", label="OMNeT++, shared diagnostic backoff")
ax.set_xlabel("Packet generation interval d (symbols)")
ax.set_ylabel("Mean generation-to-last-delivery delay (symbols)")
ax.set_title("Controlled Python vs OMNeT++ | 2 PT | 2,000,000 symbols | seed 17")
ax.grid(alpha=0.25)
ax.legend()
fig.tight_layout()
fig.savefig(RESULTS / "shared_backoff_delay.png")
plt.close(fig)
print("RESULT all_event_traces_match", report["all_event_traces_match"])
print("RESULT all_event_traces_match_within_observation_window", report["all_event_traces_match_within_observation_window"])
print("RESULT all_numeric_metrics_match", report["all_numeric_metrics_match"])
print("SAVED results/report.json results/summary.csv results/shared_backoff_delay.png", flush=True)
