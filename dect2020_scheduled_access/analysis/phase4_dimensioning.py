import csv
import math
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter

TFRAME_MS = 10.0
SLOTS_PER_FRAME = 24
MB_MS = TFRAME_MS / SLOTS_PER_FRAME
MU_PER_MS = 1.0 / MB_MS


def dect_mapping(D):
    if D < 2 or D > 24:
        raise ValueError("D must be in [2,24] for the dimensioning grid")
    L = max(1, SLOTS_PER_FRAME // D)
    mF = TFRAME_MS - TFRAME_MS / D
    lambda_sat = L / (L * MB_MS + mF)
    rho_sat = lambda_sat * MB_MS
    return L, mF, lambda_sat, rho_sat


def exp_counts(lam, nmax):
    p = lam / (lam + MU_PER_MS)
    q = 1.0 - p
    probs = np.array([q * p**k for k in range(nmax + 1)], dtype=float)
    tails = np.array([p**k for k in range(nmax + 1)], dtype=float)
    return probs, tails


def det_counts(lam, T, nmax):
    probs = np.zeros(nmax + 1, dtype=float)
    x = lam * T
    probs[0] = math.exp(-x)
    for k in range(1, nmax + 1):
        probs[k] = probs[k - 1] * x / k
    csum = np.concatenate(([0.0], np.cumsum(probs)))
    tails = np.array([max(0.0, 1.0 - csum[k]) for k in range(nmax + 1)], dtype=float)
    return probs, tails


def states(r, L):
    return [(L, 0)] + [(l, k) for k in range(1, r + 1) for l in range(L + 1)]


def transition_matrix(r, L, beta, phi, beta_tail, phi_tail):
    S = states(r, L)
    I = {s: i for i, s in enumerate(S)}
    P = np.zeros((len(S), len(S)), dtype=float)

    for row, (l, k) in enumerate(S):
        if l == L:
            for j in range(k, r):
                a = j - k
                dest = (L, 0) if j == 0 else (0, j)
                P[row, I[dest]] += phi[a]
            P[row, I[(0, r)]] += phi_tail[r - k]
        else:
            for j in range(k - 1, r):
                a = j - k + 1
                if j == 0:
                    dest = (L, 0)
                elif l + 1 == L:
                    dest = (L, j)
                else:
                    dest = (l + 1, j)
                P[row, I[dest]] += beta[a]
            dest = (L, r) if l + 1 == L else (l + 1, r)
            P[row, I[dest]] += beta_tail[r - k + 1]
    return P


def stationary(P):
    A = P.T - np.eye(len(P))
    A[-1, :] = 1.0
    b = np.zeros(len(P))
    b[-1] = 1.0
    q = np.linalg.solve(A, b)
    q[np.abs(q) < 1e-14] = 0.0
    return q


def reward_metrics(lam, r, L, mF, q, beta_tail, phi_tail):
    m = L + 1
    mean_cycle = 0.0
    area = 0.0
    blocked = 0.0

    def interval_reward(k, capacity, mean_service, tail):
        free = capacity - k
        if free <= 0:
            return capacity * mean_service, lam * mean_service
        times = [tail[n + 1] / lam for n in range(free)]
        full_time = max(0.0, mean_service - sum(times))
        interval_area = sum((k + n) * times[n] for n in range(free)) + capacity * full_time
        return interval_area, lam * full_time

    for idx, prob in enumerate(q):
        if idx == 0:
            l, k = L, 0
        else:
            z = idx - 1
            k = z // m + 1
            l = z % m

        if l == L:
            service = mF
            interval_area, interval_blocked = interval_reward(k, r, mF, phi_tail)
        else:
            service = MB_MS
            interval_area, interval_blocked = interval_reward(k, r + 1, MB_MS, beta_tail)

        mean_cycle += prob * service
        area += prob * interval_area
        blocked += prob * interval_blocked

    Nbar = area / mean_cycle
    pi = blocked / (lam * mean_cycle)
    pi = min(1.0, max(0.0, pi))
    admitted = lam * (1.0 - pi)
    vbar = Nbar / admitted if admitted > 0 else math.inf
    return Nbar, pi, vbar


def analytic_metrics(D, r, rho):
    L, mF, lambda_sat, rho_sat = dect_mapping(D)
    if rho <= 0:
        return {
            "D": D, "r": r, "L": L, "mF_ms": mF, "rho": 0.0,
            "lambda_per_ms": 0.0, "lambda_sat_per_ms": lambda_sat,
            "rho_sat": rho_sat, "blocking_probability": 0.0,
            "mean_number": 0.0, "mean_delay_ms": mF + MB_MS,
        }

    lam = rho / MB_MS
    nmax = r + 3
    beta, beta_tail = exp_counts(lam, nmax)
    phi, phi_tail = det_counts(lam, mF, nmax)
    P = transition_matrix(r, L, beta, phi, beta_tail, phi_tail)
    q = stationary(P)

    if np.max(np.abs(P.sum(axis=1) - 1.0)) > 1e-10:
        raise RuntimeError("transition rows are not stochastic")
    if np.max(np.abs(q @ P - q)) > 1e-9:
        raise RuntimeError("stationary residual too large")

    Nbar, pi, vbar = reward_metrics(lam, r, L, mF, q, beta_tail, phi_tail)
    return {
        "D": D, "r": r, "L": L, "mF_ms": mF, "rho": rho,
        "lambda_per_ms": lam, "lambda_sat_per_ms": lambda_sat,
        "rho_sat": rho_sat, "blocking_probability": pi,
        "mean_number": Nbar, "mean_delay_ms": vbar,
    }


def find_rho_for_pi(D, r, target, lo=0.0, hi=0.60):
    if target <= 0 or target >= 1:
        raise ValueError("target must lie in (0,1)")
    while analytic_metrics(D, r, hi)["blocking_probability"] < target:
        hi *= 1.5
        if hi > 5:
            raise RuntimeError("failed to bracket target blocking probability")
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        p = analytic_metrics(D, r, mid)["blocking_probability"]
        if p < target:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main():
    out = Path(__file__).resolve().parent / "phase4_output"
    out.mkdir(parents=True, exist_ok=True)

    # Canonical analytical self-check.
    expected = {
        0.5: (6.67728261876, 0.0),
        1.0: (74.49531061464, 0.016841175116),
        1.5: (141.29887947773, 1/3),
        2.0: (144.01521303749, 0.5),
    }
    _, _, _, rs = dect_mapping(10)
    for factor, (delay_ref, pi_ref) in expected.items():
        m = analytic_metrics(10, 30, factor * rs)
        if abs(m["mean_delay_ms"] - delay_ref) > 2e-6 or abs(m["blocking_probability"] - pi_ref) > 2e-8:
            raise RuntimeError(f"canonical self-check failed at factor={factor}: {m}")

    # Figure B: DECT operating-regime map.
    r_map = 30
    Ds = list(range(2, 25))
    rho_grid = np.linspace(0.0, 0.55, 151)
    map_rows = []
    Z = np.zeros((len(rho_grid), len(Ds)))
    for j, D in enumerate(Ds):
        L, mF, lams, rhos = dect_mapping(D)
        for i, rho in enumerate(rho_grid):
            pi = 0.0 if rho == 0 else analytic_metrics(D, r_map, float(rho))["blocking_probability"]
            Z[i, j] = pi
            map_rows.append({
                "D": D, "r": r_map, "L": L, "mF_ms": mF,
                "rho": float(rho), "rho_sat": rhos,
                "blocking_probability": pi,
            })
    write_csv(
        out / "phase4_operating_map.csv", map_rows,
        ["D","r","L","mF_ms","rho","rho_sat","blocking_probability"]
    )

    thresholds = [0.01, 0.05, 0.10, 0.50]
    threshold_rows = []
    threshold_curves = {t: [] for t in thresholds}
    rho_sat_curve = []
    for D in Ds:
        L, mF, lams, rhos = dect_mapping(D)
        row = {"D": D, "L": L, "mF_ms": mF, "lambda_sat_per_ms": lams, "rho_sat": rhos}
        rho_sat_curve.append(rhos)
        for t in thresholds:
            rt = find_rho_for_pi(D, r_map, t)
            row[f"rho_at_pi_{int(t*100):02d}pct"] = rt
            threshold_curves[t].append(rt)
        threshold_rows.append(row)
    write_csv(
        out / "phase4_blocking_thresholds.csv", threshold_rows,
        ["D","L","mF_ms","lambda_sat_per_ms","rho_sat"]
        + [f"rho_at_pi_{int(t*100):02d}pct" for t in thresholds]
    )

    x_edges = np.arange(1.5, 25.5, 1.0)
    dr = rho_grid[1] - rho_grid[0]
    y_edges = np.concatenate(([max(0.0, rho_grid[0]-dr/2)], rho_grid + dr/2))
    fig, ax = plt.subplots(figsize=(8.1, 5.2))
    mesh = ax.pcolormesh(x_edges, y_edges, Z, shading="flat", cmap="viridis", vmin=0.0, vmax=1.0)
    cbar = fig.colorbar(mesh, ax=ax, pad=0.02)
    cbar.set_label(r"Blocking probability $\pi$")
    for t in thresholds:
        ax.plot(
            Ds, threshold_curves[t], drawstyle="steps-mid", linewidth=1.35,
            label=fr"$\pi={int(t*100)}\%$"
        )
    ax.plot(
        Ds, rho_sat_curve, drawstyle="steps-mid", linestyle="--", linewidth=2.1,
        label=r"$\rho_{\mathrm{sat}}$"
    )
    ax.set_xlim(1.5, 24.5)
    ax.set_ylim(0.0, 0.55)
    ax.set_xticks([2,4,6,8,10,12,14,16,18,20,22,24])
    ax.set_xlabel(r"Number of PT devices $D$")
    ax.set_ylabel(r"Type-1 load $\rho$")
    ax.legend(loc="upper right", ncol=1, frameon=True, fontsize=8)
    ax.grid(False)
    fig.tight_layout()
    fig.savefig(out / "figure_B_operating_regime_map.pdf", bbox_inches="tight")
    fig.savefig(out / "figure_B_operating_regime_map.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Figure C: delay-loss trade-off.
    D_trade = 10
    _, _, _, rho_sat_trade = dect_mapping(D_trade)
    factors = [0.8, 1.0, 1.2]
    trade_rows = []
    trade = {}
    for factor in factors:
        rows = []
        for r in range(1, 51):
            m = analytic_metrics(D_trade, r, factor * rho_sat_trade)
            row = {
                "D": D_trade, "L": m["L"], "r": r,
                "rho_over_rho_sat": factor, "rho": m["rho"],
                "rho_sat": m["rho_sat"], "blocking_probability": m["blocking_probability"],
                "mean_delay_ms": m["mean_delay_ms"], "mean_number": m["mean_number"],
            }
            rows.append(row)
            trade_rows.append(row)
        trade[factor] = rows
    write_csv(
        out / "phase4_delay_loss_tradeoff.csv", trade_rows,
        ["D","L","r","rho_over_rho_sat","rho","rho_sat","blocking_probability","mean_delay_ms","mean_number"]
    )

    fig, ax = plt.subplots(figsize=(7.6, 5.1))
    colors = {0.8:"tab:blue", 1.0:"tab:orange", 1.2:"tab:green"}
    for factor in factors:
        rows = trade[factor]
        xs = [x["blocking_probability"] for x in rows]
        ys = [x["mean_delay_ms"] for x in rows]
        ax.plot(
            xs, ys, marker="o", markersize=2.6, linewidth=1.7,
            color=colors[factor], label=fr"$\\rho/\\rho_{{\\mathrm{{sat}}}}={factor:.1f}$"
        )

    # Sparse publication labels. Configurations with blocking below 1e-4
    # remain in the source CSV but are intentionally outside the displayed view.
    selected_by_factor = {
        0.8: [1, 5, 10, 15, 18],
        1.0: [1, 5, 10, 20, 30, 50],
        1.2: [1, 2, 5, 10, 20, 30, 50],
    }
    offsets = {
        (0.8, 18): (4, 6), (0.8, 15): (4, 6), (0.8, 10): (4, 6),
        (0.8, 5): (4, 6), (0.8, 1): (4, 6),
        (1.0, 50): (4, 6), (1.0, 30): (4, 6), (1.0, 20): (4, 6),
        (1.0, 10): (4, 6), (1.0, 5): (4, 6), (1.0, 1): (4, 6),
        (1.2, 50): (4, -12), (1.2, 30): (4, -8), (1.2, 20): (4, -8),
        (1.2, 10): (4, -8), (1.2, 5): (4, -8), (1.2, 2): (4, -10),
        (1.2, 1): (4, 6),
    }
    for factor, selected in selected_by_factor.items():
        rows_by_r = {x["r"]: x for x in trade[factor]}
        for r in selected:
            row = rows_by_r[r]
            x = row["blocking_probability"]
            if x < 1e-4 or x > 0.6:
                continue
            ax.annotate(
                str(r), (x, row["mean_delay_ms"]),
                xytext=offsets.get((factor, r), (4, 6)),
                textcoords="offset points", fontsize=7.5, color="black"
            )

    ax.set_xlabel(r"Blocking probability $\\pi$")
    ax.set_ylabel(r"Mean type-1 sojourn time $\\overline{v}$ [ms]")
    ax.set_xscale("log")
    ax.set_xlim(1e-4, 0.6)
    ax.set_ylim(0, 245)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.legend(loc="upper left", frameon=True)
    ax.grid(True, linewidth=0.4, alpha=0.35)
    fig.tight_layout()
    fig.savefig(out / "figure_C_delay_loss_tradeoff.pdf", bbox_inches="tight")
    fig.savefig(out / "figure_C_delay_loss_tradeoff.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    selected_D = [2, 6, 10, 13, 20, 24]
    sel = [row for row in threshold_rows if row["D"] in selected_D]
    write_csv(
        out / "phase4_selected_dimensioning.csv", sel,
        ["D","L","mF_ms","lambda_sat_per_ms","rho_sat",
         "rho_at_pi_01pct","rho_at_pi_05pct","rho_at_pi_10pct","rho_at_pi_50pct"]
    )

    lines = [
        "PHASE 4 ANALYTICAL DIMENSIONING",
        "===============================",
        f"Figure B: D=2..24, r={r_map}, rho in [0,0.55], blocking map and 1/5/10/50% contours.",
        "Figure C: D=10, r=1..50, normalized loads 0.8, 1.0, 1.2.",
        "",
        "Selected operating points (r=30):",
    ]
    for row in sel:
        lines.append(
            f"D={row['D']:2d}, L={row['L']:2d}, rho_sat={row['rho_sat']:.6f}, "
            f"rho(pi<=1%)={row['rho_at_pi_01pct']:.6f}, "
            f"rho(pi<=5%)={row['rho_at_pi_05pct']:.6f}, "
            f"rho(pi<=10%)={row['rho_at_pi_10pct']:.6f}"
        )
    (out / "phase4_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
