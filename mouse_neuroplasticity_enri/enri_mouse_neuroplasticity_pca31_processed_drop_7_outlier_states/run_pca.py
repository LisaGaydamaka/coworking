#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)

BASE = (
    ROOT.parent
    / "enri_mouse_neuroplasticity_feature_selection_all0mean_grip_longitudinal"
    / "solve_all0mean_grip_longitudinal.py"
)

LONGITUDINAL_PAIRS = [
    ("PBS", 0, 16),
    ("LPS", 0, 16),
    ("run", 0, 16),
    ("MCC", 0, 16),
    ("PBS", 16, 24),
    ("LPS", 16, 24),
]

EXCLUDED_STATES = {
    ("8.4", 16),
    ("8.2", 16),
    ("8.3", 16),
    ("9.2", 24),
    ("17.1", 24),
    ("21.4", 24),
    ("16.1", 24),
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reconstruct_processed_matrix(base):
    source = base.load_included_source()
    long_raw = base.build_long_table(source)
    final_std, prep = base.fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=base.IMPUTATION_SEED,
        sample_posterior=False,
    )
    errors = list(prep.get("errors", []))
    if errors:
        raise RuntimeError("Frozen preprocessing returned errors: " + " | ".join(errors))

    features = list(base.MODEL_FEATURES)
    if len(features) != 31:
        raise RuntimeError(f"Expected 31 MODEL_FEATURES, got {len(features)}")
    if features[-1] != "Grip":
        raise RuntimeError("Expected Grip as the 31st configured feature")

    keep = ["mouse_id", "group", "week", "status"] + features
    df = final_std[keep].copy()
    living = df["status"].isin(["observed", "imputed"]).copy()
    live = df.loc[living].reset_index(drop=True)

    excluded_mask = live.apply(
        lambda r: (str(r["mouse_id"]), int(r["week"])) in EXCLUDED_STATES,
        axis=1,
    )
    excluded = live.loc[excluded_mask, ["mouse_id", "group", "week", "status"] + features].copy()
    excluded.to_csv(OUT / "excluded_states.csv", index=False)
    live = live.loc[~excluded_mask].reset_index(drop=True)

    X = live[features].to_numpy(dtype=float)
    if not np.isfinite(X).all():
        bad = np.argwhere(~np.isfinite(X))
        raise RuntimeError(f"Living processed matrix contains non-finite values: {bad[:10].tolist()}")

    counts = live.groupby("week", observed=True).size().to_dict()
    expected = {0: 54, 16: 41, 24: 38}
    counts = {int(k): int(v) for k, v in counts.items()}
    if counts != expected:
        raise RuntimeError(f"Unexpected living row counts: {counts}, expected {expected}")

    live.to_csv(OUT / "processed_matrix_31_living.csv", index=False)
    return live, features, prep


def orient_pc1(scores: np.ndarray, components: np.ndarray, meta: pd.DataFrame):
    scores = scores.copy()
    components = components.copy()
    w0 = float(scores[meta["week"].to_numpy() == 0, 0].mean())
    w16 = float(scores[meta["week"].to_numpy() == 16, 0].mean())
    sign = 1
    if w0 < w16:
        scores[:, 0] *= -1.0
        components[0, :] *= -1.0
        sign = -1
    return scores, components, sign


def explained_variance_table(pca: PCA):
    evr = np.asarray(pca.explained_variance_ratio_, dtype=float)
    vals = np.asarray(pca.explained_variance_, dtype=float)
    out = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(len(evr))],
        "explained_variance": vals,
        "explained_variance_ratio": evr,
        "explained_variance_percent": 100.0 * evr,
        "cumulative_explained_variance_ratio": np.cumsum(evr),
        "cumulative_explained_variance_percent": 100.0 * np.cumsum(evr),
    })
    return out


def thresholds(evr):
    cum = np.cumsum(np.asarray(evr, dtype=float))
    result = {}
    for pct in [0.50, 0.70, 0.80, 0.90]:
        result[str(int(pct * 100))] = int(np.searchsorted(cum, pct) + 1)
    return result


def save_scree(evdf: pd.DataFrame, prefix: str, title: str):
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(1, len(evdf) + 1)
    ax.plot(x, evdf["explained_variance_percent"].to_numpy(), marker="o")
    ax.set_xlabel("Principal component")
    ax.set_ylabel("Explained variance (%)")
    ax.set_title(title)
    ax.set_xticks(x[::2] if len(x) > 15 else x)
    fig.tight_layout()
    fig.savefig(OUT / f"{prefix}_scree.png", dpi=180)
    plt.close(fig)


