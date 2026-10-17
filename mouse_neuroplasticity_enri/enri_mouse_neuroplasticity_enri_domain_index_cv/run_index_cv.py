#!/usr/bin/env python3
"""Fair grouped-CV comparison of 31-feature eNRI vs 3/4-domain eNRI.

All preprocessing, EFA, ranks, scale, and index weights are fitted on mouse-level
training folds. No treatment contrasts enter the directional constraints.
"""
import importlib.util
import json
import os
import warnings
from pathlib import Path

import cvxpy as cp
import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from scipy.optimize import linear_sum_assignment
from scipy.stats import rankdata
from sklearn.model_selection import StratifiedKFold

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
BASE_FILE=ROOT.parent/"enri_mouse_neuroplasticity_feature_selection_all0mean_grip_longitudinal"/"solve_all0mean_grip_longitudinal.py"
SEED=20261017
SEEDS=(17,123,2026)
FOLDS=3
K_MODELS=(3,4)
META=["mouse_id","group","week","status"]
DROPS=["Learning_T1sum","Learning_T2sum","Learning_T3sum",
       "Average_speed_NOR1","Average_speed_NOR2"]
EQS=[("PBS",0,"LPS",0),("PBS",0,"run",0),("PBS",0,"MCC",0),
     ("LPS",16,"run",16),("LPS",16,"MCC",16)]
LONGITUDINAL=[
 ("PBS",0,"PBS",16),("LPS",0,"LPS",16),
 ("run",0,"run",16),("MCC",0,"MCC",16),
 ("PBS",16,"PBS",24),("LPS",16,"LPS",24)]
GROUPS=["PBS","LPS","run","MCC"]
WEEKS=[0,16,24]
PARAMS=dict(beta=.1,lam=.1,C=.1,rho=.1,epsilon=.001)
OUTLIER_STATES={
 ("8.2",16),("8.3",16),("8.4",16),("9.2",24),
 ("16.1",24),("17.1",24),("21.4",24)}
SCHEMES=("clean133","full140")

def load_base():
    spec=importlib.util.spec_from_file_location("domain_enri_grip_longitudinal",BASE_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing historical eNRI source "+str(BASE_FILE))
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert len(m.MODEL_FEATURES)==31
    assert m.MODEL_FEATURES[-1]=="Grip"
    assert set(m.ORDER_PAIRS)=={
        (f"{a}^{wa}",f"{b}^{wb}") for a,wa,b,wb in LONGITUDINAL}
    return m

def baseline_frame(df,ids):
    return df[df.mouse_id.isin(ids)&df.week.eq(0)&df.status.isin(["observed","imputed"])].copy().reset_index(drop=True)

def rank_transform(trainbase,allrows,features):
    Ztrain=np.empty((len(trainbase),len(features)))
    Zfull=np.empty((len(allrows),len(features)))
    for j,c in enumerate(features):
        a=trainbase[c].to_numpy(float)
        ordered=np.sort(a)
        ranks=rankdata(a,method="average")
        mean=ranks.mean()
        sd=ranks.std(ddof=1)
        if sd<=0: raise RuntimeError("No rank variation "+c)
        Ztrain[:,j]=(ranks-mean)/sd
        x=allrows[c].to_numpy(float)
        left=np.searchsorted(ordered,x,side="left")
        right=np.searchsorted(ordered,x,side="right")
        Zfull[:,j]=(((left+right+1)/2)-mean)/sd
    return Ztrain,Zfull

def factor_model(frame,features,k):
    C=frame.corr(method="spearman").to_numpy(float)
    C=(C+C.T)/2
    eigen=np.linalg.eigvalsh(C)
    diag_adj=max(0.0,1e-8-eigen[0])
    if diag_adj>0:
        C=C+np.eye(len(C))*diag_adj
        v=np.sqrt(np.diag(C))
        C=C/np.outer(v,v)
    model=FactorAnalyzer(n_factors=k,method="minres",rotation="oblimin",
                         is_corr_matrix=True,use_smc=True)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=RuntimeWarning)
        model.fit(C)
    L=np.asarray(model.loadings_,float)
    P=np.asarray(model.phi_,float) if model.phi_ is not None else np.eye(k)
    # Semantic matching eliminates arbitrary EFA factor permutations and signs.
    anchors=["OFT_distance","Learning_T3mean","Time_investigating_Piramidka_NOR1"]
    if k==4: anchors.append("Time_investigating_Piramidka_zone_NOR2")
    idx=[features.index(a) for a in anchors]
    scores=np.abs(L[idx,:])
    rr,cc=linear_sum_assignment(-scores)
    reorder=[int(cc[np.where(rr==i)[0][0]]) for i in range(k)]
    L=L[:,reorder]
    P=P[np.ix_(reorder,reorder)]
    for d,i in enumerate(idx):
        if L[i,d]<0:
            L[:,d]*=-1
            P[d,:]*=-1
            P[:,d]*=-1
    if np.min(np.abs(np.diag(L[idx,:])))<.25:
        raise RuntimeError(f"Ambiguous factor anchors at k={k}")
    return C,L,P,diag_adj

