from pathlib import Path
import importlib.util
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "enri_mouse_neuroplasticity"
OUT = ROOT / "stage8_new"
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("enri_solve", BASE / "solve.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

from dynamic_qp import install as install_dynamic_qp
install_dynamic_qp(m)

REMOVED = {("run^24", "LPS^24"), ("MCC^24", "LPS^24")}
m.ORDER_PAIRS = [p for p in m.ORDER_PAIRS if p not in REMOVED]

fine = json.loads((ROOT / "fine_grid_summary.json").read_text(encoding="utf-8"))
sel = fine["selected"]
beta = float(sel["beta"])
lam = float(sel["lambda"])
C = float(sel["C"])
rho0 = float(m.SMOKE_RHO)

source = m.load_included_source()
long_raw = m.build_long_table(source)

# ----------------------------------------------------------------------
# Reference model: exact current Stage 7 configuration.
# ----------------------------------------------------------------------
final_std, base_prep = m.fit_transform_stage3(
    long_raw,
    fit_mouse_ids=None,
    random_state=m.IMPUTATION_SEED,
    sample_posterior=False,
)
errors = list(base_prep.get("errors", []))
states, xbar, state_stats = m.build_experimental_states(final_std)
errors.extend(m.validate_full_stage4(states, xbar, state_stats))

base_solution, base_meta = m.solve_qp_smoke(
    final_std, states, xbar,
    rho=rho0, beta=beta, ridge_lambda=lam, C=C,
)
errors.extend(base_meta.get("errors", []))
if base_solution is None:
    raise RuntimeError("Could not reconstruct current Stage 7 reference model: " + " | ".join(errors or ["unknown"]))

base_gamma = m._gamma_from_solution(base_solution, base_prep["scaling"])
base_enri = m.build_final_enri_table(final_std, xbar, base_solution["w"])

def treatment_diffs(solution):
    gm = solution["group_means"]
    return {
        "run24_minus_LPS24": float(gm["run^24"] - gm["LPS^24"]),
        "MCC24_minus_LPS24": float(gm["MCC^24"] - gm["LPS^24"]),
    }

base_treatment = treatment_diffs(base_solution)

# ----------------------------------------------------------------------
# 8A. Stability across the exact accepted CV splits.
# ----------------------------------------------------------------------
accepted, rejected = m.prepare_cv_splits(long_raw, source)
cv_rows = []
cv_gammas = []
cv_failures = []

for split in accepted:
    train_ids = set(split["train_ids"])
    train_df = split["final_std"][split["final_std"]["mouse_id"].isin(train_ids)].copy()
    sol, meta = m.solve_qp_smoke(
        train_df,
        split["train_states"],
        split["xbar_train"],
        rho=rho0, beta=beta, ridge_lambda=lam, C=C,
    )
    if sol is None or meta.get("errors"):
        cv_failures.append({
            "seed": int(split["seed"]),
            "fold": int(split["fold"]),
            "status": meta.get("status"),
            "errors": meta.get("errors", []),
        })
        continue
    gamma = m._gamma_from_solution(sol, split["prep_stats"]["scaling"])
    cv_gammas.append(gamma)
    td = treatment_diffs(sol)
    cv_rows.append({
        "seed": int(split["seed"]),
        "fold": int(split["fold"]),
        "gamma_cosine_to_final": m._safe_cosine(gamma, base_gamma),
        "gamma_sign_agreement_to_final": m._sign_agreement(gamma, base_gamma),
        "slack_sum": float(sol["slack_sum"]),
        "slack_max": float(sol["slack_max"]),
        "min_live_enri": float(sol["min_live_enri"]),
        **td,
    })

if cv_failures:
    errors.append(f"{len(cv_failures)} selected-hyperparameter CV stability fits failed")
if len(cv_rows) != len(accepted):
    errors.append(f"CV stability fits {len(cv_rows)} != accepted splits {len(accepted)}")

cv_feature_rows = []
if cv_gammas:
    cv_feature_rows = m._feature_stability(np.vstack(cv_gammas), base_gamma)

pairwise_cv = m._summary_quantiles(m._pairwise_cosines(cv_gammas)) if cv_gammas else m._summary_quantiles([])
cosine_to_final = m._summary_quantiles([r["gamma_cosine_to_final"] for r in cv_rows])
sign_to_final = m._summary_quantiles([r["gamma_sign_agreement_to_final"] for r in cv_rows])

def signed_summary(rows, key):
    vals = [float(r[key]) for r in rows]
    return {
        **m._summary_quantiles(vals),
        "positive_fraction": float(np.mean(np.asarray(vals) > 0)) if vals else float("nan"),
        "negative_fraction": float(np.mean(np.asarray(vals) < 0)) if vals else float("nan"),
    }

cv_treatment = {
    "run24_minus_LPS24": signed_summary(cv_rows, "run24_minus_LPS24"),
    "MCC24_minus_LPS24": signed_summary(cv_rows, "MCC24_minus_LPS24"),
}

pd.DataFrame(cv_rows).to_csv(OUT / "cv_stability.csv", index=False)
pd.DataFrame(cv_feature_rows).to_csv(OUT / "cv_feature_stability.csv", index=False)

# ----------------------------------------------------------------------
# 8B. Mouse-level complete-case sensitivity.
# ----------------------------------------------------------------------
cc_ids, cc_excluded, cc_definition_stats = m._complete_case_mouse_ids(long_raw)
cc_std_all, cc_prep = m.fit_transform_stage3(
    long_raw,
    fit_mouse_ids=cc_ids,
    random_state=m.IMPUTATION_SEED,
    sample_posterior=False,
)
cc_errors = list(cc_prep.get("errors", []))
cc_df = cc_std_all[cc_std_all["mouse_id"].isin(set(cc_ids))].copy()

if cc_df[~cc_df["death"] & ~cc_df["status"].eq("observed")].shape[0]:
    cc_errors.append("Complete-case subset contains a non-death row that is not observed")

cc_states, cc_xbar, cc_state_stats = m.build_experimental_states(
    cc_std_all,
    state_mouse_ids=cc_ids,
    reference_xbar=None,
)
cc_errors.extend(cc_state_stats.get("errors", []))
cc_solution, cc_meta = m.solve_qp_smoke(
    cc_df, cc_states, cc_xbar,
    rho=rho0, beta=beta, ridge_lambda=lam, C=C,
)
cc_errors.extend(cc_meta.get("errors", []))

complete_case = {
    "included_mice": int(len(cc_ids)),
    "excluded_mice": int(len(cc_excluded)),
    "excluded": cc_excluded,
}
if cc_solution is None or cc_errors:
    errors.append("Complete-case sensitivity failed: " + " | ".join(cc_errors or ["no solution"]))
    complete_case["errors"] = cc_errors or ["no solution"]
else:
    cc_gamma = m._gamma_from_solution(cc_solution, cc_prep["scaling"])
    cc_enri = m.build_final_enri_table(cc_df, cc_xbar, cc_solution["w"])
    cc_enri_cmp = m._compare_enri_tables(base_enri, cc_enri)
    cc_group_cmp = m._compare_group_means(base_solution, cc_solution)
    complete_case.update({
        "gamma_cosine": m._safe_cosine(base_gamma, cc_gamma),
        "sign_agreement": m._sign_agreement(base_gamma, cc_gamma),
        "living_rank_spearman": cc_enri_cmp["spearman"],
        "common_living_rows": cc_enri_cmp["common_living"],
        "individual_max_abs_diff": cc_enri_cmp["max_abs_diff"],
        "group_rank_spearman": cc_group_cmp["spearman"],
        "group_max_abs_diff": cc_group_cmp["max_abs_diff"],
        "slack_sum": float(cc_solution["slack_sum"]),
        "slack_max": float(cc_solution["slack_max"]),
        "min_live_enri": float(cc_solution["min_live_enri"]),
        **treatment_diffs(cc_solution),
    })

pd.DataFrame([{
    k: v for k, v in complete_case.items()
    if k not in {"excluded", "errors"}
}]).to_csv(OUT / "complete_case.csv", index=False)

# ----------------------------------------------------------------------
# 8C. rho sensitivity.
# ----------------------------------------------------------------------
rho_values = (0.05, 0.2, 0.3)
rho_rows = []
rho_summary = {}

for rho in rho_values:
    sol, meta = m.solve_qp_smoke(
        final_std, states, xbar,
        rho=float(rho), beta=beta, ridge_lambda=lam, C=C,
    )
    if sol is None or meta.get("errors"):
        msg = " | ".join(meta.get("errors", []) or ["no solution"])
        errors.append(f"rho={rho} sensitivity failed: {msg}")
        rho_summary[str(rho)] = {"errors": meta.get("errors", []) or ["no solution"]}
        continue
    gamma = m._gamma_from_solution(sol, base_prep["scaling"])
    enri = m.build_final_enri_table(final_std, xbar, sol["w"])
    enri_cmp = m._compare_enri_tables(base_enri, enri)
    group_cmp = m._compare_group_means(base_solution, sol)
    rec = {
        "rho": float(rho),
        "gamma_cosine": m._safe_cosine(base_gamma, gamma),
        "sign_agreement": m._sign_agreement(base_gamma, gamma),
        "living_rank_spearman": enri_cmp["spearman"],
        "individual_max_abs_diff": enri_cmp["max_abs_diff"],
        "group_rank_spearman": group_cmp["spearman"],
        "group_max_abs_diff": group_cmp["max_abs_diff"],
        "slack_sum": float(sol["slack_sum"]),
        "slack_max": float(sol["slack_max"]),
        "min_live_enri": float(sol["min_live_enri"]),
        "max_order_violation": float(sol["max_order_violation"]),
        "max_positivity_violation": float(sol["max_positivity_violation"]),
        **treatment_diffs(sol),
    }
    rho_rows.append(rec)
    rho_summary[str(rho)] = {k: v for k, v in rec.items() if k != "rho"}

pd.DataFrame(rho_rows).to_csv(OUT / "rho_sensitivity.csv", index=False)

# ----------------------------------------------------------------------
# 8D. Stochastic-imputation sensitivity.
# ----------------------------------------------------------------------
stochastic_rows = []
stochastic_invalid = []
stochastic_gammas = []

for seed in range(10):
    s_std, s_prep = m.fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=int(seed),
        sample_posterior=True,
    )
    run_errors = list(s_prep.get("errors", []))
    s_states = None
    s_xbar = None
    if not run_errors:
        s_states, s_xbar, s_state_stats = m.build_experimental_states(s_std)
        run_errors.extend(m.validate_full_stage4(s_states, s_xbar, s_state_stats))

    s_solution = None
    s_meta = {"status": "NOT_SOLVED", "errors": []}
    if not run_errors:
        s_solution, s_meta = m.solve_qp_smoke(
            s_std, s_states, s_xbar,
            rho=rho0, beta=beta, ridge_lambda=lam, C=C,
        )
        run_errors.extend(s_meta.get("errors", []))

    if s_solution is None or run_errors:
        stochastic_invalid.append({
            "seed": int(seed),
            "status": s_meta.get("status"),
            "errors": run_errors or ["no solution"],
        })
        continue

    gamma = m._gamma_from_solution(s_solution, s_prep["scaling"])
    stochastic_gammas.append(gamma)
    s_enri = m.build_final_enri_table(s_std, s_xbar, s_solution["w"])
    enri_cmp = m._compare_enri_tables(base_enri, s_enri)
    group_cmp = m._compare_group_means(base_solution, s_solution)
    stochastic_rows.append({
        "seed": int(seed),
        "gamma_cosine": m._safe_cosine(base_gamma, gamma),
        "sign_agreement": m._sign_agreement(base_gamma, gamma),
        "living_rank_spearman": enri_cmp["spearman"],
        "individual_max_abs_diff": enri_cmp["max_abs_diff"],
        "group_rank_spearman": group_cmp["spearman"],
        "group_max_abs_diff": group_cmp["max_abs_diff"],
        "slack_sum": float(s_solution["slack_sum"]),
        "slack_max": float(s_solution["slack_max"]),
        "min_live_enri": float(s_solution["min_live_enri"]),
        **treatment_diffs(s_solution),
    })

