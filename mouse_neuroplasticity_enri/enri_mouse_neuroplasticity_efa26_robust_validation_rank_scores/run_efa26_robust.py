#!/usr/bin/env python3
"""Independent robust EFA sensitivity and consistent Spearman-rank factor scores."""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import rankdata
from factor_analyzer import FactorAnalyzer

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
PARENT=ROOT.parent
FULL=PARENT/"enri_mouse_neuroplasticity_pca31_processed"/"results"/"processed_matrix_31_living.csv"
CLEAN=PARENT/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"
OLD=PARENT/"enri_mouse_neuroplasticity_efa28_deduplicated_baseline_3vs4"/"results"
META=["mouse_id","group","week","status"]
DROP_28=["Learning_T1sum","Learning_T2sum","Learning_T3sum"]
DROP_26=DROP_28+["Average_speed_NOR1","Average_speed_NOR2"]
SEED=20261013
THR=.40
NPA_MAIN=1000
NPA_OBS=500
NBOOT_MAIN=500
NBOOT_OBS=250
NBOOT_SELECTION=200
GROUPS=["PBS","LPS","run","MCC"]
WEEKS=[0,16,24]

def spearman_R(frame):
    x=frame.corr(method="spearman").to_numpy(dtype=float)
    x=(x+x.T)/2
    if not np.isfinite(x).all():
        raise ValueError("Non-finite Spearman correlation")
    smallest=float(np.linalg.eigvalsh(x)[0])
    if smallest<1e-8:
        x+=np.eye(x.shape[0])*(1e-8-smallest)
        v=np.sqrt(np.diag(x))
        x=x/np.outer(v,v)
    return x

def reduced_eigens(R):
    # SMC is a standard common-factor PA reduction (not PCA eigenvalues).
    inv=np.linalg.pinv(R,rcond=1e-9)
    d=np.diag(inv)
    smc=np.clip(1-1/np.maximum(d,1e-8),0,1)
    red=R.copy()
    np.fill_diagonal(red,smc)
    return np.linalg.eigvalsh(red)[::-1]

def ordinary_eigens(R):
    return np.linalg.eigvalsh(R)[::-1]

def parallel_analysis(frame,nrep,rng,tag):
    n,p=frame.shape
    ro=spearman_R(frame)
    obs_standard=ordinary_eigens(ro)
    obs_common=reduced_eigens(ro)
    sims={v:np.empty((nrep,p)) for v in
          ["perm_standard","perm_common","normal_standard","normal_common"]}
    z=frame.to_numpy(float)
    for b in range(nrep):
        perm=pd.DataFrame(np.column_stack([rng.permutation(z[:,j]) for j in range(p)]))
        rn=spearman_R(perm)
        sims["perm_standard"][b]=ordinary_eigens(rn)
        sims["perm_common"][b]=reduced_eigens(rn)
        rn=spearman_R(pd.DataFrame(rng.normal(size=(n,p))))
        sims["normal_standard"][b]=ordinary_eigens(rn)
        sims["normal_common"][b]=reduced_eigens(rn)
    tab=pd.DataFrame({"component":np.arange(1,p+1),
                      "observed_standard_eigen":obs_standard,
                      "observed_common_reduced_eigen":obs_common})
    details={}
    for key,v in sims.items():
        threshold=np.quantile(v,.95,axis=0)
        tab[key+"_q95"]=threshold
        if "common" in key:
            ok=obs_common>threshold
        else:
            ok=obs_standard>threshold
        tab[key+"_pass"]=ok
        tab[key+"_margin"]=(obs_common if "common" in key else obs_standard)-threshold
        details[key]={"count_total_pass":int(ok.sum()),
                      "first_nonpassing_position":int(np.where(~ok)[0][0]+1) if not np.all(ok) else None}
    tab.to_csv(OUT/(tag+"_parallel_analysis.csv"),index=False)
    return ro,tab,details

def fit_efa(R,k):
    model=FactorAnalyzer(n_factors=k,rotation="oblimin",method="minres",
                         is_corr_matrix=True,use_smc=True)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=RuntimeWarning)
        model.fit(R)
    L=np.asarray(model.loadings_,float)
    P=np.asarray(model.phi_,float) if model.phi_ is not None else np.eye(k)
    for j in range(k):
        pos=int(np.argmax(np.abs(L[:,j])))
        if L[pos,j]<0:
            L[:,j]*=-1
            P[j,:]*=-1
            P[:,j]*=-1
    if not np.isfinite(L).all() or not np.isfinite(P).all():
        raise RuntimeError("Non-finite EFA loadings")
    return L,P