def build_features(std,trainids,subset,k):
    all_live=std[std.status.isin(["observed","imputed"])].copy().reset_index(drop=True)
    if subset=="raw31":
        fields=[c for c in std.columns if c in FEATURES_31]
        # Preserve canonical input order rather than pandas indexing accidents.
        fields=FEATURES_31
        y=all_live[fields].to_numpy(float)
        z=std[META].copy()
        for j,c in enumerate(fields):
            z[f"X{j}"]=std[c].to_numpy(float)
        return z,{"fields":fields,"loadings":None,"R":None,"P":None,"transform":"baseline-standardized-original-31"}
    features=FEATURES_26
    base=baseline_frame(all_live,trainids)
    assert len(base)==len(trainids),(len(base),len(trainids))
    C,L,P,jitter=factor_model(base[features],features,k)
    zbase,zall=rank_transform(base,all_live,features)
    check=np.corrcoef(zbase,rowvar=False)
    assert np.max(np.abs(check-C))<1e-5
    W=np.linalg.pinv(C,rcond=1e-8)@L@P
    b=zbase@W
    bsd=b.std(axis=0,ddof=1)
    if (bsd<=1e-10).any():raise RuntimeError("Factor score has zero baseline variance")
    projected=(zall@W-b.mean(0))/bsd
    z=std[META].copy()
    for i in range(k):z[f"X{i}"]=np.nan
    zindex=pd.MultiIndex.from_frame(z[META[:3]])
    liveindex=pd.MultiIndex.from_frame(all_live[META[:3]])
    for i in range(k):
        ser=pd.Series(projected[:,i],index=liveindex)
        assert ser.index.is_unique
        z[f"X{i}"]=ser.reindex(zindex).to_numpy(float)
    if z.loc[z.status.eq("death"),[f"X{i}" for i in range(k)]].notna().any().any():
        raise RuntimeError("Death rows should have missing domain scores")
    return z,{"fields":[f"D{i+1}" for i in range(k)],
              "loadings":pd.DataFrame(L,index=features,
                      columns=[f"D{i+1}" for i in range(k)]),
              "R":C,"P":P,"W":W,
              "rank_jitter":jitter,
              "anchor_loadings":[float(L[features.index(a),i]) for i,a in enumerate(
                  ["OFT_distance","Learning_T3mean","Time_investigating_Piramidka_NOR1"]+
                  (["Time_investigating_Piramidka_zone_NOR2"] if k==4 else []))],
              "transform":"baseline_train_empirical_midranks_Spearman_Pearson_consistent"}

