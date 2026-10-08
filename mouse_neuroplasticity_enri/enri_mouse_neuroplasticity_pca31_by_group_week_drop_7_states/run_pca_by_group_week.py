#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"

META=["mouse_id","group","week","status"]
GROUPS=["PBS","LPS","run","MCC"]
WEEKS=[0,16,24]

df=pd.read_csv(SRC)
features=[c for c in df.columns if c not in META]
if len(features)!=31:
    raise RuntimeError(f"Expected 31 features, got {len(features)}")

rows=[]
for group in GROUPS:
    for week in WEEKS:
        sub=df[(df.group==group)&(df.week==week)].copy()
        X=sub[features].to_numpy(float)
        if len(sub)<2:
            raise RuntimeError(f"Too few rows for {group} week {week}: n={len(sub)}")
        pca=PCA(svd_solver="full")
        pca.fit(X)
        rows.append({
            "group":group,
            "week":int(week),
            "n":int(len(sub)),
            "pc1_explained_variance_ratio":float(pca.explained_variance_ratio_[0]),
            "pc1_percent":float(100*pca.explained_variance_ratio_[0]),
            "rank_max":int(min(X.shape[1],X.shape[0]-1)),
        })

res=pd.DataFrame(rows)
res.to_csv(OUT/"pc1_by_group_week.csv",index=False)

pivot=res.pivot(index="group",columns="week",values="pc1_percent").reindex(GROUPS)
pivot.columns=[f"week_{int(c)}" for c in pivot.columns]
pivot.to_csv(OUT/"pc1_percent_table.csv")

n_pivot=res.pivot(index="group",columns="week",values="n").reindex(GROUPS)
n_pivot.columns=[f"week_{int(c)}" for c in n_pivot.columns]
n_pivot.to_csv(OUT/"sample_sizes_table.csv")

summary={
    "experiment":"PCA31_BY_GROUP_WEEK_DROP_7_STATES",
    "source_matrix":"cleaned 31-feature matrix after 7 state exclusions",
    "features":31,
    "preprocessing":"no additional scaling; sklearn PCA centers within each group-week subset",
    "results":rows,
}
(OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(pivot.round(6).to_string())
print("\nSample sizes:")
print(n_pivot.to_string())
