#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import cvxpy as cp
from openpyxl.utils import get_column_letter

from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge
from sklearn.model_selection import StratifiedKFold


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "Данные по мышам.xlsx"
RESULTS_DIR = ROOT / "results"
EXCLUDED_MOUSE_IDS = {"3.2", "4.2"}

GROUP_MAP = {
    "PBS": "PBS",
    "LPS": "LPS",
    "LPS+run": "run",
    "LPS+MCC": "MCC",
}
EXPECTED_GROUP_COUNTS = {"PBS": 11, "LPS": 14, "run": 15, "MCC": 14}
EXPECTED_ALIVE = {
    16: {"PBS": 9, "LPS": 12, "run": 12, "MCC": 11},
    24: {"PBS": 8, "LPS": 11, "run": 12, "MCC": 11},
}
EXPECTED_DEATH = {
    16: {"PBS": 2, "LPS": 2, "run": 3, "MCC": 3},
    24: {"PBS": 3, "LPS": 3, "run": 3, "MCC": 3},
}

FEATURE_COLUMNS = {
    "OFT_distance": {
        0: "OFT_distance_0", 16: "OFT_distance_16", 24: "OFT_distance_24",
    },
    "Average_speed_OFT": {
        0: "Average speed_OFT_0", 16: "Averag_speed_OFT_16", 24: "Averag_speed_OFT_24",
    },
    "Total_time_mobile_OFT": {
        0: "Total time mobile_OFT_0", 16: "Total_time_mobile_OFT_16", 24: "Total_time_mobile_OFT_24",
    },
    "Absolute_turn_angle_OFT": {
        0: "Absolute turn angle_OFT_0", 16: "Absolute_turn_angle_OFT_16", 24: "Absolute_turn_angle_OFT_24",
    },
    "Time_inCenter_OFT": {
        0: "Time in the Center zone _OFT_0", 16: "Time_inCenter_OFT_16", 24: "Time_inCenter_OFT_24",
    },
    "Total_distance_travelled_NOR1": {
        0: "Total distance travelled _NOR1_0", 16: "Total distance travelled _NOR1_16", 24: "Total distance travelled _NOR1_24",
    },
    "Average_speed_NOR1": {
        0: "Average speed _NOR1_0", 16: "Average speed _NOR1_16", 24: "Average speed _NOR1_24",
    },
    "Time_investigating_Piramidka_NOR1": {
        0: "Time investigating the Piramidka _NOR1_0", 16: "Time investigating Piramidka _NOR1_16", 24: "Time investigating Piramidka _NOR1_24",
    },
    "Latency_to_first_investigation_Piramidka_NOR1": {
        0: "Latency to first investigation of the Piramidka _NOR1_0", 16: "Latency to first investigation of Piramidka _NOR1_16", 24: "Latency to first investigation of Piramidka _NOR1_24",
    },
    "Time_investigating_Stakan_NOR1": {
        0: "Time investigating the Stakan_NOR1_0", 16: "Time investigating the Stakan_NOR1_16", 24: "Time investigating the Stakan_NOR1_24",
    },
    "Latency_to_first_investigation_Stakan_NOR1": {
        0: "Latency to first investigation of the Stakan _NOR1_0", 16: "Latency to first investigation of Stakan _NOR1_16", 24: "Latency to first investigation of Stakan _NOR1_24",
    },
    "Latency_to_first_investigation_NOR1": {
        0: "Latency to firs investigation _NOR1_0", 16: "Latency to firs investigation_NOR1_16", 24: "Latency to firs investigation_NOR1_24",
    },
    "Total_time_investigating_NOR1": {
        0: "Total time investigating _NOR1_0", 16: "Total time investigating_NOR1_16", 24: "Total time investigating_NOR1_24",
    },
    "Total_distance_travelled_NOR2": {
        0: "Total distance travelled _NOR2_0", 16: "Total distance travelled _NOR2_16", 24: "Total distance travelled _NOR2_24",
    },
    "Average_speed_NOR2": {
        0: "Average speed _NOR2_0", 16: "Average speed _NOR2_16", 24: "Average speed _NOR2_24",
    },
    "Time_investigating_Piramidka_zone_NOR2": {
        0: "Time investigating the Piramidka zone _NOR2_0", 16: "Time investigating the Piramidka zone _NOR2_16", 24: "Time investigating the Piramidka zone _NOR2_24",
    },
    "Latency_to_first_investigation_Piramidka_zone_NOR2": {
        0: "Latency to first investigation of the Piramidka zone _NOR2_0", 16: "Latency to first investigation of the Piramidka zone _NOR2_16", 24: "Latency to first investigation of the Piramidka zone _NOR2_24",
    },
    "Time_investigating_Stakan_zone_NOR2": {
        0: "Time investigating the Stakan zone _NOR2_0", 16: "Time investigating the Stakan zone _NOR2_16", 24: "Time investigating the Stakan zone _NOR2_24",
    },
    "Latency_to_first_investigation_Stakan_zone_NOR2": {
        0: "Latency to first investigation of the Stakan zone _NOR2_0", 16: "Latency to first investigation of the Stakan zone _NOR2_16", 24: "Latency to first investigation of the Stakan zone _NOR2_24",
    },
    "DI_NOR2": {
        0: "DI _NOR2_0", 16: "DI_NOR2_16", 24: "DI_NOR2_24",
    },
    "Latency_to_first_investigation_NOR2": {
        0: "Latency to firs investigation_NOR2_0", 16: "Latency to firs investigation_NOR2_16", 24: "Latency to firs investigation_NOR2_24",
    },
    "Total_time_investigating_NOR2": {
        0: "Total time investigating_NOR2_0", 16: "Total time investigating_NOR2_16", 24: "Total time investigating_NOR2_24",
    },
    "Learning_T1mean": {
        0: "Learning T1mean_0", 16: "Learning T1mean_16", 24: "Learning T1mean_24",
    },
    "Learning_T1max": {
        0: "Learning T1max_0", 16: "Learning T1max_16", 24: "Learning T1max_24",
    },
    "Learning_T1sum": {
        0: "Learning T1sum_0", 16: "Learning T1sum_16", 24: "Learning T1sum_24",
    },
    "Learning_T2mean": {
        0: "Learning T2mean_0", 16: "Learning T2mean_16", 24: "Learning T2mean_24",
    },
    "Learning_T2max": {
        0: "Learning T2max_0", 16: "Learning T2max_16", 24: "Learning T2max_24",
    },
    "Learning_T2sum": {
        0: "Learning T2sum_0", 16: "Learning T2sum_16", 24: "Learning T2sum_24",
    },
    "Learning_T3mean": {
        0: "Learning T3mean_0", 16: "Learning T3mean_16", 24: "Learning T3mean_24",
    },
    "Learning_T3max": {
        0: "Learning T3max_0", 16: "Learning T3max_16", 24: "Learning T3max_24",
    },
    "Learning_T3sum": {
        0: "Learning T3sum_0", 16: "Learning T3sum_16", 24: "Learning T3sum_24",
    },
    "EnduranceT": {
        0: "EnduranceT_0", 16: "EnduranceT_16", 24: "EnduranceT_24",
    },
    "rear_support": {
        0: "rear_support_0", 16: "rear_support_16", 24: "rear_support_24",
    },
    "rear_nosupport": {
        0: "rear_nosupport_0", 16: "rear_nosupport_16", 24: "rear_nosupport_24",
    },
    "Weight": {
        0: "Weight_0", 16: "Weight_16", 24: "Weight_24",
    },
}

NOR_TIME_LATENCY_PAIRS = {
    "NOR1_Piramidka": {
        0: ("Time investigating the Piramidka _NOR1_0", "Latency to first investigation of the Piramidka _NOR1_0"),
        16: ("Time investigating Piramidka _NOR1_16", "Latency to first investigation of Piramidka _NOR1_16"),
        24: ("Time investigating Piramidka _NOR1_24", "Latency to first investigation of Piramidka _NOR1_24"),
    },
    "NOR1_Stakan": {
        0: ("Time investigating the Stakan_NOR1_0", "Latency to first investigation of the Stakan _NOR1_0"),
        16: ("Time investigating the Stakan_NOR1_16", "Latency to first investigation of Stakan _NOR1_16"),
        24: ("Time investigating the Stakan_NOR1_24", "Latency to first investigation of Stakan _NOR1_24"),
    },
    "NOR2_Piramidka": {
        0: ("Time investigating the Piramidka zone _NOR2_0", "Latency to first investigation of the Piramidka zone _NOR2_0"),
        16: ("Time investigating the Piramidka zone _NOR2_16", "Latency to first investigation of the Piramidka zone _NOR2_16"),
        24: ("Time investigating the Piramidka zone _NOR2_24", "Latency to first investigation of the Piramidka zone _NOR2_24"),
    },
    "NOR2_Stakan": {
        0: ("Time investigating the Stakan zone _NOR2_0", "Latency to first investigation of the Stakan zone _NOR2_0"),
        16: ("Time investigating the Stakan zone _NOR2_16", "Latency to first investigation of the Stakan zone _NOR2_16"),
        24: ("Time investigating the Stakan zone _NOR2_24", "Latency to first investigation of the Stakan zone _NOR2_24"),
    },
}

ACCEPTED_SCALE_VALUES = {
    ("8.2", 16, "Average_speed_NOR1"),
    ("8.3", 16, "Average_speed_NOR1"),
    ("8.4", 16, "Average_speed_NOR1"),
    ("9.2", 24, "OFT_distance"),
    ("16.1", 24, "OFT_distance"),
    ("17.1", 24, "OFT_distance"),
    ("21.1", 24, "OFT_distance"),
    ("21.4", 24, "OFT_distance"),
}


def norm_id(value):
    if pd.isna(value):
        return ""
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def is_dead(series):
    return series.fillna("").astype(str).str.strip().eq("Dead")


def excel_cell(df, row_idx, column_name):
    col_num = list(df.columns).index(column_name) + 1
    excel_row = int(row_idx) + 3
    return f"{get_column_letter(col_num)}{excel_row}"


def add_diag(rows, severity, check, detail, **kwargs):
    row = {
        "type": "qc",
        "severity": severity,
        "check": check,
        "mouse_id": "",
        "group": "",
        "week": "",
        "feature": "",
        "column": "",
        "excel_cell": "",
        "value": "",
        "detail": detail,
    }
    row.update(kwargs)
    rows.append(row)


def run_stage1():
    if not DATA_FILE.exists():
        raise FileNotFoundError(DATA_FILE)

    df = pd.read_excel(DATA_FILE, sheet_name="Лист1", header=1)
    df = df[df["Animal"].notna()].copy()
    df["mouse_id"] = df["Animal"].map(norm_id)

    diagnostics = []
    fatal_errors = []

    required = {"Group_16", "Group_24", "Animal", "CFP_16", "CFP_24"}
    for wm in FEATURE_COLUMNS.values():
        required.update(wm.values())
    missing_cols = sorted(required - set(df.columns))
    if missing_cols:
        fatal_errors.append(f"Missing required columns: {missing_cols}")
    else:
        add_diag(diagnostics, "ok", "required_columns", "All required columns are present.")

    duplicated = sorted(df.loc[df["mouse_id"].duplicated(keep=False), "mouse_id"].unique())
    if duplicated:
        fatal_errors.append(f"Duplicated mouse IDs: {duplicated}")
    else:
        add_diag(diagnostics, "ok", "unique_ids", f"{len(df)} unique mouse IDs before exclusions.")

    missing_excluded = sorted(EXCLUDED_MOUSE_IDS - set(df["mouse_id"]))
    if missing_excluded:
        fatal_errors.append(f"Excluded mouse IDs not found: {missing_excluded}")

    included = df[~df["mouse_id"].isin(EXCLUDED_MOUSE_IDS)].copy()
    if len(included) != 54:
        fatal_errors.append(f"Expected 54 included mice, got {len(included)}.")
    else:
        add_diag(diagnostics, "ok", "included_mouse_count", "54 mice after excluding 3.2 and 4.2.", value=54)

    included["group"] = included["Group_24"].map(GROUP_MAP)
    bad_group = included[included["group"].isna()]
    if len(bad_group):
        fatal_errors.append(
            "Unmapped Group_24 values: "
            + repr(sorted(bad_group["Group_24"].astype(str).unique()))
        )

    group_counts = included["group"].value_counts().to_dict()
    for group, expected in EXPECTED_GROUP_COUNTS.items():
        actual = int(group_counts.get(group, 0))
        sev = "ok" if actual == expected else "fatal"
        add_diag(
            diagnostics, sev, "group_count",
            f"{group}: expected {expected}, got {actual}.",
            group=group, value=actual,
        )
        if actual != expected:
            fatal_errors.append(f"Group {group}: expected {expected}, got {actual}.")

    expected_group16 = included["group"].map(
        {"PBS": "PBS", "LPS": "LPS", "run": "LPS", "MCC": "LPS"}
    )
    actual_group16 = included["Group_16"].fillna("").astype(str).str.strip()
    mismatch = included[actual_group16.ne(expected_group16)]
    if len(mismatch):
        for idx, row in mismatch.iterrows():
            add_diag(
                diagnostics, "fatal", "group16_consistency",
                f"Expected Group_16={expected_group16.loc[idx]!r}, got {row['Group_16']!r}.",
                mouse_id=row["mouse_id"], group=row["group"],
                column="Group_16", excel_cell=excel_cell(df, idx, "Group_16"),
                value=row["Group_16"],
            )
        fatal_errors.append(f"{len(mismatch)} Group_16 inconsistencies.")
    else:
        add_diag(diagnostics, "ok", "group16_consistency", "Group_16 matches exposure interpretation for all 54 mice.")

    included["dead16"] = is_dead(included["CFP_16"])
    included["dead24"] = is_dead(included["CFP_24"])

    nonmono = included[included["dead16"] & ~included["dead24"]]
    if len(nonmono):
        fatal_errors.append(
            "Death is not monotone for: "
            + ", ".join(nonmono["mouse_id"].tolist())
        )
    else:
        add_diag(diagnostics, "ok", "death_monotonicity", "All CFP_16=Dead mice are also CFP_24=Dead.")

    for week in (16, 24):
        dead_col = f"dead{week}"
        for group in EXPECTED_GROUP_COUNTS:
            sub = included[included["group"].eq(group)]
            deaths = int(sub[dead_col].sum())
            alive = int((~sub[dead_col]).sum())
            exp_d = EXPECTED_DEATH[week][group]
            exp_a = EXPECTED_ALIVE[week][group]
            ok = deaths == exp_d and alive == exp_a
            add_diag(
                diagnostics, "ok" if ok else "fatal", "alive_death_count",
                f"week {week}, {group}: alive={alive} (expected {exp_a}), death={deaths} (expected {exp_d}).",
                group=group, week=week, value=f"{alive}/{deaths}",
            )
            if not ok:
                fatal_errors.append(
                    f"week {week} {group}: alive/death {alive}/{deaths}, expected {exp_a}/{exp_d}."
                )

    # Empty CFP is explicitly not death; record cases for audit.
    for week in (16, 24):
        cfp = f"CFP_{week}"
        empty = included[cfp].isna() | included[cfp].astype(str).str.strip().eq("")
        for idx, row in included[empty].iterrows():
            add_diag(
                diagnostics, "info", "empty_cfp_not_death",
                "Empty CFP is treated as alive unless CFP explicitly equals Dead.",
                mouse_id=row["mouse_id"], group=row["group"], week=week,
                column=cfp, excel_cell=excel_cell(df, idx, cfp),
            )

    # Validate numeric values and physical bounds for model features.
    numeric = {}
    for feature, wm in FEATURE_COLUMNS.items():
        numeric[feature] = {}
        for week, col in wm.items():
            raw = included[col]
            vals = pd.to_numeric(raw, errors="coerce")
            numeric[feature][week] = vals
            nonblank = raw.notna() & raw.astype(str).str.strip().ne("")
            bad_numeric = nonblank & vals.isna()
            for idx, row in included[bad_numeric].iterrows():
                add_diag(
                    diagnostics, "fatal", "nonnumeric_model_value",
                    "Model feature contains a nonnumeric nonblank value.",
                    mouse_id=row["mouse_id"], group=row["group"], week=week,
                    feature=feature, column=col, excel_cell=excel_cell(df, idx, col),
                    value=row[col],
                )
                fatal_errors.append(f"Nonnumeric {feature} week {week} for {row['mouse_id']}.")

            dead_mask = pd.Series(False, index=included.index)
            if week == 16:
                dead_mask = included["dead16"]
            elif week == 24:
                dead_mask = included["dead24"]
            alive_vals = vals[~dead_mask & vals.notna()]

            if feature == "DI_NOR2":
                bad = (~dead_mask) & vals.notna() & ((vals < -1) | (vals > 1))
                for idx, row in included[bad].iterrows():
                    add_diag(
                        diagnostics, "fatal", "di_bounds",
                        "DI outside [-1,1].",
                        mouse_id=row["mouse_id"], group=row["group"], week=week,
                        feature=feature, column=col, excel_cell=excel_cell(df, idx, col),
                        value=float(vals.loc[idx]),
                    )
                    fatal_errors.append(f"DI out of bounds for {row['mouse_id']} week {week}.")
            else:
                bad = (~dead_mask) & vals.notna() & (vals < 0)
                for idx, row in included[bad].iterrows():
                    add_diag(
                        diagnostics, "fatal", "negative_model_value",
                        "Feature expected to be nonnegative is negative.",
                        mouse_id=row["mouse_id"], group=row["group"], week=week,
                        feature=feature, column=col, excel_cell=excel_cell(df, idx, col),
                        value=float(vals.loc[idx]),
                    )
                    fatal_errors.append(f"Negative {feature} for {row['mouse_id']} week {week}.")

            if len(alive_vals):
                med = float(alive_vals.median())
                mad = float((alive_vals - med).abs().median())
                if math.isfinite(mad) and mad > 0:
                    out = (~dead_mask) & vals.notna() & ((vals - med).abs() > 10 * mad)
                    for idx, row in included[out].iterrows():
                        key = (row["mouse_id"], week, feature)
                        if key in ACCEPTED_SCALE_VALUES:
                            severity = "accepted"
                            check = "accepted_scale_value"
                            detail = (
                                f"|x-median| > 10*MAD; median={med:.8g}, MAD={mad:.8g}. "
                                "Reviewed by user and accepted as correct source data; retained unchanged."
                            )
                        else:
                            severity = "review"
                            check = "scale_outlier"
                            detail = f"|x-median| > 10*MAD; median={med:.8g}, MAD={mad:.8g}."
                        add_diag(
                            diagnostics, severity, check, detail,
                            mouse_id=row["mouse_id"], group=row["group"], week=week,
                            feature=feature, column=col, excel_cell=excel_cell(df, idx, col),
                            value=float(vals.loc[idx]),
                        )

    # Missingness among living observations.
    max_missing = 0
    fully_missing_living = []
    for idx, row in included.iterrows():
        for week in (0, 16, 24):
            if week == 16 and row["dead16"]:
                continue
            if week == 24 and row["dead24"]:
                continue
            vals = [
                pd.to_numeric(pd.Series([row[FEATURE_COLUMNS[f][week]]]), errors="coerce").iloc[0]
                for f in MODEL_FEATURES
            ]
            missing = int(pd.isna(vals).sum())
            max_missing = max(max_missing, missing)
            if missing == len(MODEL_FEATURES):
                fully_missing_living.append((row["mouse_id"], week))
    add_diag(
        diagnostics, "ok" if not fully_missing_living else "blocker",
        "living_visit_missingness",
        f"Maximum missing among living visits: {max_missing}/30 model features; fully missing model vectors: {len(fully_missing_living)}.",
        value=max_missing,
    )
    for mid, week in fully_missing_living:
        add_diag(
            diagnostics, "blocker", "fully_missing_living_visit",
            "Living visit has all 30 model features missing.",
            mouse_id=mid, week=week,
        )

    # Structural NOR censoring: Time=0 while corresponding latency is missing.
    structural_count = 0
    for label, wm in NOR_TIME_LATENCY_PAIRS.items():
        for week, (time_col, lat_col) in wm.items():
            time_vals = pd.to_numeric(included[time_col], errors="coerce")
            lat_vals = pd.to_numeric(included[lat_col], errors="coerce")
            dead_mask = pd.Series(False, index=included.index)
            if week == 16:
                dead_mask = included["dead16"]
            elif week == 24:
                dead_mask = included["dead24"]
            mask = (~dead_mask) & time_vals.eq(0) & lat_vals.isna()
            for idx, row in included[mask].iterrows():
                structural_count += 1
                add_diag(
                    diagnostics, "info", "structural_nor_latency",
                    "Time=0 and object latency is missing; at stage 2 it will be encoded as the maximum observed value of the same latency feature computed from train only, with censored_latency=1.",
                    mouse_id=row["mouse_id"], group=row["group"], week=week,
                    feature=label, column=lat_col, excel_cell=excel_cell(df, idx, lat_col),
                )

    # The eight reviewed scale values are retained unchanged and must remain auditable.
    found_accepted = {
        (r["mouse_id"], int(r["week"]), r["feature"])
        for r in diagnostics
        if r["check"] == "accepted_scale_value"
    }
    missing_accepted = sorted(ACCEPTED_SCALE_VALUES - found_accepted)
    if missing_accepted:
        add_diag(
            diagnostics, "review", "accepted_scale_value_set_changed",
            f"Some previously accepted values no longer satisfy the current MAD rule: {missing_accepted}. Source values remain unchanged.",
        )

    blocker_count = sum(r["severity"] == "blocker" for r in diagnostics)
    review_count = sum(r["severity"] == "review" for r in diagnostics)
    accepted_count = sum(r["severity"] == "accepted" for r in diagnostics)

    if fatal_errors:
        status = "FATAL"
    elif blocker_count:
        status = "BLOCKED"
    else:
        status = "READY"

    add_diag(
        diagnostics, "summary", "stage1_status",
        f"Stage 1 status={status}; blockers={blocker_count}; review_flags={review_count}; accepted_scale_values={accepted_count}; structural_NOR_latency={structural_count}; max_missing_living={max_missing}.",
        value=status,
    )

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "diagnostics.csv"
    pd.DataFrame(diagnostics).to_csv(out, index=False)

    summary = {
        "stage": 1,
        "status": status,
        "included_mice": len(included),
        "excluded_mouse_ids": sorted(EXCLUDED_MOUSE_IDS),
        "group_counts": {k: int(group_counts.get(k, 0)) for k in EXPECTED_GROUP_COUNTS},
        "alive_counts": EXPECTED_ALIVE,
        "death_counts": EXPECTED_DEATH,
        "max_missing_living_visit": max_missing,
        "structural_nor_latency_count": structural_count,
        "blocker_rows": blocker_count,
        "review_rows": review_count,
        "accepted_scale_values": accepted_count,
        "censored_latency_rule": "train_feature_max",
        "fatal_errors": fatal_errors,
        "diagnostics_file": str(out.relative_to(ROOT)),
    }
    print("STAGE1_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if fatal_errors:
        raise RuntimeError("Stage 1 fatal checks failed: " + " | ".join(fatal_errors))



NOR_BLOCKS = {
    "NOR1": {
        "time_p": "Time_investigating_Piramidka_NOR1",
        "lat_p": "Latency_to_first_investigation_Piramidka_NOR1",
        "time_s": "Time_investigating_Stakan_NOR1",
        "lat_s": "Latency_to_first_investigation_Stakan_NOR1",
        "lat_first": "Latency_to_first_investigation_NOR1",
        "total": "Total_time_investigating_NOR1",
        "di": None,
    },
    "NOR2": {
        "time_p": "Time_investigating_Piramidka_zone_NOR2",
        "lat_p": "Latency_to_first_investigation_Piramidka_zone_NOR2",
        "time_s": "Time_investigating_Stakan_zone_NOR2",
        "lat_s": "Latency_to_first_investigation_Stakan_zone_NOR2",
        "lat_first": "Latency_to_first_investigation_NOR2",
        "total": "Total_time_investigating_NOR2",
        "di": "DI_NOR2",
    },
}

OBJECT_LATENCY_PAIRS = [
    ("Time_investigating_Piramidka_NOR1", "Latency_to_first_investigation_Piramidka_NOR1"),
    ("Time_investigating_Stakan_NOR1", "Latency_to_first_investigation_Stakan_NOR1"),
    ("Time_investigating_Piramidka_zone_NOR2", "Latency_to_first_investigation_Piramidka_zone_NOR2"),
    ("Time_investigating_Stakan_zone_NOR2", "Latency_to_first_investigation_Stakan_zone_NOR2"),
]

ROTAROD_FEATURES = [
    "Learning_T1mean", "Learning_T1max", "Learning_T1sum",
    "Learning_T2mean", "Learning_T2max", "Learning_T2sum",
    "Learning_T3mean", "Learning_T3max", "Learning_T3sum",
]

MAX_MISSING_PER_VISIT = 7
FLOAT_TOL = 1e-8


def load_included_source():
    df = pd.read_excel(DATA_FILE, sheet_name="Лист1", header=1)
    df = df[df["Animal"].notna()].copy()
    df["mouse_id"] = df["Animal"].map(norm_id)
    df = df[~df["mouse_id"].isin(EXCLUDED_MOUSE_IDS)].copy()
    df["group"] = df["Group_24"].map(GROUP_MAP)
    df["dead16"] = is_dead(df["CFP_16"])
    df["dead24"] = is_dead(df["CFP_24"])
    return df


def build_long_table(source):
    rows = []
    for _, src in source.iterrows():
        for week in (0, 16, 24):
            dead = bool((week == 16 and src["dead16"]) or (week == 24 and src["dead24"]))
            row = {
                "mouse_id": src["mouse_id"],
                "group": src["group"],
                "week": week,
                "death": dead,
                "censored_latency": 0,
                "censored_latency_count": 0,
                "zero_exploration": 0,
                "missing_count_before": 0,
                "missing_count": 0,
                "status": "death" if dead else "",
            }
            for feature, week_map in FEATURE_COLUMNS.items():
                raw = src[week_map[week]]
                value = pd.to_numeric(pd.Series([raw]), errors="coerce").iloc[0]
                row[feature] = np.nan if dead else value
            if not dead:
                row["missing_count_before"] = int(
                    sum(pd.isna(row[feature]) for feature in MODEL_FEATURES)
                )
            rows.append(row)
    long_df = pd.DataFrame(rows)
    return long_df


def _different(a, b, tol=FLOAT_TOL):
    if pd.isna(a) and pd.isna(b):
        return False
    if pd.isna(a) != pd.isna(b):
        return True
    return not math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)