def get_state(df,feature_cols,ids,g,w):
    mouse_set=set(ids)
    sub=df[df.mouse_id.isin(mouse_set)&df.group.eq(g)&df.week.eq(w)]
    # Excluded visits are *missing* and are not assigned the score zero.
    # Dead rows legitimately contribute zero in group state averages.
    keep=sub[sub.status.isin(["observed","imputed","death"])]
    living=keep[keep.status.isin(["observed","imputed"])]
    dead=keep[keep.status.eq("death")]
    if len(keep)<1:raise RuntimeError(f"No usable state {g}^{w}")
    x=living[feature_cols].to_numpy(float)
    if len(x) and not np.isfinite(x).all():
        raise RuntimeError(f"Nonfinite state features {g}^{w}")
    return dict(n=len(keep),living=len(living),dead=len(dead),
                X=x,death_ids=dead.mouse_id.tolist())

def make_state_collection(df,ids,cols,mu):
    out={}
    p=len(cols)
    for g in GROUPS:
        for w in WEEKS:
            st=get_state(df,cols,ids,g,w)
            n=st["n"]; X=st["X"];m=len(X)
            st["a"]=m/n
            st["b"]=np.sum(X-mu,axis=0)/n if m else np.zeros(p)
            st["S"]=np.cov(X,rowvar=False,ddof=1) if m>=2 else np.zeros((p,p))
            if st["S"].shape!=(p,p):
                st["S"]=np.reshape(st["S"],(p,p))
            out[(g,w)]=st
    return out

def solve_weights(df,trainids,feature_cols):
    baseline=get_state(df,feature_cols,trainids,"PBS",0)
    allbaseline=df[df.mouse_id.isin(trainids)&df.week.eq(0)&df.status.isin(["observed","imputed"])]
    mu=allbaseline[feature_cols].to_numpy(float).mean(axis=0)
    assert np.isfinite(mu).all()
    states=make_state_collection(df,trainids,feature_cols,mu)
    # Same equal-weight average of 12 within-state covariances as historical QP.
    Q=np.mean(np.stack([states[(g,w)]["S"] for g in GROUPS for w in WEEKS]),axis=0)
    Q=(Q+Q.T)/2
    smallest=float(np.linalg.eigvalsh(Q)[0])
    Q+=np.eye(len(Q))*max(0.0,-smallest+1e-10)
    w=cp.Variable(len(feature_cols))
    eta=cp.Variable(len(LONGITUDINAL),nonneg=True)
    equal=[(states[(g,w0)]["a"]-states[(h,w1)]["a"])+
           (states[(g,w0)]["b"]-states[(h,w1)]["b"])@w
           for g,w0,h,w1 in EQS]
    margin=[(states[(g,w0)]["a"]-states[(h,w1)]["a"])+
            (states[(g,w0)]["b"]-states[(h,w1)]["b"])@w
            for g,w0,h,w1 in LONGITUDINAL]
    train=df[df.mouse_id.isin(trainids)&df.status.isin(["observed","imputed"])]
    X=train[feature_cols].to_numpy(float)
    constraints=[margin[i]>=PARAMS["rho"]-eta[i] for i in range(len(margin))]
    constraints.append(1+(X-mu)@w>=PARAMS["epsilon"])
    objective=cp.quad_form(w,cp.psd_wrap(Q))+PARAMS["lam"]*cp.sum_squares(w)+PARAMS["C"]*cp.sum(eta)+PARAMS["beta"]*cp.sum_squares(cp.hstack(equal))
    prob=cp.Problem(cp.Minimize(objective),constraints)
    exc=None
    for solver in ["OSQP","CLARABEL"]:
        try:
            prob.solve(solver=solver,warm_start=False,verbose=False)
        except Exception as e:
            exc=str(e)
            continue
        if prob.status in ["optimal","optimal_inaccurate"] and w.value is not None:
            break
    if w.value is None or prob.status not in ["optimal","optimal_inaccurate"]:
        raise RuntimeError(f"QP failure {prob.status} {exc}")
    weights=np.asarray(w.value,float).ravel()
    if not np.isfinite(weights).all():
        raise RuntimeError("Nonfinite QP weights")
    norm_error=abs(np.mean(1+(allbaseline[feature_cols].to_numpy(float)-mu)@weights)-1)
    assert norm_error<1e-8
    tval=1+(X-mu)@weights
    if np.min(tval)<PARAMS["epsilon"]-1e-5:
        raise RuntimeError("Train positivity violated "+str(float(np.min(tval))))
    return mu,weights,dict(solver_status=prob.status,solver=prob.solver_stats.solver_name,
                           train_min=float(np.min(tval)),
                           train_norm_error=float(norm_error),
                           weight_norm=float(np.linalg.norm(weights)),
                           sum_slack=float(np.sum(eta.value)),
                           objective=float(prob.value))

