#!/usr/bin/env python3
"""
Base-model wrapper for the ALL0MEAN normalization experiment.

Only the normalization origin changes. At week 0, compute a mean feature
vector separately for PBS^0, LPS^0, run^0 and MCC^0, then average the four
state means with equal weight. Hence the arithmetic mean of the four week-0
state eNRI means is 1. Validation reuses the train-derived reference exactly.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np

_ORIGINAL = Path(__file__).resolve().parent / "solve.py"
_spec = importlib.util.spec_from_file_location("enri_original_all0mean_base", _ORIGINAL)
if _spec is None or _spec.loader is None:
    raise RuntimeError(f"Cannot import original base model from {_ORIGINAL}")
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

for _name in dir(_base):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_base, _name)

NORMALIZATION_MODE = "equal_mean_of_four_week0_states"
NORMALIZATION_STATE_LABELS = ("PBS^0", "LPS^0", "run^0", "MCC^0")


def build_experimental_states(final_std, state_mouse_ids=None, reference_xbar=None):
    if state_mouse_ids is None:
        subset = final_std.copy()
        scope = "all_included"
    else:
        ids = set(state_mouse_ids)
        subset = final_std[final_std["mouse_id"].isin(ids)].copy()
        scope = "mouse_subset"

    errors = []
    if subset.empty:
        return {}, None, {"scope": scope, "errors": ["State subset is empty."]}

    dup = subset[["mouse_id", "week"]].duplicated()
    if dup.any():
        errors.append("Duplicate mouse_id/week rows in state subset.")

    per_mouse_weeks = subset.groupby("mouse_id")["week"].nunique()
    bad_weeks = per_mouse_weeks[per_mouse_weeks.ne(3)]
    if len(bad_weeks):
        errors.append(
            "Some mice do not have exactly three state rows: "
            + _base.json.dumps(
                {str(k): int(v) for k, v in bad_weeks.items()},
                ensure_ascii=False,
            )
        )

    if reference_xbar is None:
        baseline_state_means = []
        for group in _base.STATE_GROUPS:
            rows0 = subset[
                subset["group"].eq(group)
                & subset["week"].eq(0)
                & subset["status"].isin(["observed", "imputed"])
            ]
            if rows0.empty:
                errors.append(
                    f"No living complete {group}^0 rows available for normalization reference."
                )
                continue
            baseline_state_means.append(
                rows0[_base.MODEL_FEATURES]
                .astype(float)
                .mean(axis=0)
                .to_numpy(dtype=float)
            )
        xbar = (
            np.mean(np.stack(baseline_state_means, axis=0), axis=0)
            if len(baseline_state_means) == len(_base.STATE_GROUPS)
            else None
        )
    else:
        xbar = np.asarray(reference_xbar, dtype=float)

    if xbar is not None:
        if xbar.shape != (len(_base.MODEL_FEATURES),):
            errors.append(
                f"xbar_all0 has shape {xbar.shape}; expected {(len(_base.MODEL_FEATURES),)}."
            )
        elif not np.isfinite(xbar).all():
            errors.append("xbar_all0 contains non-finite values.")

    states = {}
    for group in _base.STATE_GROUPS:
        group_mice = sorted(
            subset.loc[subset["group"].eq(group), "mouse_id"].unique()
        )
        N_group = len(group_mice)

        for week in _base.STATE_WEEKS:
            label = _base.state_label(group, week)
            rows = subset[
                subset["group"].eq(group) & subset["week"].eq(week)
            ].copy()

            if len(rows) != N_group:
                errors.append(
                    f"{label}: expected one row for each of {N_group} group mice, got {len(rows)}."
                )

            R = rows[rows["status"].eq("observed")]
            I = rows[rows["status"].eq("imputed")]
            D = rows[rows["status"].eq("death")]
            U = rows[rows["status"].eq("missing_visit")]
            O = rows[rows["status"].isin(["observed", "imputed"])]

            N_A = N_group
            counts = {
                "N": int(N_A),
                "R": int(len(R)),
                "I": int(len(I)),
                "O": int(len(O)),
                "D": int(len(D)),
                "U": int(len(U)),
            }

            if counts["R"] + counts["I"] != counts["O"]:
                errors.append(f"{label}: R+I != O.")
            if counts["O"] + counts["D"] + counts["U"] != N_A:
                errors.append(
                    f"{label}: O+D+U={counts['O'] + counts['D'] + counts['U']} != N={N_A}."
                )

            if len(O):
                X = O[_base.MODEL_FEATURES].to_numpy(dtype=float)
                if not np.isfinite(X).all():
                    errors.append(f"{label}: O_A contains non-finite model values.")
            else:
                X = np.empty((0, len(_base.MODEL_FEATURES)), dtype=float)
                errors.append(f"{label}: O_A is empty.")

            if xbar is None or N_A == 0:
                a_A = np.nan
                b_A = np.full(len(_base.MODEL_FEATURES), np.nan)
            else:
                a_A = float(len(O) / N_A)
                b_A = (
                    (X - xbar).sum(axis=0) / N_A
                    if len(O)
                    else np.zeros(len(_base.MODEL_FEATURES))
                )

            if len(O) >= 2:
                S_A = np.cov(X, rowvar=False, ddof=1)
            else:
                S_A = np.full(
                    (len(_base.MODEL_FEATURES), len(_base.MODEL_FEATURES)),
                    np.nan,
                )
                errors.append(
                    f"{label}: fewer than 2 living complete observations for covariance."
                )

            finite_cov = bool(np.isfinite(S_A).all())
            symmetry_error = (
                float(np.max(np.abs(S_A - S_A.T)))
                if finite_cov
                else float("nan")
            )
            if finite_cov:
                S_sym = 0.5 * (S_A + S_A.T)
                eigvals = np.linalg.eigvalsh(S_sym)
                min_eig = float(eigvals.min())
                rank = int(np.linalg.matrix_rank(S_sym, tol=1e-10))
                trace = float(np.trace(S_sym))
            else:
                min_eig = float("nan")
                rank = 0
                trace = float("nan")

            states[label] = {
                **counts,
                "a": a_A,
                "b": b_A,
                "S": S_A,
                "covariance_finite": finite_cov,
                "covariance_symmetry_error": symmetry_error,
                "covariance_min_eigenvalue": min_eig,
                "covariance_rank": rank,
                "covariance_trace": trace,
            }

    return states, xbar, {
        "scope": scope,
        "normalization_mode": NORMALIZATION_MODE,
        "normalization_states": list(NORMALIZATION_STATE_LABELS),
        "errors": errors,
    }


def validate_full_stage4(states, xbar, stats):
    errors = list(stats["errors"])

    expected_state_labels = {
        _base.state_label(g, w)
        for g in _base.STATE_GROUPS
        for w in _base.STATE_WEEKS
    }
    if set(states) != expected_state_labels:
        errors.append(
            "State label set mismatch: "
            + _base.json.dumps(sorted(set(states) ^ expected_state_labels))
        )
    if len(states) != 12:
        errors.append(f"Expected 12 states, got {len(states)}.")

    expected_alive_by_week = {
        0: _base.EXPECTED_GROUP_COUNTS,
        16: _base.EXPECTED_ALIVE[16],
        24: _base.EXPECTED_ALIVE[24],
    }
    expected_death_by_week = {
        0: {g: 0 for g in _base.STATE_GROUPS},
        16: _base.EXPECTED_DEATH[16],
        24: _base.EXPECTED_DEATH[24],
    }

    for group in _base.STATE_GROUPS:
        for week in _base.STATE_WEEKS:
            label = _base.state_label(group, week)
            if label not in states:
                continue
            st = states[label]
            if st["N"] != _base.EXPECTED_GROUP_COUNTS[group]:
                errors.append(
                    f"{label}: N={st['N']}, expected {_base.EXPECTED_GROUP_COUNTS[group]}."
                )
            if st["O"] != expected_alive_by_week[week][group]:
                errors.append(
                    f"{label}: O={st['O']}, expected alive={expected_alive_by_week[week][group]}."
                )
            if st["D"] != expected_death_by_week[week][group]:
                errors.append(
                    f"{label}: D={st['D']}, expected death={expected_death_by_week[week][group]}."
                )
            if st["U"] != 0:
                errors.append(f"{label}: U={st['U']} but full model requires U=0.")
            if not math.isclose(
                st["a"], st["O"] / st["N"], rel_tol=0, abs_tol=1e-12
            ):
                errors.append(f"{label}: a_A != O_A/N_A.")

    if xbar is None:
        errors.append("xbar_all0 is missing.")
    else:
        baseline_b = np.stack(
            [np.asarray(states[f"{g}^0"]["b"], dtype=float)
             for g in _base.STATE_GROUPS],
            axis=0,
        )
        max_abs_mean_b = float(np.max(np.abs(baseline_b.mean(axis=0))))
        if max_abs_mean_b > 1e-10:
            errors.append(
                "Equal-state week-0 centering failed: "
                f"max abs mean baseline b={max_abs_mean_b}."
            )

    return errors


_base.build_experimental_states = build_experimental_states
_base.validate_full_stage4 = validate_full_stage4

MODEL_FEATURES = _base.MODEL_FEATURES
BASE_FEATURES = _base.BASE_FEATURES