def deterministic_preprocess(long_df, fit_mouse_ids=None):
    """
    Apply stage-2 deterministic preprocessing.

    If fit_mouse_ids is None, feature maxima for censored latency are fitted on
    all included living non-censored observations. In CV, stage 3/6 will pass
    train mouse IDs so validation never contributes to these maxima.
    """
    out = long_df.copy(deep=True)
    living = ~out["death"]

    if fit_mouse_ids is None:
        fit_mask = living.copy()
        fit_scope = "all_included_living"
    else:
        fit_mouse_ids = set(fit_mouse_ids)
        fit_mask = living & out["mouse_id"].isin(fit_mouse_ids)
        fit_scope = "train_only"

    censor_maxima = {}
    censored_cells = 0
    errors = []

    for time_feature, latency_feature in OBJECT_LATENCY_PAIRS:
        structural = living & out[time_feature].eq(0) & out[latency_feature].isna()
        observed_fit = fit_mask & out[latency_feature].notna()
        observed_values = out.loc[observed_fit, latency_feature].astype(float)

        if structural.any():
            if observed_values.empty:
                errors.append(
                    f"No observed non-censored fit values for {latency_feature}; "
                    f"cannot encode {int(structural.sum())} censored values."
                )
                censor_maxima[latency_feature] = None
                continue
            max_value = float(observed_values.max())
            censor_maxima[latency_feature] = max_value
            out.loc[structural, latency_feature] = max_value
            out.loc[structural, "censored_latency"] = 1
            out.loc[structural, "censored_latency_count"] += 1
            censored_cells += int(structural.sum())
        elif not observed_values.empty:
            censor_maxima[latency_feature] = float(observed_values.max())
        else:
            censor_maxima[latency_feature] = None

    recovered_base_time_cells = 0
    total_recomputed_cells = 0
    total_changed_cells = 0
    first_latency_recomputed_cells = 0
    first_latency_changed_cells = 0
    di_recomputed_cells = 0
    di_changed_cells = 0
    zero_exploration_visits = 0

    for block_name, cfg in NOR_BLOCKS.items():
        tp = cfg["time_p"]
        ts = cfg["time_s"]
        total = cfg["total"]
        lp = cfg["lat_p"]
        ls = cfg["lat_s"]
        first = cfg["lat_first"]

        for idx in out.index[living]:
            tpv = out.at[idx, tp]
            tsv = out.at[idx, ts]
            total_old = out.at[idx, total]

            if pd.isna(tpv) and pd.notna(tsv) and pd.notna(total_old):
                recovered = float(total_old) - float(tsv)
                if recovered >= -FLOAT_TOL:
                    recovered = max(0.0, recovered)
                    out.at[idx, tp] = recovered
                    tpv = recovered
                    recovered_base_time_cells += 1
                else:
                    errors.append(
                        f"{out.at[idx,'mouse_id']} week {out.at[idx,'week']} {block_name}: "
                        f"TotalTime - known Stakan time is negative ({recovered})."
                    )
            elif pd.isna(tsv) and pd.notna(tpv) and pd.notna(total_old):
                recovered = float(total_old) - float(tpv)
                if recovered >= -FLOAT_TOL:
                    recovered = max(0.0, recovered)
                    out.at[idx, ts] = recovered
                    tsv = recovered
                    recovered_base_time_cells += 1
                else:
                    errors.append(
                        f"{out.at[idx,'mouse_id']} week {out.at[idx,'week']} {block_name}: "
                        f"TotalTime - known Piramidka time is negative ({recovered})."
                    )

            if pd.notna(tpv) and pd.notna(tsv):
                total_new = float(tpv) + float(tsv)
                total_recomputed_cells += 1
                if _different(total_old, total_new):
                    total_changed_cells += 1
                out.at[idx, total] = total_new
            else:
                if pd.notna(total_old):
                    total_changed_cells += 1
                out.at[idx, total] = np.nan

            lpv = out.at[idx, lp]
            lsv = out.at[idx, ls]
            first_old = out.at[idx, first]
            if pd.notna(lpv) and pd.notna(lsv):
                first_new = min(float(lpv), float(lsv))
                first_latency_recomputed_cells += 1
                if _different(first_old, first_new):
                    first_latency_changed_cells += 1
                out.at[idx, first] = first_new
            else:
                if pd.notna(first_old):
                    first_latency_changed_cells += 1
                out.at[idx, first] = np.nan

        if cfg["di"] is not None:
            di = cfg["di"]
            for idx in out.index[living]:
                tpv = out.at[idx, tp]
                tsv = out.at[idx, ts]
                di_old = out.at[idx, di]
                if pd.notna(tpv) and pd.notna(tsv):
                    denom = float(tpv) + float(tsv)
                    if math.isclose(denom, 0.0, abs_tol=FLOAT_TOL):
                        di_new = 0.0
                        out.at[idx, "zero_exploration"] = 1
                        zero_exploration_visits += 1
                    elif denom > 0:
                        di_new = (float(tpv) - float(tsv)) / denom
                    else:
                        errors.append(
                            f"{out.at[idx,'mouse_id']} week {out.at[idx,'week']} NOR2: "
                            f"negative investigation-time denominator {denom}."
                        )
                        di_new = np.nan
                    if pd.notna(di_new):
                        di_recomputed_cells += 1
                    if _different(di_old, di_new):
                        di_changed_cells += 1
                    out.at[idx, di] = di_new
                else:
                    if pd.notna(di_old):
                        di_changed_cells += 1
                    out.at[idx, di] = np.nan

    for idx in out.index:
        if out.at[idx, "death"]:
            out.at[idx, "missing_count"] = len(MODEL_FEATURES)
            out.at[idx, "status"] = "death"
            continue

        missing = int(sum(pd.isna(out.at[idx, feature]) for feature in MODEL_FEATURES))
        out.at[idx, "missing_count"] = missing
        if missing == 0:
            out.at[idx, "status"] = "observed"
        elif missing <= MAX_MISSING_PER_VISIT:
            # This means "eligible for statistical imputation at stage 3".
            out.at[idx, "status"] = "imputed"
        else:
            out.at[idx, "status"] = "missing_visit"

    stats = {
        "fit_scope": fit_scope,
        "censor_maxima": censor_maxima,
        "censored_cells": censored_cells,
        "censored_visits": int((out["censored_latency"] == 1).sum()),
        "recovered_base_time_cells": recovered_base_time_cells,
        "total_recomputed_cells": total_recomputed_cells,
        "total_changed_cells": total_changed_cells,
        "first_latency_recomputed_cells": first_latency_recomputed_cells,
        "first_latency_changed_cells": first_latency_changed_cells,
        "di_recomputed_cells": di_recomputed_cells,
        "di_changed_cells": di_changed_cells,
        "zero_exploration_visits": zero_exploration_visits,
        "errors": errors,
    }
    return out, stats


def add_stage2_diag(rows, severity, check, detail, value="", feature="", week="", group="", mouse_id=""):
    rows.append({
        "type": "stage2",
        "severity": severity,
        "check": check,
        "mouse_id": mouse_id,
        "group": group,
        "week": week,
        "feature": feature,
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
    })


def validate_stage2(long_raw, processed, stats):
    errors = []
    if len(processed) != 54 * 3:
        errors.append(f"Expected 162 long-table rows, got {len(processed)}.")
    if processed[["mouse_id", "week"]].duplicated().any():
        errors.append("Duplicate mouse_id/week rows in long table.")

    death_rows = processed["death"]
    death_count = int(death_rows.sum())
    if death_count != 22:
        errors.append(f"Expected 22 death rows (10 at week16 + 12 at week24), got {death_count}.")
    if processed.loc[death_rows, list(FEATURE_COLUMNS)].notna().any().any():
        errors.append("At least one death row retained a functional model value.")

    living = ~processed["death"]
    if (processed.loc[living, "missing_count"] > MAX_MISSING_PER_VISIT).any():
        bad_rows = []
        for idx in processed.index[living & (processed["missing_count"] > MAX_MISSING_PER_VISIT)]:
            missing_features = [f for f in MODEL_FEATURES if pd.isna(processed.at[idx, f])]
            bad_rows.append({
                "mouse_id": processed.at[idx, "mouse_id"],
                "week": int(processed.at[idx, "week"]),
                "missing_count": int(processed.at[idx, "missing_count"]),
                "missing_features": missing_features,
            })
        errors.append("Living missing_visit remains after deterministic preprocessing: " + json.dumps(bad_rows, ensure_ascii=False))

    # Censored values must be finite and equal to the fitted maximum.
    for _, latency_feature in OBJECT_LATENCY_PAIRS:
        max_value = stats["censor_maxima"].get(latency_feature)
        # Structural cells are identifiable by raw Time=0 / raw latency=NaN.
        time_feature = next(t for t, l in OBJECT_LATENCY_PAIRS if l == latency_feature)
        structural = (
            (~long_raw["death"])
            & long_raw[time_feature].eq(0)
            & long_raw[latency_feature].isna()
        )
        if structural.any():
            if max_value is None or not math.isfinite(float(max_value)):
                errors.append(f"No finite censor maximum for {latency_feature}.")
            else:
                vals = processed.loc[structural, latency_feature].astype(float)
                if not np.allclose(vals.to_numpy(), float(max_value), rtol=0, atol=FLOAT_TOL):
                    errors.append(f"Censored values do not equal fitted maximum for {latency_feature}.")
                if not (processed.loc[structural, "censored_latency"] == 1).all():
                    errors.append(f"Censored flag missing for {latency_feature}.")

    # Derived NOR identities.
    for block_name, cfg in NOR_BLOCKS.items():
        tp, ts = cfg["time_p"], cfg["time_s"]
        total, lp, ls, first = cfg["total"], cfg["lat_p"], cfg["lat_s"], cfg["lat_first"]

        complete_time = living & processed[tp].notna() & processed[ts].notna()
        lhs = processed.loc[complete_time, total].astype(float).to_numpy()
        rhs = (processed.loc[complete_time, tp].astype(float) + processed.loc[complete_time, ts].astype(float)).to_numpy()
        if len(lhs) and not np.allclose(lhs, rhs, rtol=0, atol=FLOAT_TOL):
            errors.append(f"{block_name} TotalTime identity failed.")

        complete_lat = living & processed[lp].notna() & processed[ls].notna()
        lhs = processed.loc[complete_lat, first].astype(float).to_numpy()
        rhs = np.minimum(
            processed.loc[complete_lat, lp].astype(float).to_numpy(),
            processed.loc[complete_lat, ls].astype(float).to_numpy(),
        )
        if len(lhs) and not np.allclose(lhs, rhs, rtol=0, atol=FLOAT_TOL):
            errors.append(f"{block_name} first-latency identity failed.")

        if cfg["di"] is not None:
            di = cfg["di"]
            comp = complete_time
            denom = (
                processed.loc[comp, tp].astype(float).to_numpy()
                + processed.loc[comp, ts].astype(float).to_numpy()
            )
            numer = (
                processed.loc[comp, tp].astype(float).to_numpy()
                - processed.loc[comp, ts].astype(float).to_numpy()
            )
            expected = np.divide(numer, denom, out=np.zeros_like(numer), where=np.abs(denom) > FLOAT_TOL)
            actual = processed.loc[comp, di].astype(float).to_numpy()
            if len(actual) and not np.allclose(actual, expected, rtol=0, atol=FLOAT_TOL):
                errors.append("NOR2 DI identity failed.")

    # Rotarod is not deterministically changed.
    for feature in ROTAROD_FEATURES:
        a = long_raw.loc[living, feature].to_numpy(dtype=float)
        b = processed.loc[living, feature].to_numpy(dtype=float)
        if not np.allclose(a, b, rtol=0, atol=FLOAT_TOL, equal_nan=True):
            errors.append(f"Rotarod feature {feature} was modified during deterministic preprocessing.")

    errors.extend(stats["errors"])
    return errors


