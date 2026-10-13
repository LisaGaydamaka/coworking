#!/usr/bin/env python3
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from scipy.optimize import linear_sum_assignment

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"
OLD=ROOT.parent/"enri_mouse_neuroplasticity_efa31_domains_3vs4_longitudinal"/"results"
DROP=["Learning_T1sum","Learning_T2sum","Learning_T3sum"]
META=["mouse_id","group","week","status"]
NPA=1000
NB=500
SEED=20261007
THR=.40
CORE_THR=.70
GROUPS=["PBS","LPS","run","MCC"]
WEEKS=[0,16,24]

def scorr(df):
    r=df.corr(method="spearman").to_numpy(float)
    r=(r+r.T)/2
    m=float(np.linalg.eigvalsh(r).min())
    if m<1e-8:
        r+=np.eye(len(r))*(1e-8-m)
        z=np.sqrt(np.diag(r))
        r=r/np.outer(z,z)
    return r

def fit(R,k):
    f=FactorAnalyzer(n_factors=k,rotation="oblimin",method="minres",is_corr_matrix=True,use_smc=True)
    f.fit(R)
    L=np.asarray(f.loadings_,float)
    P=np.asarray(f.phi_,float) if getattr(f,"phi_",None) is not None else np.eye(k)
    for i in range(k):
        j=int(np.argmax(np.abs(L[:,i])))
        if L[j,i]<0:
            L[:,i]*=-1
            P[i,:]*=-1
            P[:,i]*=-1
    return L,P

def cosine(A,B):
    den=np.linalg.norm(A,axis=0)[:,None]*np.linalg.norm(B,axis=0)[None,:]
    return A.T@B/np.maximum(den,1e-12)

def align(ref,other):
    S=cosine(ref,other)
    rr,cc=linear_sum_assignment(-np.abs(S))
    out=np.zeros_like(ref)
    cs=np.zeros(ref.shape[1])
    for i,j in zip(rr,cc):
        out[:,i]=other[:,j]*(1 if S[i,j]>=0 else -1)
        cs[i]=abs(S[i,j])
    return out,cs

def parallel(base,rng):
    n,p=base.shape
    R=scorr(base)
    observed=np.linalg.eigvalsh(R)[::-1]
    simulated=np.empty((NPA,p))
    for i in range(NPA):
        z=pd.DataFrame(rng.normal(size=(n,p)))
        simulated[i]=np.linalg.eigvalsh(scorr(z))[::-1]
    q95=np.quantile(simulated,.95,axis=0)
    pa=pd.DataFrame({"component":np.arange(1,p+1),
                     "observed_eigenvalue":observed,
                     "random_q95":q95,
                     "random_mean":simulated.mean(0),
                     "margin":observed-q95,
                     "retain":observed>q95})
    pa.to_csv(OUT/"parallel_analysis_28.csv",index=False)
    fig,ax=plt.subplots(figsize=(9,5))
    ax.plot(pa.component,pa.observed_eigenvalue,"o-",label="Observed 28 features")
    ax.plot(pa.component,pa.random_q95,"o-",label="Simulated 95th percentile")
    ax.set_xlabel("Component")
    ax.set_ylabel("Eigenvalue")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT/"parallel_analysis_28.png",dpi=160)
    plt.close(fig)
    return R,pa

def boot(base,ref,k,draws):
    vectors=[]
    congruences=[]
    errors=0
    for ids in draws:
        try:
            newR=scorr(base.iloc[ids].reset_index(drop=True))
            L,_=fit(newR,k)
            aligned,c=align(ref,L)
            if np.isfinite(aligned).all():
                vectors.append(aligned)
                congruences.append(c)
            else:
                errors+=1
        except Exception:
            errors+=1
    if len(vectors)<400:
        raise RuntimeError(f"Too few successful bootstrap fits for k={k}: {len(vectors)}")
    return np.stack(vectors),np.stack(congruences),errors