def produce_index(df,mu,weights,cols):
    out=df[META].copy()
    out["eNRI"]=np.nan
    live=df.status.isin(["observed","imputed"])
    X=df.loc[live,cols].to_numpy(float)
    out.loc[live,"eNRI"]=1+(X-mu)@weights
    out.loc[df.status.eq("death"),"eNRI"]=0.
    return out

def evaluate(index,ids):
    part=index[index.mouse_id.isin(ids)]
    vals=part[part.status.isin(["observed","imputed"])]["eNRI"].to_numpy(float)
    pos=float(np.mean(vals<PARAMS["epsilon"])) if len(vals) else np.nan
    if not np.isfinite(pos):raise RuntimeError("No validation living records")
    means={}
    for g in GROUPS:
        for w in WEEKS:
            one=part[part.group.eq(g)&part.week.eq(w)&part.status.isin(["observed","imputed","death"])]
            if len(one)==0:raise RuntimeError(f"No validation state {g}^{w}")
            means[(g,w)]=float(one.eNRI.mean())
    margins=np.array([means[(a,t)]-means[(b,u)] for a,t,b,u in LONGITUDINAL])
    eqs=np.array([means[(a,t)]-means[(b,u)] for a,t,b,u in EQS])
    return {
        "V_pos":pos,
        "min_living_eNRI":float(np.min(vals)),
        "V_sign":float(np.mean(margins<0)),
        "V_margin":float(np.mean(np.maximum(0,PARAMS["rho"]-margins))),
        "V_eq":float(np.mean(eqs**2)),
        "V_var_group_means":float(np.var(np.array(list(means.values())),ddof=1)),
        "mean_eNRI_living":float(np.mean(vals)),
        "n_val_living":int(len(vals)),
        "n_val_total":int(len(part)),
        "validation_group_means":{f"{g}^{w}":v for (g,w),v in means.items()},
    }

def prepare(base,raw,fitids,scheme):
    df=raw
    if scheme=="clean133":
        remove=df.apply(lambda row:(str(row.mouse_id),int(row.week)) in OUTLIER_STATES,axis=1)
        assert sum(remove)==7
        df=df.loc[~remove].reset_index(drop=True)
    out,info=base.fit_transform_stage3(df,fit_mouse_ids=set(fitids),
                                       random_state=base.IMPUTATION_SEED,
                                       sample_posterior=False)
    if info.get("errors"):raise RuntimeError("Preprocessing "+str(info["errors"]))
    keep=out.status.isin(["observed","imputed","death"])
    out=out.loc[keep].copy().reset_index(drop=True)
    assert out[META[:3]].duplicated().sum()==0
    if out.loc[out.status.isin(["observed","imputed"]),FEATURES_31].isna().any().any():
        raise RuntimeError("Unimputed values")
    return out,info

