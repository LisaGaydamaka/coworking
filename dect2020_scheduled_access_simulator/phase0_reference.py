import math
import numpy as np

MU = 2.4
M_B = 1.0 / MU
F = 9.0

def exp_arrival_count(lam, mu, nmax):
    p = lam / (lam + mu)
    q = 1.0 - p
    probs = np.array([q * p**k for k in range(nmax + 1)], dtype=float)
    tails = np.array([p**k for k in range(nmax + 1)], dtype=float)
    return probs, tails

def det_arrival_count(lam, T, nmax):
    probs = np.zeros(nmax + 1, dtype=float)
    probs[0] = math.exp(-lam * T)
    for k in range(1, nmax + 1):
        probs[k] = probs[k-1] * lam * T / k
    tails = np.array([1.0 - probs[:k].sum() for k in range(nmax + 1)])
    return probs, tails

def states(r, L):
    return [(L, 0)] + [(l, k) for k in range(1, r + 1) for l in range(L + 1)]

def scalar_transition(r, L, beta, phi, beta_tail, phi_tail):
    S = states(r, L)
    I = {s: i for i, s in enumerate(S)}
    P = np.zeros((len(S), len(S)))
    for row, (l, k) in enumerate(S):
        if l == L:
            for j in range(k, r):
                a = j - k
                dest = (L, 0) if j == 0 else (0, j)
                P[row, I[dest]] += phi[a]
            dest = (L, 0) if r == 0 else (0, r)
            P[row, I[dest]] += phi_tail[r - k]
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
            j = r
            dest = (L, j) if l + 1 == L else (l + 1, j)
            P[row, I[dest]] += beta_tail[r - k + 1]
    return S, P

def block_transition(r, L, beta, phi, beta_tail, phi_tail):
    m = L + 1
    n = 1 + r * m
    P = np.zeros((n, n))
    def level_slice(k):
        a = 1 + (k - 1) * m
        return slice(a, a + m)
    def B(a, tail=False):
        x = beta_tail[a] if tail else beta[a]
        M = np.zeros((m, m))
        for l in range(L):
            M[l, l + 1] = x
        return M
    def FF(a, tail=False):
        x = phi_tail[a] if tail else phi[a]
        M = np.zeros((m, m))
        M[L, 0] = x
        return M

    P[0, 0] = phi[0]
    for k in range(1, r):
        row = np.zeros(m)
        row[0] = phi[k]
        P[0, level_slice(k)] = row
    row = np.zeros(m)
    row[0] = phi_tail[r]
    P[0, level_slice(r)] = row

    b0 = np.array([beta[0]] * L + [0.0])
    P[level_slice(1), 0] = b0

    for i in range(1, r + 1):
        if i > 1:
            P[level_slice(i), level_slice(i - 1)] += B(0)
        for j in range(i, r):
            s = j - i + 1
            P[level_slice(i), level_slice(j)] += B(s) + FF(s - 1)
        s = r - i + 1
        P[level_slice(i), level_slice(r)] += B(s, tail=True) + FF(s - 1, tail=True)
    return P

def stationary(P):
    A = P.T - np.eye(len(P))
    A[-1, :] = 1.0
    b = np.zeros(len(P))
    b[-1] = 1.0
    return np.linalg.solve(A, b)

def corrected_process_distribution(lam, r, L, mB, mF, q, beta_tail, phi_tail):
    m = L + 1
    qL = np.zeros(r + 1)
    qL[0] = q[0]
    q_type1 = np.zeros((L, r + 1))
    for k in range(1, r + 1):
        base = 1 + (k - 1) * m
        q_type1[:, k] = q[base:base + L]
        qL[k] = q[base + L]

    H = mF * qL.sum() + mB * q_type1.sum()
    pL = np.zeros(r + 1)
    p1 = np.zeros((L, r + 2))

    for j in range(r):
        pL[j] = sum(qL[k] * phi_tail[j - k + 1] for k in range(j + 1)) / (lam * H)

    for k in range(r + 1):
        h = r - k
        pre = sum(phi_tail[n + 1] for n in range(h)) / lam
        pL[r] += qL[k] * (mF - pre) / H

    for l in range(L):
        for j in range(1, r + 1):
            p1[l, j] = sum(
                q_type1[l, k] * beta_tail[j - k + 1]
                for k in range(1, j + 1)
            ) / (lam * H)
        for k in range(1, r + 1):
            h = r + 1 - k
            pre = sum(beta_tail[n + 1] for n in range(h)) / lam
            p1[l, r + 1] += q_type1[l, k] * (mB - pre) / H
    return H, pL, p1

def reward_metrics(lam, r, L, mB, mF, q, beta_tail, phi_tail):
    m = L + 1
    H = area = blocked = 0.0

    def interval_reward(k, capacity, mean_service, tail):
        free = capacity - k
        if free <= 0:
            return capacity * mean_service, lam * mean_service
        times = [tail[n + 1] / lam for n in range(free)]
        full_time = mean_service - sum(times)
        area = sum((k + n) * times[n] for n in range(free)) + capacity * full_time
        return area, lam * full_time

    for idx, prob in enumerate(q):
        if idx == 0:
            l, k = L, 0
        else:
            z = idx - 1
            k = z // m + 1
            l = z % m
        if l == L:
            T = mF
            A, B = interval_reward(k, r, mF, phi_tail)
        else:
            T = mB
            A, B = interval_reward(k, r + 1, mB, beta_tail)
        H += prob * T
        area += prob * A
        blocked += prob * B

    N = area / H
    pi = blocked / (lam * H)
    delay = N / (lam * (1 - pi))
    return H, N, pi, delay