def run_stage2():
    # Re-run stage 1 first so every stage-2 action is protected by current preflight checks.
    run_stage1()

    source = load_included_source()
    long_raw = build_long_table(source)
    processed, stats = deterministic_preprocess(long_raw, fit_mouse_ids=None)
    errors = validate_stage2(long_raw, processed, stats)

    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[diagnostics["type"].astype(str) != "stage2"].copy()
    stage2_rows = []

    add_stage2_diag(
        stage2_rows, "ok", "long_table",
        "Long table contains one row per included mouse and week.",
        value=len(processed),
    )
    add_stage2_diag(
        stage2_rows, "ok", "death_rows",
        "Death rows have all 35 processed functional features unavailable; the eNRI model uses 30 MODEL_FEATURES.",
        value=int(processed["death"].sum()),
    )

    for feature, max_value in stats["censor_maxima"].items():
        add_stage2_diag(
            stage2_rows,
            "ok" if max_value is not None else "fatal",
            "censored_latency_max",
            "Full-data stage-2 audit maximum. In future CV this same rule is fitted on train only.",
            value="" if max_value is None else float(max_value),
            feature=feature,
        )

    add_stage2_diag(
        stage2_rows, "ok", "censored_latency_encoding",
        "Structural Time=0/Latency=NaN cells were encoded by the corresponding observed-feature maximum and flagged censored_latency=1. Full-data mode is used only for this stage-2 audit; CV will fit maxima on train only.",
        value=stats["censored_cells"],
    )
    add_stage2_diag(
        stage2_rows, "ok", "nor_base_time_recovery",
        "Missing object-investigation times recovered deterministically from TotalTime minus the known component where possible.",
        value=stats["recovered_base_time_cells"],
    )
    add_stage2_diag(
        stage2_rows, "ok", "nor_total_time",
        f"Recomputed {stats['total_recomputed_cells']} NOR TotalTime cells; {stats['total_changed_cells']} source values were filled or changed by the deterministic identity.",
        value=stats["total_changed_cells"],
    )
    add_stage2_diag(
        stage2_rows, "ok", "nor_first_latency",
        f"Recomputed {stats['first_latency_recomputed_cells']} first-latency cells; {stats['first_latency_changed_cells']} source values were filled or changed.",
        value=stats["first_latency_changed_cells"],
    )
    add_stage2_diag(
        stage2_rows, "ok", "nor_di",
        f"Recomputed {stats['di_recomputed_cells']} DI cells; {stats['di_changed_cells']} source values were filled or changed; zero-exploration visits={stats['zero_exploration_visits']}.",
        value=stats["di_changed_cells"],
    )

    status_counts = processed["status"].value_counts().to_dict()
    for status in ("observed", "imputed", "death", "missing_visit"):
        add_stage2_diag(
            stage2_rows, "ok" if status != "missing_visit" or int(status_counts.get(status, 0)) == 0 else "fatal",
            "status_count",
            "Stage-2 status count. 'imputed' means eligible for statistical imputation at stage 3; no statistical imputation has yet been performed.",
            value=int(status_counts.get(status, 0)),
            feature=status,
        )

    max_missing_after = int(processed.loc[~processed["death"], "missing_count"].max())
    max_missing_before = int(processed.loc[~processed["death"], "missing_count_before"].max())
    add_stage2_diag(
        stage2_rows, "ok", "missingness_after_deterministic",
        f"Maximum living missing_count over 30 MODEL_FEATURES changed from {max_missing_before}/30 before deterministic preprocessing to {max_missing_after}/30 after it.",
        value=max_missing_after,
    )

    status = "READY" if not errors else "FATAL"
    for err in errors:
        add_stage2_diag(stage2_rows, "fatal", "stage2_validation", err)
    add_stage2_diag(
        stage2_rows,
        "summary",
        "stage2_status",
        f"Stage 2 status={status}; validation_errors={len(errors)}; censored_latency_cells={stats['censored_cells']}; censored_visits={stats['censored_visits']}; max_missing_after={max_missing_after}.",
        value=status,
    )

    merged = pd.concat([diagnostics, pd.DataFrame(stage2_rows)], ignore_index=True)
    merged.to_csv(diagnostics_path, index=False)

    summary = {
        "stage": 2,
        "status": status,
        "long_rows": int(len(processed)),
        "living_rows": int((~processed["death"]).sum()),
        "death_rows": int(processed["death"].sum()),
        "censored_latency_rule": "feature_max_fit_scope",
        "censor_fit_scope_stage2_audit": stats["fit_scope"],
        "censor_maxima": stats["censor_maxima"],
        "censored_latency_cells": int(stats["censored_cells"]),
        "censored_visits": int(stats["censored_visits"]),
        "recovered_base_time_cells": int(stats["recovered_base_time_cells"]),
        "zero_exploration_visits": int(stats["zero_exploration_visits"]),
        "status_counts": {k: int(v) for k, v in status_counts.items()},
        "max_missing_before": max_missing_before,
        "max_missing_after": max_missing_after,
        "validation_errors": errors,
        "diagnostics_file": str(diagnostics_path.relative_to(ROOT)),
    }
    print("STAGE2_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if errors:
        raise RuntimeError("Stage 2 validation failed: " + " | ".join(errors))


DERIVED_FEATURES = [
    "Latency_to_first_investigation_NOR1",
    "Total_time_investigating_NOR1",
    "DI_NOR2",
    "Latency_to_first_investigation_NOR2",
    "Total_time_investigating_NOR2",
]
MODEL_FEATURES = [f for f in FEATURE_COLUMNS if f not in DERIVED_FEATURES]
BASE_FEATURES = MODEL_FEATURES  # compatibility alias; these 30 features define eNRI
IMPUTATION_SEED = 20260928


def compute_baseline_scaling(processed, fit_mouse_ids=None):
    living = ~processed["death"]
    if fit_mouse_ids is None:
        fit_mask = living
        fit_scope = "all_included"
    else:
        fit_mouse_ids = set(fit_mouse_ids)
        fit_mask = living & processed["mouse_id"].isin(fit_mouse_ids)
        fit_scope = "train_only"

    baseline_mask = fit_mask & processed["week"].eq(0)
    mean = {}
    std = {}
    n_obs = {}
    errors = []

    for feature in MODEL_FEATURES:
        vals = pd.to_numeric(
            processed.loc[baseline_mask, feature], errors="coerce"
        ).dropna().astype(float)
        n_obs[feature] = int(len(vals))
        if len(vals) < 2:
            mean[feature] = None
            std[feature] = None
            errors.append(
                f"{feature}: fewer than 2 available baseline fit values ({len(vals)})."
            )
            continue

        m = float(vals.mean())
        s = float(vals.std(ddof=1))
        mean[feature] = m
        std[feature] = s

        if not math.isfinite(m):
            errors.append(f"{feature}: non-finite baseline mean.")
        if not math.isfinite(s) or s <= 0:
            errors.append(f"{feature}: invalid baseline sample std={s}.")

    return {
        "fit_scope": fit_scope,
        "mean": mean,
        "std": std,
        "n_obs": n_obs,
        "errors": errors,
    }


def recompute_derived_features(raw_df):
    out = raw_df.copy(deep=True)
    living = ~out["death"]
    zero_exploration = np.zeros(len(out), dtype=int)

    for cfg in NOR_BLOCKS.values():
        tp = cfg["time_p"]
        ts = cfg["time_s"]
        total = cfg["total"]
        lp = cfg["lat_p"]
        ls = cfg["lat_s"]
        first = cfg["lat_first"]

        idxs = out.index[living]
        tpv = pd.to_numeric(out.loc[idxs, tp], errors="coerce")
        tsv = pd.to_numeric(out.loc[idxs, ts], errors="coerce")
        both_time = tpv.notna() & tsv.notna()

        out.loc[idxs, total] = np.nan
        out.loc[idxs[both_time], total] = (
            tpv.loc[both_time].astype(float) + tsv.loc[both_time].astype(float)
        ).to_numpy()

        lpv = pd.to_numeric(out.loc[idxs, lp], errors="coerce")
        lsv = pd.to_numeric(out.loc[idxs, ls], errors="coerce")
        both_lat = lpv.notna() & lsv.notna()

        out.loc[idxs, first] = np.nan
        out.loc[idxs[both_lat], first] = np.minimum(
            lpv.loc[both_lat].astype(float).to_numpy(),
            lsv.loc[both_lat].astype(float).to_numpy(),
        )

        if cfg["di"] is not None:
            di = cfg["di"]
            out.loc[idxs, di] = np.nan
            valid_idx = idxs[both_time]
            tpa = out.loc[valid_idx, tp].astype(float).to_numpy()
            tsa = out.loc[valid_idx, ts].astype(float).to_numpy()
            denom = tpa + tsa
            numer = tpa - tsa
            di_vals = np.divide(
                numer,
                denom,
                out=np.zeros_like(numer, dtype=float),
                where=np.abs(denom) > FLOAT_TOL,
            )
            out.loc[valid_idx, di] = di_vals
            zero_idx = valid_idx[np.abs(denom) <= FLOAT_TOL]
            if len(zero_idx):
                out.loc[zero_idx, "zero_exploration"] = 1

    return out


def fit_transform_stage3(long_raw, fit_mouse_ids=None, random_state=IMPUTATION_SEED, sample_posterior=False):
    processed, deterministic_stats = deterministic_preprocess(
        long_raw, fit_mouse_ids=fit_mouse_ids
    )
    errors = list(deterministic_stats["errors"])

    living = ~processed["death"]
    if fit_mouse_ids is None:
        fit_mask = living
        fit_scope = "all_included_living"
    else:
        fit_mouse_ids = set(fit_mouse_ids)
        fit_mask = living & processed["mouse_id"].isin(fit_mouse_ids)
        fit_scope = "train_only"

    if (processed.loc[fit_mask, "status"] == "missing_visit").any():
        bad = processed.loc[
            fit_mask & processed["status"].eq("missing_visit"),
            ["mouse_id", "week", "missing_count"],
        ]
        errors.append(
            "Fit data contains missing_visit rows: " + bad.to_json(orient="records")
        )

    scaling = compute_baseline_scaling(processed, fit_mouse_ids=fit_mouse_ids)
    errors.extend(scaling["errors"])

    if errors:
        return processed, {
            "fit_scope": fit_scope,
            "deterministic": deterministic_stats,
            "scaling": scaling,
            "errors": errors,
        }

    means = scaling["mean"]
    stds = scaling["std"]

    # Standardize the 30 MODEL_FEATURES with baseline fit parameters.
    standardized_base = pd.DataFrame(
        index=processed.index, columns=BASE_FEATURES, dtype=float
    )
    for feature in BASE_FEATURES:
        standardized_base[feature] = (
            pd.to_numeric(processed[feature], errors="coerce") - means[feature]
        ) / stds[feature]

    living_idx = processed.index[living]
    fit_idx = processed.index[fit_mask]

    design = standardized_base.loc[living_idx, BASE_FEATURES].copy()
    design["week_16"] = processed.loc[living_idx, "week"].eq(16).astype(float).to_numpy()
    design["week_24"] = processed.loc[living_idx, "week"].eq(24).astype(float).to_numpy()

    fit_design = design.loc[fit_idx]
    if fit_design.empty:
        errors.append("No living fit rows for IterativeImputer.")
        return processed, {
            "fit_scope": fit_scope,
            "deterministic": deterministic_stats,
            "scaling": scaling,
            "errors": errors,
        }

    # IterativeImputer is fitted only on fit rows. Group is intentionally absent.
    imputer = IterativeImputer(
        estimator=BayesianRidge(),
        sample_posterior=bool(sample_posterior),
        max_iter=20,
        tol=1e-3,
        random_state=random_state,
    )
    imputer.fit(fit_design)
    transformed = imputer.transform(design)

    if transformed.shape[1] != len(BASE_FEATURES) + 2:
        errors.append(
            f"Unexpected imputer output width {transformed.shape[1]}; "
            f"expected {len(BASE_FEATURES) + 2}."
        )
        return processed, {
            "fit_scope": fit_scope,
            "deterministic": deterministic_stats,
            "scaling": scaling,
            "errors": errors,
        }

    transformed_base = transformed[:, : len(BASE_FEATURES)]
    result_raw = processed.copy(deep=True)

    missing_base_before = standardized_base.loc[living_idx, BASE_FEATURES].isna()
    imputed_cell_count = int(missing_base_before.to_numpy().sum())
    imputed_feature_counts = {
        feature: int(missing_base_before[feature].sum())
        for feature in BASE_FEATURES
        if int(missing_base_before[feature].sum()) > 0
    }

    # Return imputed MODEL_FEATURES to raw scale.
    for j, feature in enumerate(BASE_FEATURES):
        raw_vals = transformed_base[:, j] * stds[feature] + means[feature]
        result_raw.loc[living_idx, feature] = raw_vals

    # Derivatives are recomputed only after all base values are available.
    result_raw = recompute_derived_features(result_raw)

    # Final standardized 30-dimensional MODEL_FEATURES vector.
    # The five deterministic derived features remain in raw units for QC only
    # and are never passed to the eNRI optimization.
    final_std = result_raw.copy(deep=True)
    for feature in MODEL_FEATURES:
        final_std.loc[living_idx, feature] = (
            pd.to_numeric(result_raw.loc[living_idx, feature], errors="coerce")
            - means[feature]
        ) / stds[feature]
        final_std.loc[~living, feature] = np.nan

    # Preserve stage-2 missing_count as the number of missing values before
    # statistical imputation; update the final status only.
    final_std.loc[living & processed["missing_count"].eq(0), "status"] = "observed"
    final_std.loc[living & processed["missing_count"].gt(0), "status"] = "imputed"
    final_std.loc[~living, "status"] = "death"

    # Diagnostics: observed MODEL_FEATURE cells must remain unchanged after imputer roundtrip.
    max_observed_roundtrip_error = 0.0
    for feature in BASE_FEATURES:
        obs_mask = living & processed[feature].notna()
        if obs_mask.any():
            before = processed.loc[obs_mask, feature].astype(float).to_numpy()
            after = result_raw.loc[obs_mask, feature].astype(float).to_numpy()
            err = float(np.max(np.abs(before - after)))
            max_observed_roundtrip_error = max(max_observed_roundtrip_error, err)

    # Physical checks on the raw post-imputation representation.
    nonnegative_features = list(MODEL_FEATURES)
    negative_values = []
    for feature in nonnegative_features:
        vals = pd.to_numeric(result_raw.loc[living, feature], errors="coerce")
        bad = vals < -FLOAT_TOL
        if bad.any():
            for idx in vals.index[bad]:
                negative_values.append({
                    "mouse_id": result_raw.at[idx, "mouse_id"],
                    "week": int(result_raw.at[idx, "week"]),
                    "feature": feature,
                    "value": float(vals.loc[idx]),
                })

    di_vals = pd.to_numeric(result_raw.loc[living, "DI_NOR2"], errors="coerce")
    di_bad = di_vals.notna() & ((di_vals < -1 - FLOAT_TOL) | (di_vals > 1 + FLOAT_TOL))
    di_violations = [
        {
            "mouse_id": result_raw.at[idx, "mouse_id"],
            "week": int(result_raw.at[idx, "week"]),
            "value": float(di_vals.loc[idx]),
        }
        for idx in di_vals.index[di_bad]
    ]

    remaining_raw_missing = int(
        result_raw.loc[living, MODEL_FEATURES].isna().to_numpy().sum()
    )
    remaining_std_missing = int(
        final_std.loc[living, MODEL_FEATURES].isna().to_numpy().sum()
    )
    finite_final = np.isfinite(
        final_std.loc[living, MODEL_FEATURES].to_numpy(dtype=float)
    ).all()

    # Validate exact derived identities after imputation.
    derived_errors = []
    for block_name, cfg in NOR_BLOCKS.items():
        tp, ts = cfg["time_p"], cfg["time_s"]
        total, lp, ls, first = cfg["total"], cfg["lat_p"], cfg["lat_s"], cfg["lat_first"]
        idxs = result_raw.index[living]

        total_expected = (
            result_raw.loc[idxs, tp].astype(float).to_numpy()
            + result_raw.loc[idxs, ts].astype(float).to_numpy()
        )
        total_actual = result_raw.loc[idxs, total].astype(float).to_numpy()
        if not np.allclose(total_actual, total_expected, rtol=0, atol=FLOAT_TOL):
            derived_errors.append(f"{block_name} TotalTime identity failed after imputation.")

        first_expected = np.minimum(
            result_raw.loc[idxs, lp].astype(float).to_numpy(),
            result_raw.loc[idxs, ls].astype(float).to_numpy(),
        )
        first_actual = result_raw.loc[idxs, first].astype(float).to_numpy()
        if not np.allclose(first_actual, first_expected, rtol=0, atol=FLOAT_TOL):
            derived_errors.append(f"{block_name} first-latency identity failed after imputation.")

        if cfg["di"] is not None:
            di = cfg["di"]
            tpv = result_raw.loc[idxs, tp].astype(float).to_numpy()
            tsv = result_raw.loc[idxs, ts].astype(float).to_numpy()
            denom = tpv + tsv
            expected = np.divide(
                tpv - tsv,
                denom,
                out=np.zeros_like(denom, dtype=float),
                where=np.abs(denom) > FLOAT_TOL,
            )
            actual = result_raw.loc[idxs, di].astype(float).to_numpy()
            if not np.allclose(actual, expected, rtol=0, atol=FLOAT_TOL):
                derived_errors.append("NOR2 DI identity failed after imputation.")

    errors.extend(derived_errors)
    if remaining_raw_missing:
        errors.append(f"{remaining_raw_missing} raw living MODEL_FEATURE cells remain missing after imputation.")
    if remaining_std_missing:
        errors.append(f"{remaining_std_missing} standardized living MODEL_FEATURE cells remain missing.")
    if not finite_final:
        errors.append("At least one final standardized living MODEL_FEATURE value is non-finite.")
    if max_observed_roundtrip_error > 1e-7:
        errors.append(
            f"Observed base values changed during imputer roundtrip; max error={max_observed_roundtrip_error}."
        )
    if negative_values:
        errors.append(
            "Negative post-imputation values in nonnegative features: "
            + json.dumps(negative_values, ensure_ascii=False)
        )
    if di_violations:
        errors.append(
            "Post-imputation DI outside [-1,1]: "
            + json.dumps(di_violations, ensure_ascii=False)
        )

    stats = {
        "fit_scope": fit_scope,
        "deterministic": deterministic_stats,
        "scaling": scaling,
        "imputer_n_iter": int(imputer.n_iter_),
        "imputation_sample_posterior": bool(sample_posterior),
        "imputation_random_state": int(random_state),
        "imputed_base_cells": imputed_cell_count,
        "imputed_feature_counts": imputed_feature_counts,
        "max_observed_roundtrip_error": max_observed_roundtrip_error,
        "remaining_raw_missing": remaining_raw_missing,
        "remaining_std_missing": remaining_std_missing,
        "negative_values": negative_values,
        "di_violations": di_violations,
        "errors": errors,
    }
    return final_std, stats


def add_stage3_diag(rows, severity, check, detail, value="", feature="", week="", group="", mouse_id=""):
    rows.append({
        "type": "stage3",
        "severity": severity,
        "check": check,
        "mouse_id": mouse_id,
        "group": group,
        "week": week,
        "feature": feature,
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
    })


def run_stage3():
    # Stage 3 includes and revalidates stages 1-2 before fitting statistical preprocessing.
    run_stage2()

    source = load_included_source()
    long_raw = build_long_table(source)
    final_std, stats = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=IMPUTATION_SEED,
    )
    errors = list(stats.get("errors", []))

    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[diagnostics["type"].astype(str) != "stage3"].copy()
    rows = []

    scaling = stats["scaling"]
    for feature in MODEL_FEATURES:
        add_stage3_diag(
            rows,
            "ok",
            "baseline_scaling",
            "Baseline mean and sample std (ddof=1) for a MODEL_FEATURE fitted on available week-0 values. Full-data audit uses all included mice; CV will fit train only.",
            value=f"n={scaling['n_obs'][feature]}; mean={scaling['mean'][feature]:.12g}; std={scaling['std'][feature]:.12g}",
            feature=feature,
            week=0,
        )

    add_stage3_diag(
        rows,
        "ok",
        "imputer_fit",
        "IterativeImputer(BayesianRidge, sample_posterior=False, max_iter=20, tol=1e-3) fitted on standardized 30 MODEL_FEATURES plus week_16/week_24 indicators; group and five deterministic derived QC features are not used.",
        value=stats["imputer_n_iter"],
    )
    add_stage3_diag(
        rows,
        "ok",
        "imputed_base_cells",
        "Number of missing MODEL_FEATURE cells filled by IterativeImputer.",
        value=stats["imputed_base_cells"],
    )

    for feature, count in sorted(stats["imputed_feature_counts"].items()):
        add_stage3_diag(
            rows,
            "ok",
            "imputed_feature_count",
            "Missing MODEL_FEATURE cells filled by IterativeImputer.",
            value=count,
            feature=feature,
        )

    status_counts = final_std["status"].value_counts().to_dict()
    for status in ("observed", "imputed", "death", "missing_visit"):
        count = int(status_counts.get(status, 0))
        add_stage3_diag(
            rows,
            "ok" if status != "missing_visit" or count == 0 else "fatal",
            "status_count",
            "Final stage-3 visit status.",
            value=count,
            feature=status,
        )

    add_stage3_diag(
        rows,
        "ok" if stats["remaining_std_missing"] == 0 else "fatal",
        "complete_35d_living",
        "All living eligible visits must have a complete standardized 30-dimensional MODEL_FEATURES vector after imputation. Five deterministic derived features are QC-only.",
        value=stats["remaining_std_missing"],
    )
    add_stage3_diag(
        rows,
        "ok" if stats["max_observed_roundtrip_error"] <= 1e-7 else "fatal",
        "observed_values_preserved",
        "Maximum raw-scale absolute change among originally observed MODEL_FEATURES after standardize/impute/inverse-transform.",
        value=stats["max_observed_roundtrip_error"],
    )

    for err in errors:
        add_stage3_diag(rows, "fatal", "stage3_validation", err)

    status = "READY" if not errors else "FATAL"
    add_stage3_diag(
        rows,
        "summary",
        "stage3_status",
        f"Stage 3 status={status}; validation_errors={len(errors)}; imputed_base_cells={stats['imputed_base_cells']}; final living standardized missing={stats['remaining_std_missing']}.",
        value=status,
    )

    merged = pd.concat([diagnostics, pd.DataFrame(rows)], ignore_index=True)
    merged.to_csv(diagnostics_path, index=False)

    summary = {
        "stage": 3,
        "status": status,
        "fit_scope_stage3_audit": stats["fit_scope"],
        "model_features": len(MODEL_FEATURES),
        "derived_qc_features": len(DERIVED_FEATURES),
        "living_rows": int((~final_std["death"]).sum()),
        "death_rows": int(final_std["death"].sum()),
        "status_counts": {k: int(v) for k, v in status_counts.items()},
        "imputed_base_cells": int(stats["imputed_base_cells"]),
        "imputed_feature_counts": stats["imputed_feature_counts"],
        "imputer_n_iter": int(stats["imputer_n_iter"]),
        "remaining_standardized_missing": int(stats["remaining_std_missing"]),
        "max_observed_roundtrip_error": float(stats["max_observed_roundtrip_error"]),
        "validation_errors": errors,
        "diagnostics_file": str(diagnostics_path.relative_to(ROOT)),
    }
    print("STAGE3_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if errors:
        raise RuntimeError("Stage 3 validation failed: " + " | ".join(errors))


STATE_GROUPS = ("PBS", "LPS", "run", "MCC")
STATE_WEEKS = (0, 16, 24)


def state_label(group, week):
    return f"{group}^{week}"


def build_experimental_states(final_std, state_mouse_ids=None, reference_xbar=None):
    """
    Build the 12 group×week states in the 30-dimensional eNRI feature space.

    state_mouse_ids controls which mice contribute to N_A/R_A/I_A/O_A/D_A/U_A.
    reference_xbar is the normalization vector used in b_A. If omitted, it is
    computed from living complete PBS^0 rows in the same state subset.
    Later CV code can therefore build train states, retain xbar_PBS0_train, and
    reuse that same reference for validation states without leakage.
    """
    if state_mouse_ids is None:
        subset = final_std.copy()
        scope = "all_included"
    else:
        ids = set(state_mouse_ids)
        subset = final_std[final_std["mouse_id"].isin(ids)].copy()
        scope = "mouse_subset"

    errors = []
    if subset.empty:
        return {}, None, {
            "scope": scope,
            "errors": ["State subset is empty."],
        }

    # Every included mouse must have exactly one row at each of 0/16/24.
    dup = subset[["mouse_id", "week"]].duplicated()
    if dup.any():
        errors.append("Duplicate mouse_id/week rows in state subset.")

    per_mouse_weeks = subset.groupby("mouse_id")["week"].nunique()
    bad_weeks = per_mouse_weeks[per_mouse_weeks.ne(3)]
    if len(bad_weeks):
        errors.append(
            "Some mice do not have exactly three state rows: "
            + json.dumps({str(k): int(v) for k, v in bad_weeks.items()}, ensure_ascii=False)
        )

    # Determine the normalization reference from PBS^0 living complete observations.
    if reference_xbar is None:
        pbs0 = subset[
            subset["group"].eq("PBS")
            & subset["week"].eq(0)
            & subset["status"].isin(["observed", "imputed"])
        ]
        if pbs0.empty:
            errors.append("No living complete PBS^0 rows available for normalization reference.")
            xbar = None
        else:
            xbar = pbs0[MODEL_FEATURES].astype(float).mean(axis=0).to_numpy(dtype=float)
    else:
        xbar = np.asarray(reference_xbar, dtype=float)

    if xbar is not None:
        if xbar.shape != (len(MODEL_FEATURES),):
            errors.append(
                f"xbar_PBS0 has shape {xbar.shape}; expected {(len(MODEL_FEATURES),)}."
            )
        elif not np.isfinite(xbar).all():
            errors.append("xbar_PBS0 contains non-finite values.")

    states = {}
    for group in STATE_GROUPS:
        group_mice = sorted(subset.loc[subset["group"].eq(group), "mouse_id"].unique())
        N_group = len(group_mice)

        for week in STATE_WEEKS:
            label = state_label(group, week)
            rows = subset[subset["group"].eq(group) & subset["week"].eq(week)].copy()

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
                X = O[MODEL_FEATURES].to_numpy(dtype=float)
                if not np.isfinite(X).all():
                    errors.append(f"{label}: O_A contains non-finite model values.")
            else:
                X = np.empty((0, len(MODEL_FEATURES)), dtype=float)
                errors.append(f"{label}: O_A is empty.")

            if xbar is None or N_A == 0:
                a_A = np.nan
                b_A = np.full(len(MODEL_FEATURES), np.nan)
            else:
                a_A = float(len(O) / N_A)
                b_A = ((X - xbar).sum(axis=0) / N_A) if len(O) else np.zeros(len(MODEL_FEATURES))

            if len(O) >= 2:
                S_A = np.cov(X, rowvar=False, ddof=1)
            else:
                S_A = np.full((len(MODEL_FEATURES), len(MODEL_FEATURES)), np.nan)
                errors.append(f"{label}: fewer than 2 living complete observations for covariance.")

            if S_A.shape != (len(MODEL_FEATURES), len(MODEL_FEATURES)):
                errors.append(f"{label}: covariance shape {S_A.shape} is invalid.")

            finite_cov = bool(np.isfinite(S_A).all())
            symmetry_error = (
                float(np.max(np.abs(S_A - S_A.T))) if finite_cov else float("nan")
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

            if not finite_cov:
                errors.append(f"{label}: covariance contains non-finite values.")
            if finite_cov and symmetry_error > 1e-10:
                errors.append(f"{label}: covariance asymmetry {symmetry_error} exceeds tolerance.")
            # Individual sample covariance matrices are theoretically PSD but
            # rank-deficient (p=30 > n in every state). Tiny negative eigenvalues
            # can therefore appear from floating-point eigendecomposition. The
            # PLAN's hard -1e-8 PSD check applies to the symmetrized Q_var at
            # stage 5, not to each singular S_A separately. Record min_eig here
            # for diagnostics without turning it into a stage-4 blocker.

            states[label] = {
                "group": group,
                "week": int(week),
                "N": int(N_A),
                "R": int(len(R)),
                "I": int(len(I)),
                "O": int(len(O)),
                "D": int(len(D)),
                "U": int(len(U)),
                "R_mouse_ids": sorted(R["mouse_id"].tolist()),
                "I_mouse_ids": sorted(I["mouse_id"].tolist()),
                "O_mouse_ids": sorted(O["mouse_id"].tolist()),
                "D_mouse_ids": sorted(D["mouse_id"].tolist()),
                "U_mouse_ids": sorted(U["mouse_id"].tolist()),
                "a": float(a_A),
                "b": np.asarray(b_A, dtype=float),
                "S": np.asarray(S_A, dtype=float),
                "covariance_min_eigenvalue": min_eig,
                "covariance_rank": rank,
                "covariance_trace": trace,
                "covariance_symmetry_error": symmetry_error,
            }

    stats = {
        "scope": scope,
        "state_count": int(len(states)),
        "feature_count": int(len(MODEL_FEATURES)),
        "errors": errors,
    }
    return states, xbar, stats


def validate_full_stage4(states, xbar, stats):
    errors = list(stats["errors"])

    expected_state_labels = {
        state_label(g, w) for g in STATE_GROUPS for w in STATE_WEEKS
    }
    if set(states) != expected_state_labels:
        errors.append(
            "State label set mismatch: "
            + json.dumps(sorted(set(states) ^ expected_state_labels))
        )

    if len(states) != 12:
        errors.append(f"Expected 12 states, got {len(states)}.")

    expected_N = EXPECTED_GROUP_COUNTS
    expected_alive_by_week = {
        0: EXPECTED_GROUP_COUNTS,
        16: EXPECTED_ALIVE[16],
        24: EXPECTED_ALIVE[24],
    }
    expected_death_by_week = {
        0: {g: 0 for g in STATE_GROUPS},
        16: EXPECTED_DEATH[16],
        24: EXPECTED_DEATH[24],
    }

    for group in STATE_GROUPS:
        for week in STATE_WEEKS:
            label = state_label(group, week)
            if label not in states:
                continue
            s = states[label]

            if s["N"] != expected_N[group]:
                errors.append(
                    f"{label}: N={s['N']}, expected {expected_N[group]}."
                )
            if s["O"] != expected_alive_by_week[week][group]:
                errors.append(
                    f"{label}: O={s['O']}, expected alive={expected_alive_by_week[week][group]}."
                )
            if s["D"] != expected_death_by_week[week][group]:
                errors.append(
                    f"{label}: D={s['D']}, expected death={expected_death_by_week[week][group]}."
                )
            if s["U"] != 0:
                errors.append(f"{label}: U={s['U']} but full model requires U=0.")
            if not math.isclose(
                s["a"],
                s["O"] / s["N"],
                rel_tol=0,
                abs_tol=1e-12,
            ):
                errors.append(f"{label}: a_A != O_A/N_A.")

    if xbar is None:
        errors.append("xbar_PBS0 is missing.")
    else:
        # By construction, b_PBS0 must be essentially zero because PBS^0 has no deaths.
        pbs0_b = states["PBS^0"]["b"]
        max_abs_pbs0_b = float(np.max(np.abs(pbs0_b)))
        if max_abs_pbs0_b > 1e-10:
            errors.append(
                f"PBS^0 b_A is not zero under PBS^0 centering; max abs={max_abs_pbs0_b}."
            )

    return errors


def add_stage4_diag(rows, severity, check, detail, value="", feature="", week="", group="", mouse_id=""):
    rows.append({
        "type": "state",
        "severity": severity,
        "check": check,
        "mouse_id": mouse_id,
        "group": group,
        "week": week,
        "feature": feature,
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
    })


def run_stage4():
    # Re-run all upstream preprocessing before constructing states.
    run_stage3()

    source = load_included_source()
    long_raw = build_long_table(source)
    final_std, stage3_stats = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=IMPUTATION_SEED,
    )
    upstream_errors = list(stage3_stats.get("errors", []))

    states, xbar, state_stats = build_experimental_states(final_std)
    errors = upstream_errors + validate_full_stage4(states, xbar, state_stats)

    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    diagnostics = pd.read_csv(diagnostics_path)
    # Replace prior stage-4 state diagnostics if this stage is rerun.
    diagnostics = diagnostics[
        ~(
            diagnostics["type"].astype(str).eq("state")
            & diagnostics["check"].astype(str).str.startswith("stage4_")
        )
    ].copy()

    rows = []
    for group in STATE_GROUPS:
        for week in STATE_WEEKS:
            label = state_label(group, week)
            s = states[label]
            add_stage4_diag(
                rows,
                "ok",
                "stage4_state_counts",
                (
                    f"{label}: N={s['N']}, R={s['R']}, I={s['I']}, "
                    f"O={s['O']}, D={s['D']}, U={s['U']}."
                ),
                value=f"N={s['N']};R={s['R']};I={s['I']};O={s['O']};D={s['D']};U={s['U']}",
                feature=label,
                group=group,
                week=week,
            )
            add_stage4_diag(
                rows,
                "ok",
                "stage4_state_a",
                "a_A = |O_A| / N_A; deaths therefore contribute zero to the group-mean eNRI representation.",
                value=f"{s['a']:.12g}",
                feature=label,
                group=group,
                week=week,
            )
            add_stage4_diag(
                rows,
                "ok",
                "stage4_state_b",
                "b_A is the 30-vector (1/N_A) * sum_{i in O_A}(x_i - xbar_PBS0). Value reports its Euclidean norm.",
                value=f"{float(np.linalg.norm(s['b'])):.12g}",
                feature=label,
                group=group,
                week=week,
            )
            add_stage4_diag(
                rows,
                "ok",
                "stage4_state_covariance",
                (
                    f"S_A is 30x30 sample covariance over O_A. "
                    f"rank={s['covariance_rank']}; trace={s['covariance_trace']:.12g}; "
                    f"min_eigenvalue={s['covariance_min_eigenvalue']:.12g}; "
                    f"symmetry_error={s['covariance_symmetry_error']:.3g}. "
                    "Because p=30 exceeds state sample size, S_A is singular; tiny negative "
                    "eigenvalues from floating-point eigendecomposition are diagnostic only. "
                    "The hard PSD tolerance is applied to symmetrized Q_var at stage 5."
                ),
                value=f"{s['covariance_min_eigenvalue']:.12g}",
                feature=label,
                group=group,
                week=week,
            )

    xbar_norm = float(np.linalg.norm(xbar)) if xbar is not None else float("nan")
    add_stage4_diag(
        rows,
        "ok" if xbar is not None else "fatal",
        "stage4_xbar_pbs0",
        "Normalization reference xbar_PBS0 computed from living complete PBS week-0 standardized MODEL_FEATURES. Value reports Euclidean norm.",
        value=f"{xbar_norm:.12g}",
        feature="xbar_PBS0",
        group="PBS",
        week=0,
    )

    for err in errors:
        add_stage4_diag(rows, "fatal", "stage4_validation", err)

    status = "READY" if not errors else "FATAL"
    add_stage4_diag(
        rows,
        "summary",
        "stage4_status",
        (
            f"Stage 4 status={status}; states={len(states)}; model_features={len(MODEL_FEATURES)}; "
            f"validation_errors={len(errors)}."
        ),
        value=status,
    )

    merged = pd.concat([diagnostics, pd.DataFrame(rows)], ignore_index=True)
    merged.to_csv(diagnostics_path, index=False)

    state_counts = {
        label: {
            k: int(states[label][k])
            for k in ("N", "R", "I", "O", "D", "U")
        }
        for label in sorted(states)
    }
    covariance_min_eigs = {
        label: float(states[label]["covariance_min_eigenvalue"])
        for label in sorted(states)
    }
    covariance_ranks = {
        label: int(states[label]["covariance_rank"])
        for label in sorted(states)
    }

    summary = {
        "stage": 4,
        "status": status,
        "state_count": int(len(states)),
        "model_features": int(len(MODEL_FEATURES)),
        "xbar_pbs0_norm": xbar_norm,
        "state_counts": state_counts,
        "covariance_min_eigenvalues": covariance_min_eigs,
        "covariance_ranks": covariance_ranks,
        "validation_errors": errors,
        "diagnostics_file": str(diagnostics_path.relative_to(ROOT)),
    }
    print("STAGE4_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if errors:
        raise RuntimeError("Stage 4 validation failed: " + " | ".join(errors))


EQUALITY_PAIRS = [
    ("PBS^0", "LPS^0"),
    ("PBS^0", "run^0"),
    ("PBS^0", "MCC^0"),
    ("LPS^16", "run^16"),
    ("LPS^16", "MCC^16"),
]

ORDER_PAIRS = [
    ("PBS^16", "LPS^16"),
    ("PBS^24", "LPS^24"),
    ("run^24", "LPS^24"),
    ("MCC^24", "LPS^24"),
    ("PBS^0", "PBS^16"),
    ("LPS^0", "LPS^16"),
    ("run^0", "run^16"),
    ("MCC^0", "MCC^16"),
    ("PBS^16", "PBS^24"),
    ("LPS^16", "LPS^24"),
]

SMOKE_RHO = 0.1
SMOKE_BETA = 1.0
SMOKE_LAMBDA = 1.0
SMOKE_C = 1.0
POSITIVITY_EPSILON = 1e-3
QP_TOLERANCE = 1e-7


def assemble_qvar(states):
    mats = [np.asarray(states[state_label(g, w)]["S"], dtype=float)
            for w in STATE_WEEKS for g in STATE_GROUPS]
    Q = np.mean(np.stack(mats, axis=0), axis=0)
    Q = 0.5 * (Q + Q.T)
    finite = bool(np.isfinite(Q).all())
    if finite:
        eigvals = np.linalg.eigvalsh(Q)
        min_eig = float(eigvals.min())
        max_eig = float(eigvals.max())
        rank = int(np.linalg.matrix_rank(Q, tol=1e-10))
        symmetry_error = float(np.max(np.abs(Q - Q.T)))
        trace = float(np.trace(Q))
    else:
        min_eig = float("nan")
        max_eig = float("nan")
        rank = 0
        symmetry_error = float("nan")
        trace = float("nan")
    return Q, {
        "finite": finite,
        "min_eigenvalue": min_eig,
        "max_eigenvalue": max_eig,
        "rank": rank,
        "symmetry_error": symmetry_error,
        "trace": trace,
    }


def pair_affine_components(states, A, B):
    c_ab = float(states[A]["a"] - states[B]["a"])
    d_ab = np.asarray(states[A]["b"] - states[B]["b"], dtype=float)
    return c_ab, d_ab


def solve_qp_smoke(final_std, states, xbar,
                   rho=SMOKE_RHO, beta=SMOKE_BETA,
                   ridge_lambda=SMOKE_LAMBDA, C=SMOKE_C):
    errors = []

    # The sets used by the QP are fixed by the experimental design.
    expected_E = {
        ("PBS^0", "LPS^0"),
        ("PBS^0", "run^0"),
        ("PBS^0", "MCC^0"),
        ("LPS^16", "run^16"),
        ("LPS^16", "MCC^16"),
    }
    expected_O = {
        ("PBS^16", "LPS^16"),
        ("PBS^24", "LPS^24"),
        ("run^24", "LPS^24"),
        ("MCC^24", "LPS^24"),
        ("PBS^0", "PBS^16"),
        ("LPS^0", "LPS^16"),
        ("run^0", "run^16"),
        ("MCC^0", "MCC^16"),
        ("PBS^16", "PBS^24"),
        ("LPS^16", "LPS^24"),
    }
    if set(EQUALITY_PAIRS) != expected_E:
        errors.append("Equality-pair set does not match PLAN.")
    if set(ORDER_PAIRS) != expected_O:
        errors.append("Order-pair set does not match PLAN.")

    # All states used by E or O must have no living missing_visit rows.
    involved_states = {x for pair in EQUALITY_PAIRS + ORDER_PAIRS for x in pair}
    for label in sorted(involved_states):
        if states[label]["U"] != 0:
            errors.append(f"{label}: U_A={states[label]['U']} but QP requires U_A=0.")

    Q_var, q_stats = assemble_qvar(states)
    if not q_stats["finite"]:
        errors.append("Q_var contains non-finite values.")
    if q_stats["symmetry_error"] > 1e-12:
        errors.append(
            f"Q_var symmetry error {q_stats['symmetry_error']} exceeds tolerance."
        )
    if q_stats["min_eigenvalue"] < -1e-8:
        errors.append(
            f"Q_var minimum eigenvalue {q_stats['min_eigenvalue']} < -1e-8."
        )

    if xbar is None or np.asarray(xbar).shape != (len(MODEL_FEATURES),):
        errors.append("Invalid xbar_PBS0 for QP.")

    living = final_std["status"].isin(["observed", "imputed"])
    X_live = final_std.loc[living, MODEL_FEATURES].to_numpy(dtype=float)
    live_meta = final_std.loc[living, ["mouse_id", "group", "week", "status"]].copy()

    if len(X_live) == 0:
        errors.append("No living complete rows available for positivity constraints.")
    if not np.isfinite(X_live).all():
        errors.append("Non-finite values in positivity design matrix.")

    if errors:
        return None, {
            "status": "NOT_SOLVED",
            "errors": errors,
            "qvar": q_stats,
        }

    p = len(MODEL_FEATURES)
    m = len(ORDER_PAIRS)
    w = cp.Variable(p, name="w")
    eta = cp.Variable(m, nonneg=True, name="eta")

    # Q_var has already passed the explicit numerical PSD check above.
    # psd_wrap prevents CVXPY's independent eigenvalue classifier from
    # rejecting a numerically valid PSD matrix due to roundoff.
    objective_terms = [
        cp.quad_form(w, cp.psd_wrap(Q_var)),
        ridge_lambda * cp.sum_squares(w),
        C * cp.sum(eta),
    ]

    equality_exprs = []
    for A, B in EQUALITY_PAIRS:
        c_ab, d_ab = pair_affine_components(states, A, B)
        expr = c_ab + d_ab @ w
        equality_exprs.append(expr)
    objective_terms.append(beta * cp.sum_squares(cp.hstack(equality_exprs)))

    constraints = []
    order_exprs = []
    for k, (A, B) in enumerate(ORDER_PAIRS):
        c_ab, d_ab = pair_affine_components(states, A, B)
        expr = c_ab + d_ab @ w
        order_exprs.append(expr)
        constraints.append(expr >= rho - eta[k])

    centered_live = X_live - np.asarray(xbar, dtype=float)
    positivity_expr = 1.0 + centered_live @ w
    constraints.append(positivity_expr >= POSITIVITY_EPSILON)

    problem = cp.Problem(cp.Minimize(sum(objective_terms)), constraints)
    try:
        objective_value = problem.solve(
            solver=cp.OSQP,
            eps_abs=1e-8,
            eps_rel=1e-8,
            max_iter=100000,
            verbose=False,
        )
    except Exception as exc:
        return None, {
            "status": "SOLVER_EXCEPTION",
            "errors": [f"OSQP exception: {type(exc).__name__}: {exc}"],
            "qvar": q_stats,
        }

    solver_status = str(problem.status)
    if solver_status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}:
        errors.append(f"Unexpected solver status: {solver_status}.")
    if w.value is None or eta.value is None:
        errors.append("Solver returned no primal solution.")
        return None, {
            "status": solver_status,
            "errors": errors,
            "qvar": q_stats,
            "objective": None if objective_value is None else float(objective_value),
        }

    wv = np.asarray(w.value, dtype=float).reshape(-1)
    etav = np.asarray(eta.value, dtype=float).reshape(-1)

    if len(wv) != p or not np.isfinite(wv).all():
        errors.append("Weight vector is missing, wrong-sized, or non-finite.")
    if len(etav) != m or not np.isfinite(etav).all():
        errors.append("Slack vector is missing, wrong-sized, or non-finite.")

    equality_deltas = {}
    for A, B in EQUALITY_PAIRS:
        c_ab, d_ab = pair_affine_components(states, A, B)
        equality_deltas[f"{A}>{B}"] = float(c_ab + d_ab @ wv)

    order_results = {}
    max_order_violation = 0.0
    min_order_residual = float("inf")
    for k, (A, B) in enumerate(ORDER_PAIRS):
        c_ab, d_ab = pair_affine_components(states, A, B)
        delta = float(c_ab + d_ab @ wv)
        residual = float(delta - rho + etav[k])
        violation = max(0.0, -residual)
        max_order_violation = max(max_order_violation, violation)
        min_order_residual = min(min_order_residual, residual)
        order_results[f"{A}>{B}"] = {
            "delta": delta,
            "slack": float(etav[k]),
            "residual": residual,
            "violation": violation,
        }

    eta_nonneg_violation = max(0.0, float(-np.min(etav)))
    live_enri = 1.0 + centered_live @ wv
    min_live_enri = float(np.min(live_enri))
    positivity_residuals = live_enri - POSITIVITY_EPSILON
    min_positivity_residual = float(np.min(positivity_residuals))
    max_positivity_violation = max(0.0, -min_positivity_residual)

    # Locate the positivity constraint closest to binding for diagnostics.
    min_idx = int(np.argmin(live_enri))
    min_meta = live_meta.iloc[min_idx].to_dict()
    min_meta["week"] = int(min_meta["week"])

    group_means = {}
    for label, state in states.items():
        group_means[label] = float(state["a"] + state["b"] @ wv)

    # PBS^0 normalization should be exactly one up to floating-point noise.
    pbs0_normalization_error = abs(group_means["PBS^0"] - 1.0)

    # Recompute objective components from the numerical solution.
    variance_term = float(wv @ Q_var @ wv)
    equality_term = float(beta * sum(v * v for v in equality_deltas.values()))
    ridge_term = float(ridge_lambda * (wv @ wv))
    slack_term = float(C * np.sum(etav))
    objective_recomputed = variance_term + equality_term + ridge_term + slack_term
    objective_solver = float(problem.value)
    objective_gap = abs(objective_recomputed - objective_solver)

    if max_order_violation > QP_TOLERANCE:
        errors.append(
            f"Maximum order-constraint violation {max_order_violation} > {QP_TOLERANCE}."
        )
    if eta_nonneg_violation > QP_TOLERANCE:
        errors.append(
            f"Slack nonnegativity violation {eta_nonneg_violation} > {QP_TOLERANCE}."
        )
    if max_positivity_violation > QP_TOLERANCE:
        errors.append(
            f"Maximum positivity violation {max_positivity_violation} > {QP_TOLERANCE}."
        )
    if pbs0_normalization_error > QP_TOLERANCE:
        errors.append(
            f"PBS^0 normalization error {pbs0_normalization_error} > {QP_TOLERANCE}."
        )
    if objective_gap > 1e-6 * max(1.0, abs(objective_solver)):
        errors.append(
            f"Recomputed objective differs from solver objective by {objective_gap}."
        )

    solver_stats = problem.solver_stats
    extra = getattr(solver_stats, "extra_stats", None)
    num_iters = getattr(solver_stats, "num_iters", None)
    solve_time = getattr(solver_stats, "solve_time", None)

    result = {
        "w": wv,
        "eta": etav,
        "qvar": Q_var,
        "qvar_stats": q_stats,
        "solver_status": solver_status,
        "solver_name": str(solver_stats.solver_name),
        "solver_num_iters": None if num_iters is None else int(num_iters),
        "solver_time": None if solve_time is None else float(solve_time),
        "objective": objective_solver,
        "objective_components": {
            "variance": variance_term,
            "equality": equality_term,
            "ridge": ridge_term,
            "slack": slack_term,
        },
        "objective_recomputed": objective_recomputed,
        "objective_gap": objective_gap,
        "equality_deltas": equality_deltas,
        "order_results": order_results,
        "group_means": group_means,
        "min_live_enri": min_live_enri,
        "min_live_enri_meta": min_meta,
        "min_positivity_residual": min_positivity_residual,
        "max_positivity_violation": max_positivity_violation,
        "max_order_violation": max_order_violation,
        "min_order_residual": min_order_residual,
        "eta_nonneg_violation": eta_nonneg_violation,
        "pbs0_normalization_error": pbs0_normalization_error,
        "weight_l2_norm": float(np.linalg.norm(wv)),
        "weight_max_abs": float(np.max(np.abs(wv))),
        "slack_sum": float(np.sum(etav)),
        "slack_max": float(np.max(etav)),
        "errors": errors,
    }
    return result, {"status": solver_status, "errors": errors, "qvar": q_stats}


def add_stage5_diag(rows, severity, check, detail, value="", feature="", week="", group="", mouse_id=""):
    rows.append({
        "type": "qp",
        "severity": severity,
        "check": check,
        "mouse_id": mouse_id,
        "group": group,
        "week": week,
        "feature": feature,
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
    })


def run_stage5():
    # Stage 5 revalidates stages 1-4, then solves the first full-data smoke-test QP.
    run_stage4()

    source = load_included_source()
    long_raw = build_long_table(source)
    final_std, stage3_stats = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=IMPUTATION_SEED,
    )
    upstream_errors = list(stage3_stats.get("errors", []))

    states, xbar, state_stats = build_experimental_states(final_std)
    upstream_errors.extend(validate_full_stage4(states, xbar, state_stats))

    solution, qp_meta = solve_qp_smoke(
        final_std,
        states,
        xbar,
        rho=SMOKE_RHO,
        beta=SMOKE_BETA,
        ridge_lambda=SMOKE_LAMBDA,
        C=SMOKE_C,
    )

    errors = upstream_errors + list(qp_meta.get("errors", []))
    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[
        ~(
            diagnostics["type"].astype(str).eq("qp")
            & diagnostics["check"].astype(str).str.startswith("stage5_")
        )
    ].copy()
    rows = []

    q_stats = qp_meta["qvar"]
    add_stage5_diag(
        rows,
        "ok" if q_stats["finite"] and q_stats["min_eigenvalue"] >= -1e-8 else "fatal",
        "stage5_qvar",
        (
            f"Q_var is the equal-weight mean of 12 S_A matrices, symmetrized before QP. "
            f"shape=30x30; rank={q_stats['rank']}; trace={q_stats['trace']:.12g}; "
            f"min_eigenvalue={q_stats['min_eigenvalue']:.12g}; "
            f"max_eigenvalue={q_stats['max_eigenvalue']:.12g}; "
            f"symmetry_error={q_stats['symmetry_error']:.3g}."
        ),
        value=f"{q_stats['min_eigenvalue']:.12g}",
        feature="Q_var",
    )

    if solution is not None:
        add_stage5_diag(
            rows,
            "ok" if solution["solver_status"] in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE} else "fatal",
            "stage5_solver",
            (
                f"OSQP smoke test with rho={SMOKE_RHO}, beta={SMOKE_BETA}, "
                f"lambda={SMOKE_LAMBDA}, C={SMOKE_C}; "
                f"iterations={solution['solver_num_iters']}; solve_time={solution['solver_time']}."
            ),
            value=solution["solver_status"],
        )
        add_stage5_diag(
            rows,
            "ok",
            "stage5_objective",
            (
                f"objective={solution['objective']:.12g}; "
                f"variance={solution['objective_components']['variance']:.12g}; "
                f"equality={solution['objective_components']['equality']:.12g}; "
                f"ridge={solution['objective_components']['ridge']:.12g}; "
                f"slack={solution['objective_components']['slack']:.12g}; "
                f"recomputed_gap={solution['objective_gap']:.3g}."
            ),
            value=f"{solution['objective']:.12g}",
        )

        for feature, weight in zip(MODEL_FEATURES, solution["w"]):
            add_stage5_diag(
                rows,
                "ok",
                "stage5_weight",
                "Smoke-test standardized-feature weight; not the final CV-selected model weight.",
                value=f"{float(weight):.12g}",
                feature=feature,
            )

        for pair, delta in solution["equality_deltas"].items():
            add_stage5_diag(
                rows,
                "ok",
                "stage5_equality_delta",
                "Soft equality residual mu_A - mu_B; penalized in the objective, not a hard constraint.",
                value=f"{delta:.12g}",
                feature=pair,
            )

        for pair, rec in solution["order_results"].items():
            add_stage5_diag(
                rows,
                "ok" if rec["violation"] <= QP_TOLERANCE else "fatal",
                "stage5_order_constraint",
                (
                    f"delta={rec['delta']:.12g}; rho={SMOKE_RHO}; "
                    f"slack={rec['slack']:.12g}; residual=delta-rho+slack={rec['residual']:.12g}; "
                    f"violation={rec['violation']:.3g}."
                ),
                value=f"{rec['residual']:.12g}",
                feature=pair,
            )

        for label, mu in sorted(solution["group_means"].items()):
            add_stage5_diag(
                rows,
                "ok",
                "stage5_group_mean",
                "Smoke-test group mean eNRI including deaths as zero through a_A and b_A.",
                value=f"{mu:.12g}",
                feature=label,
            )

        min_meta = solution["min_live_enri_meta"]
        add_stage5_diag(
            rows,
            "ok" if solution["max_positivity_violation"] <= QP_TOLERANCE else "fatal",
            "stage5_positivity",
            (
                f"Minimum living eNRI={solution['min_live_enri']:.12g}; "
                f"epsilon={POSITIVITY_EPSILON}; "
                f"min residual={solution['min_positivity_residual']:.12g}; "
                f"max violation={solution['max_positivity_violation']:.3g}. "
                "Constraint applies to all observed+imputed living visits."
            ),
            value=f"{solution['min_live_enri']:.12g}",
            mouse_id=str(min_meta["mouse_id"]),
            group=str(min_meta["group"]),
            week=int(min_meta["week"]),
            feature=str(min_meta["status"]),
        )
        add_stage5_diag(
            rows,
            "ok" if solution["eta_nonneg_violation"] <= QP_TOLERANCE else "fatal",
            "stage5_slack",
            (
                f"sum_eta={solution['slack_sum']:.12g}; "
                f"max_eta={solution['slack_max']:.12g}; "
                f"nonnegativity_violation={solution['eta_nonneg_violation']:.3g}."
            ),
            value=f"{solution['slack_sum']:.12g}",
        )
        add_stage5_diag(
            rows,
            "ok" if solution["pbs0_normalization_error"] <= QP_TOLERANCE else "fatal",
            "stage5_pbs0_normalization",
            "PBS^0 mean eNRI must equal 1 by centering on xbar_PBS0.",
            value=f"{solution['group_means']['PBS^0']:.12g}",
            feature="PBS^0",
        )

    for err in errors:
        add_stage5_diag(rows, "fatal", "stage5_validation", err)

    status = "READY" if not errors and solution is not None else "FATAL"
    add_stage5_diag(
        rows,
        "summary",
        "stage5_status",
        (
            f"Stage 5 status={status}; solver={qp_meta.get('status')}; "
            f"validation_errors={len(errors)}; "
            f"rho={SMOKE_RHO}; beta={SMOKE_BETA}; lambda={SMOKE_LAMBDA}; C={SMOKE_C}."
        ),
        value=status,
    )

    merged = pd.concat([diagnostics, pd.DataFrame(rows)], ignore_index=True)
    merged.to_csv(diagnostics_path, index=False)

    summary = {
        "stage": 5,
        "status": status,
        "solver_status": qp_meta.get("status"),
        "rho": SMOKE_RHO,
        "beta": SMOKE_BETA,
        "lambda": SMOKE_LAMBDA,
        "C": SMOKE_C,
        "model_features": len(MODEL_FEATURES),
        "equality_pairs": len(EQUALITY_PAIRS),
        "order_pairs": len(ORDER_PAIRS),
        "positivity_rows": int(final_std["status"].isin(["observed", "imputed"]).sum()),
        "qvar_min_eigenvalue": float(q_stats["min_eigenvalue"]),
        "qvar_rank": int(q_stats["rank"]),
        "validation_errors": errors,
        "diagnostics_file": str(diagnostics_path.relative_to(ROOT)),
    }
    if solution is not None:
        summary.update({
            "objective": float(solution["objective"]),
            "objective_components": solution["objective_components"],
            "weight_l2_norm": float(solution["weight_l2_norm"]),
            "weight_max_abs": float(solution["weight_max_abs"]),
            "slack_sum": float(solution["slack_sum"]),
            "slack_max": float(solution["slack_max"]),
            "max_order_violation": float(solution["max_order_violation"]),
            "max_positivity_violation": float(solution["max_positivity_violation"]),
            "min_live_enri": float(solution["min_live_enri"]),
            "pbs0_mean": float(solution["group_means"]["PBS^0"]),
            "group_means": solution["group_means"],
        })

    print("STAGE5_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if status != "READY":
        raise RuntimeError("Stage 5 validation failed: " + " | ".join(errors))


CV_SEEDS = tuple(range(10))
CV_GRID = (0.1, 1.0, 10.0)
CV_SELECTION_TOL = 1e-6
CV_MIN_TRAIN_O = 5
CV_MIN_VAL_O = 2


def evaluate_validation_metrics(final_std, val_ids, val_states, xbar_train, weights, rho=SMOKE_RHO):
    val_ids = set(val_ids)
    val_rows = final_std[final_std["mouse_id"].isin(val_ids)].copy()
    living = val_rows["status"].isin(["observed", "imputed"])
    live_rows = val_rows[living]

    X = live_rows[MODEL_FEATURES].to_numpy(dtype=float)
    w = np.asarray(weights, dtype=float)
    xbar = np.asarray(xbar_train, dtype=float)
    enri_live = 1.0 + (X - xbar) @ w

    if len(enri_live) == 0:
        raise ValueError("Validation split has no living complete observations.")

    V_pos = float(np.mean(enri_live < POSITIVITY_EPSILON))

    order_deltas = []
    for A, B in ORDER_PAIRS:
        c_ab, d_ab = pair_affine_components(val_states, A, B)
        order_deltas.append(float(c_ab + d_ab @ w))
    order_deltas = np.asarray(order_deltas, dtype=float)

    V_sign = float(np.mean(order_deltas <= 0.0))
    V_margin = float(np.mean(np.maximum(0.0, rho - order_deltas)))

    eq_deltas = []
    for A, B in EQUALITY_PAIRS:
        c_ab, d_ab = pair_affine_components(val_states, A, B)
        eq_deltas.append(float(c_ab + d_ab @ w))
    eq_deltas = np.asarray(eq_deltas, dtype=float)
    V_eq = float(np.sqrt(np.mean(eq_deltas ** 2)))

    state_vars = []
    for group in STATE_GROUPS:
        for week in STATE_WEEKS:
            label = state_label(group, week)
            S = np.asarray(val_states[label]["S"], dtype=float)
            state_vars.append(float(w @ S @ w))
    V_var = float(np.mean(state_vars))
    V_w = float(np.linalg.norm(w))

    return {
        "V_pos": V_pos,
        "V_sign": V_sign,
        "V_margin": V_margin,
        "V_eq": V_eq,
        "V_var": V_var,
        "V_w": V_w,
        "validation_living": int(len(enri_live)),
        "validation_min_enri": float(np.min(enri_live)),
        "validation_order_deltas": order_deltas.tolist(),
        "validation_eq_deltas": eq_deltas.tolist(),
    }


def lexicographic_select(aggregate_rows, tol=CV_SELECTION_TOL):
    if not aggregate_rows:
        raise ValueError("No aggregate CV rows available for selection.")

    metrics = ["V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w"]
    survivors = list(aggregate_rows)
    selection_trace = []

    for metric in metrics:
        best = min(float(row[metric]) for row in survivors)
        survivors = [
            row for row in survivors
            if float(row[metric]) <= best + tol
        ]
        selection_trace.append({
            "metric": metric,
            "best": float(best),
            "survivors": int(len(survivors)),
        })

    selected = min(
        survivors,
        key=lambda row: (float(row["beta"]), float(row["lambda"]), float(row["C"])),
    )
    return selected, selection_trace


def prepare_cv_splits(long_raw, source):
    mouse_df = source[["mouse_id", "group"]].drop_duplicates().copy()
    mouse_df = mouse_df.sort_values("mouse_id").reset_index(drop=True)
    X_dummy = np.zeros((len(mouse_df), 1), dtype=float)
    y = mouse_df["group"].to_numpy()

    accepted = []
    rejected = []

    for seed in CV_SEEDS:
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)
        for fold, (train_idx, val_idx) in enumerate(skf.split(X_dummy, y), start=1):
            train_ids = mouse_df.iloc[train_idx]["mouse_id"].tolist()
            val_ids = mouse_df.iloc[val_idx]["mouse_id"].tolist()

            overlap = sorted(set(train_ids) & set(val_ids))
            if overlap:
                rejected.append({
                    "seed": seed,
                    "fold": fold,
                    "reason": f"train/validation mouse overlap: {overlap}",
                })
                continue

            final_std, prep_stats = fit_transform_stage3(
                long_raw,
                fit_mouse_ids=train_ids,
                random_state=IMPUTATION_SEED,
            )

            prep_errors = list(prep_stats.get("errors", []))
            if prep_stats.get("fit_scope") != "train_only":
                prep_errors.append(
                    f"Unexpected preprocessing fit scope: {prep_stats.get('fit_scope')}"
                )
            if prep_stats.get("deterministic", {}).get("fit_scope") != "train_only":
                prep_errors.append(
                    "Censored-latency maxima were not fitted train-only."
                )
            if prep_stats.get("scaling", {}).get("fit_scope") != "train_only":
                prep_errors.append(
                    "Baseline scaling was not fitted train-only."
                )

            train_states, xbar_train, train_state_stats = build_experimental_states(
                final_std,
                state_mouse_ids=train_ids,
                reference_xbar=None,
            )
            val_states, xbar_val_used, val_state_stats = build_experimental_states(
                final_std,
                state_mouse_ids=val_ids,
                reference_xbar=xbar_train,
            )

            # Eligibility is determined by O counts after train-only preprocessing.
            train_o = {
                label: int(s["O"]) for label, s in train_states.items()
            }
            val_o = {
                label: int(s["O"]) for label, s in val_states.items()
            }
            min_train_o = min(train_o.values()) if train_o else 0
            min_val_o = min(val_o.values()) if val_o else 0

            reasons = []
            reasons.extend(prep_errors)

            if min_train_o < CV_MIN_TRAIN_O:
                bad = {k: v for k, v in train_o.items() if v < CV_MIN_TRAIN_O}
                reasons.append(
                    "train O_A below 5: " + json.dumps(bad, sort_keys=True)
                )
            if min_val_o < CV_MIN_VAL_O:
                bad = {k: v for k, v in val_o.items() if v < CV_MIN_VAL_O}
                reasons.append(
                    "validation O_A below 2: " + json.dumps(bad, sort_keys=True)
                )

            # If the count thresholds pass, state construction must otherwise be valid.
            if min_train_o >= CV_MIN_TRAIN_O:
                reasons.extend(train_state_stats.get("errors", []))
            if min_val_o >= CV_MIN_VAL_O:
                reasons.extend(val_state_stats.get("errors", []))

            # The validation state builder must use exactly the train PBS0 reference.
            if xbar_train is None or xbar_val_used is None:
                reasons.append("Missing train PBS0 reference for validation.")
            elif not np.allclose(
                np.asarray(xbar_train, dtype=float),
                np.asarray(xbar_val_used, dtype=float),
                rtol=0,
                atol=0,
            ):
                reasons.append("Validation did not reuse xbar_PBS0_train exactly.")

            split_record = {
                "seed": int(seed),
                "fold": int(fold),
                "train_ids": train_ids,
                "val_ids": val_ids,
                "train_n": int(len(train_ids)),
                "val_n": int(len(val_ids)),
                "min_train_O": int(min_train_o),
                "min_val_O": int(min_val_o),
                "train_group_counts": {
                    g: int(sum(mouse_df.iloc[train_idx]["group"].eq(g)))
                    for g in STATE_GROUPS
                },
                "val_group_counts": {
                    g: int(sum(mouse_df.iloc[val_idx]["group"].eq(g)))
                    for g in STATE_GROUPS
                },
            }

            if reasons:
                split_record["reason"] = " | ".join(reasons)
                rejected.append(split_record)
                continue

            # Store preprocessed fold data so exactly the same accepted splits and
            # preprocessing are reused for every hyperparameter combination.
            split_record.update({
                "final_std": final_std,
                "train_states": train_states,
                "val_states": val_states,
                "xbar_train": np.asarray(xbar_train, dtype=float),
                "prep_stats": prep_stats,
            })
            accepted.append(split_record)

    return accepted, rejected