def factor_model(R,k,base,df,features,draws):
    L,P=fit(R,k)
    n=len(features)
    headers=[f"D{i+1}" for i in range(k)]
    ref=pd.DataFrame({"feature":features,**{f"D{i+1}":L[:,i] for i in range(k)}})
    ref["max_abs_loading"]=np.max(np.abs(L),axis=1)
    ref["primary_domain"]=[f"D{np.argmax(np.abs(L[j]))+1}" if np.max(np.abs(L[j]))>=THR else "unassigned" for j in range(n)]
    ref["crossload_count"]=np.sum(np.abs(L)>=THR,axis=1)
    ref.to_csv(OUT/f"k{k}_loadings_28.csv",index=False)
    pd.DataFrame(P,index=headers,columns=headers).to_csv(OUT/f"k{k}_factor_correlations.csv")
    BL,CG,nfail=boot(base[features],L,k,draws)
    np.save(OUT/f"k{k}_bootstrap_loadings.npy",BL)
    st=[]
    for j,f in enumerate(features):
        dom=np.argmax(np.abs(L[j]))
        B=BL[:,j,:]
        pstrong=float(np.mean(np.abs(B[:,dom])>=THR))
        pdom=float(np.mean(np.argmax(np.abs(B),axis=1)==dom))
        st.append({"feature":f,
            "primary_domain":ref.primary_domain.iloc[j],
            "loading":float(L[j,dom]),
            "bootstrap_prob_abs_ge_040":pstrong,
            "bootstrap_prob_primary_dominant":pdom,
            "stable_core":bool(ref.primary_domain.iloc[j]!="unassigned" and pstrong>=CORE_THR and pdom>=CORE_THR)})
    st=pd.DataFrame(st)
    st.to_csv(OUT/f"k{k}_feature_stability.csv",index=False)
    # Frozen scoring fitted on baseline only; never refit at later visits.
    mu=base[features].mean().to_numpy(float)
    sd=base[features].std(ddof=1).to_numpy(float)
    sd[sd==0]=1
    W=np.linalg.pinv(R)@L@P
    bS=((base[features].to_numpy(float)-mu)/sd)@W
    bmu=bS.mean(0)
    bsd=bS.std(0,ddof=1)
    bsd[bsd==0]=1
    allS=((((df[features].to_numpy(float)-mu)/sd)@W)-bmu)/bsd
    scores=df[META].copy()
    for i,c in enumerate(headers):
        scores[c+"_score"]=allS[:,i]
    scores.to_csv(OUT/f"k{k}_scores_all_weeks.csv",index=False)
    group_rows=[]
    for g in GROUPS:
        for week in WEEKS:
            sel=scores[(scores.group==g)&(scores.week==week)]
            for c in headers:
                group_rows.append({"group":g,"week":week,"domain":c,"n":int(len(sel)),
                                   "mean_score":float(sel[c+"_score"].mean()),
                                   "sd_score":float(sel[c+"_score"].std(ddof=1))})
    gtab=pd.DataFrame(group_rows)
    gtab.to_csv(OUT/f"k{k}_group_week_mean_scores.csv",index=False)
    for c in headers:
        fig,ax=plt.subplots(figsize=(8,4.5))
        for g in GROUPS:
            gsub=gtab[(gtab.group==g)&(gtab.domain==c)]
            ax.plot(gsub.week,gsub.mean_score,"o-",label=g)
        ax.set_xticks(WEEKS)
        ax.axhline(0,linewidth=.7)
        ax.set_xlabel("Week")
        ax.set_ylabel("Baseline-SD domain score")
        ax.set_title(f"28-feature EFA, k={k}, {c}")
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT/f"k{k}_{c}_trajectories.png",dpi=160)
        plt.close(fig)
    rmse=float(np.sqrt(np.mean((R-L@P@L.T)[~np.eye(len(R),dtype=bool)]**2)))
    factors=[{"factor":headers[i],
              "median_congruence":float(np.median(CG[:,i])),
              "q10_congruence":float(np.quantile(CG[:,i],.1)),
              "q90_congruence":float(np.quantile(CG[:,i],.9)),
              "members":ref.loc[ref.primary_domain.eq(headers[i]),"feature"].tolist(),
              "stable_core":st.loc[st.primary_domain.eq(headers[i]) & st.stable_core,"feature"].tolist()}
             for i in range(k)]
    return {"L":L,"P":P,"score":scores,"reference":ref,"stability":st,
            "info":{"n_factors":k,
                    "bootstrap_valid":len(CG),"bootstrap_failed":nfail,
                    "offdiagonal_reconstruction_rmse":rmse,
                    "factors":factors,
                    "unassigned":ref.loc[ref.primary_domain.eq("unassigned"),"feature"].tolist(),
                    "crossloading":ref.loc[ref.crossload_count.gt(1),"feature"].tolist()}}