def metrics_from_process(lam, r, pL, p1):
    total = pL.sum() + p1.sum()
    pi = pL[r] + p1[:, r + 1].sum()
    N = sum(j * pL[j] for j in range(r + 1))
    N += sum(j * p1[:, j].sum() for j in range(1, r + 2))
    delay = N / (lam * (1 - pi))
    return total, N, pi, delay

def audit_case(r, L, rho):
    lam = rho * MU
    nmax = r + 3
    beta, bt = exp_arrival_count(lam, MU, nmax)
    phi, pt = det_arrival_count(lam, F, nmax)

    S, Ps = scalar_transition(r, L, beta, phi, bt, pt)
    Pb = block_transition(r, L, beta, phi, bt, pt)

    q = stationary(Ps)
    H, pL, p1 = corrected_process_distribution(lam, r, L, M_B, F, q, bt, pt)
    p_total, N1, pi1, d1 = metrics_from_process(lam, r, pL, p1)
    H2, N2, pi2, d2 = reward_metrics(lam, r, L, M_B, F, q, bt, pt)

    return {
        "row_err": np.max(np.abs(Ps.sum(axis=1) - 1)),
        "min_p": Ps.min(),
        "block_diff": np.max(np.abs(Ps - Pb)),
        "stationary_resid": np.max(np.abs(q @ Ps - q)),
        "q_norm_err": abs(q.sum() - 1),
        "p_norm_err": abs(p_total - 1),
        "H_diff": abs(H - H2),
        "N_diff": abs(N1 - N2),
        "pi_diff": abs(pi1 - pi2),
        "delay_diff": abs(d1 - d2),
    }

def main():
    cases = [
        audit_case(r, L, rho)
        for r in [1, 2, 3, 5, 10, 30]
        for L in [1, 2, 4]
        for rho in [0.01, 0.05, 0.085, 0.12, 0.5, 2.0]
    ]

    checks = {
        "max row-sum error": max(c["row_err"] for c in cases),
        "minimum transition probability": min(c["min_p"] for c in cases),
        "max scalar-vs-block matrix difference": max(c["block_diff"] for c in cases),
        "max stationary residual": max(c["stationary_resid"] for c in cases),
        "max embedded normalization error": max(c["q_norm_err"] for c in cases),
        "max process normalization error": max(c["p_norm_err"] for c in cases),
        "max mean-sojourn-time identity error": max(c["H_diff"] for c in cases),
        "max mean-N cross-check difference": max(c["N_diff"] for c in cases),
        "max blocking cross-check difference": max(c["pi_diff"] for c in cases),
        "max delay cross-check difference": max(c["delay_diff"] for c in cases),
    }
    limits = {
        "max row-sum error": 1e-12,
        "minimum transition probability": -1e-14,
        "max scalar-vs-block matrix difference": 1e-12,
        "max stationary residual": 1e-10,
        "max embedded normalization error": 1e-12,
        "max process normalization error": 1e-10,
        "max mean-sojourn-time identity error": 1e-10,
        "max mean-N cross-check difference": 1e-10,
        "max blocking cross-check difference": 1e-10,
        "max delay cross-check difference": 1e-8,
    }

    passed = True
    lines = ["PHASE 0 MODEL AUDIT", "===================", f"Cases checked: {len(cases)}", ""]
    for name, value in checks.items():
        ok = value >= limits[name] if name == "minimum transition probability" else value <= limits[name]
        passed &= ok
        lines.append(f"{name}: {value:.3e}  [{'PASS' if ok else 'FAIL'}]")

    lambda_sat = 2 / (2 * M_B + F)
    rho_sat = lambda_sat * M_B
    lines += ["", "Baseline L=2 saturated capacity:",
              f"lambda_sat = {lambda_sat:.12f} packets/ms",
              f"rho_sat = {rho_sat:.12f}"]

    r, L, rho = 3, 2, 0.1
    lam = rho * MU
    beta, bt = exp_arrival_count(lam, MU, r + 3)
    phi, pt = det_arrival_count(lam, F, r + 3)
    S, P = scalar_transition(r, L, beta, phi, bt, pt)
    I = {s: i for i, s in enumerate(S)}
    lines += ["", "Boundary transition example (L=2,r=3,rho=0.1):"]
    for s in [(2,0),(2,2),(1,2),(0,1)]:
        row = P[I[s]]
        dest = [(S[j], row[j]) for j in range(len(S)) if row[j] > 1e-14]
        lines.append(f"{s} -> " + ", ".join(f"{d}:{p:.8f}" for d,p in dest))

    with open("phase0_audit_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    if not passed:
        raise SystemExit("Phase 0 audit failed")

if __name__ == "__main__":
    main()