def run_cv_grid(accepted_splits):
    fold_rows = []
    solver_failures = []

    for beta in CV_GRID:
        for ridge_lambda in CV_GRID:
            for C in CV_GRID:
                for split in accepted_splits:
                    train_ids = set(split["train_ids"])
                    train_df = split["final_std"][
                        split["final_std"]["mouse_id"].isin(train_ids)
                    ].copy()

                    solution, qp_meta = solve_qp_smoke(
                        train_df,
                        split["train_states"],
                        split["xbar_train"],
                        rho=SMOKE_RHO,
                        beta=float(beta),
                        ridge_lambda=float(ridge_lambda),
                        C=float(C),
                    )

                    if solution is None or qp_meta.get("errors"):
                        solver_failures.append({
                            "seed": split["seed"],
                            "fold": split["fold"],
                            "beta": float(beta),
                            "lambda": float(ridge_lambda),
                            "C": float(C),
                            "status": qp_meta.get("status"),
                            "errors": qp_meta.get("errors", []),
                        })
                        continue

                    metrics = evaluate_validation_metrics(
                        split["final_std"],
                        split["val_ids"],
                        split["val_states"],
                        split["xbar_train"],
                        solution["w"],
                        rho=SMOKE_RHO,
                    )

                    fold_rows.append({
                        "seed": int(split["seed"]),
                        "fold": int(split["fold"]),
                        "beta": float(beta),
                        "lambda": float(ridge_lambda),
                        "C": float(C),
                        **{k: float(metrics[k]) for k in (
                            "V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w"
                        )},
                        "solver_status": solution["solver_status"],
                        "train_min_live_enri": float(solution["min_live_enri"]),
                        "train_max_order_violation": float(solution["max_order_violation"]),
                        "train_slack_sum": float(solution["slack_sum"]),
                        "validation_living": int(metrics["validation_living"]),
                        "validation_min_enri": float(metrics["validation_min_enri"]),
                    })

    return fold_rows, solver_failures