def compare_31_to_28(models,features):
    maps=[]
    scorecorr=[]
    for k in [3,4]:
        prior=pd.read_csv(OLD/f"k{k}_loadings.csv").set_index("feature")
        oldL=prior.loc[features,[f"D{i+1}" for i in range(k)]].to_numpy(float)
        newL=models[k]["L"]
        S=cosine(oldL,newL)
        pd.DataFrame(S,index=[f"old_D{i+1}" for i in range(k)],
                     columns=[f"new_D{i+1}" for i in range(k)]).to_csv(OUT/f"k{k}_old31_to_new28_cosines.csv")
        rr,cc=linear_sum_assignment(-np.abs(S))
        old_scores=pd.read_csv(OLD/f"k{k}_factor_scores_all_weeks.csv")
        joined=old_scores.merge(models[k]["score"],on=META,suffixes=("_old31","_new28"),validate="one_to_one")
        for i,j in zip(rr,cc):
            maps.append({"model_k":k,"old_domain":f"D{i+1}","new_domain":f"D{j+1}",
                         "loading_cosine_signed":float(S[i,j]),"loading_cosine_absolute":float(abs(S[i,j]))})
            for week in [0,16,24]:
                one=joined[joined.week.eq(week)]
                a=one[f"D{i+1}_score_old31"].to_numpy(float)
                b=one[f"D{j+1}_score_new28"].to_numpy(float)
                scorecorr.append({"model_k":k,"old_domain":f"D{i+1}","new_domain":f"D{j+1}",
                                  "week":week,"score_correlation_abs":float(abs(np.corrcoef(a,b)[0,1]))})
    pd.DataFrame(maps).to_csv(OUT/"old31_new28_factor_mapping.csv",index=False)
    pd.DataFrame(scorecorr).to_csv(OUT/"old31_new28_score_correlations.csv",index=False)
    return maps,scorecorr