def run_split(base,raw,allids,trainids,valids,scheme,splitname,
              raw_output=False):
    processed,prep=prepare(base,raw,trainids,scheme)
    rows=[]
    preds={}
    for model in ["raw31","domain3","domain4"]:
        k=None if model=="raw31" else int(model[-1])
        view,details=build_features(processed,trainids,
                                    "raw31" if k is None else "domain",k)
        cols=[f"X{i}" for i in range(31 if k is None else k)]
        mu,w,trainmeta=solve_weights(view,trainids,cols)
        index=produce_index(view,mu,w,cols)
        stats=evaluate(index,valids) if valids is not None else evaluate(index,trainids)
        summary={
            "scheme":scheme,"split":splitname,"model":model,
            "train_mice":len(trainids),"validation_mice":len(valids) if valids is not None else 0,
            "N_parameters":len(w),
            **{k:stats[k] for k in stats if k!="validation_group_means"},
            **trainmeta}
        rows.append(summary)
        if valids is not None:
            pred=index[index.mouse_id.isin(valids)].copy()
            pred["model"]=model;pred["split"]=splitname;pred["scheme"]=scheme
            preds[model]=pred
        else:
            index.to_csv(OUT/f"fullfit_{scheme}_{model}_scores.csv",index=False)
            pd.DataFrame({"parameter":details["fields"],"weight":w}).to_csv(
                OUT/f"fullfit_{scheme}_{model}_weights.csv",index=False)
            if details["loadings"] is not None:
                details["loadings"].to_csv(
                    OUT/f"fullfit_{scheme}_{model}_loadings.csv",index_label="feature")
                pd.DataFrame(details["P"]).to_csv(
                    OUT/f"fullfit_{scheme}_{model}_factor_correlations.csv",index=False)
                (OUT/f"fullfit_{scheme}_{model}_anchors.json").write_text(
                    json.dumps(details["anchor_loadings"],indent=2)+"\n")
    if valids is not None:
        joined=preds["raw31"][META[:3]+["eNRI"]].rename(columns={"eNRI":"raw31"})
        for m in ["domain3","domain4"]:
            joined=joined.merge(
                preds[m][META[:3]+["eNRI"]].rename(columns={"eNRI":m}),
                on=META[:3],validate="one_to_one")
        comparisons=[]
        for m in ["domain3","domain4"]:
            r=joined[["raw31",m]].corr().iloc[0,1]
            mae=float(np.mean(np.abs(joined["raw31"]-joined[m])))
            comparisons.append({"split":splitname,"scheme":scheme,"model":m,
                                "same_fold_correlation_to_raw31":float(r),
                                "mae_to_raw31":mae,"N":len(joined)})
        return rows,pd.concat(preds.values(),ignore_index=True),comparisons
    return rows,None,None

