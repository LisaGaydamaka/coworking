#!/usr/bin/env python3
"""Read-only audit of original Excel source values for 7 PCA-excluded mouse-visits."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
DATA=ROOT.parent/"enri_mouse_neuroplasticity"/"Данные по мышам.xlsx"
REMOVED=[
    ("8.2","MCC",16,"Average_speed_NOR1","Average speed _NOR1_16"),
    ("8.3","MCC",16,"Average_speed_NOR1","Average speed _NOR1_16"),
    ("8.4","MCC",16,"Average_speed_NOR1","Average speed _NOR1_16"),
    ("9.2","MCC",24,"OFT_distance","OFT_distance_24"),
    ("16.1","PBS",24,"OFT_distance","OFT_distance_24"),
    ("17.1","PBS",24,"OFT_distance","OFT_distance_24"),
    ("21.4","run",24,"OFT_distance","OFT_distance_24"),
]
def norm_id(v):
    if pd.isna(v):return ""
    s=str(v).strip()
    if s.endswith(".0"):s=s[:-2]
    return s

def main():
    if not DATA.exists(): raise FileNotFoundError(str(DATA))
    df=pd.read_excel(DATA,sheet_name="Лист1",header=1)
    df=df.loc[df.Animal.notna()].copy()
    df["mouse_id"]=df.Animal.map(norm_id)
    records=[]
    for mid,g,w,feat,col in REMOVED:
        rows=df[df.mouse_id.eq(mid)]
        assert len(rows)==1,(mid,len(rows))
        row=rows.iloc[0]
        source_value=pd.to_numeric(pd.Series([row[col]]),errors="coerce").iloc[0]
        assert pd.notna(source_value),(mid,col)
        # compare with same-week living observations across the original cohort
        alive=~df[f"CFP_{w}"].fillna("").astype(str).str.strip().eq("Dead")
        vals=pd.to_numeric(df.loc[alive,col],errors="coerce").dropna()
        med=float(vals.median())
        mad=float((vals-med).abs().median())
        cell=get_column_letter(list(df.columns).index(col)+1)+str(int(row.name)+3)
        records.append({"mouse_id":mid,"group":g,"week":w,
                        "feature":feat,"original_excel_column":col,"excel_cell":cell,
                        "raw_excel_value":float(source_value),
                        "same_week_alive_n_nonmissing":int(len(vals)),
                        "same_week_alive_median":med,
                        "same_week_alive_mad":mad,
                        "distance_from_median_in_MAD":abs(float(source_value)-med)/mad if mad>0 else None,
                        "above_10_MAD":bool(mad>0 and abs(float(source_value)-med)>10*mad),
                        "source_already_flagged_reviewed_accepted":True})
    output=pd.DataFrame(records)
    output.to_csv(OUT/"original_excel_7_removed_values_audit.csv",index=False)

    # A related eighth measurement is accepted by the historic QC but not excluded from PCA.
    x=df[df.mouse_id.eq("21.1")]
    retained=float(pd.to_numeric(x.iloc[0]["OFT_distance_24"],errors="coerce")) if len(x)==1 else None
    info={"source_filename":DATA.name,"rows_reviewed":7,
          "original_values_found_for_all_seven":True,
          "historic_pipeline_accepted_scale_values_note":"Historical solve.py listed all 7 as accepted correct source measurements; extreme values were excluded from some PCA/EFA longitudinal sensitivity analyses for leverage, not automatically declared recording errors.",
          "other_accepted_but_NOT_excluded_state":{"mouse_id":"21.1","week":24,
                                                   "feature":"OFT_distance","raw_value":retained},
          "audit":records,
          "limitation":"Reading Excel confirms stored numerical values, but does not independently verify instrumentation or units; do not alter the workbook without external source validation."}
    (OUT/"ORIGINAL_EXCEL_AUDIT.json").write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Original Excel values for removed mouse-visits")
    print(output[["mouse_id","week","feature","raw_excel_value","same_week_alive_median","distance_from_median_in_MAD"]].to_string(index=False))

if __name__=="__main__":
    main()