def save_loadings(loadings: pd.DataFrame, prefix: str, title: str):
    d = loadings.copy()
    d["abs_loading"] = d["PC1_loading"].abs()
    d = d.sort_values("abs_loading", ascending=True).tail(20)
    fig, ax = plt.subplots(figsize=(9, 7))
    ax.barh(d["feature"], d["PC1_loading"])
    ax.set_xlabel("PC1 loading")
    ax.set_title(title + " — 20 largest |loadings|")
    fig.tight_layout()
    fig.savefig(OUT / f"{prefix}_pc1_loadings.png", dpi=180)
    plt.close(fig)


def group_week_table(scores_df: pd.DataFrame, score_col: str, prefix: str):
    g = (
        scores_df.groupby(["group", "week"], observed=True)[score_col]
        .agg(["count", "mean", "std"])
        .reset_index()
    )
    g["sem"] = g["std"] / np.sqrt(g["count"])
    g.to_csv(OUT / f"{prefix}_pc1_group_week.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5))
    for group, sub in g.groupby("group", observed=True):
        sub = sub.sort_values("week")
        ax.plot(sub["week"], sub["mean"], marker="o", label=str(group))
    ax.set_xlabel("Week")
    ax.set_ylabel("Mean PC1 score")
    ax.set_title(f"{prefix.capitalize()} PCA: mean PC1 by group and week")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / f"{prefix}_pc1_group_week.png", dpi=180)
    plt.close(fig)
    return g