if not stochastic_rows:
    errors.append("No valid stochastic-imputation sensitivity runs")

pd.DataFrame(stochastic_rows).to_csv(OUT / "stochastic_imputation.csv", index=False)
pd.DataFrame([
    {"seed": x["seed"], "status": x["status"], "errors": json.dumps(x["errors"], ensure_ascii=False)}
    for x in stochastic_invalid
]).to_csv(OUT / "stochastic_imputation_invalid.csv", index=False)

stochastic_summary = {
    "requested_runs": 10,
    "valid_runs": int(len(stochastic_rows)),
    "invalid_runs": int(len(stochastic_invalid)),
}
for metric in (
    "gamma_cosine", "sign_agreement", "living_rank_spearman",
    "group_rank_spearman", "group_max_abs_diff", "slack_sum",
):
    stochastic_summary[metric] = m._summary_quantiles([x[metric] for x in stochastic_rows])

stochastic_summary["run24_minus_LPS24"] = signed_summary(stochastic_rows, "run24_minus_LPS24")
stochastic_summary["MCC24_minus_LPS24"] = signed_summary(stochastic_rows, "MCC24_minus_LPS24")

# ----------------------------------------------------------------------
# Summary and consistency checks.
# ----------------------------------------------------------------------
summary = {
    "stage": 8,
    "status": "READY" if not errors else "FATAL",
    "configuration": {
        "removed_order_pairs": [list(x) for x in sorted(REMOVED)],
        "remaining_order_pairs": [list(x) for x in m.ORDER_PAIRS],
        "beta": beta,
        "lambda": lam,
        "C": C,
        "rho": rho0,
    },
    "reference": {
        "weight_l2_norm": float(base_solution["weight_l2_norm"]),
        "weight_max_abs": float(base_solution["weight_max_abs"]),
        "slack_sum": float(base_solution["slack_sum"]),
        "min_live_enri": float(base_solution["min_live_enri"]),
        **base_treatment,
    },
    "cv_stability": {
        "accepted_splits": int(len(accepted)),
        "rejected_splits": int(len(rejected)),
        "successful_selected_fits": int(len(cv_rows)),
        "pairwise_gamma_cosine": pairwise_cv,
        "cosine_to_final": cosine_to_final,
        "sign_agreement_to_final": sign_to_final,
        "feature_final_sign_agreement": m._summary_quantiles(
            [r["final_sign_agreement"] for r in cv_feature_rows]
        ),
        "unconstrained_treatment_differences": cv_treatment,
    },
    "complete_case": complete_case,
    "rho_sensitivity": rho_summary,
    "stochastic_imputation": stochastic_summary,
    "invalid_stochastic_runs": stochastic_invalid,
    "validation_errors": errors,
    "outputs": {
        "cv_stability": "stage8_new/cv_stability.csv",
        "cv_feature_stability": "stage8_new/cv_feature_stability.csv",
        "complete_case": "stage8_new/complete_case.csv",
        "rho_sensitivity": "stage8_new/rho_sensitivity.csv",
        "stochastic_imputation": "stage8_new/stochastic_imputation.csv",
        "stochastic_invalid": "stage8_new/stochastic_imputation_invalid.csv",
    },
}
(OUT / "stage8_summary.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)

print("NO_TREATMENT_ORDER_STAGE8=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))
if errors:
    raise RuntimeError("Stage8 validation failed: " + " | ".join(errors))