def main():
    df=pd.read_csv(SRC,dtype={"mouse_id":str})
    assert len(df)==133 and sum(df.week.eq(0))==54 and sum(df.week.eq(16))==41 and sum(df.week.eq(24))==38
    assert len(df.columns)-len(META)==31
    base=df[df.week.eq(0)].reset_index(drop=True)
    duplicates=[]
    for t in [1,2,3]:
        a,b=f"Learning_T{t}mean",f"Learning_T{t}sum"
        assert np.array_equal(base[a].to_numpy(),base[b].to_numpy())
        diffs=np.abs(df[a].to_numpy(float)-df[b].to_numpy(float))
        duplicates.append({"pair":a+" / "+b,"baseline_exact_duplicate":True,
                           "all_week_different_rows":int(np.sum(diffs>1e-10)),
                           "max_absolute_difference_all_weeks":float(diffs.max())})
    pd.DataFrame(duplicates).to_csv(OUT/"duplicates_audit.csv",index=False)
    features=[c for c in df.columns if c not in META+DROP]
    assert len(features)==28
    rng=np.random.default_rng(SEED)
    R,pa=parallel(base[features],rng)
    pa_k=int(pa.retain.sum())
    if pa_k<1 or pa_k>7:
        raise RuntimeError(f"Unexpected retained count={pa_k}")
    ks=sorted(set([3,4,pa_k]))
    draws=[rng.integers(0,54,size=54) for _ in range(NB)]
    models={}
    for k in ks:
        models[k]=factor_model(R,k,base,df,features,draws)

    oldpa=pd.read_csv(OLD/"parallel_analysis.csv")
    pc=[]
    for i in range(8):
        a,b=oldpa.iloc[i],pa.iloc[i]
        pc.append({"component":i+1,
                   "old31_observed":float(a.observed_eigenvalue),
                   "old31_random_q95":float(a.random_q95),
                   "new28_observed":float(b.observed_eigenvalue),
                   "new28_random_q95":float(b.random_q95),
                   "new28_margin":float(b.margin),
                   "new28_retain":bool(b.retain)})
    pd.DataFrame(pc).to_csv(OUT/"parallel_old31_new28_comparison.csv",index=False)

    oldnew,scorecorr=compare_31_to_28(models,features)
    S=cosine(models[3]["L"],models[4]["L"])
    pd.DataFrame(S,index=["k3_D1","k3_D2","k3_D3"],
                 columns=[f"k4_D{i+1}" for i in range(4)]).to_csv(OUT/"k3_k4_loading_similarity.csv")

    summary={"experiment":"EFA28_DEDUPLICATED_BASELINE",
             "source":"Cleaned 133-state, 31-feature processed matrix after 7 state exclusions",
             "baseline_n":54,"all_week_n":133,"features_used":28,
             "excluded_duplicate_features":DROP,
             "duplicate_audit":duplicates,
             "parallel_analysis":{"n_simulations":NPA,"retained_factors":pa_k,"first_eight":pa.head(8).to_dict("records")},
             "method":"Spearman + MINRES oblimin",
             "bootstrap_n":NB,
             "reference_loading_threshold":THR,
             "stable_core_probability_threshold":CORE_THR,
             "solutions":{f"k{k}":models[k]["info"] for k in ks},
             "old31_to_new28_factor_mapping":oldnew,
             "old31_to_new28_score_correlations":scorecorr,
             "notes":[
                 "Factor names are arbitrary and should be interpreted from loadings.",
                 "Later weeks are projections on the baseline solution, not refits.",
                 "No claims of treatment effects or mortality correction are made.",
                 "n=54 at baseline limits precision. Remaining highly correlated features may still overweight test blocks."
             ]}
    (OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    lines=["# Repeat EFA on 28 features after removing exact baseline duplicates","",
           "Original data cleaning and seven removed mouse-week states are unchanged.",
           "Excluded columns: "+", ".join(DROP)+".",
           "All three mean/sum pairs were identical on each of 54 baseline mice.","",
           f"Parallel analysis: {pa_k} factors pass observed eigenvalue > random 95th percentile.","",
           "## Old 31-feature vs new 28-feature parallel analysis","",
           "| Component | Old eig | Old null q95 | New eig | New null q95 | Margin new |",
           "|---|---:|---:|---:|---:|---:|"]
    for a in pc:
        lines.append(f"| {a['component']} | {a['old31_observed']:.3f} | {a['old31_random_q95']:.3f} | {a['new28_observed']:.3f} | {a['new28_random_q95']:.3f} | {a['new28_margin']:+.3f} |")
    for k in ks:
        lines+=["",f"## k={k}, MINRES oblimin / bootstrap {NB}",""]
        x=models[k]["info"]
        lines.append(f"Offdiagonal residual RMSE: {x['offdiagonal_reconstruction_rmse']:.4f}. Bootstrap valid: {x['bootstrap_valid']}.")
        for f in x["factors"]:
            lines.append(f"- {f['factor']}: bootstrap cosine median={f['median_congruence']:.3f}, q10={f['q10_congruence']:.3f}, q90={f['q90_congruence']:.3f}.")
            lines.append("  - Members: "+(", ".join(f["members"]) if f["members"] else "(none)"))
            lines.append("  - Stable core: "+(", ".join(f["stable_core"]) if f["stable_core"] else "(none)"))
    lines+=["","## Matched factors vs old 31-feature EFA",""]
    for r in oldnew:
        lines.append(f"- k={r['model_k']}: old {r['old_domain']} -> new {r['new_domain']}, absolute loading cosine={r['loading_cosine_absolute']:.3f}.")
    lines+=["","## Caveats","",
            "The new PCA/eigenvalue retention is not the same thing as the EFA factor loadings.",
            "Small baseline sample, multiple correlated behavioral measures, and near-threshold factors require caution.",
            "Frozen factor scores at week 16 and 24 are descriptive only.",
            "All previous experiment files are left untouched."]
    (OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"pa_factors":pa_k,
                      "parallel_first_six":pc[:6],
                      "models":{f"k{k}":models[k]["info"] for k in ks},
                      "old_new_mapping":oldnew},
                     ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
