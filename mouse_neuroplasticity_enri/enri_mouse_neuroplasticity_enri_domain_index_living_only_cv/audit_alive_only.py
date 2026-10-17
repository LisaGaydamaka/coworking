#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np
import pandas as pd
import run_index_cv as model
OUT=Path(__file__).resolve().parent/"results"
KEY=["mouse_id","group","week","status"]
def read(f):return pd.read_csv(OUT/f,dtype={"mouse_id":str})
def main():
    oof=read("out_of_fold_mouse_week_predictions.csv")
    controls=[]
    for (scheme,split),chunk in oof.groupby(["scheme","split"]):
        reference=chunk[chunk.model.eq("raw31")][KEY].copy()
        reference["eNRI"]=np.where(reference.status.isin(["observed","imputed"]),1.,np.nan)
        stats=model.evaluate(reference,reference.mouse_id.unique().tolist())
        controls.append({"scheme":scheme,"split":split,"model":"constant_alive_1",
                         **{k:stats[k] for k in ("V_pos","V_sign","V_margin","V_eq",
                                                   "V_var_group_means","n_val_living")}})
    pd.DataFrame(controls).to_csv(OUT/"constant_alive_control_cv.csv",index=False)
    control_means=pd.DataFrame(controls).groupby("scheme")[
        ["V_pos","V_sign","V_margin","V_eq","V_var_group_means"]].mean().reset_index()
    control_means.to_csv(OUT/"constant_alive_control_summary.csv",index=False)
    qc=[]
    for scheme in model.SCHEMES:
        combined=None
        combined_domains=None
        for modelname in ["raw31","domain3","domain4"]:
            df=read(f"fullfit_{scheme}_{modelname}_scores.csv")
            death=df.status.eq("death");living=df.status.isin(["observed","imputed"])
            assert death.sum()==22
            assert df.loc[death,"eNRI"].isna().all()
            assert df.loc[living,"eNRI"].notna().all()
            vals=df.loc[living,"eNRI"].to_numpy(float)
            qc.append({"scheme":scheme,"model":modelname,"living_n":len(vals),
                       "death_n_with_null_score":int(death.sum()),
                       "living_mean":float(vals.mean()),"living_sd":float(vals.std(ddof=1)),
                       "living_min":float(vals.min()),"living_max":float(vals.max()),
                       "mean_abs_deviation_from_one":float(np.mean(abs(vals-1)))})
            renamed=df.rename(columns={"eNRI":f"eNRI_{modelname}"})
            combined=renamed if combined is None else combined.merge(renamed,on=KEY,validate="one_to_one")
            if modelname.startswith("domain"):
                domain=read(f"fullfit_{scheme}_{modelname}_domain_scores.csv")
                ds=[v for v in domain.columns if v.endswith("_score")]
                assert domain.loc[domain.status.eq("death"),ds].isna().all().all()
                domain=domain.rename(columns={v:f"{modelname}_{v}" for v in ds})
                combined_domains=domain if combined_domains is None else combined_domains.merge(domain,on=KEY,validate="one_to_one")
        n=155 if scheme=="clean133" else 162
        assert len(combined)==n and len(combined_domains)==n
        combined.to_csv(OUT/f"eNRI_all_models_{scheme}.csv",index=False)
        combined_domains.to_csv(OUT/f"domain_scores_all_models_{scheme}.csv",index=False)
        means=[]
        for (group,week),chunk in combined.groupby(["group","week"]):
            live=chunk[chunk.status.isin(["observed","imputed"])]
            for mod in ["raw31","domain3","domain4"]:
                means.append({"group":group,"week":week,"model":mod,
                    "n_alive":len(live),"n_death":int((chunk.status=="death").sum()),
                    "mean_alive_eNRI":float(live[f"eNRI_{mod}"].mean())})
        pd.DataFrame(means).to_csv(OUT/f"group_week_survivor_means_{scheme}.csv",index=False)
    pd.DataFrame(qc).to_csv(OUT/"all_models_death_null_qc.csv",index=False)
    correlations=read("paired_fold_domain_vs_original.csv")
    correlations.groupby(["scheme","model"])[["living_only_correlation_to_raw31","living_only_mae_to_raw31"]].mean().reset_index().to_csv(
        OUT/"living_only_pairwise_agreement.csv",index=False)
    report={"null_control":control_means.to_dict("records"),"fullfit_quality":qc,
        "oof_correlations":correlations.groupby(["scheme","model"])[
            ["living_only_correlation_to_raw31","living_only_mae_to_raw31"]].mean().reset_index().to_dict("records"),
        "all_postmortem_scores_null":True,
        "interpretation":"Only living mouse-week values enter optimization, evaluation and group means. Mortality is a separate outcome."}
    (OUT/"LIVING_ONLY_AUDIT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":
    main()
