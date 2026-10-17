#!/usr/bin/env python3
"""Merge cached eNRI and per-mouse domain scores into convenient analysis tables."""
import pandas as pd
from pathlib import Path
OUT=Path(__file__).resolve().parent/"results"
def load(f):
    return pd.read_csv(OUT/f,dtype={"mouse_id":str})
KEY=["mouse_id","group","week","status"]
def main():
    for scheme in ["clean133","full140"]:
        merged=None
        for model in ["raw31","domain3","domain4"]:
            x=load(f"fullfit_{scheme}_{model}_scores.csv")
            x=x.rename(columns={"eNRI":f"eNRI_{model}"})
            merged=x if merged is None else merged.merge(x,on=KEY,validate="one_to_one")
        expected=155 if scheme=="clean133" else 162
        assert len(merged)==expected
        assert not merged[["eNRI_raw31","eNRI_domain3","eNRI_domain4"]].isna().any().any()
        merged.to_csv(OUT/f"eNRI_all_models_{scheme}.csv",index=False)
        scores=None
        for k in [3,4]:
            one=load(f"fullfit_{scheme}_domain{k}_domain_scores.csv")
            one=one.rename(columns={f"D{i}_score":f"k{k}_D{i}_score" for i in range(1,k+1)})
            scores=one if scores is None else scores.merge(one,on=KEY,validate="one_to_one")
        assert len(scores)==expected
        scores.to_csv(OUT/f"domain_scores_{scheme}_3_and_4.csv",index=False)
        rows=[]
        for (group,week),section in merged.groupby(["group","week"]):
            alive=section[section.status.isin(["observed","imputed"])]
            for m in ["raw31","domain3","domain4"]:
                rows.append({"group":group,"week":week,"model":m,
                             "states_including_deaths":len(section),
                             "alive_n":len(alive),
                             "death_n":sum(section.status.eq("death")),
                             "mean_eNRI_including_death":section[f"eNRI_{m}"].mean(),
                             "mean_eNRI_living_only":alive[f"eNRI_{m}"].mean()})
        pd.DataFrame(rows).to_csv(OUT/f"group_week_all_models_{scheme}.csv",index=False)
if __name__=="__main__":
    main()