def aggregate_cv_grid(fold_rows, accepted_split_count):
    if not fold_rows:
        return []

    df = pd.DataFrame(fold_rows)
    metric_cols = ["V_pos", "V_sign", "V_margin", "V_eq", "V_var", "V_w"]
    aggregate_rows = []

    for beta in CV_GRID:
        for ridge_lambda in CV_GRID:
            for C in CV_GRID:
                sub = df[
                    df["beta"].eq(float(beta))
                    & df["lambda"].eq(float(ridge_lambda))
                    & df["C"].eq(float(C))
                ]
                if len(sub) != accepted_split_count:
                    continue
                row = {
                    "beta": float(beta),
                    "lambda": float(ridge_lambda),
                    "C": float(C),
                    "folds": int(len(sub)),
                }
                for metric in metric_cols:
                    row[metric] = float(sub[metric].mean())
                aggregate_rows.append(row)

    return aggregate_rows


def add_stage6_diag(rows, severity, check, detail, lambda_value=np.nan, **kwargs):
    row = {
        "type": "cv",
        "severity": severity,
        "check": check,
        "mouse_id": "",
        "group": "",
        "week": "",
        "feature": "",
        "column": "",
        "excel_cell": "",
        "value": "",
        "detail": detail,
        "seed": np.nan,
        "fold": np.nan,
        "beta": np.nan,
        "lambda": lambda_value,
        "C": np.nan,
        "V_pos": np.nan,
        "V_sign": np.nan,
        "V_margin": np.nan,
        "V_eq": np.nan,
        "V_var": np.nan,
        "V_w": np.nan,
        "solver_status": "",
    }
    row.update(kwargs)
    rows.append(row)