def similarity(a,b):
    norms=np.linalg.norm(a,axis=0)[:,None]*np.linalg.norm(b,axis=0)[None,:]
    return (a.T@b)/np.maximum(norms,1e-12)

def align(ref,other):
    S=similarity(ref,other)
    rr,cc=linear_sum_assignment(-np.abs(S))
    aligned=np.zeros_like(ref)
    congruence=np.zeros(ref.shape[1])
    for i,j in zip(rr,cc):
        aligned[:,i]=other[:,j]*(1 if S[i,j]>=0 else -1)
        congruence[i]=abs(S[i,j])
    return aligned,congruence

def bootstrap_efa(base,ref,k,rng,number):
    load=[]
    cos=[]
    failures=0
    for b in range(number):
        idx=rng.integers(0,len(base),size=len(base))
        try:
            R=spearman_R(base.iloc[idx].reset_index(drop=True))
            L,_=fit_efa(R,k)
            aligned,s=align(ref,L)
            load.append(aligned);cos.append(s)
        except Exception:
            failures+=1
    if len(load)<int(number*.8):
        raise RuntimeError(f"Bootstrap failure k{k}: {len(load)}/{number}")
    return np.stack(load),np.stack(cos),failures

def model_fit(R,L,P,features,tag,k):
    labels=[f"D{i+1}" for i in range(k)]
    ld=pd.DataFrame(L,columns=labels)
    ld.insert(0,"feature",features)
    ld["max_abs_loading"]=np.max(np.abs(L),axis=1)
    ld["primary_domain"]=[labels[int(np.argmax(np.abs(L[j]))) ] if max(abs(L[j]))>=THR else "unassigned" for j in range(len(features))]
    ld["crossloading_count"]=np.sum(np.abs(L)>=THR,axis=1)
    ld.to_csv(OUT/f"{tag}_k{k}_loadings.csv",index=False)
    pd.DataFrame(P,index=labels,columns=labels).to_csv(OUT/f"{tag}_k{k}_factor_correlations.csv")
    residual=R-L@P@L.T
    mask=~np.eye(len(R),dtype=bool)
    r=residual[mask]
    metrics={"rmse":float(np.sqrt(np.mean(r**2))),
             "mean_absolute_error":float(np.mean(np.abs(r))),
             "n_pairs_abs_error_gt_0_2":int(np.sum(np.abs(r)>.2)/2),
             "max_absolute_offdiagonal_error":float(np.max(np.abs(r))),
             "smc_factor_communalities_min":float(np.min(np.diag(L@P@L.T))),
             "smc_factor_communalities_max":float(np.max(np.diag(L@P@L.T)))}
    # Unique unordered pairs of features
    pairs=[]
    for i in range(len(R)):
        for j in range(i+1,len(R)):
            pairs.append({"feature_a":features[i],"feature_b":features[j],
                          "observed_spearman":float(R[i,j]),
                          "fitted_efa":float((L@P@L.T)[i,j]),
                          "residual":float(residual[i,j])})
    pd.DataFrame(pairs).sort_values("residual",key=lambda s:s.abs(),ascending=False).to_csv(
        OUT/f"{tag}_k{k}_largest_residuals.csv",index=False)
    return ld,metrics

def rank_standardize(baseline,all_data,features):
    # Transform ALL visits with frozen baseline empirical midranks.
    # Pearson correlation of baseline transformed variables == Spearman R.
    Zbase=np.empty((len(baseline),len(features)))
    Zall=np.empty((len(all_data),len(features)))
    audit=[]
    for j,key in enumerate(features):
        b=baseline[key].to_numpy(float)
        vals=np.sort(b)
        ranks=rankdata(b,method="average")
        mean=ranks.mean()
        sd=ranks.std(ddof=1)
        if sd<1e-10: raise RuntimeError(f"Zero rank SD: {key}")
        Zbase[:,j]=(ranks-mean)/sd
        full=all_data[key].to_numpy(float)
        left=np.searchsorted(vals,full,side="left")
        right=np.searchsorted(vals,full,side="right")
        frozen_midrank=(left+right+1)/2
        Zall[:,j]=(frozen_midrank-mean)/sd
        # all data includes baseline, sanity check identical
        audit.append({"feature":key,"n_unique_baseline":int(len(np.unique(b))),
                      "fraction_all_values_below_baseline_min":float(np.mean(full<vals[0])),
                      "fraction_all_values_above_baseline_max":float(np.mean(full>vals[-1]))})
    return Zbase,Zall,pd.DataFrame(audit)

