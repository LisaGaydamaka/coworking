#!/usr/bin/env python3
"""Analyze no-feature survival baseline and live-only concordance, save factor scores."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import run_index_cv as e

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"

def read(f):
    return pd.read_csv(OUT/f,dtype={"mouse_id":str})

def baseline_control():
    pred=read("out_of_fold_mouse_week_predictions.csv")
    fields=["V_pos","V_sign","V_margin","V_eq","V_var_group_means"]
    rows=[]
    for (scheme,split),chunk in pred.groupby(["scheme","split"]):
        seen=chunk[chunk.model.eq("raw31")].copy()
        assert seen[["mouse_id","week"]].duplicated().sum()==0
        seen["eNRI"]=np.where(seen.status.eq("death"),0.,1.)
        ids=seen.mouse_id.unique().tolist()
        metrics=e.evaluate(seen,ids)
        rows.append({"scheme":scheme,"split":split,"model":"survival_only",
                     **{key:metrics[key] for key in fields},
                     "n_val_living":metrics["n_val_living"],
                     "n_val_total":metrics["n_val_total"]})
    pd.DataFrame(rows).to_csv(OUT/"survival_only_cv_metrics.csv",index=False)
    mean=pd.DataFrame(rows).groupby("scheme")[fields].mean().reset_index()
    mean.to_csv(OUT/"survival_only_cv_summary.csv",index=False)
    original=read("paired_grouped_cv_metrics.csv")
    joint=original.merge(pd.DataFrame(rows),on=["scheme","split"],
                         suffixes=("","_survival"),validate="many_to_one")
    compare=[]
    for scheme in e.SCHEMES:
        for model in ["raw31","domain3","domain4"]:
            one=joint[joint.scheme.eq(scheme)&joint.model.eq(model)]
            for metric in ["V_pos","V_sign","V_margin","V_eq","V_var_group_means"]:
                delta=one[metric].to_numpy(float)-one[metric+"_survival"].to_numpy(float)
                compare.append({"scheme":scheme,"model":model,"metric":metric,
                                "mean_delta_model_minus_survival":float(delta.mean()),
                                "fraction_model_better":float(np.mean(delta<0)),
                                "folds":len(one)})
    pd.DataFrame(compare).to_csv(OUT/"survival_baseline_comparison.csv",index=False)
    return mean.to_dict("records")

def living_concordance():
    pred=read("out_of_fold_mouse_week_predictions.csv")
    out=[]
    for (scheme,split),chunk in pred.groupby(["scheme","split"]):
        r=chunk[chunk.model.eq("raw31")][e.META[:3]+["status","eNRI"]].rename(columns={"eNRI":"raw31"})
        for m in ["domain3","domain4"]:
            d=chunk[chunk.model.eq(m)][e.META[:3]+["eNRI"]].rename(columns={"eNRI":m})
            r=r.merge(d,on=e.META[:3],validate="one_to_one")
        assert len(r)==chunk.model.value_counts().min()
        life=r.status.isin(["observed","imputed"])
        for m in ["domain3","domain4"]:
            sub=r[life]
            a,b=sub.raw31.to_numpy(float),sub[m].to_numpy(float)
            if np.std(a)<1e-12 or np.std(b)<1e-12:
                corr=np.nan
            else:corr=float(np.corrcoef(a,b)[0,1])
            out.append({"scheme":scheme,"split":split,"model":m,
                        "living_only_pearson_vs_raw31":corr,
                        "living_only_mae":float(np.mean(abs(a-b))),
                        "living_n":len(sub),
                        "all_states_pearson_vs_raw31":float(r[["raw31",m]].corr().iloc[0,1])})
    result=pd.DataFrame(out)
    result.to_csv(OUT/"out_of_fold_living_only_concordance.csv",index=False)
    return result.groupby(["scheme","model"])[
        ["living_only_pearson_vs_raw31","living_only_mae","all_states_pearson_vs_raw31"]].mean().reset_index().to_dict("records")

def save_final_domain_scores():
    base=e.load_base()
    e.FEATURES_31=list(base.MODEL_FEATURES)
    e.FEATURES_26=[x for x in e.FEATURES_31 if x not in e.DROPS]
    raw=base.build_long_table(base.load_included_source())
    raw.mouse_id=raw.mouse_id.astype(str)
    ids=raw[raw.week.eq(0)].mouse_id.unique().tolist()
    assert len(ids)==54
    rows=[]
    for scheme in e.SCHEMES:
        std,_=e.prepare(base,raw,ids,scheme)
        for k in [3,4]:
            domain,details=e.build_features(std,ids,"domain",k)
            cols=[f"X{i}" for i in range(k)]
            rename={f"X{i}":f"D{i+1}_score" for i in range(k)}
            df=domain[e.META+cols].rename(columns=rename)
            df.to_csv(OUT/f"fullfit_{scheme}_domain{k}_domain_scores.csv",index=False)
            weights=pd.DataFrame(details["W"],index=e.FEATURES_26,
                                 columns=[f"D{i+1}_regression_weight" for i in range(k)])
            weights.to_csv(OUT/f"fullfit_{scheme}_domain{k}_feature_to_domain_weights.csv",index_label="feature")
            # verify that the domain scores are exactly the ones used to fit existing eNRI
            frozen=read(f"fullfit_{scheme}_domain{k}_scores.csv")
            qm=pd.read_csv(OUT/f"fullfit_{scheme}_domain{k}_weights.csv")
            mu=df[df.week.eq(0)][list(rename.values())].mean().to_numpy(float)
            m=df[df.status.isin(["observed","imputed"])].copy()
            pred=1+(m[list(rename.values())].to_numpy(float)-mu)@qm.weight.to_numpy(float)
            j=frozen.merge(m[e.META[:3]],on=e.META[:3],validate="one_to_one")
            original=j.eNRI.to_numpy(float)
            maxerr=float(np.max(abs(pred-original))) if len(pred)==len(original) else float("nan")
            if not np.isfinite(maxerr) or maxerr>1e-8:
                raise RuntimeError(f"Stored fullfit domain scores do not reproduce index ({scheme},{k}): {maxerr}")
            rows.append({"scheme":scheme,"domains":k,"rows":len(df),
                         "baseline_n":int(df.week.eq(0).sum()),
                         "living_n":int(df.status.isin(["observed","imputed"]).sum()),
                         "death_n":int(df.status.eq("death").sum()),
                         "score_consistency_max_abs_error":maxerr})
    pd.DataFrame(rows).to_csv(OUT/"fullfit_domain_score_QA.csv",index=False)
    return rows

def alive_decomposition():
    result=[]
    for scheme in e.SCHEMES:
        for model in ["raw31","domain3","domain4"]:
            df=read(f"fullfit_{scheme}_{model}_scores.csv")
            a=df.loc[df.status.isin(["observed","imputed"]),"eNRI"].to_numpy(float)
            d=df.loc[df.status.eq("death"),"eNRI"].to_numpy(float)
            result.append({"scheme":scheme,"model":model,"living_n":len(a),
                           "death_n":len(d),
                           "living_mean":float(a.mean()),
                           "living_sd":float(a.std(ddof=1)),
                           "mean_living_abs_deviation_from_1":float(np.mean(abs(a-1))),
                           "living_range":float(np.max(a)-np.min(a)),
                           "all_deaths_score_zero":bool(np.all(d==0))})
    pd.DataFrame(result).to_csv(OUT/"fullfit_survival_contribution.csv",index=False)
    return result

def main():
    baseline=baseline_control()
    concordance=living_concordance()
    domainrows=save_final_domain_scores()
    survival=alive_decomposition()
    info={"null_survival_only_cv":baseline,
          "oof_live_only_versus_all_state_correlations":concordance,
          "saved_individual_domain_scores":domainrows,
          "fullfit_living_deviation_from_one":survival,
          "interpretation":[
            "The 1=alive/0=dead null needs no behavior predictors and can satisfy group monotonic trends because of death.",
            "Correlations computed including death states can be close to one even when independent living behavior contributes weakly.",
            "Comparing constrained train/out-of-fold sign metrics is not external neuroplasticity validation.",
            "Domain scores for death remain undefined (NaN), whereas the eNRI assigns zero to death."
          ]}
    (OUT/"NULL_MODEL_AND_SCORES.json").write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(info,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
