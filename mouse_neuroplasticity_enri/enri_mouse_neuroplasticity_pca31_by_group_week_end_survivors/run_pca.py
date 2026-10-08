#!/usr/bin/env python3
from pathlib import Path
import json
import pandas as pd
from sklearn.decomposition import PCA

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"
META=["mouse_id","group","week","status"]
GROUPS=["PBS","LPS","run","MCC"]; WEEKS=[0,16,24]
END_IDS=["1.1","1.4","1.5","2.1","3.1","3.3","3.4","4.1","4.4","6.3","8.2","8.3","8.4","9.2","9.3","10.3","11.1","12.1","12.2","12.3","12.4","12.5","16.1","16.2","16.3","17.1","17.2","17.4","18.1","18.2","19.1","19.2","19.3","19.4","20.1","20.4","20.5","21.1","21.2","21.3","21.4","21.5"]

df=pd.read_csv(SRC)
df["mouse_id"]=df["mouse_id"].astype(str)
features=[c for c in df.columns if c not in META]
df=df[df.mouse_id.isin(END_IDS)].copy()

rows=[]
for g in GROUPS:
    for w in WEEKS:
        s=df[(df.group==g)&(df.week==w)]
        X=s[features].to_numpy(float)
        pca=PCA(svd_solver="full").fit(X)
        rows.append({"group":g,"week":w,"n":len(s),"pc1_percent":100*float(pca.explained_variance_ratio_[0])})

res=pd.DataFrame(rows)
res.to_csv(OUT/"pc1_by_group_week_end_survivors.csv",index=False)
tab=res.pivot(index="group",columns="week",values="pc1_percent").reindex(GROUPS)
tab.columns=[f"week_{c}" for c in tab.columns]; tab.to_csv(OUT/"pc1_percent_table.csv")
nt=res.pivot(index="group",columns="week",values="n").reindex(GROUPS)
nt.columns=[f"week_{c}" for c in nt.columns]; nt.to_csv(OUT/"sample_sizes_table.csv")
summary={"end_survivors":42,"survivor_ids":END_IDS,"survivors_by_group":{"PBS":8,"LPS":11,"run":12,"MCC":11},"features":31,"results":rows,"note":"Survivor IDs were defined from living week-24 rows in the pre-exclusion matrix; the seven previously excluded states were not restored."}
(OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(tab.round(6)); print(nt)