def factor_scores(base,all_data,features,R,L,P,tag,k):
    zbase,zall,audit=rank_standardize(base,all_data,features)
    assert np.max(np.abs(np.corrcoef(zbase,rowvar=False)-R))<1e-6, "Rank correlation mismatch"
    W=np.linalg.pinv(R,rcond=1e-8)@L@P
    sbase=zbase@W
    center=sbase.mean(0)
    sd=sbase.std(0,ddof=1)
    assert (sd>0).all()
    scores=(zall@W-center)/sd
    df=all_data[META].copy()
    for i in range(k):
        df[f"D{i+1}_score"]=scores[:,i]
    df.to_csv(OUT/f"{tag}_k{k}_rank_frozen_scores.csv",index=False)
    weights=pd.DataFrame(W,columns=[f"D{i+1}_weight" for i in range(k)])
    weights.insert(0,"feature",features)
    weights.to_csv(OUT/f"{tag}_k{k}_rank_score_weights.csv",index=False)
    audit.to_csv(OUT/f"{tag}_k{k}_rank_projection_diagnostics.csv",index=False)
    return df,W

def group_summary(scores,tag,k):
    tab=[]
    for group in GROUPS:
        for w in WEEKS:
            one=scores[(scores.group==group)&(scores.week==w)]
            for d in range(1,k+1):
                vals=one[f"D{d}_score"].to_numpy(float)
                tab.append({"group":group,"week":w,"domain":f"D{d}","n":len(vals),
                            "mean":float(np.mean(vals)),"sd":float(np.std(vals,ddof=1))})
    out=pd.DataFrame(tab)
    out.to_csv(OUT/f"{tag}_k{k}_group_week.csv",index=False)
    return out

def paired_bootstrap_stability(base,thresholds,rng):
    # Diagnostic only: null thresholds held fixed from the baseline PA.
    n=len(base);p=base.shape[1]
    accepted=[]
    for _ in range(NBOOT_SELECTION):
        idx=rng.integers(0,n,size=n)
        E=ordinary_eigens(spearman_R(base.iloc[idx].reset_index(drop=True)))
        accepted.append([int(np.sum(E>q)) for q in thresholds])
    return accepted

