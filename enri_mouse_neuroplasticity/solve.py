#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter

from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer
from sklearn.linear_model import BayesianRidge


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


def fit_transform_stage3(long_raw, fit_mouse_ids=None, random_state=IMPUTATION_SEED):
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
        sample_posterior=False,
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
    else:
        raise SystemExit(f"Stage {args.stage} is not implemented yet.")


if __name__ == "__main__":
    main()