def main():
    global FEATURES_31,FEATURES_26
    base=load_base()
    FEATURES_31=list(base.MODEL_FEATURES)
    FEATURES_26=[s for s in FEATURES_31 if s not in DROPS]
    assert len(FEATURES_26)==26
    source=base.load_included_source()
    raw=base.build_long_table(source)
    raw.mouse_id=raw.mouse_id.astype(str)
    assert len(raw)==162, len(raw)
    assert sum(raw.status.eq("death"))==22
    baseline=raw[raw.week.eq(0)]
    mice=baseline[["mouse_id","group"]].drop_duplicates().sort_values("mouse_id").reset_index(drop=True)
    assert len(mice)==54 and mice.group.value_counts().to_dict()=={"run":15,"LPS":14,"MCC":14,"PBS":11}
    ids=mice.mouse_id.to_numpy(str)
    groups=mice.group.to_numpy(str)
    all_rows=[];all_preds=[];all_compare=[];splits=[]
    for seed in SEEDS:
        skf=StratifiedKFold(n_splits=FOLDS,shuffle=True,random_state=seed)
        for fi,(train_i,val_i) in enumerate(skf.split(ids,groups)):
            tr=ids[train_i].tolist()
            va=ids[val_i].tolist()
            name=f"seed{seed}_fold{fi}"
            assert len(set(tr)&set(va))==0
            assert len(set(tr)|set(va))==54
            splits.append({"name":name,"train_ids":tr,"validation_ids":va})
            for scheme in SCHEMES:
                rows,pred,comps=run_split(base,raw,ids,tr,va,scheme,name)
                all_rows.extend(rows)
                all_preds.append(pred)
                all_compare.extend(comps)
    cv=pd.DataFrame(all_rows)
    cv.to_csv(OUT/"paired_grouped_cv_metrics.csv",index=False)
    allpred=pd.concat(all_preds,ignore_index=True)
    allpred.to_csv(OUT/"out_of_fold_mouse_week_predictions.csv",index=False)
    comp=pd.DataFrame(all_compare)
    comp.to_csv(OUT/"paired_fold_domain_vs_original.csv",index=False)
    (OUT/"cv_mouse_splits.json").write_text(json.dumps(splits,indent=2,ensure_ascii=False)+"\n")
    fullfits=[]
    for scheme in SCHEMES:
        rows,_,_=run_split(base,raw,ids,ids.tolist(),None,scheme,"fullfit")
        fullfits+=rows
    pd.DataFrame(fullfits).to_csv(OUT/"fullfit_metrics.csv",index=False)
    aggregate=[]
    for (scheme,model),g in cv.groupby(["scheme","model"]):
        rec={"scheme":scheme,"model":model,"folds":len(g),
             "train_mice_mean":float(g.train_mice.mean()),
             "validation_mice_mean":float(g.validation_mice.mean())}
        for metric in ["V_pos","V_sign","V_margin","V_eq","V_var_group_means",
                       "min_living_eNRI","mean_eNRI_living","weight_norm","sum_slack"]:
            rec[metric+"_mean"]=float(g[metric].mean())
            rec[metric+"_median"]=float(g[metric].median())
            rec[metric+"_sd"]=float(g[metric].std(ddof=1))
        aggregate.append(rec)
    summary=pd.DataFrame(aggregate)
    summary.to_csv(OUT/"cv_summary.csv",index=False)
    paired=[]
    for sch in SCHEMES:
        bas=cv[cv.scheme.eq(sch)&cv.model.eq("raw31")].set_index("split")
        for model in ["domain3","domain4"]:
            trial=cv[cv.scheme.eq(sch)&cv.model.eq(model)].set_index("split")
            assert set(bas.index)==set(trial.index)
            for metric in ["V_pos","V_sign","V_margin","V_eq","V_var_group_means"]:
                dif=(trial[metric]-bas[metric]).to_numpy(float)
                paired.append({"scheme":sch,"model":model,"metric":metric,
                               "delta_domain_minus_raw31_mean":float(dif.mean()),
                               "delta_median":float(np.median(dif)),
                               "fraction_folds_domain_better":float(np.mean(dif<0)),
                               "paired_n_splits":len(dif)})
    pd.DataFrame(paired).to_csv(OUT/"paired_cv_delta_summary.csv",index=False)
    overall={"data":{"mice":54,"week0":54,"alive_before_seven":140,
                     "living_clean":133,"death_states":22,
                     "previous_excluded_mouse_weeks":7},
             "models":["raw31","domain3","domain4"],
             "schemes":list(SCHEMES),
             "cv":{"seeds":SEEDS,"n_folds_per_seed":FOLDS,
                   "splits":len(splits),"full_pipeline_train_only":True,
                   "group_stratified_mouse_split":True,
                   "features_per_domain":26},
             "index_objective":{
                "terms":"mean-12-state variance + ridge_lambda*|w|^2 + C*sum(slack) + beta*sum(soft baseline/16 equalities)^2",
                "directional_constraints":"only 6 within-group time inequalities; no between-treatment superiority conditions",
                "parameters":PARAMS,
                "death_eNRI_zero":True,
                "missing_outlier_visit_policy":"Excluded observations omitted from state denominators, not coded as deaths"},
             "fit_and_comparison":aggregate,
             "limitations":[
                 "No observed biological ground-truth neuroplasticity outcome; comparison uses constraint validation and descriptive concordance, not predictive proof.",
                 "Group-and-week constraints are imposed in train; valid heldout folds test their out-of-sample satisfaction, not causality.",
                 "Hyperparameters held fixed from historical project and are not re-tuned to favor either model.",
                 "Deterministic preprocessing and IterativeImputer fit on training MICE only, though training weeks 16/24 may help impute training baseline.",
                 "The clean133 policy completely omits seven previously flagged alive mouse-weeks and excludes them from state means; missingness may not be random.",
                 "No external validation or formal inference on treatment effect."
             ]}
    (OUT/"SUMMARY.json").write_text(json.dumps(overall,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"rows":len(cv),"models":aggregate,"paired":paired,
                      "fullfit":fullfits},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
