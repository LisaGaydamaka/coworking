#!/usr/bin/env python3
"""Regenerate manuscript Section 5 Figures 5 and 6 from the analytical model.

Uses the unchanged finite-buffer embedded-chain/occupation-time solver with
exponential type-1 service and frame-aligned deterministic vacations.
No OMNeT++ data, manuscript files, or other project outputs are modified.
"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import numpy as np

from revision_corrected_figures import metrics
from revision_plot_layout import save_compact

HERE = Path(__file__).resolve().parent
OUT = HERE / "revision_output"
OUT.mkdir(exist_ok=True)
MB = 10.0 / 24.0
DS = list(range(2, 25))
TARGETS = (0.01, 0.05, 0.10, 0.50)
LOAD_GRID = np.linspace(0.0, 0.55, 151)


def load_thresholds():
    p = OUT / "revision_corrected_dimensioning_thresholds.csv"
    with p.open(newline="", encoding="utf-8") as f:
        data = {int(row["D"]): row for row in csv.DictReader(f)}
    assert sorted(data) == DS
    return data


def figure5(thresholds):
    by_L = {}
    for L in sorted(set(24 // D for D in DS)):
        by_L[L] = np.array([metrics(L, 30, float(rho), "exponential")[1]
                            if rho > 0 else 0.0 for rho in LOAD_GRID])
    Z = np.stack([by_L[24 // D] for D in DS], axis=1)
    dy = LOAD_GRID[1] - LOAD_GRID[0]
    y_edges = np.concatenate(([0.0],
                              (LOAD_GRID[:-1] + LOAD_GRID[1:]) / 2,
                              [LOAD_GRID[-1] + dy / 2]))
    fig, ax = plt.subplots(figsize=(7.55, 4.6))
    mesh = ax.pcolormesh(np.arange(1.5, 25.5), y_edges, Z,
                         shading="flat", vmin=0, vmax=1)
    fig.colorbar(mesh, ax=ax, pad=.02).set_label(r"Blocking probability $\pi$")
    for target in TARGETS:
        key = f"rho_exponential_at_pi_{int(target*100)}pct"
        ax.plot(DS, [float(thresholds[D][key]) for D in DS],
                drawstyle="steps-mid", lw=1.5,
                label=fr"$\pi={100*target:g}\%$")
    ax.plot(DS, [(24//D)*MB/10 for D in DS], drawstyle="steps-mid",
            ls="--", lw=2.1, label=r"$\rho_{\mathrm{sat}}$")
    ax.set_xlim(1.5, 24.5)
    ax.set_ylim(0, .55)
    ax.set_xticks([2,4,6,8,10,12,14,16,18,20,22,24])
    ax.set_xlabel("Number of PT devices $D$")
    ax.set_ylabel(r"Offered load $\rho=\lambda m_B^{(1)}$")
    ax.legend(loc="upper right", ncol=2, framealpha=.94, fontsize=8)
    save_compact(fig, OUT, "section5_figure5_analytical_exponential_no_title")
    plt.close(fig)
    print("Figure 5: analytical exponential queue; no title")


def figure6():
    L = 2
    rho_sat = L * MB / 10.0
    fig, ax = plt.subplots(figsize=(7.55, 4.6))
    # Same normalized loads, buffer range and logarithmic axis as the manuscript.
    # Selected r labels reproduce the informative annotations of the older plot.
    labels = {
        0.8: {5:(-4, 8), 10:(-2, 8), 15:(-2, 8), 18:(2, 8)},
        1.0: {5:(0, 9), 10:(0, 9), 20:(4, 7), 30:(4, 7), 50:(4, 7)},
        1.2: {5:(7, 3), 10:(7, 0), 20:(7, 0), 30:(7, 0), 50:(7, 0)},
    }
    for factor in (0.8, 1.0, 1.2):
        points = []
        for r in range(1, 51):
            delay, block, _ = metrics(L, r, float(factor*rho_sat), "exponential")
            points.append((r, block, delay))
        ax.plot([p[1] for p in points], [p[2] for p in points],
                lw=1.6, marker="o", markersize=2.3,
                label=fr"$\rho/\rho_{{\mathrm{{sat}}}}={factor:.1f}$")
        for r, dxdy in labels[factor].items():
            _, block, delay = points[r-1]
            if 1e-4 <= block <= .6:
                ax.annotate(str(r), xy=(block, delay),
                            xytext=dxdy, textcoords="offset points",
                            fontsize=8, clip_on=True)
    ax.set_xscale("log")
    ax.set_xlim(1e-4, .6)
    ax.set_ylim(0, 250)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel(r"Blocking probability $\pi$ (logarithmic scale)")
    ax.set_ylabel("Mean admitted-packet sojourn time [ms]")
    ax.legend(loc="upper left", framealpha=.95, fontsize=8)
    ax.grid(True, alpha=.25, lw=.6)
    save_compact(fig, OUT, "section5_figure6_analytical_exponential_labeled_no_title")
    plt.close(fig)
    # Guard the requested model assumptions and representative point.
    delay, block, _ = metrics(2, 30, rho_sat, "exponential")
    assert abs(delay-75.75245574308477) < 1e-6
    assert abs(block-.016838518319679526) < 1e-9
    print(f"Figure 6: r labels; no title; D10/r30 saturation delay={delay:.6f}ms")


if __name__ == "__main__":
    figure5(load_thresholds())
    figure6()