def run_stage6():
    # Revalidate the complete upstream pipeline and smoke-test before CV.
    run_stage5()

    source = load_included_source()
    long_raw = build_long_table(source)

    accepted_splits, rejected_splits = prepare_cv_splits(long_raw, source)
    errors = []

    if not accepted_splits:
        errors.append("No valid repeated stratified 3-fold CV splits.")
    if len(accepted_splits) + len(rejected_splits) != len(CV_SEEDS) * 3:
        errors.append(
            "CV split accounting mismatch: accepted + rejected != 30."
        )

    fold_rows = []
    solver_failures = []
    aggregate_rows = []
    selected = None
    selection_trace = []

    if accepted_splits:
        fold_rows, solver_failures = run_cv_grid(accepted_splits)
        if solver_failures:
            errors.append(
                f"{len(solver_failures)} QP fits failed across the fixed accepted split/grid set."
            )

        aggregate_rows = aggregate_cv_grid(
            fold_rows,
            accepted_split_count=len(accepted_splits),
        )
        if len(aggregate_rows) != len(CV_GRID) ** 3:
            errors.append(
                f"Expected 27 complete hyperparameter aggregates, got {len(aggregate_rows)}."
            )
        elif not solver_failures:
            selected, selection_trace = lexicographic_select(
                aggregate_rows,
                tol=CV_SELECTION_TOL,
            )

    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[
        ~diagnostics["type"].astype(str).eq("cv")
    ].copy()
    rows = []

    # Split diagnostics first.
    accepted_keys = {(x["seed"], x["fold"]) for x in accepted_splits}
    for split in accepted_splits:
        add_stage6_diag(
            rows,
            "ok",
            "stage6_split",
            (
                f"Accepted stratified mouse-level split; train_n={split['train_n']}, "
                f"val_n={split['val_n']}, min_train_O={split['min_train_O']}, "
                f"min_val_O={split['min_val_O']}; preprocessing/scaling/imputer/censor maxima "
                "were fitted on train only."
            ),
            seed=split["seed"],
            fold=split["fold"],
            value="accepted",
        )
    for split in rejected_splits:
        add_stage6_diag(
            rows,
            "review",
            "stage6_split",
            "Rejected before hyperparameter comparison: " + split.get("reason", "unspecified"),
            seed=split.get("seed", np.nan),
            fold=split.get("fold", np.nan),
            value="rejected",
        )

    # One row per accepted split × parameter combination, as specified in PLAN.
    for rec in fold_rows:
        add_stage6_diag(
            rows,
            "ok",
            "stage6_fold_metrics",
            (
                f"Validation metrics on fixed accepted split; "
                f"validation_living={rec['validation_living']}; "
                f"validation_min_enri={rec['validation_min_enri']:.12g}; "
                f"train_slack_sum={rec['train_slack_sum']:.12g}."
            ),
            seed=rec["seed"],
            fold=rec["fold"],
            beta=rec["beta"],
            lambda_value=rec["lambda"],
            C=rec["C"],
            V_pos=rec["V_pos"],
            V_sign=rec["V_sign"],
            V_margin=rec["V_margin"],
            V_eq=rec["V_eq"],
            V_var=rec["V_var"],
            V_w=rec["V_w"],
            solver_status=rec["solver_status"],
            value="fold",
        )

    for failure in solver_failures:
        add_stage6_diag(
            rows,
            "fatal",
            "stage6_solver_failure",
            json.dumps(failure["errors"], ensure_ascii=False),
            seed=failure["seed"],
            fold=failure["fold"],
            beta=failure["beta"],
            lambda_value=failure["lambda"],
            C=failure["C"],
            solver_status=str(failure["status"]),
        )

    for agg in aggregate_rows:
        add_stage6_diag(
            rows,
            "ok",
            "stage6_aggregate",
            "Arithmetic mean of validation metrics over all accepted seed/fold splits.",
            beta=agg["beta"],
            lambda_value=agg["lambda"],
            C=agg["C"],
            V_pos=agg["V_pos"],
            V_sign=agg["V_sign"],
            V_margin=agg["V_margin"],
            V_eq=agg["V_eq"],
            V_var=agg["V_var"],
            V_w=agg["V_w"],
            value=agg["folds"],
        )

    if selected is not None:
        add_stage6_diag(
            rows,
            "summary",
            "stage6_selected_hyperparameters",
            (
                "Selected by tolerance-aware lexicographic order "
                "(V_pos,V_sign,V_margin,V_eq,V_var,V_w), tolerance=1e-6; "
                "remaining exact/tolerance tie resolved by ascending (beta,lambda,C). "
                "Trace=" + json.dumps(selection_trace, ensure_ascii=False)
            ),
            beta=selected["beta"],
            lambda_value=selected["lambda"],
            C=selected["C"],
            V_pos=selected["V_pos"],
            V_sign=selected["V_sign"],
            V_margin=selected["V_margin"],
            V_eq=selected["V_eq"],
            V_var=selected["V_var"],
            V_w=selected["V_w"],
            value="selected",
        )

    for err in errors:
        add_stage6_diag(rows, "fatal", "stage6_validation", err)

    status = "READY" if not errors and selected is not None else "FATAL"
    add_stage6_diag(
        rows,
        "summary",
        "stage6_status",
        (
            f"Stage 6 status={status}; accepted_splits={len(accepted_splits)}; "
            f"rejected_splits={len(rejected_splits)}; grid_combinations={len(CV_GRID)**3}; "
            f"fold_metric_rows={len(fold_rows)}; solver_failures={len(solver_failures)}."
        ),
        value=status,
        beta=np.nan if selected is None else selected["beta"],
        lambda_value=np.nan if selected is None else selected["lambda"],
        C=np.nan if selected is None else selected["C"],
    )

    merged = pd.concat([diagnostics, pd.DataFrame(rows)], ignore_index=True, sort=False)
    merged.to_csv(diagnostics_path, index=False)

    summary = {
        "stage": 6,
        "status": status,
        "cv_seeds": list(CV_SEEDS),
        "n_splits_per_seed": 3,
        "accepted_splits": int(len(accepted_splits)),
        "rejected_splits": int(len(rejected_splits)),
        "grid_values": list(CV_GRID),
        "grid_combinations": int(len(CV_GRID) ** 3),
        "fold_metric_rows": int(len(fold_rows)),
        "solver_failures": int(len(solver_failures)),
        "selection_tolerance": CV_SELECTION_TOL,
        "selection_trace": selection_trace,
        "validation_errors": errors,
        "diagnostics_file": str(diagnostics_path.relative_to(ROOT)),
    }
    if selected is not None:
        summary["selected"] = {
            "beta": float(selected["beta"]),
            "lambda": float(selected["lambda"]),
            "C": float(selected["C"]),
            "V_pos": float(selected["V_pos"]),
            "V_sign": float(selected["V_sign"]),
            "V_margin": float(selected["V_margin"]),
            "V_eq": float(selected["V_eq"]),
            "V_var": float(selected["V_var"]),
            "V_w": float(selected["V_w"]),
        }

    print("STAGE6_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if status != "READY":
        raise RuntimeError("Stage 6 validation failed: " + " | ".join(errors))


def load_stage6_selection(diagnostics_path):
    if not diagnostics_path.exists():
        raise RuntimeError("Stage 6 diagnostics are missing.")

    d = pd.read_csv(diagnostics_path)
    selected = d[
        d["check"].astype(str).eq("stage6_selected_hyperparameters")
        & d["severity"].astype(str).eq("summary")
    ]
    status_rows = d[
        d["check"].astype(str).eq("stage6_status")
        & d["severity"].astype(str).eq("summary")
    ]
    if len(status_rows) != 1 or str(status_rows.iloc[0]["value"]) != "READY":
        raise RuntimeError("Stage 6 is not recorded as READY in diagnostics.")
    if len(selected) != 1:
        raise RuntimeError(
            f"Expected exactly one stage6_selected_hyperparameters row, got {len(selected)}."
        )

    row = selected.iloc[0]
    values = {
        "beta": float(row["beta"]),
        "lambda": float(row["lambda"]),
        "C": float(row["C"]),
    }
    if not all(math.isfinite(v) and v > 0 for v in values.values()):
        raise RuntimeError(f"Invalid selected hyperparameters: {values}")
    return values


def build_final_enri_table(final_std, xbar, weights):
    out = final_std[
        ["mouse_id", "group", "week", "status", "missing_count", "death"]
    ].copy()
    out["eNRI"] = np.nan

    living = out["status"].isin(["observed", "imputed"])
    X = final_std.loc[living, MODEL_FEATURES].to_numpy(dtype=float)
    xbar = np.asarray(xbar, dtype=float)
    w = np.asarray(weights, dtype=float)
    out.loc[living, "eNRI"] = 1.0 + (X - xbar) @ w

    death = out["status"].eq("death")
    out.loc[death, "eNRI"] = 0.0

    # missing_visit, if it ever exists in a future dataset, remains NaN by design.
    return out[["mouse_id", "group", "week", "eNRI", "status", "missing_count"]]


def validate_stage7_outputs(enri_df, weights, solution, states):
    errors = []
    w = np.asarray(weights, dtype=float)

    if len(w) != len(MODEL_FEATURES):
        errors.append(f"Expected {len(MODEL_FEATURES)} final weights, got {len(w)}.")
    if not np.isfinite(w).all():
        errors.append("Final weights contain non-finite values.")

    living = enri_df["status"].isin(["observed", "imputed"])
    deaths = enri_df["status"].eq("death")
    missing = enri_df["status"].eq("missing_visit")
    imputed = enri_df["status"].eq("imputed")

    live_vals = pd.to_numeric(enri_df.loc[living, "eNRI"], errors="coerce")
    if live_vals.isna().any() or not np.isfinite(live_vals.to_numpy(dtype=float)).all():
        errors.append("At least one living observed/imputed row has non-finite eNRI.")
    if len(live_vals) and float(live_vals.min()) < POSITIVITY_EPSILON - QP_TOLERANCE:
        errors.append(
            f"Minimum living eNRI {float(live_vals.min())} violates positivity."
        )

    death_vals = pd.to_numeric(enri_df.loc[deaths, "eNRI"], errors="coerce")
    if len(death_vals) and not np.allclose(
        death_vals.to_numpy(dtype=float), 0.0, rtol=0, atol=0
    ):
        errors.append("At least one death row does not have eNRI=0 exactly.")

    if imputed.any():
        imp_vals = pd.to_numeric(enri_df.loc[imputed, "eNRI"], errors="coerce")
        if imp_vals.isna().any() or not np.isfinite(imp_vals.to_numpy(dtype=float)).all():
            errors.append("At least one imputed row has non-finite eNRI.")

    if missing.any() and enri_df.loc[missing, "eNRI"].notna().any():
        errors.append("A missing_visit row has non-NaN eNRI.")

    # Verify direct group means from per-row eNRI against the QP state representation.
    group_mean_errors = {}
    for group in STATE_GROUPS:
        for week in STATE_WEEKS:
            label = state_label(group, week)
            rows = enri_df[
                enri_df["group"].eq(group) & enri_df["week"].eq(week)
            ]
            if len(rows) != states[label]["N"]:
                errors.append(
                    f"{label}: enri.csv row count {len(rows)} != state N {states[label]['N']}."
                )
                continue
            # There are no missing_visit rows in the current final model. If there
            # were, a group mean would need an explicit policy before comparison.
            if rows["status"].eq("missing_visit").any():
                continue
            direct_mean = float(rows["eNRI"].astype(float).mean())
            model_mean = float(solution["group_means"][label])
            err = abs(direct_mean - model_mean)
            group_mean_errors[label] = err
            if err > 1e-10:
                errors.append(
                    f"{label}: direct mean {direct_mean} != QP mean {model_mean}; error={err}."
                )

    pbs0 = enri_df[
        enri_df["group"].eq("PBS") & enri_df["week"].eq(0)
    ]["eNRI"].astype(float)
    pbs0_mean = float(pbs0.mean())
    if abs(pbs0_mean - 1.0) > QP_TOLERANCE:
        errors.append(f"PBS^0 mean eNRI={pbs0_mean}, expected 1.")

    if solution["max_order_violation"] > QP_TOLERANCE:
        errors.append(
            f"Final QP order violation {solution['max_order_violation']} exceeds tolerance."
        )
    if solution["max_positivity_violation"] > QP_TOLERANCE:
        errors.append(
            f"Final QP positivity violation {solution['max_positivity_violation']} exceeds tolerance."
        )
    if solution["eta_nonneg_violation"] > QP_TOLERANCE:
        errors.append(
            f"Final QP eta nonnegativity violation {solution['eta_nonneg_violation']} exceeds tolerance."
        )

    return errors, {
        "living_rows": int(living.sum()),
        "death_rows": int(deaths.sum()),
        "imputed_rows": int(imputed.sum()),
        "missing_visit_rows": int(missing.sum()),
        "min_live_enri": None if not len(live_vals) else float(live_vals.min()),
        "max_live_enri": None if not len(live_vals) else float(live_vals.max()),
        "pbs0_mean": pbs0_mean,
        "max_group_mean_reconstruction_error": (
            0.0 if not group_mean_errors else float(max(group_mean_errors.values()))
        ),
    }


def add_stage7_diag(rows, severity, check, detail, value="", feature="", week="", group="", mouse_id=""):
    rows.append({
        "type": "qp",
        "severity": severity,
        "check": check,
        "mouse_id": mouse_id,
        "group": group,
        "week": week,
        "feature": feature,
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
    })


def run_stage7():
    # Read and preserve the completed stage-6 CV diagnostics before upstream
    # revalidation because stage 1 intentionally rebuilds diagnostics.csv.
    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    persisted_diagnostics = pd.read_csv(diagnostics_path)
    persisted_cv = persisted_diagnostics[
        persisted_diagnostics["type"].astype(str).eq("cv")
    ].copy()
    selected = load_stage6_selection(diagnostics_path)

    # Revalidate deterministic/statistical preprocessing and state construction.
    # Stage 6 itself is not recomputed here.
    run_stage4()

    source = load_included_source()
    long_raw = build_long_table(source)
    final_std, stage3_stats = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=IMPUTATION_SEED,
    )
    errors = list(stage3_stats.get("errors", []))

    states, xbar, state_stats = build_experimental_states(final_std)
    errors.extend(validate_full_stage4(states, xbar, state_stats))

    solution, qp_meta = solve_qp_smoke(
        final_std,
        states,
        xbar,
        rho=SMOKE_RHO,
        beta=selected["beta"],
        ridge_lambda=selected["lambda"],
        C=selected["C"],
    )
    errors.extend(qp_meta.get("errors", []))

    if solution is None:
        raise RuntimeError(
            "Stage 7 final QP did not return a solution: "
            + " | ".join(errors or ["unknown solver failure"])
        )

    weights = np.asarray(solution["w"], dtype=float)
    enri_df = build_final_enri_table(final_std, xbar, weights)
    validation_errors, output_stats = validate_stage7_outputs(
        enri_df, weights, solution, states
    )
    errors.extend(validation_errors)

    # Stage-7 final model artifacts. Stage 8 may append robustness diagnostics;
    # stage 9 will perform the final packaging/checklist without changing the
    # core weights unless an explicit sensitivity decision requires it.
    weights_path = RESULTS_DIR / "weights.csv"
    enri_path = RESULTS_DIR / "enri.csv"
    model_path = RESULTS_DIR / "model.json"

    pd.DataFrame({
        "feature": MODEL_FEATURES,
        "weight": [float(x) for x in weights],
    }).to_csv(weights_path, index=False)

    enri_df.to_csv(enri_path, index=False)

    scaling = stage3_stats["scaling"]
    censor_maxima = stage3_stats["deterministic"]["censor_maxima"]
    model = {
        "excluded_mouse_ids": sorted(EXCLUDED_MOUSE_IDS),
        "group_map": GROUP_MAP,
        "features": list(MODEL_FEATURES),
        "feature_columns": {
            feature: {str(week): column for week, column in FEATURE_COLUMNS[feature].items()}
            for feature in MODEL_FEATURES
        },
        "derived_features": list(DERIVED_FEATURES),
        "censored_latency_rule": "train_feature_max",
        "censored_latency_final_maxima": {
            k: None if v is None else float(v) for k, v in censor_maxima.items()
        },
        "max_missing_per_visit": int(MAX_MISSING_PER_VISIT),
        "mean": [float(scaling["mean"][f]) for f in MODEL_FEATURES],
        "std": [float(scaling["std"][f]) for f in MODEL_FEATURES],
        "xbar_pbs0": [float(x) for x in np.asarray(xbar, dtype=float)],
        "weights": [float(x) for x in weights],
        "rho": float(SMOKE_RHO),
        "beta": float(selected["beta"]),
        "lambda": float(selected["lambda"]),
        "C": float(selected["C"]),
        "epsilon": float(POSITIVITY_EPSILON),
        "cv_tolerance": float(CV_SELECTION_TOL),
        "random_seeds": list(CV_SEEDS),
        "imputation_method": "IterativeImputer(BayesianRidge)",
        "imputation_sample_posterior": False,
        "imputation_seed": int(IMPUTATION_SEED),
        "solver_status": str(solution["solver_status"]),
        "solver_name": str(solution["solver_name"]),
        "stage": 7,
    }
    model_path.write_text(
        json.dumps(model, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[
        ~(
            diagnostics["type"].astype(str).eq("qp")
            & diagnostics["check"].astype(str).str.startswith("stage7_")
        )
    ].copy()
    rows = []

    add_stage7_diag(
        rows,
        "ok",
        "stage7_hyperparameters",
        "Final model uses the hyperparameters selected by stage-6 repeated stratified CV.",
        value=(
            f"beta={selected['beta']};lambda={selected['lambda']};C={selected['C']}"
        ),
    )
    add_stage7_diag(
        rows,
        "ok" if solution["solver_status"] in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE} else "fatal",
        "stage7_solver",
        (
            f"Final full-data QP; solver={solution['solver_name']}; "
            f"iterations={solution['solver_num_iters']}; objective={solution['objective']:.12g}."
        ),
        value=solution["solver_status"],
    )

    for feature, weight in zip(MODEL_FEATURES, weights):
        add_stage7_diag(
            rows,
            "ok",
            "stage7_weight",
            "Final standardized-feature eNRI weight selected after CV hyperparameters.",
            value=f"{float(weight):.12g}",
            feature=feature,
        )

    for pair, delta in solution["equality_deltas"].items():
        add_stage7_diag(
            rows,
            "ok",
            "stage7_equality_delta",
            "Final soft-equality residual mu_A - mu_B.",
            value=f"{delta:.12g}",
            feature=pair,
        )

    for pair, rec in solution["order_results"].items():
        add_stage7_diag(
            rows,
            "ok" if rec["violation"] <= QP_TOLERANCE else "fatal",
            "stage7_order_constraint",
            (
                f"delta={rec['delta']:.12g}; rho={SMOKE_RHO}; "
                f"eta={rec['slack']:.12g}; residual={rec['residual']:.12g}; "
                f"violation={rec['violation']:.3g}."
            ),
            value=f"{rec['residual']:.12g}",
            feature=pair,
        )

    for label, mu in sorted(solution["group_means"].items()):
        state = states[label]
        add_stage7_diag(
            rows,
            "ok",
            "stage7_group_mean",
            (
                f"Final mean eNRI including deaths as zero; "
                f"N={state['N']}, O={state['O']}, D={state['D']}, I={state['I']}."
            ),
            value=f"{mu:.12g}",
            feature=label,
            group=state["group"],
            week=state["week"],
        )

    add_stage7_diag(
        rows,
        "ok" if output_stats["min_live_enri"] >= POSITIVITY_EPSILON - QP_TOLERANCE else "fatal",
        "stage7_positivity",
        (
            f"Living rows={output_stats['living_rows']}; "
            f"min eNRI={output_stats['min_live_enri']:.12g}; "
            f"max eNRI={output_stats['max_live_enri']:.12g}; epsilon={POSITIVITY_EPSILON}."
        ),
        value=f"{output_stats['min_live_enri']:.12g}",
    )
    add_stage7_diag(
        rows,
        "ok" if abs(output_stats["pbs0_mean"] - 1.0) <= QP_TOLERANCE else "fatal",
        "stage7_pbs0_normalization",
        "Direct mean from final enri.csv for PBS week 0.",
        value=f"{output_stats['pbs0_mean']:.12g}",
        feature="PBS^0",
    )
    add_stage7_diag(
        rows,
        "ok",
        "stage7_output_counts",
        (
            f"living={output_stats['living_rows']}; death={output_stats['death_rows']}; "
            f"imputed={output_stats['imputed_rows']}; "
            f"missing_visit={output_stats['missing_visit_rows']}."
        ),
        value=len(enri_df),
    )
    add_stage7_diag(
        rows,
        "ok",
        "stage7_objective",
        (
            f"variance={solution['objective_components']['variance']:.12g}; "
            f"equality={solution['objective_components']['equality']:.12g}; "
            f"ridge={solution['objective_components']['ridge']:.12g}; "
            f"slack={solution['objective_components']['slack']:.12g}; "
            f"sum_eta={solution['slack_sum']:.12g}."
        ),
        value=f"{solution['objective']:.12g}",
    )

    for err in errors:
        add_stage7_diag(rows, "fatal", "stage7_validation", err)

    status = "READY" if not errors else "FATAL"
    add_stage7_diag(
        rows,
        "summary",
        "stage7_status",
        (
            f"Stage 7 status={status}; final_weights={len(weights)}; "
            f"enri_rows={len(enri_df)}; validation_errors={len(errors)}; "
            f"beta={selected['beta']}; lambda={selected['lambda']}; C={selected['C']}."
        ),
        value=status,
    )

    # Restore the full stage-6 CV record so final diagnostics retain the
    # hyperparameter-selection evidence together with stage-7 results.
    diagnostics = diagnostics[
        ~diagnostics["type"].astype(str).eq("cv")
    ].copy()
    merged = pd.concat(
        [diagnostics, persisted_cv, pd.DataFrame(rows)],
        ignore_index=True,
        sort=False,
    )
    merged.to_csv(diagnostics_path, index=False)

    summary = {
        "stage": 7,
        "status": status,
        "solver_status": solution["solver_status"],
        "beta": float(selected["beta"]),
        "lambda": float(selected["lambda"]),
        "C": float(selected["C"]),
        "rho": float(SMOKE_RHO),
        "model_features": int(len(MODEL_FEATURES)),
        "final_weights": int(len(weights)),
        "weight_l2_norm": float(solution["weight_l2_norm"]),
        "weight_max_abs": float(solution["weight_max_abs"]),
        "objective": float(solution["objective"]),
        "objective_components": solution["objective_components"],
        "slack_sum": float(solution["slack_sum"]),
        "slack_max": float(solution["slack_max"]),
        "max_order_violation": float(solution["max_order_violation"]),
        "max_positivity_violation": float(solution["max_positivity_violation"]),
        "living_rows": int(output_stats["living_rows"]),
        "death_rows": int(output_stats["death_rows"]),
        "imputed_rows": int(output_stats["imputed_rows"]),
        "missing_visit_rows": int(output_stats["missing_visit_rows"]),
        "min_live_enri": float(output_stats["min_live_enri"]),
        "max_live_enri": float(output_stats["max_live_enri"]),
        "pbs0_mean": float(output_stats["pbs0_mean"]),
        "max_group_mean_reconstruction_error": float(
            output_stats["max_group_mean_reconstruction_error"]
        ),
        "group_means": solution["group_means"],
        "validation_errors": errors,
        "outputs": {
            "weights": str(weights_path.relative_to(ROOT)),
            "enri": str(enri_path.relative_to(ROOT)),
            "diagnostics": str(diagnostics_path.relative_to(ROOT)),
            "model": str(model_path.relative_to(ROOT)),
        },
    }
    print("STAGE7_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if status != "READY":
        raise RuntimeError("Stage 7 validation failed: " + " | ".join(errors))


STAGE8_RHO_VALUES = (0.05, 0.2, 0.3)
STAGE8_STOCHASTIC_SEEDS = tuple(range(10))
STABILITY_SIGN_TOL = 1e-12


def _safe_cosine(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if not (math.isfinite(na) and math.isfinite(nb)) or na <= 0 or nb <= 0:
        return float("nan")
    return float((a @ b) / (na * nb))


def _sign_vector(v, tol=STABILITY_SIGN_TOL):
    v = np.asarray(v, dtype=float)
    out = np.zeros(v.shape, dtype=int)
    out[v > tol] = 1
    out[v < -tol] = -1
    return out


def _sign_agreement(a, b, tol=STABILITY_SIGN_TOL):
    sa = _sign_vector(a, tol=tol)
    sb = _sign_vector(b, tol=tol)
    return float(np.mean(sa == sb))


def _spearman_from_arrays(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    ra = pd.Series(a).rank(method="average").to_numpy(dtype=float)
    rb = pd.Series(b).rank(method="average").to_numpy(dtype=float)
    if np.std(ra) <= 0 or np.std(rb) <= 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])


def _gamma_from_solution(solution, scaling):
    std = np.asarray([float(scaling["std"][f]) for f in MODEL_FEATURES], dtype=float)
    w = np.asarray(solution["w"], dtype=float)
    if std.shape != w.shape or np.any(~np.isfinite(std)) or np.any(std <= 0):
        raise RuntimeError("Invalid scaling std for raw-scale slopes.")
    return w / std


def _compare_enri_tables(reference_enri, candidate_enri):
    ref = reference_enri[
        reference_enri["status"].isin(["observed", "imputed"])
    ][["mouse_id", "week", "eNRI"]].rename(columns={"eNRI": "ref"})
    cand = candidate_enri[
        candidate_enri["status"].isin(["observed", "imputed"])
    ][["mouse_id", "week", "eNRI"]].rename(columns={"eNRI": "cand"})
    merged = ref.merge(cand, on=["mouse_id", "week"], how="inner")
    if len(merged) < 2:
        return {
            "common_living": int(len(merged)),
            "spearman": float("nan"),
            "max_abs_diff": float("nan"),
            "median_abs_diff": float("nan"),
        }
    diff = np.abs(
        merged["cand"].to_numpy(dtype=float) - merged["ref"].to_numpy(dtype=float)
    )
    return {
        "common_living": int(len(merged)),
        "spearman": _spearman_from_arrays(
            merged["ref"].to_numpy(dtype=float),
            merged["cand"].to_numpy(dtype=float),
        ),
        "max_abs_diff": float(np.max(diff)),
        "median_abs_diff": float(np.median(diff)),
    }


def _compare_group_means(reference_solution, candidate_solution):
    labels = [state_label(g, w) for w in STATE_WEEKS for g in STATE_GROUPS]
    ref = np.asarray([reference_solution["group_means"][x] for x in labels], dtype=float)
    cand = np.asarray([candidate_solution["group_means"][x] for x in labels], dtype=float)
    return {
        "spearman": _spearman_from_arrays(ref, cand),
        "max_abs_diff": float(np.max(np.abs(cand - ref))),
        "mean_abs_diff": float(np.mean(np.abs(cand - ref))),
    }


def _feature_stability(gamma_matrix, final_gamma):
    gamma_matrix = np.asarray(gamma_matrix, dtype=float)
    final_gamma = np.asarray(final_gamma, dtype=float)
    if gamma_matrix.ndim != 2 or gamma_matrix.shape[1] != len(MODEL_FEATURES):
        raise RuntimeError(f"Invalid gamma matrix shape {gamma_matrix.shape}.")
    rows = []
    final_sign = _sign_vector(final_gamma)
    for j, feature in enumerate(MODEL_FEATURES):
        v = gamma_matrix[:, j]
        fold_sign = _sign_vector(v)
        rows.append({
            "feature": feature,
            "median": float(np.median(v)),
            "q10": float(np.quantile(v, 0.10)),
            "q90": float(np.quantile(v, 0.90)),
            "positive_frequency": float(np.mean(fold_sign > 0)),
            "negative_frequency": float(np.mean(fold_sign < 0)),
            "zero_frequency": float(np.mean(fold_sign == 0)),
            "final_sign_agreement": float(np.mean(fold_sign == final_sign[j])),
        })
    return rows


def _pairwise_cosines(vectors):
    vectors = [np.asarray(v, dtype=float) for v in vectors]
    values = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            values.append(_safe_cosine(vectors[i], vectors[j]))
    return values


def _summary_quantiles(values):
    v = np.asarray([x for x in values if math.isfinite(float(x))], dtype=float)
    if not len(v):
        return {
            "n": 0,
            "min": float("nan"),
            "q10": float("nan"),
            "median": float("nan"),
            "q90": float("nan"),
            "max": float("nan"),
        }
    return {
        "n": int(len(v)),
        "min": float(np.min(v)),
        "q10": float(np.quantile(v, 0.10)),
        "median": float(np.median(v)),
        "q90": float(np.quantile(v, 0.90)),
        "max": float(np.max(v)),
    }


def _complete_case_mouse_ids(long_raw):
    processed, stats = deterministic_preprocess(long_raw, fit_mouse_ids=None)
    ids = []
    excluded = []
    for mouse_id, rows in processed.groupby("mouse_id"):
        living = rows[~rows["death"]]
        bad = living[living["missing_count"].gt(0)]
        if bad.empty:
            ids.append(str(mouse_id))
        else:
            excluded.append({
                "mouse_id": str(mouse_id),
                "weeks": [int(x) for x in bad["week"].tolist()],
                "missing_counts": [int(x) for x in bad["missing_count"].tolist()],
            })
    return sorted(ids), excluded, stats


def add_stage8_diag(rows, diag_type, severity, check, detail, value="", feature="",
                    seed=np.nan, fold=np.nan, rho=np.nan, **kwargs):
    row = {
        "type": diag_type,
        "severity": severity,
        "check": check,
        "mouse_id": "",
        "group": "",
        "week": "",
        "feature": feature,
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
        "seed": seed,
        "fold": fold,
        "beta": np.nan,
        "lambda": np.nan,
        "C": np.nan,
        "V_pos": np.nan,
        "V_sign": np.nan,
        "V_margin": np.nan,
        "V_eq": np.nan,
        "V_var": np.nan,
        "V_w": np.nan,
        "solver_status": "",
        "rho": rho,
    }
    row.update(kwargs)
    rows.append(row)


def run_stage8():
    # Stage 7 is re-run first so the sensitivity analyses are always tied to the
    # exact current final model and to the persisted stage-6 selection.
    run_stage7()

    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    selected = load_stage6_selection(diagnostics_path)

    source = load_included_source()
    long_raw = build_long_table(source)

    # Reconstruct the deterministic full-data final model used as the reference.
    final_std, base_prep = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=IMPUTATION_SEED,
        sample_posterior=False,
    )
    errors = list(base_prep.get("errors", []))
    states, xbar, state_stats = build_experimental_states(final_std)
    errors.extend(validate_full_stage4(states, xbar, state_stats))

    base_solution, base_meta = solve_qp_smoke(
        final_std,
        states,
        xbar,
        rho=SMOKE_RHO,
        beta=selected["beta"],
        ridge_lambda=selected["lambda"],
        C=selected["C"],
    )
    errors.extend(base_meta.get("errors", []))
    if base_solution is None:
        raise RuntimeError(
            "Stage 8 could not reconstruct the stage-7 reference model: "
            + " | ".join(errors or ["unknown error"])
        )

    base_gamma = _gamma_from_solution(base_solution, base_prep["scaling"])
    base_enri = build_final_enri_table(final_std, xbar, base_solution["w"])

    rows = []

    # ------------------------------------------------------------------
    # 8A. Raw-scale slope stability across the exact accepted CV splits.
    # ------------------------------------------------------------------
    accepted_splits, rejected_splits = prepare_cv_splits(long_raw, source)
    cv_gammas = []
    cv_records = []
    cv_failures = []

    for split in accepted_splits:
        train_ids = set(split["train_ids"])
        train_df = split["final_std"][
            split["final_std"]["mouse_id"].isin(train_ids)
        ].copy()
        sol, meta = solve_qp_smoke(
            train_df,
            split["train_states"],
            split["xbar_train"],
            rho=SMOKE_RHO,
            beta=selected["beta"],
            ridge_lambda=selected["lambda"],
            C=selected["C"],
        )
        if sol is None or meta.get("errors"):
            cv_failures.append({
                "seed": int(split["seed"]),
                "fold": int(split["fold"]),
                "status": meta.get("status"),
                "errors": meta.get("errors", []),
            })
            continue

        gamma = _gamma_from_solution(sol, split["prep_stats"]["scaling"])
        cv_gammas.append(gamma)
        final_cos = _safe_cosine(gamma, base_gamma)
        cv_records.append({
            "seed": int(split["seed"]),
            "fold": int(split["fold"]),
            "gamma": gamma,
            "cosine_to_final": final_cos,
            "sign_agreement_to_final": _sign_agreement(gamma, base_gamma),
            "slack_sum": float(sol["slack_sum"]),
            "min_live_enri": float(sol["min_live_enri"]),
        })
        add_stage8_diag(
            rows,
            "stability",
            "ok",
            "stage8_cv_fold",
            (
                f"Selected-hyperparameter train fit on accepted CV split; "
                f"cosine(raw-scale gamma, final)={final_cos:.12g}; "
                f"sign agreement={_sign_agreement(gamma, base_gamma):.12g}; "
                f"slack_sum={sol['slack_sum']:.12g}."
            ),
            value=f"{final_cos:.12g}",
            seed=int(split["seed"]),
            fold=int(split["fold"]),
            solver_status=str(sol["solver_status"]),
        )

    if cv_failures:
        errors.append(
            f"{len(cv_failures)} selected-hyperparameter CV stability fits failed."
        )
        for failure in cv_failures:
            add_stage8_diag(
                rows,
                "stability",
                "fatal",
                "stage8_cv_fold_failure",
                json.dumps(failure["errors"], ensure_ascii=False),
                seed=failure["seed"],
                fold=failure["fold"],
                solver_status=str(failure["status"]),
            )

    if len(cv_gammas) != len(accepted_splits):
        errors.append(
            f"CV gamma count {len(cv_gammas)} != accepted split count {len(accepted_splits)}."
        )

    cv_feature_rows = []
    cv_pairwise_summary = _summary_quantiles([])
    cv_final_cos_summary = _summary_quantiles([])
    if cv_gammas:
        cv_gamma_matrix = np.vstack(cv_gammas)
        cv_feature_rows = _feature_stability(cv_gamma_matrix, base_gamma)
        for rec in cv_feature_rows:
            add_stage8_diag(
                rows,
                "stability",
                "ok",
                "stage8_cv_feature_gamma",
                (
                    f"raw-scale gamma across selected-hyperparameter CV train fits: "
                    f"median={rec['median']:.12g}; q10={rec['q10']:.12g}; "
                    f"q90={rec['q90']:.12g}; positive_frequency={rec['positive_frequency']:.12g}; "
                    f"negative_frequency={rec['negative_frequency']:.12g}; "
                    f"final_sign_agreement={rec['final_sign_agreement']:.12g}."
                ),
                value=f"{rec['median']:.12g}",
                feature=rec["feature"],
            )

        pairwise_cos = _pairwise_cosines(cv_gammas)
        cv_pairwise_summary = _summary_quantiles(pairwise_cos)
        final_cosines = [x["cosine_to_final"] for x in cv_records]
        cv_final_cos_summary = _summary_quantiles(final_cosines)
        add_stage8_diag(
            rows,
            "stability",
            "ok",
            "stage8_cv_pairwise_cosine",
            (
                f"Pairwise cosine similarity among {len(cv_gammas)} raw-scale gamma vectors; "
                f"n_pairs={cv_pairwise_summary['n']}; min={cv_pairwise_summary['min']:.12g}; "
                f"q10={cv_pairwise_summary['q10']:.12g}; median={cv_pairwise_summary['median']:.12g}; "
                f"q90={cv_pairwise_summary['q90']:.12g}; max={cv_pairwise_summary['max']:.12g}."
            ),
            value=f"{cv_pairwise_summary['median']:.12g}",
        )

    # ------------------------------------------------------------------
    # 8B. Complete-case sensitivity, defined at mouse level.
    # ------------------------------------------------------------------
    cc_ids, cc_excluded, cc_definition_stats = _complete_case_mouse_ids(long_raw)
    cc_std_all, cc_prep = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=cc_ids,
        random_state=IMPUTATION_SEED,
        sample_posterior=False,
    )
    cc_errors = list(cc_prep.get("errors", []))
    cc_df = cc_std_all[cc_std_all["mouse_id"].isin(set(cc_ids))].copy()

    if cc_df[
        ~cc_df["death"] & ~cc_df["status"].eq("observed")
    ].shape[0]:
        cc_errors.append("Complete-case subset contains a non-death row that is not observed.")

    cc_states, cc_xbar, cc_state_stats = build_experimental_states(
        cc_std_all,
        state_mouse_ids=cc_ids,
        reference_xbar=None,
    )
    cc_errors.extend(cc_state_stats.get("errors", []))
    cc_solution, cc_meta = solve_qp_smoke(
        cc_df,
        cc_states,
        cc_xbar,
        rho=SMOKE_RHO,
        beta=selected["beta"],
        ridge_lambda=selected["lambda"],
        C=selected["C"],
    )
    cc_errors.extend(cc_meta.get("errors", []))

    cc_summary = {
        "included_mice": int(len(cc_ids)),
        "excluded_mice": int(len(cc_excluded)),
        "excluded": cc_excluded,
    }
    if cc_solution is None or cc_errors:
        errors.append(
            "Complete-case sensitivity failed: " + " | ".join(cc_errors or ["no solution"])
        )
        for err in cc_errors or ["Complete-case solver returned no solution."]:
            add_stage8_diag(
                rows, "sensitivity", "fatal", "stage8_complete_case_failure", err
            )
    else:
        cc_gamma = _gamma_from_solution(cc_solution, cc_prep["scaling"])
        cc_enri = build_final_enri_table(cc_df, cc_xbar, cc_solution["w"])
        cc_enri_cmp = _compare_enri_tables(base_enri, cc_enri)
        cc_group_cmp = _compare_group_means(base_solution, cc_solution)
        cc_summary.update({
            "gamma_cosine": _safe_cosine(base_gamma, cc_gamma),
            "sign_agreement": _sign_agreement(base_gamma, cc_gamma),
            "living_rank_spearman": cc_enri_cmp["spearman"],
            "common_living_rows": cc_enri_cmp["common_living"],
            "individual_max_abs_diff": cc_enri_cmp["max_abs_diff"],
            "group_rank_spearman": cc_group_cmp["spearman"],
            "group_max_abs_diff": cc_group_cmp["max_abs_diff"],
            "slack_sum": float(cc_solution["slack_sum"]),
            "slack_max": float(cc_solution["slack_max"]),
            "min_live_enri": float(cc_solution["min_live_enri"]),
        })
        add_stage8_diag(
            rows,
            "sensitivity",
            "ok",
            "stage8_complete_case",
            (
                f"Mouse-level complete-case model: included={len(cc_ids)}, excluded={len(cc_excluded)}; "
                f"gamma cosine={cc_summary['gamma_cosine']:.12g}; "
                f"sign agreement={cc_summary['sign_agreement']:.12g}; "
                f"living eNRI rank Spearman={cc_summary['living_rank_spearman']:.12g}; "
                f"group-rank Spearman={cc_summary['group_rank_spearman']:.12g}; "
                f"max group mean change={cc_summary['group_max_abs_diff']:.12g}; "
                f"slack_sum={cc_summary['slack_sum']:.12g}."
            ),
            value=f"{cc_summary['gamma_cosine']:.12g}",
            solver_status=str(cc_solution["solver_status"]),
        )
        for feature, g0, g1 in zip(MODEL_FEATURES, base_gamma, cc_gamma):
            add_stage8_diag(
                rows,
                "sensitivity",
                "ok",
                "stage8_complete_case_gamma",
                (
                    f"final_gamma={float(g0):.12g}; complete_case_gamma={float(g1):.12g}; "
                    f"same_sign={int(_sign_vector([g0])[0] == _sign_vector([g1])[0])}."
                ),
                value=f"{float(g1):.12g}",
                feature=feature,
            )

    # ------------------------------------------------------------------
    # 8C. Margin sensitivity rho in {0.05,0.2,0.3}.
    # ------------------------------------------------------------------
    rho_summary = {}
    for rho in STAGE8_RHO_VALUES:
        sol, meta = solve_qp_smoke(
            final_std,
            states,
            xbar,
            rho=float(rho),
            beta=selected["beta"],
            ridge_lambda=selected["lambda"],
            C=selected["C"],
        )
        if sol is None or meta.get("errors"):
            msg = f"rho={rho}: " + " | ".join(meta.get("errors", []) or ["no solution"])
            errors.append("Margin sensitivity failed: " + msg)
            add_stage8_diag(
                rows, "sensitivity", "fatal", "stage8_rho_failure", msg, rho=float(rho),
                solver_status=str(meta.get("status")),
            )
            continue

        gamma = _gamma_from_solution(sol, base_prep["scaling"])
        enri = build_final_enri_table(final_std, xbar, sol["w"])
        enri_cmp = _compare_enri_tables(base_enri, enri)
        group_cmp = _compare_group_means(base_solution, sol)
        sign_agree = _sign_agreement(base_gamma, gamma)
        gamma_cos = _safe_cosine(base_gamma, gamma)
        rec = {
            "gamma_cosine": gamma_cos,
            "sign_agreement": sign_agree,
            "living_rank_spearman": enri_cmp["spearman"],
            "individual_max_abs_diff": enri_cmp["max_abs_diff"],
            "group_rank_spearman": group_cmp["spearman"],
            "group_max_abs_diff": group_cmp["max_abs_diff"],
            "slack_sum": float(sol["slack_sum"]),
            "slack_max": float(sol["slack_max"]),
            "min_live_enri": float(sol["min_live_enri"]),
            "max_order_violation": float(sol["max_order_violation"]),
            "max_positivity_violation": float(sol["max_positivity_violation"]),
        }
        rho_summary[str(rho)] = rec
        add_stage8_diag(
            rows,
            "sensitivity",
            "ok",
            "stage8_rho",
            (
                f"rho={rho}; gamma cosine={gamma_cos:.12g}; sign agreement={sign_agree:.12g}; "
                f"living-rank Spearman={rec['living_rank_spearman']:.12g}; "
                f"group-rank Spearman={rec['group_rank_spearman']:.12g}; "
                f"max group mean change={rec['group_max_abs_diff']:.12g}; "
                f"slack_sum={rec['slack_sum']:.12g}; slack_max={rec['slack_max']:.12g}; "
                f"max order violation={rec['max_order_violation']:.3g}."
            ),
            value=f"{gamma_cos:.12g}",
            rho=float(rho),
            solver_status=str(sol["solver_status"]),
        )
        for label, mu in sorted(sol["group_means"].items()):
            add_stage8_diag(
                rows,
                "sensitivity",
                "ok",
                "stage8_rho_group_mean",
                f"Group mean eNRI for rho sensitivity; base_rho0.1={base_solution['group_means'][label]:.12g}.",
                value=f"{float(mu):.12g}",
                feature=label,
                rho=float(rho),
            )

    # ------------------------------------------------------------------
    # 8D. Ten posterior-sampling imputation sensitivity runs.
    # ------------------------------------------------------------------
    stochastic_records = []
    stochastic_invalid = []
    stochastic_gammas = []

    for seed in STAGE8_STOCHASTIC_SEEDS:
        s_std, s_prep = fit_transform_stage3(
            long_raw,
            fit_mouse_ids=None,
            random_state=int(seed),
            sample_posterior=True,
        )
        run_errors = list(s_prep.get("errors", []))
        if not run_errors:
            s_states, s_xbar, s_state_stats = build_experimental_states(s_std)
            run_errors.extend(validate_full_stage4(s_states, s_xbar, s_state_stats))
        else:
            s_states, s_xbar = None, None

        s_solution = None
        s_meta = {"status": "NOT_SOLVED", "errors": []}
        if not run_errors:
            s_solution, s_meta = solve_qp_smoke(
                s_std,
                s_states,
                s_xbar,
                rho=SMOKE_RHO,
                beta=selected["beta"],
                ridge_lambda=selected["lambda"],
                C=selected["C"],
            )
            run_errors.extend(s_meta.get("errors", []))

        if s_solution is None or run_errors:
            rec = {
                "seed": int(seed),
                "status": s_meta.get("status"),
                "errors": run_errors or ["no solution"],
            }
            stochastic_invalid.append(rec)
            add_stage8_diag(
                rows,
                "sensitivity",
                "review",
                "stage8_stochastic_invalid",
                json.dumps(rec["errors"], ensure_ascii=False),
                seed=int(seed),
                value="invalid",
                solver_status=str(rec["status"]),
            )
            continue

        gamma = _gamma_from_solution(s_solution, s_prep["scaling"])
        stochastic_gammas.append(gamma)
        s_enri = build_final_enri_table(s_std, s_xbar, s_solution["w"])
        enri_cmp = _compare_enri_tables(base_enri, s_enri)
        group_cmp = _compare_group_means(base_solution, s_solution)
        rec = {
            "seed": int(seed),
            "gamma_cosine": _safe_cosine(base_gamma, gamma),
            "sign_agreement": _sign_agreement(base_gamma, gamma),
            "living_rank_spearman": enri_cmp["spearman"],
            "individual_max_abs_diff": enri_cmp["max_abs_diff"],
            "group_rank_spearman": group_cmp["spearman"],
            "group_max_abs_diff": group_cmp["max_abs_diff"],
            "slack_sum": float(s_solution["slack_sum"]),
            "slack_max": float(s_solution["slack_max"]),
            "min_live_enri": float(s_solution["min_live_enri"]),
        }
        stochastic_records.append(rec)
        add_stage8_diag(
            rows,
            "sensitivity",
            "ok",
            "stage8_stochastic_run",
            (
                f"sample_posterior=True; gamma cosine={rec['gamma_cosine']:.12g}; "
                f"sign agreement={rec['sign_agreement']:.12g}; "
                f"living-rank Spearman={rec['living_rank_spearman']:.12g}; "
                f"group-rank Spearman={rec['group_rank_spearman']:.12g}; "
                f"max group mean change={rec['group_max_abs_diff']:.12g}; "
                f"slack_sum={rec['slack_sum']:.12g}."
            ),
            seed=int(seed),
            value=f"{rec['gamma_cosine']:.12g}",
            solver_status=str(s_solution["solver_status"]),
        )

    stochastic_summary = {
        "requested_runs": int(len(STAGE8_STOCHASTIC_SEEDS)),
        "valid_runs": int(len(stochastic_records)),
        "invalid_runs": int(len(stochastic_invalid)),
    }
    if stochastic_records:
        for metric in (
            "gamma_cosine", "sign_agreement", "living_rank_spearman",
            "group_rank_spearman", "group_max_abs_diff", "slack_sum"
        ):
            stochastic_summary[metric] = _summary_quantiles(
                [x[metric] for x in stochastic_records]
            )

        stochastic_feature_rows = _feature_stability(
            np.vstack(stochastic_gammas), base_gamma
        )
        for rec in stochastic_feature_rows:
            add_stage8_diag(
                rows,
                "sensitivity",
                "ok",
                "stage8_stochastic_feature_gamma",
                (
                    f"Across valid posterior-imputation runs: median gamma={rec['median']:.12g}; "
                    f"q10={rec['q10']:.12g}; q90={rec['q90']:.12g}; "
                    f"final_sign_agreement={rec['final_sign_agreement']:.12g}."
                ),
                value=f"{rec['median']:.12g}",
                feature=rec["feature"],
            )
    else:
        errors.append("No valid stochastic-imputation sensitivity runs.")

    # ------------------------------------------------------------------
    # Save diagnostics only; the stage-7 core weights/eNRI/model stay unchanged.
    # ------------------------------------------------------------------
    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[
        ~diagnostics["type"].astype(str).isin(["stability", "sensitivity"])
    ].copy()

    for err in errors:
        add_stage8_diag(rows, "stability", "fatal", "stage8_validation", err)

    status = "READY" if not errors else "FATAL"
    add_stage8_diag(
        rows,
        "stability",
        "summary",
        "stage8_status",
        (
            f"Stage 8 status={status}; accepted_cv_splits={len(accepted_splits)}; "
            f"cv_selected_fits={len(cv_gammas)}; complete_case_mice={len(cc_ids)}; "
            f"rho_runs={len(rho_summary)}/{len(STAGE8_RHO_VALUES)}; "
            f"stochastic_valid={len(stochastic_records)}/{len(STAGE8_STOCHASTIC_SEEDS)}; "
            f"validation_errors={len(errors)}."
        ),
        value=status,
    )

    merged = pd.concat([diagnostics, pd.DataFrame(rows)], ignore_index=True, sort=False)
    merged.to_csv(diagnostics_path, index=False)

    feature_sign_agreements = [
        x["final_sign_agreement"] for x in cv_feature_rows
    ] if cv_feature_rows else []

    summary = {
        "stage": 8,
        "status": status,
        "selected_hyperparameters": {
            "beta": float(selected["beta"]),
            "lambda": float(selected["lambda"]),
            "C": float(selected["C"]),
            "rho": float(SMOKE_RHO),
        },
        "cv_stability": {
            "accepted_splits": int(len(accepted_splits)),
            "rejected_splits": int(len(rejected_splits)),
            "successful_selected_fits": int(len(cv_gammas)),
            "pairwise_gamma_cosine": cv_pairwise_summary,
            "cosine_to_final": cv_final_cos_summary,
            "feature_final_sign_agreement": _summary_quantiles(feature_sign_agreements),
        },
        "complete_case": cc_summary,
        "rho_sensitivity": rho_summary,
        "stochastic_imputation": stochastic_summary,
        "validation_errors": errors,
        "diagnostics_file": str(diagnostics_path.relative_to(ROOT)),
        "core_artifacts_unchanged": [
            "results/weights.csv",
            "results/enri.csv",
            "results/model.json",
        ],
    }
    print("STAGE8_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if status != "READY":
        raise RuntimeError("Stage 8 validation failed: " + " | ".join(errors))


def add_stage9_diag(rows, severity, check, detail, value=""):
    rows.append({
        "type": "final",
        "severity": severity,
        "check": check,
        "mouse_id": "",
        "group": "",
        "week": "",
        "feature": "",
        "column": "",
        "excel_cell": "",
        "value": value,
        "detail": detail,
    })


def _summary_status_value(diagnostics, check):
    rows = diagnostics[
        diagnostics["check"].astype(str).eq(check)
        & diagnostics["severity"].astype(str).eq("summary")
    ]
    if len(rows) != 1:
        return None
    return str(rows.iloc[0]["value"])


def _artifact_reproducibility(before_text, after_text, kind):
    if kind == "weights":
        a = pd.read_csv(pd.io.common.StringIO(before_text))
        b = pd.read_csv(pd.io.common.StringIO(after_text))
        same_structure = (
            list(a.columns) == list(b.columns)
            and a["feature"].astype(str).tolist() == b["feature"].astype(str).tolist()
            and len(a) == len(b)
        )
        numeric_ok = (
            same_structure
            and np.allclose(
                pd.to_numeric(a["weight"], errors="coerce").to_numpy(dtype=float),
                pd.to_numeric(b["weight"], errors="coerce").to_numpy(dtype=float),
                rtol=1e-10, atol=1e-12, equal_nan=True,
            )
        )
        return bool(numeric_ok), bool(before_text == after_text)

    if kind == "enri":
        a = pd.read_csv(pd.io.common.StringIO(before_text))
        b = pd.read_csv(pd.io.common.StringIO(after_text))
        key_cols = ["mouse_id", "group", "week", "status", "missing_count"]
        same_structure = (
            list(a.columns) == list(b.columns)
            and len(a) == len(b)
            and a[key_cols].astype(str).equals(b[key_cols].astype(str))
        )
        numeric_ok = (
            same_structure
            and np.allclose(
                pd.to_numeric(a["eNRI"], errors="coerce").to_numpy(dtype=float),
                pd.to_numeric(b["eNRI"], errors="coerce").to_numpy(dtype=float),
                rtol=1e-10, atol=1e-12, equal_nan=True,
            )
        )
        return bool(numeric_ok), bool(before_text == after_text)

    if kind == "model":
        a = json.loads(before_text)
        b = json.loads(after_text)
        scalar_keys = [
            "excluded_mouse_ids", "group_map", "features", "feature_columns",
            "derived_features", "censored_latency_rule", "max_missing_per_visit",
            "rho", "beta", "lambda", "C", "epsilon", "cv_tolerance",
            "random_seeds", "imputation_method", "imputation_sample_posterior",
            "imputation_seed", "solver_status", "solver_name",
        ]
        structural_ok = all(a.get(k) == b.get(k) for k in scalar_keys)
        array_keys = ["mean", "std", "xbar_pbs0", "weights"]
        arrays_ok = all(
            np.allclose(
                np.asarray(a.get(k, []), dtype=float),
                np.asarray(b.get(k, []), dtype=float),
                rtol=1e-10, atol=1e-12, equal_nan=True,
            )
            for k in array_keys
        )
        maxima_ok = a.get("censored_latency_final_maxima") == b.get(
            "censored_latency_final_maxima"
        )
        return bool(structural_ok and arrays_ok and maxima_ok), bool(before_text == after_text)

    raise ValueError(kind)


def run_stage9():
    # Stage 9 starts from the persisted stage-8 package, reruns stage 8 through
    # the same GitHub Actions environment, and then performs the final 25 checks.
    weights_path = RESULTS_DIR / "weights.csv"
    enri_path = RESULTS_DIR / "enri.csv"
    model_path = RESULTS_DIR / "model.json"
    diagnostics_path = RESULTS_DIR / "diagnostics.csv"
    required_paths = [weights_path, enri_path, diagnostics_path, model_path]

    missing_before = [str(p.relative_to(ROOT)) for p in required_paths if not p.exists()]
    if missing_before:
        raise RuntimeError(
            "Stage 9 requires the completed stage-8 package; missing: "
            + ", ".join(missing_before)
        )

    before = {
        "weights": weights_path.read_text(encoding="utf-8"),
        "enri": enri_path.read_text(encoding="utf-8"),
        "model": model_path.read_text(encoding="utf-8"),
        "diagnostics": diagnostics_path.read_text(encoding="utf-8"),
    }
    before_diag = pd.read_csv(pd.io.common.StringIO(before["diagnostics"]))
    before_statuses = {
        k: _summary_status_value(before_diag, k)
        for k in ("stage6_status", "stage7_status", "stage8_status")
    }

    # This reruns the full robustness layer and reconstructs the stage-7 core
    # artifacts from the persisted stage-6 hyperparameter selection.
    run_stage8()

    after = {
        "weights": weights_path.read_text(encoding="utf-8"),
        "enri": enri_path.read_text(encoding="utf-8"),
        "model": model_path.read_text(encoding="utf-8"),
        "diagnostics": diagnostics_path.read_text(encoding="utf-8"),
    }
    diagnostics = pd.read_csv(diagnostics_path)
    after_statuses = {
        k: _summary_status_value(diagnostics, k)
        for k in ("stage6_status", "stage7_status", "stage8_status")
    }

    repro = {}
    exact = {}
    for kind in ("weights", "enri", "model"):
        repro[kind], exact[kind] = _artifact_reproducibility(
            before[kind], after[kind], kind
        )
    status_repro = (
        before_statuses == after_statuses
        and all(v == "READY" for v in after_statuses.values())
    )
    reproducible = all(repro.values()) and status_repro

    source = load_included_source()
    long_raw = build_long_table(source)
    final_std, stage3_stats = fit_transform_stage3(
        long_raw,
        fit_mouse_ids=None,
        random_state=IMPUTATION_SEED,
        sample_posterior=False,
    )
    states, xbar, state_stats = build_experimental_states(final_std)
    selected = load_stage6_selection(diagnostics_path)
    solution, qp_meta = solve_qp_smoke(
        final_std,
        states,
        xbar,
        rho=SMOKE_RHO,
        beta=selected["beta"],
        ridge_lambda=selected["lambda"],
        C=selected["C"],
    )
    if solution is None:
        raise RuntimeError(
            "Stage 9 could not reconstruct the final QP: "
            + " | ".join(qp_meta.get("errors", []) or ["no solution"])
        )

    weights_df = pd.read_csv(weights_path)
    enri_df = pd.read_csv(enri_path)
    model = json.loads(model_path.read_text(encoding="utf-8"))
    deterministic_df, deterministic_stats = deterministic_preprocess(
        long_raw, fit_mouse_ids=None
    )
    accepted_splits, rejected_splits = prepare_cv_splits(long_raw, source)

    rows = []
    failures = []

    def check(number, name, condition, detail_ok, detail_bad=None, value=""):
        ok = bool(condition)
        detail = detail_ok if ok else (detail_bad or detail_ok)
        add_stage9_diag(
            rows,
            "ok" if ok else "fatal",
            f"stage9_check_{number:02d}_{name}",
            detail,
            value=value,
        )
        if not ok:
            failures.append(f"{number:02d} {name}: {detail}")
        return ok

    # Reproducibility is an explicit stage-level requirement in addition to
    # the numbered final checklist.
    add_stage9_diag(
        rows,
        "ok" if reproducible else "fatal",
        "stage9_reproducibility",
        (
            "Re-ran stage 8 and compared the regenerated core package with the "
            f"persisted stage-8 package. Numeric equivalence: {repro}; exact_bytes: "
            f"{exact}; stage statuses before={before_statuses}, after={after_statuses}."
        ),
        value="PASS" if reproducible else "FAIL",
    )
    if not reproducible:
        failures.append("reproducibility: regenerated core artifacts differ beyond tolerance")

    # 1. 54 included mice; exclusions absent.
    included_ids = set(source["mouse_id"].astype(str))
    check(
        1, "included_mice",
        len(included_ids) == 54 and not (EXCLUDED_MOUSE_IDS & included_ids),
        "54 included mice; excluded IDs 3.2 and 4.2 are absent.",
        f"included={len(included_ids)}; excluded_present={sorted(EXCLUDED_MOUSE_IDS & included_ids)}",
        value=len(included_ids),
    )

    # 2. Fixed group sizes.
    group_counts = source["group"].value_counts().to_dict()
    check(
        2, "group_sizes",
        all(int(group_counts.get(g, 0)) == n for g, n in EXPECTED_GROUP_COUNTS.items()),
        f"Fixed group sizes match {EXPECTED_GROUP_COUNTS}.",
        f"Observed group sizes: {group_counts}.",
        value=json.dumps({g: int(group_counts.get(g, 0)) for g in STATE_GROUPS}, sort_keys=True),
    )

    # 3. Alive/death counts.
    count_ok = True
    observed_counts = {}
    for week, dead_col in ((16, "dead16"), (24, "dead24")):
        observed_counts[week] = {}
        for group in STATE_GROUPS:
            sub = source[source["group"].eq(group)]
            dead = int(sub[dead_col].sum())
            alive = int((~sub[dead_col]).sum())
            observed_counts[week][group] = {"alive": alive, "death": dead}
            if alive != EXPECTED_ALIVE[week][group] or dead != EXPECTED_DEATH[week][group]:
                count_ok = False
    check(
        3, "alive_death_counts",
        count_ok,
        "Alive/death counts at weeks 16 and 24 match the control counts.",
        f"Observed counts: {observed_counts}.",
        value=json.dumps(observed_counts, sort_keys=True),
    )

    # 4. Death monotonicity.
    death_monotone = bool((~source["dead16"] | source["dead24"]).all())
    check(
        4, "death_monotonicity",
        death_monotone,
        "Death status is monotone: every week-16 death remains death at week 24.",
        "At least one week-16 death is not marked dead at week 24.",
    )

    # 5-6. Weights.
    feature_match = (
        len(weights_df) == 30
        and weights_df["feature"].astype(str).tolist() == list(MODEL_FEATURES)
    )
    check(
        5, "thirty_weights",
        feature_match,
        "weights.csv contains exactly the 30 MODEL_FEATURES in canonical order.",
        f"weight_rows={len(weights_df)}; feature_order_match={feature_match}.",
        value=len(weights_df),
    )
    weight_values = pd.to_numeric(weights_df["weight"], errors="coerce").to_numpy(dtype=float)
    check(
        6, "finite_weights",
        len(weight_values) == 30 and np.isfinite(weight_values).all(),
        "All 30 final weights are finite.",
        "At least one final weight is non-finite.",
    )

    # 7. eta >= 0.
    eta = np.asarray(solution["eta"], dtype=float)
    min_eta = float(np.min(eta))
    check(
        7, "eta_nonnegative",
        min_eta >= -QP_TOLERANCE,
        f"All order slacks are nonnegative within tolerance; min eta={min_eta:.12g}.",
        f"Negative eta beyond tolerance; min eta={min_eta:.12g}.",
        value=min_eta,
    )

    # 8. Living positivity.
    living_mask = enri_df["status"].isin(["observed", "imputed"])
    live_enri = pd.to_numeric(enri_df.loc[living_mask, "eNRI"], errors="coerce")
    min_live = float(live_enri.min())
    check(
        8, "living_positivity",
        live_enri.notna().all()
        and np.isfinite(live_enri.to_numpy(dtype=float)).all()
        and min_live >= POSITIVITY_EPSILON - QP_TOLERANCE,
        f"All observed/imputed living eNRI satisfy epsilon={POSITIVITY_EPSILON}; min={min_live:.12g}.",
        f"Living positivity failed; min={min_live:.12g}.",
        value=min_live,
    )

    # 9. PBS0 normalization.
    pbs0_mean = float(
        enri_df[enri_df["group"].eq("PBS") & enri_df["week"].eq(0)]["eNRI"].mean()
    )
    check(
        9, "pbs0_normalization",
        abs(pbs0_mean - 1.0) <= QP_TOLERANCE,
        f"Mean PBS^0 eNRI={pbs0_mean:.12g}.",
        f"PBS^0 normalization failed: {pbs0_mean:.12g}.",
        value=pbs0_mean,
    )

    # 10. Death eNRI = 0.
    death_vals = pd.to_numeric(
        enri_df.loc[enri_df["status"].eq("death"), "eNRI"], errors="coerce"
    ).to_numpy(dtype=float)
    check(
        10, "death_zero",
        len(death_vals) == 22 and np.allclose(death_vals, 0.0, rtol=0, atol=0),
        "All 22 death rows have eNRI=0 exactly.",
        f"death_rows={len(death_vals)} or nonzero death eNRI present.",
        value=len(death_vals),
    )

    # 11. Imputed rows finite.
    imputed_vals = pd.to_numeric(
        enri_df.loc[enri_df["status"].eq("imputed"), "eNRI"], errors="coerce"
    )
    check(
        11, "imputed_finite",
        len(imputed_vals) == 5
        and imputed_vals.notna().all()
        and np.isfinite(imputed_vals.to_numpy(dtype=float)).all(),
        "All 5 imputed visits have finite eNRI.",
        f"imputed_rows={len(imputed_vals)} or non-finite eNRI present.",
        value=len(imputed_vals),
    )

    # 12. missing_visit rows stay NaN.
    missing_rows = enri_df["status"].eq("missing_visit")
    check(
        12, "missing_visit_nan",
        not missing_rows.any() or enri_df.loc[missing_rows, "eNRI"].isna().all(),
        f"missing_visit policy is correct; current missing_visit rows={int(missing_rows.sum())}.",
        "At least one missing_visit has a non-NaN eNRI.",
        value=int(missing_rows.sum()),
    )

    # 13. No missing_visit in E union O.
    involved = {x for pair in EQUALITY_PAIRS + ORDER_PAIRS for x in pair}
    u_ok = all(states[label]["U"] == 0 for label in involved)
    check(
        13, "no_missing_in_constraints",
        u_ok,
        "All states used by equality/order relations have U_A=0.",
        "At least one constrained state has U_A>0.",
    )

    # 14. All 12 states are fixed-group states with expected N.
    expected_labels = {state_label(g, w) for g in STATE_GROUPS for w in STATE_WEEKS}
    fixed_state_ok = (
        set(states) == expected_labels
        and all(states[state_label(g, w)]["N"] == EXPECTED_GROUP_COUNTS[g]
                for g in STATE_GROUPS for w in STATE_WEEKS)
    )
    check(
        14, "twelve_fixed_states",
        fixed_state_ok,
        "All 12 group×week states use the fixed original group and expected denominators.",
        "State labels or fixed-group denominators do not match the design.",
        value=len(states),
    )

    # 15. CV denominators come only from the corresponding train/validation part.
    denominator_ok = True
    denominator_mismatches = []
    for split in accepted_splits:
        for group in STATE_GROUPS:
            for week in STATE_WEEKS:
                label = state_label(group, week)
                tn = int(split["train_states"][label]["N"])
                vn = int(split["val_states"][label]["N"])
                et = int(split["train_group_counts"][group])
                ev = int(split["val_group_counts"][group])
                if tn != et or vn != ev:
                    denominator_ok = False
                    denominator_mismatches.append(
                        [split["seed"], split["fold"], label, tn, et, vn, ev]
                    )
    check(
        15, "cv_denominators",
        denominator_ok and len(accepted_splits) == 22,
        "All 22 accepted CV splits use train-only and validation-only group denominators.",
        f"accepted_splits={len(accepted_splits)}; mismatches={denominator_mismatches[:5]}.",
        value=len(accepted_splits),
    )

    # 16. Positivity and variance use observed+imputed.
    o_definition_ok = all(s["O"] == s["R"] + s["I"] for s in states.values())
    Q_direct = np.mean(np.stack([states[state_label(g,w)]["S"]
        for w in STATE_WEEKS for g in STATE_GROUPS], axis=0), axis=0)
    Q_direct = 0.5 * (Q_direct + Q_direct.T)
    q_same = np.allclose(Q_direct, solution["qvar"], rtol=1e-10, atol=1e-12)
    positivity_count_ok = int(living_mask.sum()) == 140
    check(
        16, "observed_plus_imputed",
        o_definition_ok and q_same and positivity_count_ok,
        "Variance states use O_A=R_A∪I_A and positivity covers all 140 observed+imputed living visits.",
        f"O definition={o_definition_ok}; Q_var match={q_same}; positivity_rows={int(living_mask.sum())}.",
    )

    # 17. Deterministic derived identities.
    derived_ok = True
    derived_max_err = 0.0
    living_final = ~final_std["death"]
    for cfg in NOR_BLOCKS.values():
        idx = final_std.index[living_final]
        tp = final_std.loc[idx, cfg["time_p"]].astype(float).to_numpy()
        ts = final_std.loc[idx, cfg["time_s"]].astype(float).to_numpy()
        total = final_std.loc[idx, cfg["total"]].astype(float).to_numpy()
        err = float(np.max(np.abs(total - (tp + ts))))
        derived_max_err = max(derived_max_err, err)
        derived_ok = derived_ok and err <= FLOAT_TOL

        lp = final_std.loc[idx, cfg["lat_p"]].astype(float).to_numpy()
        ls = final_std.loc[idx, cfg["lat_s"]].astype(float).to_numpy()
        first = final_std.loc[idx, cfg["lat_first"]].astype(float).to_numpy()
        err = float(np.max(np.abs(first - np.minimum(lp, ls))))
        derived_max_err = max(derived_max_err, err)
        derived_ok = derived_ok and err <= FLOAT_TOL

        if cfg["di"] is not None:
            denom = tp + ts
            expected_di = np.divide(
                tp - ts, denom, out=np.zeros_like(denom), where=np.abs(denom) > FLOAT_TOL
            )
            actual_di = final_std.loc[idx, cfg["di"]].astype(float).to_numpy()
            err = float(np.max(np.abs(actual_di - expected_di)))
            derived_max_err = max(derived_max_err, err)
            derived_ok = derived_ok and err <= FLOAT_TOL
    check(
        17, "derived_identities",
        derived_ok,
        f"All deterministic NOR identities hold; max absolute residual={derived_max_err:.3g}.",
        f"Derived identity residual exceeds tolerance; max={derived_max_err:.3g}.",
        value=derived_max_err,
    )

    # 18. Latency rules and no CV leakage.
    latency_ok = True
    structural_cells = 0
    for time_feature, latency_feature in OBJECT_LATENCY_PAIRS:
        structural = (
            (~long_raw["death"])
            & long_raw[time_feature].eq(0)
            & long_raw[latency_feature].isna()
        )
        structural_cells += int(structural.sum())
        maxv = deterministic_stats["censor_maxima"][latency_feature]
        if structural.any():
            latency_ok = latency_ok and np.allclose(
                deterministic_df.loc[structural, latency_feature].astype(float).to_numpy(),
                float(maxv), rtol=0, atol=FLOAT_TOL
            )
            latency_ok = latency_ok and (
                deterministic_df.loc[structural, "censored_latency"].eq(1).all()
            )
        observed_latency = deterministic_df.loc[
            (~deterministic_df["death"]) & deterministic_df[latency_feature].notna(),
            latency_feature,
        ].astype(float)
        latency_ok = latency_ok and bool((observed_latency >= -FLOAT_TOL).all())
    cv_no_leakage = all(
        split["prep_stats"].get("fit_scope") == "train_only"
        and split["prep_stats"].get("deterministic", {}).get("fit_scope") == "train_only"
        and split["prep_stats"].get("scaling", {}).get("fit_scope") == "train_only"
        for split in accepted_splits
    )
    check(
        18, "latency_censoring",
        latency_ok and structural_cells == 28 and cv_no_leakage,
        "28 structural latency cells are flagged and encoded by the fitted feature maximum; all accepted CV preprocessing is train-only.",
        f"latency_ok={latency_ok}; structural_cells={structural_cells}; cv_no_leakage={cv_no_leakage}.",
        value=structural_cells,
    )

    # 19. DI bounds.
    di_vals = final_std.loc[living_final, "DI_NOR2"].astype(float)
    di_ok = bool(((di_vals >= -1 - FLOAT_TOL) & (di_vals <= 1 + FLOAT_TOL)).all())
    check(
        19, "di_bounds",
        di_ok,
        "All living DI_NOR2 values lie in [-1,1].",
        f"DI range=({float(di_vals.min())},{float(di_vals.max())}).",
        value=f"{float(di_vals.min()):.12g},{float(di_vals.max()):.12g}",
    )

    # 20. Reviewed scale values preserved; no unresolved fatal/blocker QC.
    accepted_qc = diagnostics[
        diagnostics["check"].astype(str).eq("accepted_scale_value")
        & diagnostics["severity"].astype(str).eq("accepted")
    ]
    bad_qc = diagnostics[
        diagnostics["type"].astype(str).eq("qc")
        & diagnostics["severity"].astype(str).isin(["fatal", "blocker"])
    ]
    review_qc = diagnostics[
        diagnostics["type"].astype(str).eq("qc")
        & diagnostics["severity"].astype(str).eq("review")
    ]
    check(
        20, "data_qc",
        len(accepted_qc) == 8 and len(bad_qc) == 0,
        f"Eight reviewed scale values are preserved; unresolved fatal/blocker QC=0; review flags={len(review_qc)}.",
        f"accepted_scale_values={len(accepted_qc)}; fatal_or_blocker_qc={len(bad_qc)}.",
        value=f"accepted={len(accepted_qc)};review={len(review_qc)}",
    )

    # 21. Identical accepted split keys for every hyperparameter triple.
    fm = diagnostics[diagnostics["check"].astype(str).eq("stage6_fold_metrics")].copy()
    accepted_keys = {
        (int(x["seed"]), int(x["fold"])) for x in accepted_splits
    }
    grid_keys_ok = len(fm) == 22 * 27
    if grid_keys_ok:
        for _, sub in fm.groupby(["beta", "lambda", "C"], dropna=False):
            keys = set(zip(sub["seed"].astype(int), sub["fold"].astype(int)))
            if keys != accepted_keys:
                grid_keys_ok = False
                break
    check(
        21, "fixed_cv_splits",
        grid_keys_ok,
        "All 27 hyperparameter combinations use the same 22 accepted seed/fold splits (594 fold fits).",
        f"stage6_fold_metric_rows={len(fm)}; expected=594.",
        value=len(fm),
    )

    # 22. Imputer/scaling/censor fitting is train-only in every accepted fold.
    train_only_ok = all(
        split["prep_stats"].get("fit_scope") == "train_only"
        and split["prep_stats"].get("deterministic", {}).get("fit_scope") == "train_only"
        and split["prep_stats"].get("scaling", {}).get("fit_scope") == "train_only"
        for split in accepted_splits
    )
    check(
        22, "train_only_preprocessing",
        train_only_ok,
        "All 22 accepted folds fit censor maxima, baseline scaling and IterativeImputer on train only.",
        "At least one accepted fold is not marked train-only for preprocessing.",
    )

    # 23. Final QP hard constraints.
    hard_qp_ok = (
        solution["solver_status"] in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE}
        and solution["max_order_violation"] <= QP_TOLERANCE
        and solution["max_positivity_violation"] <= QP_TOLERANCE
        and solution["eta_nonneg_violation"] <= QP_TOLERANCE
    )
    check(
        23, "qp_constraints",
        hard_qp_ok,
        (
            f"Final QP status={solution['solver_status']}; max order violation="
            f"{solution['max_order_violation']:.3g}; max positivity violation="
            f"{solution['max_positivity_violation']:.3g}; eta nonneg violation="
            f"{solution['eta_nonneg_violation']:.3g}."
        ),
        "At least one final hard QP constraint exceeds numerical tolerance.",
    )

    # 24. Four final files.
    files_exist = all(p.exists() and p.stat().st_size > 0 for p in required_paths)
    check(
        24, "four_artifacts",
        files_exist,
        "weights.csv, enri.csv, diagnostics.csv and model.json all exist and are non-empty.",
        "At least one required final artifact is missing or empty.",
    )

    # 25. model.json can reproduce eNRI for a complete 30-feature vector.
    model_arrays_ok = (
        model.get("features") == list(MODEL_FEATURES)
        and len(model.get("mean", [])) == 30
        and len(model.get("std", [])) == 30
        and len(model.get("xbar_pbs0", [])) == 30
        and len(model.get("weights", [])) == 30
        and np.isfinite(np.asarray(model.get("mean", []), dtype=float)).all()
        and np.isfinite(np.asarray(model.get("std", []), dtype=float)).all()
        and (np.asarray(model.get("std", []), dtype=float) > 0).all()
        and np.isfinite(np.asarray(model.get("xbar_pbs0", []), dtype=float)).all()
        and np.isfinite(np.asarray(model.get("weights", []), dtype=float)).all()
    )
    model_repro_err = float("inf")
    if model_arrays_ok:
        mmean = np.asarray(model["mean"], dtype=float)
        mstd = np.asarray(model["std"], dtype=float)
        mxbar = np.asarray(model["xbar_pbs0"], dtype=float)
        mw = np.asarray(model["weights"], dtype=float)
        Xstd = final_std.loc[living_final, MODEL_FEATURES].to_numpy(dtype=float)
        # Recover the corresponding complete raw 30-vector, then recompute eNRI
        # using only the serialization stored in model.json.
        Xraw_complete = Xstd * mstd + mmean
        Xstd_from_model = (Xraw_complete - mmean) / mstd
        predicted = 1.0 + (Xstd_from_model - mxbar) @ mw
        persisted = (
            enri_df[enri_df["status"].isin(["observed", "imputed"])]
            .set_index(["mouse_id", "week"])
        )
        final_living_meta = final_std.loc[
            living_final, ["mouse_id", "week"]
        ]
        persisted_ordered = np.array([
            float(persisted.loc[(str(mid), int(week)), "eNRI"])
            for mid, week in final_living_meta.itertuples(index=False, name=None)
        ])
        model_repro_err = float(np.max(np.abs(predicted - persisted_ordered)))
    check(
        25, "model_json_recalculation",
        model_arrays_ok and model_repro_err <= 1e-10,
        f"model.json reproduces eNRI for complete 30-feature vectors; max absolute error={model_repro_err:.3g}.",
        f"model.json sufficiency failed; arrays_ok={model_arrays_ok}; max_error={model_repro_err}.",
        value=model_repro_err,
    )

    # Record the pinned environment actually seen by the stage-9 runner.
    import importlib.metadata as importlib_metadata
    packages = {
        name: importlib_metadata.version(name)
        for name in (
            "pandas", "numpy", "openpyxl", "scikit-learn",
            "scipy", "cvxpy", "osqp"
        )
    }
    add_stage9_diag(
        rows,
        "ok",
        "stage9_environment",
        "Pinned numerical environment used by the final GitHub Actions run: "
        + json.dumps(packages, sort_keys=True),
        value="pinned",
    )

    status = "READY" if not failures else "FATAL"
    add_stage9_diag(
        rows,
        "summary",
        "stage9_status",
        (
            f"Stage 9 status={status}; numbered_checks=25; "
            f"failed_checks={len(failures)}; reproducible={reproducible}; "
            f"stage6={after_statuses['stage6_status']}; "
            f"stage7={after_statuses['stage7_status']}; "
            f"stage8={after_statuses['stage8_status']}."
        ),
        value=status,
    )

    diagnostics = pd.read_csv(diagnostics_path)
    diagnostics = diagnostics[
        ~diagnostics["type"].astype(str).eq("final")
    ].copy()
    merged = pd.concat([diagnostics, pd.DataFrame(rows)], ignore_index=True, sort=False)
    merged.to_csv(diagnostics_path, index=False)

    summary = {
        "stage": 9,
        "status": status,
        "numbered_checks": 25,
        "failed_checks": failures,
        "reproducibility": {
            "numeric_equivalence": repro,
            "exact_bytes": exact,
            "stage_statuses_before": before_statuses,
            "stage_statuses_after": after_statuses,
        },
        "environment": packages,
        "artifacts": [
            "results/weights.csv",
            "results/enri.csv",
            "results/diagnostics.csv",
            "results/model.json",
        ],
        "final_model": {
            "mice": 54,
            "model_features": 30,
            "enri_rows": int(len(enri_df)),
            "living_rows": int(living_mask.sum()),
            "death_rows": int(enri_df["status"].eq("death").sum()),
            "imputed_rows": int(enri_df["status"].eq("imputed").sum()),
            "missing_visit_rows": int(enri_df["status"].eq("missing_visit").sum()),
            "beta": float(selected["beta"]),
            "lambda": float(selected["lambda"]),
            "C": float(selected["C"]),
            "rho": float(SMOKE_RHO),
            "min_living_enri": min_live,
            "max_living_enri": float(live_enri.max()),
            "pbs0_mean": pbs0_mean,
            "slack_sum": float(solution["slack_sum"]),
            "slack_max": float(solution["slack_max"]),
        },
        "cv": {
            "accepted_splits": int(len(accepted_splits)),
            "rejected_splits": int(len(rejected_splits)),
            "fold_metric_rows": int(len(fm)),
        },
    }
    print("STAGE9_SUMMARY=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))

    if status != "READY":
        raise RuntimeError("Stage 9 final checks failed: " + " | ".join(failures))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True)
    args = parser.parse_args()

    if args.stage == 1:
        run_stage1()
    elif args.stage == 2:
        run_stage2()
    elif args.stage == 3:
        run_stage3()
    elif args.stage == 4:
        run_stage4()
    elif args.stage == 5:
        run_stage5()
    elif args.stage == 6:
        run_stage6()
    elif args.stage == 7:
        run_stage7()
    elif args.stage == 8:
        run_stage8()
    elif args.stage == 9:
        run_stage9()
    else:
        raise SystemExit(f"Stage {args.stage} is not implemented yet.")


if __name__ == "__main__":
    main()