def main():
    clean=pd.read_csv(CLEAN,dtype={"mouse_id":str})
    full=pd.read_csv(FULL,dtype={"mouse_id":str})
    assert len(clean)==133 and len(full)==140
    assert [sum(clean.week.eq(w)) for w in WEEKS]==[54,41,38]
    assert [sum(full.week.eq(w)) for w in WEEKS]==[54,44,42]
    source_features=[c for c in clean.columns if c not in META]
    assert len(source_features)==31
    features=[c for c in source_features if c not in DROP_26]
    assert len(features)==26
    baseline=clean[clean.week.eq(0)].reset_index(drop=True)
    observed=baseline[baseline.status.eq("observed")].reset_index(drop=True)
    assert len(baseline)==54 and len(observed)==52
    assert len(baseline[baseline.status.eq("imputed")])==2
    assert len(clean[clean.status.eq("imputed")])==5

    excluded=full.merge(clean[META[:3]],on=META[:3],how="left",indicator=True)
    exc=excluded[excluded._merge.eq("left_only")].drop(columns=["_merge"])
    assert len(exc)==7 and set(zip(exc.mouse_id,exc.week))=={
        ("8.2",16),("8.3",16),("8.4",16),("9.2",24),
        ("16.1",24),("17.1",24),("21.4",24)}
    exc[META+["OFT_distance","Average_speed_NOR1"]].to_csv(
        OUT/"previously_excluded_7_audit.csv",index=False)

    corr28=baseline[[c for c in source_features if c not in DROP_28]].corr(method="spearman")
    redundant=[]
    for a,b in [("Total_distance_travelled_NOR1","Average_speed_NOR1"),
                ("Total_distance_travelled_NOR2","Average_speed_NOR2"),
                ("OFT_distance","Average_speed_OFT"),
                ("Learning_T2mean","Learning_T2max"),
                ("Learning_T3mean","Learning_T3max")]:
        redundant.append({"a":a,"b":b,"spearman_baseline":float(corr28.loc[a,b]),
                          "removed_in_26":b in DROP_26})
    pd.DataFrame(redundant).to_csv(OUT/"redundancy_audit.csv",index=False)

    rng=np.random.default_rng(SEED)
    R26,pa26,diag26=parallel_analysis(baseline[features],NPA_MAIN,rng,"main26")
    R52,pa52,diag52=parallel_analysis(observed[features],NPA_OBS,rng,"observed52")
    oldpa=pd.read_csv(OLD/"parallel_analysis_28.csv")
    comparison=[]
    for i in range(8):
        old=oldpa.iloc[i];new=pa26.iloc[i];ob=pa52.iloc[i]
        comparison.append({"component":i+1,"old28_eigen":float(old.observed_eigenvalue),
                           "old28_normal_q95":float(old.random_q95),
                           "new26_eigen":float(new.observed_standard_eigen),
                           "new26_normal_q95":float(new.normal_standard_q95),
                           "new26_permutation_q95":float(new.perm_standard_q95),
                           "new26_common_reduced_eigen":float(new.observed_common_reduced_eigen),
                           "new26_common_permutation_q95":float(new.perm_common_q95),
                           "observed52_eigen":float(ob.observed_standard_eigen),
                           "observed52_permutation_q95":float(ob.perm_standard_q95)})
    pd.DataFrame(comparison).to_csv(OUT/"pa_28_vs_26_vs_52_comparison.csv",index=False)

    selection=paired_bootstrap_stability(
        baseline[features],[pa26.perm_standard_q95.to_numpy(float),
                            pa26.perm_common_q95.to_numpy(float)],rng)
    selection_df=pd.DataFrame(selection,columns=["standard_n_pass","common_n_pass"])
    selection_df.to_csv(OUT/"bootstrap_pa_threshold_diagnostic.csv",index=False)

    models={}
    for tag,frame,R,nboot in [
        ("main26",baseline,R26,NBOOT_MAIN),
        ("observed52",observed,R52,NBOOT_OBS)]:
        models[tag]={}
        for k in [3,4]:
            L,P=fit_efa(R,k)
            ld,fitm=model_fit(R,L,P,features,tag,k)
            BL,CG,failures=bootstrap_efa(frame[features],L,k,rng,nboot)
            np.save(OUT/f"{tag}_k{k}_bootstrap_loadings.npy",BL)
            feature_stability=[]
            for i,name in enumerate(features):
                j=int(np.argmax(abs(L[i])))
                feature_stability.append({
                    "feature":name,
                    "reference_domain":ld.loc[i,"primary_domain"],
                    "reference_loading":float(L[i,j]),
                    "prob_loading_abs_ge_0_4":float(np.mean(abs(BL[:,i,j])>=THR)),
                    "prob_same_primary_domain":float(np.mean(np.argmax(abs(BL[:,i,:]),axis=1)==j))})
            pd.DataFrame(feature_stability).to_csv(OUT/f"{tag}_k{k}_feature_stability.csv",index=False)
            factors=[{"factor":f"D{j+1}",
                      "median_bootstrap_congruence":float(np.median(CG[:,j])),
                      "q10_bootstrap_congruence":float(np.quantile(CG[:,j],.10)),
                      "q90_bootstrap_congruence":float(np.quantile(CG[:,j],.90)),
                      "assigned_features":ld.loc[ld.primary_domain.eq(f"D{j+1}"),"feature"].tolist()}
                     for j in range(k)]
            models[tag][k]={"L":L,"P":P,"ld":ld,
                            "metrics":fitm,
                            "bootstrap_valid":int(len(CG)),"bootstrap_failed":failures,
                            "factors":factors}

    for k in [3,4]:
        a=models["main26"][k]["L"]
        b=models["observed52"][k]["L"]
        s=similarity(a,b)
        rr,cc=linear_sum_assignment(-abs(s))
        pd.DataFrame([{"k":k,"all54_domain":f"D{i+1}","observed52_domain":f"D{j+1}",
                      "abs_loading_cosine":float(abs(s[i,j]))}
                      for i,j in zip(rr,cc)]).to_csv(OUT/f"k{k}_observed52_loading_sensitivity.csv",index=False)

    # Old 28-feature EFA vs new 26-feature EFA on identical shared feature space.
    for k in [3,4]:
        old=pd.read_csv(OLD/f"k{k}_loadings_28.csv").set_index("feature")
        previous=old.loc[features,[f"D{i+1}" for i in range(k)]].to_numpy(float)
        current=models["main26"][k]["L"]
        S=similarity(previous,current)
        rr,cc=linear_sum_assignment(-abs(S))
        pd.DataFrame([{"k":k,"old28_factor":f"D{i+1}",
                       "new26_factor":f"D{j+1}",
                       "abs_cosine":float(abs(S[i,j]))}
                      for i,j in zip(rr,cc)]).to_csv(OUT/f"k{k}_old28_new26_loading_mapping.csv",index=False)

    # frozen rank-based scores, both for cleaned and all previously surviving visits
    for k in [3,4]:
        current=models["main26"][k]
        clean_scores,W=factor_scores(baseline,clean,features,R26,current["L"],current["P"],"clean133",k)
        full_scores,W2=factor_scores(baseline,full,features,R26,current["L"],current["P"],"full140",k)
        assert np.max(abs(W-W2))<1e-12
        matched=clean_scores.merge(full_scores,on=META,suffixes=("_clean","_full"),validate="one_to_one")
        for j in range(1,k+1):
            assert np.allclose(matched[f"D{j}_score_clean"],matched[f"D{j}_score_full"])
        clean_tab=group_summary(clean_scores,"clean133",k)
        full_tab=group_summary(full_scores,"full140",k)
        joined=clean_tab.merge(full_tab,on=["group","week","domain"],suffixes=("_clean","_full"))
        joined["mean_effect_of_restoring_seven"]=joined.mean_full-joined.mean_clean
        joined.to_csv(OUT/f"k{k}_impact_restoring_seven_states.csv",index=False)

        # Old-style raw-standardized regression factor scores vs consistent rank scores,
        # on the same 26-feature fit and same 133 states.
        mu=baseline[features].mean().to_numpy(float)
        sd=baseline[features].std(ddof=1).to_numpy(float)
        Wraw=np.linalg.pinv(R26,rcond=1e-8)@current["L"]@current["P"]
        br=((baseline[features].to_numpy(float)-mu)/sd)@Wraw
        ar=((clean[features].to_numpy(float)-mu)/sd)@Wraw
        oldscore=(ar-br.mean(0))/br.std(0,ddof=1)
        raw=pd.DataFrame({"mouse_id":clean.mouse_id,"group":clean.group,
                          "week":clean.week,"status":clean.status})
        for i in range(k):
            raw[f"D{i+1}_score"]=oldscore[:,i]
        raw.to_csv(OUT/f"clean133_k{k}_raw_formula_sensitivity_scores.csv",index=False)
        for j in range(1,k+1):
            rscore=clean_scores[f"D{j}_score"].to_numpy(float)
            source=raw[f"D{j}_score"].to_numpy(float)
            if j==1: correlations=[]
            correlations.append({"factor":f"D{j}",
                                 "overall_pearson_raw_vs_rank":float(np.corrcoef(rscore,source)[0,1]),
                                 "baseline_pearson_raw_vs_rank":float(np.corrcoef(rscore[clean.week.eq(0)],source[clean.week.eq(0)])[0,1]),
                                 "week24_pearson_raw_vs_rank":float(np.corrcoef(rscore[clean.week.eq(24)],source[clean.week.eq(24)])[0,1])})
        pd.DataFrame(correlations).to_csv(OUT/f"k{k}_raw_vs_rank_scores_correlation.csv",index=False)

    summary={
        "experiment":"EFA26_SPEARMAN_RANK_SCORE_ROBUSTNESS",
        "data":{"clean_living_rows":133,"full_living_rows":140,
                "baseline_n":54,"observed_only_baseline_n":52,
                "week_counts_clean":{"0":54,"16":41,"24":38},
                "week_counts_full":{"0":54,"16":44,"24":42},
                "seven_excluded_states_all_postbaseline":True},
        "features":{"initial":31,"previous":28,"current":26,
                    "removed_from_31":DROP_26,
                    "redundancy_audit":redundant},
        "parallel_analysis":{
            "method":"Spearman; 1000 baseline column-permutation nulls preserving ties, plus 1000 Gaussian nulls; SMC diagonal reduction for common-factor PA",
            "main_26":diag26,
            "observed_only_52":diag52,
            "first_eight":comparison,
            "bootstrap_threshold_stability_descriptive":{
                "repeats":NBOOT_SELECTION,
                "standard_factor_count_frequencies":selection_df.standard_n_pass.value_counts().sort_index().to_dict(),
                "common_factor_count_frequencies":selection_df.common_n_pass.value_counts().sort_index().to_dict(),
                "warning":"fixed original q95 thresholds reused for bootstrap samples; descriptive only"}},
        "efa":{"model":"MINRES oblimin",
               "models":{tag:{f"k{k}":{key:value for key,value in model.items() if key not in ("L","P","ld")}
                                for k,model in results.items()}
                         for tag,results in models.items()}},
        "score_projection":{
            "method":"Frozen baseline midrank / baseline midrank SD of 26 variables; regression W=pinv(Spearman R)@pattern loadings@factor correlations; baseline-standardized factor scores",
            "clean_states":133,"full_states":140,
            "outlier_reintroduction":"sensitivity only, not corrections to raw values",
            "caveat":"Rank method limits leverage from extreme later values but still includes their rank"},
        "limitations":[
            "No original raw Excel instrument readings were corrected or independently validated.",
            "Preprocessing fitted baseline scaling and imputation using all surviving weeks; strict prospective isolation requires rerunning preprocessing train-only.",
            "All models and effects are descriptive; no mixed-effects inferential tests performed.",
            "The baseline 54 (or observed-only 52) is small compared with 26 features.",
            "Four-factor fitting flexibility does not by itself establish four real latent constructs.",
        ]}
    (OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report=["# Independent EFA26 robustness and frozen-rank scoring","",
            "## Data","",
            "Clean 133 mouse-weeks, full 140, baseline 54 (52 with status=observed); all seven prior outlier-state removals were postbaseline.",
            "Removed Learning T1/T2/T3 sum (exact baseline duplicates) and NOR1/NOR2 average speed (Spearman r>0.997 with respective distance).","",
            "## Parallel analysis","",
            "| Component | 28 old eig | 26 eig | 26 Gaussian q95 | 26 perm q95 | 26 common eig | 26 common perm q95 |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for v in comparison:
        report.append(f"| {v['component']} | {v['old28_eigen']:.3f} | {v['new26_eigen']:.3f} | {v['new26_normal_q95']:.3f} | {v['new26_permutation_q95']:.3f} | {v['new26_common_reduced_eigen']:.3f} | {v['new26_common_permutation_q95']:.3f} |")
    report+=["","Factor counts: "+json.dumps(diag26,ensure_ascii=False),"",
             "Observed-only sensitivity factor counts: "+json.dumps(diag52,ensure_ascii=False),""]
    for tag in ["main26","observed52"]:
        for k in [3,4]:
            obj=models[tag][k]
            report.append(f"## {tag}: k={k}")
            report.append(f"- RMSE of off-diagonal correlations: {obj['metrics']['rmse']:.4f}; pairs |residual|>0.2: {obj['metrics']['n_pairs_abs_error_gt_0_2']}.")
            report.append(f"- Bootstrap valid: {obj['bootstrap_valid']}, failures: {obj['bootstrap_failed']}.")
            for f in obj["factors"]:
                report.append(f"- {f['factor']}: median cosine={f['median_bootstrap_congruence']:.3f}; q10={f['q10_bootstrap_congruence']:.3f}; assigned: {', '.join(f['assigned_features'])}.")
            report.append("")
    report+=["## Consistent domain-score calculation","",
             "The previous model computed regression scores using raw-scale standardized values but a Spearman-derived correlation matrix. This model replaces those with frozen baseline midrank-standardized scores. The baseline transformed values reproduce the Spearman R exactly.",
             "The same baseline midrank transformation and factor-regression weights are used for week 0, 16, and 24 without refitting.",
             "Full 140-state score projection is a descriptive sensitivity analysis of the seven exclusions. It does not validate or repair implausible raw measurements.",
             "See k3/k4 clean133 vs full140 impact tables and raw vs rank score correlations.","",
             "## Outstanding validation limitations","",
             "- Actual raw source Excel readings for the seven outliers must still be audited before editing the source.",
             "- Historical imputation pipeline used all-week fitting; strict prospective modeling would require baseline-only imputation fitting.",
             "- n=54 (or 52) is modest relative to 26 variables; treat factor counts as tentative.",
             "- Domain scores are descriptive and are not inference of causal treatments or aging effects."]
    (OUT/"REPORT.md").write_text("\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps({"pa":diag26,"pa_observed52":diag52,
                      "selection_bootstrap":summary["parallel_analysis"]["bootstrap_threshold_stability_descriptive"],
                      "models":{tag:{f"k{k}":{"metrics":obj["metrics"],"factors":obj["factors"]}
                                      for k,obj in val.items()}for tag,val in models.items()}},
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