def longitudinal_checks(group_week: pd.DataFrame, prefix: str):
    lookup = {
        (str(r.group), int(r.week)): float(r.mean)
        for r in group_week.itertuples(index=False)
    }
    rows = []
    for group, wa, wb in LONGITUDINAL_PAIRS:
        a = lookup[(group, wa)]
        b = lookup[(group, wb)]
        rows.append({
            "group": group,
            "week_a": wa,
            "week_b": wb,
            "mean_PC1_a": a,
            "mean_PC1_b": b,
            "difference_a_minus_b": a - b,
            "relation_a_gt_b": bool(a > b),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"{prefix}_pc1_longitudinal_checks.csv", index=False)
    return out


def run_pca(live, features, fit_mask, prefix, title):
    X_all = live[features].to_numpy(dtype=float)
    X_fit = X_all[fit_mask]

    pca = PCA(n_components=min(X_fit.shape[0], X_fit.shape[1]), svd_solver="full")
    pca.fit(X_fit)
    scores = pca.transform(X_all)
    components = pca.components_.copy()

    scores, components, sign = orient_pc1(
        scores,
        components,
        live[["week"]].reset_index(drop=True),
    )

    evdf = explained_variance_table(pca)
    evdf.to_csv(OUT / f"{prefix}_explained_variance.csv", index=False)

    loadings = pd.DataFrame({
        "feature": features,
        "PC1_loading": components[0, :],
        "abs_PC1_loading": np.abs(components[0, :]),
    }).sort_values("abs_PC1_loading", ascending=False)
    loadings.to_csv(OUT / f"{prefix}_pc1_loadings.csv", index=False)

    scores_df = live[["mouse_id", "group", "week", "status"]].copy()
    for j in range(scores.shape[1]):
        scores_df[f"PC{j+1}"] = scores[:, j]
    scores_df.to_csv(OUT / f"{prefix}_scores.csv", index=False)

    gw = group_week_table(scores_df, "PC1", prefix)
    checks = longitudinal_checks(gw, prefix)

    save_scree(evdf, prefix, title)
    save_loadings(loadings, prefix, title)

    summary = {
        "fit_rows": int(X_fit.shape[0]),
        "projected_rows": int(X_all.shape[0]),
        "features": int(X_fit.shape[1]),
        "pc1_sign_multiplier": int(sign),
        "pc1_explained_variance_ratio": float(pca.explained_variance_ratio_[0]),
        "pc1_explained_variance_percent": float(100.0 * pca.explained_variance_ratio_[0]),
        "pc1_pc2_cumulative_percent": float(100.0 * pca.explained_variance_ratio_[:2].sum()),
        "pc1_pc3_cumulative_percent": float(100.0 * pca.explained_variance_ratio_[:3].sum()),
        "components_needed_for_cumulative_variance": thresholds(pca.explained_variance_ratio_),
        "longitudinal_relations_true": int(checks["relation_a_gt_b"].sum()),
        "longitudinal_relations_total": int(len(checks)),
        "top_10_abs_pc1_loadings": [
            {
                "feature": str(r.feature),
                "loading": float(r.PC1_loading),
                "abs_loading": float(r.abs_PC1_loading),
            }
            for r in loadings.head(10).itertuples(index=False)
        ],
    }
    return summary, scores_df


def write_report(summary):
    p = summary["pooled"]
    b = summary["baseline"]
    cmp = summary["comparison"]
    text = f"""# PCA31 on the processed eNRI feature matrix

## Input

The experiment uses the exact 31-feature processed matrix produced by the
frozen GRIP31 preprocessing pipeline. No second standardization is applied.
PCA performs only its ordinary mean-centering.

Living rows: {summary["data"]["living_rows"]}; week 0={summary["data"]["week_counts"]["0"]},
week 16={summary["data"]["week_counts"]["16"]}, week 24={summary["data"]["week_counts"]["24"]}.

## Pooled PCA

PC1 explained variance: **{p["pc1_explained_variance_percent"]:.2f}%**.

Cumulative variance:
- PC1+PC2: {p["pc1_pc2_cumulative_percent"]:.2f}%
- PC1+PC2+PC3: {p["pc1_pc3_cumulative_percent"]:.2f}%
- components for 50%: {p["components_needed_for_cumulative_variance"]["50"]}
- components for 70%: {p["components_needed_for_cumulative_variance"]["70"]}
- components for 80%: {p["components_needed_for_cumulative_variance"]["80"]}
- components for 90%: {p["components_needed_for_cumulative_variance"]["90"]}

After the global sign convention, {p["longitudinal_relations_true"]}/6 specified
longitudinal group-mean directions are observed descriptively. These relations
were not used to fit PCA.

## Baseline PCA → later projection

PC1 explained variance within week 0: **{b["pc1_explained_variance_percent"]:.2f}%**.

Cumulative variance:
- PC1+PC2: {b["pc1_pc2_cumulative_percent"]:.2f}%
- PC1+PC2+PC3: {b["pc1_pc3_cumulative_percent"]:.2f}%
- components for 50%: {b["components_needed_for_cumulative_variance"]["50"]}
- components for 70%: {b["components_needed_for_cumulative_variance"]["70"]}
- components for 80%: {b["components_needed_for_cumulative_variance"]["80"]}
- components for 90%: {b["components_needed_for_cumulative_variance"]["90"]}

Using the frozen week-0 PC1 direction, {b["longitudinal_relations_true"]}/6
longitudinal group-mean directions are observed descriptively.

## Relation between the two PC1 scores

Pearson correlation across the same living mouse×week rows:
**{cmp["pearson_r"]:.4f}**.

Spearman correlation:
**{cmp["spearman_rho"]:.4f}**.

The sign convention is presentation-only. Multiplying any PC by -1 does not
change explained variance or the PCA solution.
"""
    (OUT / "REPORT.md").write_text(text, encoding="utf-8")


def main():
    base = load_module(BASE, "pca31_frozen_longitudinal_base")
    live, features, prep = reconstruct_processed_matrix(base)

    pooled_mask = np.ones(len(live), dtype=bool)
    baseline_mask = live["week"].eq(0).to_numpy()

    pooled_summary, pooled_scores = run_pca(
        live, features, pooled_mask, "pooled", "Pooled PCA on processed 31-feature matrix"
    )
    baseline_summary, baseline_scores = run_pca(
        live, features, baseline_mask, "baseline", "Baseline PCA on processed 31-feature matrix"
    )

    pr = pearsonr(
        pooled_scores["PC1"].to_numpy(dtype=float),
        baseline_scores["PC1"].to_numpy(dtype=float),
    )
    sr = spearmanr(
        pooled_scores["PC1"].to_numpy(dtype=float),
        baseline_scores["PC1"].to_numpy(dtype=float),
    )

    summary = {
        "experiment": "PCA31_PROCESSED_LONGITUDINAL_DROP_7_OUTLIER_STATES",
        "data": {
            "analytic_mice": 54,
            "features": 31,
            "living_rows": int(len(live)),
            "week_counts": {
                str(int(k)): int(v)
                for k, v in live.groupby("week", observed=True).size().to_dict().items()
            },
            "repeated_standardization": False,
            "pca_centering": True,
            "dead_rows_in_pca": False,
            "excluded_states": [
                {"mouse_id": mouse_id, "week": week}
                for mouse_id, week in sorted(EXCLUDED_STATES)
            ],
            "group_used_for_pca_fit": False,
            "constraints_used_for_pca_fit": False,
        },
        "pooled": pooled_summary,
        "baseline": baseline_summary,
        "comparison": {
            "pearson_r": float(pr.statistic),
            "pearson_p": float(pr.pvalue),
            "spearman_rho": float(sr.statistic),
            "spearman_p": float(sr.pvalue),
        },
        "preprocessing_errors": list(prep.get("errors", [])),
    }

    (OUT / "PCA_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_report(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
