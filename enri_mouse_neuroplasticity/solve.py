#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter


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
                for f in FEATURE_COLUMNS
            ]
            missing = int(pd.isna(vals).sum())
            max_missing = max(max_missing, missing)
            if missing == len(FEATURE_COLUMNS):
                fully_missing_living.append((row["mouse_id"], week))
    add_diag(
        diagnostics, "ok" if not fully_missing_living else "blocker",
        "living_visit_missingness",
        f"Maximum missing among living visits: {max_missing}/35; fully missing living visits: {len(fully_missing_living)}.",
        value=max_missing,
    )
    for mid, week in fully_missing_living:
        add_diag(
            diagnostics, "blocker", "fully_missing_living_visit",
            "Living visit has all 35 model features missing.",
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=int, required=True)
    args = parser.parse_args()

    if args.stage == 1:
        run_stage1()
    else:
        raise SystemExit(f"Stage {args.stage} is not implemented yet.")


if __name__ == "__main__":
    main()
