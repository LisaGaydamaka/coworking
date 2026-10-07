#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from factor_analyzer import FactorAnalyzer
from scipy.optimize import linear_sum_assignment

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"

META=["mouse_id","group","week","status"]
THR=0.40
STAB_THR=0.70
NPA=1000
NB=500
SEED=20261007
GROUPS=["PBS","LPS","run","MCC"]
WEEKS=[0,16,24]

def scorr(x):
    r=x.corr(method="spearman").to_numpy(float)
    r=(r+r.T)/2
    m=float(np.linalg.eigvalsh(r).min())
    if m<1e-8:
        r=r+np.eye(r.shape[0])*(1e-8-m)
        d=np.sqrt(np.diag(r))
        r=r/np.outer(d,d)
    return r

def fit_efa(r,k):
    f=FactorAnalyzer(n_factors=k,rotation="oblimin",method="minres",is_corr_matrix=True,use_smc=True)
    f.fit(r)
    L=np.asarray(f.loadings_,float)
    P=np.asarray(f.phi_,float) if getattr(f,"phi_",None) is not None else np.eye(k)
    # deterministic sign orientation
    for d in range(k):
        j=int(np.argmax(np.abs(L[:,d])))
        if L[j,d]<0:
            L[:,d]*=-1
            P[d,:]*=-1
            P[:,d]*=-1
    return L,P

def cosine_matrix(A,B):
    S=np.zeros((A.shape[1],B.shape[1]),float)
    for i in range(A.shape[1]):
        for j in range(B.shape[1]):
            den=np.linalg.norm(A[:,i])*np.linalg.norm(B[:,j])
            S[i,j]=0.0 if den==0 else float(A[:,i]@B[:,j]/den)
    return S

def align_same_k(ref,cur):
    S=cosine_matrix(ref,cur)
    rr,cc=linear_sum_assignment(-np.abs(S))
    out=np.zeros_like(ref)
    cg=np.zeros(ref.shape[1])
    for r,c in zip(rr,cc):
        v=cur[:,c].copy()
        if S[r,c]<0:
            v*=-1
        out[:,r]=v
        den=np.linalg.norm(ref[:,r])*np.linalg.norm(v)
        cg[r]=0.0 if den==0 else float(ref[:,r]@v/den)
    return out,cg

def parallel_analysis(base_features,rng):
    n,p=base_features.shape
    R=scorr(base_features)
    obs=np.linalg.eigvalsh(R)[::-1]
    rand=np.empty((NPA,p),float)
    for b in range(NPA):
        Z=pd.DataFrame(rng.normal(size=(n,p)))
        rand[b]=np.linalg.eigvalsh(scorr(Z))[::-1]
    q95=np.quantile(rand,.95,axis=0)
    mean=rand.mean(axis=0)
    tab=pd.DataFrame({
        "component":np.arange(1,p+1),
        "observed_eigenvalue":obs,
        "random_mean":mean,
        "random_q95":q95,
        "margin_observed_minus_q95":obs-q95,
        "retain":obs>q95,
    })
    tab.to_csv(OUT/"parallel_analysis.csv",index=False)
    fig,ax=plt.subplots(figsize=(9,5))
    ax.plot(tab.component,tab.observed_eigenvalue,marker="o",label="Observed")
    ax.plot(tab.component,tab.random_q95,marker="o",label="Random q95")
    ax.axvline(4.5,linestyle="--",linewidth=1)
    ax.set_xlabel("Component")
    ax.set_ylabel("Eigenvalue")
    ax.set_title("Parallel analysis")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT/"parallel_analysis.png",dpi=180)
    plt.close(fig)
    return R,tab

def model_fit_metrics(R,L,P):
    common=L@P@L.T
    mask=~np.eye(R.shape[0],dtype=bool)
    resid=(R-common)[mask]
    return {
        "offdiag_rmse":float(np.sqrt(np.mean(resid**2))),
        "offdiag_mae":float(np.mean(np.abs(resid))),
        "mean_communality":float(np.mean(np.diag(common))),
        "median_communality":float(np.median(np.diag(common))),
    }

def bootstrap_model(base_features,k,ref_L,boot_idx):
    BL=[]
    CG=[]
    failures=0
    for idx in boot_idx:
        try:
            rb=scorr(base_features.iloc[idx].reset_index(drop=True))
            lb,_=fit_efa(rb,k)
            a,c=align_same_k(ref_L,lb)
            if np.isfinite(a).all():
                BL.append(a); CG.append(c)
            else:
                failures+=1
        except Exception:
            failures+=1
    if len(BL)<400:
        raise RuntimeError(f"k={k}: only {len(BL)} valid bootstrap fits")
    return np.stack(BL),np.stack(CG),failures

def make_reference_tables(features,L,P,k):
    ld=pd.DataFrame({"feature":features,**{f"D{d+1}":L[:,d] for d in range(k)}})
    ld["max_abs_loading"]=np.max(np.abs(L),axis=1)
    ld["primary_domain"]=[
        f"D{int(np.argmax(np.abs(L[j])))+1}" if np.max(np.abs(L[j]))>=THR else "unassigned"
        for j in range(len(features))
    ]
    ld["cross_loading_count_ge_0_40"]=np.sum(np.abs(L)>=THR,axis=1)
    ld.to_csv(OUT/f"k{k}_loadings.csv",index=False)
    pd.DataFrame(P,index=[f"D{i+1}" for i in range(k)],columns=[f"D{i+1}" for i in range(k)]).to_csv(OUT/f"k{k}_factor_correlations.csv")
    return ld

def stability_table(features,L,BL,k):
    rows=[]
    for j,f in enumerate(features):
        p=int(np.argmax(np.abs(L[j])))
        B=BL[:,j,:]
        ref_assigned=np.max(np.abs(L[j]))>=THR
        rows.append({
            "feature":f,
            "reference_primary_domain":f"D{p+1}" if ref_assigned else "unassigned",
            "reference_primary_loading":float(L[j,p]),
            "reference_abs_loading":float(abs(L[j,p])),
            "reference_cross_loading_count":int(np.sum(np.abs(L[j])>=THR)),
            "bootstrap_prob_loading_ge_0_40_in_reference_domain":float(np.mean(np.abs(B[:,p])>=THR)),
            "bootstrap_prob_any_loading_ge_0_40":float(np.mean(np.max(np.abs(B),axis=1)>=THR)),
            "bootstrap_prob_reference_domain_is_dominant":float(np.mean(np.argmax(np.abs(B),axis=1)==p)),
        })
    st=pd.DataFrame(rows)
    st["stable_core"]=(
        st.reference_primary_domain.ne("unassigned")
        & st.bootstrap_prob_loading_ge_0_40_in_reference_domain.ge(STAB_THR)
        & st.bootstrap_prob_reference_domain_is_dominant.ge(STAB_THR)
    )
    st.to_csv(OUT/f"k{k}_feature_stability.csv",index=False)
    return st

def frozen_scores(df,base,features,R,L,P,k):
    mu=base[features].mean().to_numpy(float)
    sd=base[features].std(ddof=1).to_numpy(float)
    sd[sd==0]=1.0
    W=np.linalg.pinv(R)@L@P
    bZ=(base[features].to_numpy(float)-mu)/sd
    bS=bZ@W
    sm=bS.mean(axis=0)
    ss=bS.std(axis=0,ddof=1)
    ss[ss==0]=1.0
    Z=(df[features].to_numpy(float)-mu)/sd
    S=(Z@W-sm)/ss
    out=df[META].copy()
    for d in range(k):
        out[f"D{d+1}_score"]=S[:,d]
    out.to_csv(OUT/f"k{k}_factor_scores_all_weeks.csv",index=False)
    return out

def longitudinal_tables(scores,k):
    score_cols=[f"D{d+1}_score" for d in range(k)]
    means=scores.groupby(["group","week"],observed=True)[score_cols].agg(["count","mean","std"]).reset_index()
    means.to_csv(OUT/f"k{k}_group_week_summary.csv",index=False)

    rows=[]
    for group in GROUPS:
        g=scores[scores.group.eq(group)]
        for d in range(1,k+1):
            col=f"D{d}_score"
            m={w:float(g.loc[g.week.eq(w),col].mean()) if np.any(g.week.eq(w)) else np.nan for w in WEEKS}
            rows.append({
                "group":group,"domain":f"D{d}",
                "mean_week0":m[0],"mean_week16":m[16],"mean_week24":m[24],
                "delta_0_minus_16":m[0]-m[16],
                "delta_16_minus_24":m[16]-m[24],
                "delta_0_minus_24":m[0]-m[24],
                "week0_gt_week16":bool(m[0]>m[16]),
                "week16_gt_week24":bool(m[16]>m[24]),
            })
    tr=pd.DataFrame(rows)
    tr.to_csv(OUT/f"k{k}_longitudinal_group_domain_changes.csv",index=False)

    for d in range(1,k+1):
        col=f"D{d}_score"
        gm=scores.groupby(["group","week"],observed=True)[col].mean().reset_index()
        fig,ax=plt.subplots(figsize=(8,5))
        for group,sub in gm.groupby("group",observed=True):
            sub=sub.sort_values("week")
            ax.plot(sub.week,sub[col],marker="o",label=group)
        ax.axhline(0,linewidth=.8)
        ax.set_xticks(WEEKS)
        ax.set_xlabel("Week")
        ax.set_ylabel("Frozen factor score (baseline SD)")
        ax.set_title(f"k={k}, D{d}: group trajectories")
        ax.legend()
        fig.tight_layout()
        fig.savefig(OUT/f"k{k}_D{d}_group_week.png",dpi=180)
        plt.close(fig)
    return means,tr

def cross_solution_mapping(L3,L4):
    S=cosine_matrix(L3,L4)
    rr,cc=linear_sum_assignment(-np.abs(S))
    rows=[]
    for r,c in zip(rr,cc):
        rows.append({
            "k3_domain":f"D{r+1}",
            "best_k4_domain":f"D{c+1}",
            "signed_loading_congruence":float(S[r,c]),
            "absolute_loading_congruence":float(abs(S[r,c])),
        })
    out=pd.DataFrame(rows).sort_values("k3_domain")
    out.to_csv(OUT/"k3_to_k4_domain_mapping.csv",index=False)
    pd.DataFrame(S,index=[f"k3_D{i+1}" for i in range(3)],columns=[f"k4_D{i+1}" for i in range(4)]).to_csv(OUT/"k3_k4_loading_similarity_matrix.csv")
    return out

def score_correlations(s3,s4,mapping):
    joined=s3.merge(s4,on=META,suffixes=("_k3","_k4"))
    rows=[]
    for _,r in mapping.iterrows():
        a=r.k3_domain; b=r.best_k4_domain
        x=joined[f"{a}_score_k3"].to_numpy(float)
        y=joined[f"{b}_score_k4"].to_numpy(float)
        rows.append({
            "k3_domain":a,"k4_domain":b,
            "pearson_all_weeks":float(np.corrcoef(x,y)[0,1]),
            "pearson_baseline":float(np.corrcoef(
                joined.loc[joined.week.eq(0),f"{a}_score_k3"],
                joined.loc[joined.week.eq(0),f"{b}_score_k4"])[0,1]),
        })
    out=pd.DataFrame(rows)
    out.to_csv(OUT/"k3_k4_score_correlations.csv",index=False)
    return out

def summarize_model(k,L,P,ld,st,CG,fitm,tr):
    fs=[]
    for d in range(k):
        fs.append({
            "domain":f"D{d+1}",
            "median_congruence":float(np.median(CG[:,d])),
            "q10":float(np.quantile(CG[:,d],.10)),
            "q90":float(np.quantile(CG[:,d],.90)),
        })
    members={}
    stable={}
    for d in range(1,k+1):
        members[f"D{d}"]=ld.loc[ld.primary_domain.eq(f"D{d}"),"feature"].tolist()
        stable[f"D{d}"]=st.loc[st.stable_core & st.reference_primary_domain.eq(f"D{d}"),"feature"].tolist()
    return {
        "k":k,
        "fit_metrics":fitm,
        "factor_stability":fs,
        "reference_members":members,
        "stable_core_members":stable,
        "unassigned":ld.loc[ld.primary_domain.eq("unassigned"),"feature"].tolist(),
        "cross_loading_features":ld.loc[ld.cross_loading_count_ge_0_40.gt(1),"feature"].tolist(),
        "positive_0_to_16_group_domain_count":int(tr.week0_gt_week16.sum()),
        "positive_16_to_24_group_domain_count":int(tr.week16_gt_week24.sum()),
        "group_domain_comparisons_each_interval":int(len(tr)),
    }

def main():
    df=pd.read_csv(SRC)
    features=[c for c in df.columns if c not in META]
    base=df[df.week.eq(0)].reset_index(drop=True)
    if len(features)!=31 or len(base)!=54 or len(df)!=133:
        raise RuntimeError(f"unexpected dimensions: p={len(features)} baseline={len(base)} all={len(df)}")

    rng=np.random.default_rng(SEED)
    R,pa=parallel_analysis(base[features],rng)
    boot_idx=[rng.integers(0,len(base),size=len(base)) for _ in range(NB)]

    models={}
    for k in [3,4]:
        L,P=fit_efa(R,k)
        ld=make_reference_tables(features,L,P,k)
        BL,CG,failures=bootstrap_model(base[features],k,L,boot_idx)
        np.save(OUT/f"k{k}_bootstrap_aligned_loadings.npy",BL)
        st=stability_table(features,L,BL,k)
        scores=frozen_scores(df,base,features,R,L,P,k)
        means,tr=longitudinal_tables(scores,k)
        fitm=model_fit_metrics(R,L,P)
        models[k]={"L":L,"P":P,"ld":ld,"st":st,"BL":BL,"CG":CG,"scores":scores,"tr":tr,
                   "summary":summarize_model(k,L,P,ld,st,CG,fitm,tr),
                   "bootstrap_failures":failures}

    mapping=cross_solution_mapping(models[3]["L"],models[4]["L"])
    scorecorr=score_correlations(models[3]["scores"],models[4]["scores"],mapping)

    pa4=pa.iloc[3]
    comparison={
        "parallel_analysis_k4_margin":float(pa4.margin_observed_minus_q95),
        "parallel_analysis_k4_observed":float(pa4.observed_eigenvalue),
        "parallel_analysis_k4_random_q95":float(pa4.random_q95),
        "fit_improvement_rmse_k4_vs_k3":float(models[3]["summary"]["fit_metrics"]["offdiag_rmse"]-models[4]["summary"]["fit_metrics"]["offdiag_rmse"]),
        "domain_mapping":mapping.to_dict(orient="records"),
        "mapped_score_correlations":scorecorr.to_dict(orient="records"),
    }

    # Decision rule: prefer 3 factors if the 4th PA margin is very small (<0.10)
    # and the 4th factor bootstrap q10 congruence is below 0.80; otherwise retain 4.
    d4=models[4]["summary"]["factor_stability"][3]
    prefer3=(
        comparison["parallel_analysis_k4_margin"]<0.10
        and d4["q10"]<0.80
    )
    recommendation={
        "preferred_descriptive_solution":"k=3" if prefer3 else "k=4",
        "reason":{
            "k4_parallel_margin_small":bool(comparison["parallel_analysis_k4_margin"]<0.10),
            "k4_domain4_q10_below_0_80":bool(d4["q10"]<0.80),
            "note":"Rule is predefined in this experiment for parsimony; both solutions are reported.",
        }
    }

    summary={
        "experiment":"EFA31_3VS4_LONGITUDINAL",
        "source_matrix":"cleaned 31-feature matrix after 7 state exclusions",
        "baseline_rows":54,
        "all_living_rows":133,
        "features":31,
        "correlation":"Spearman",
        "efa":"MINRES + oblimin",
        "loading_threshold":THR,
        "stable_core_thresholds":{
            "abs_loading":THR,
            "bootstrap_prob_loading_ge_threshold":STAB_THR,
            "bootstrap_prob_reference_domain_dominant":STAB_THR,
        },
        "parallel_analysis_simulations":NPA,
        "bootstrap_resamples_per_model":NB,
        "k3":models[3]["summary"],
        "k4":models[4]["summary"],
        "comparison":comparison,
        "recommendation":recommendation,
    }
    (OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    lines=[
        "# EFA31: 3-factor vs 4-factor comparison and longitudinal domain analysis","",
        "Domains are defined only on week 0 (54 mice). Week 16/24 never redefine the factors.","",
        f"Parallel-analysis component 4: observed={comparison['parallel_analysis_k4_observed']:.4f}, q95={comparison['parallel_analysis_k4_random_q95']:.4f}, margin={comparison['parallel_analysis_k4_margin']:.4f}.","",
        "## Stability",""
    ]
    for k in [3,4]:
        lines.append(f"### k={k}")
        for x in models[k]["summary"]["factor_stability"]:
            lines.append(f"- {x['domain']}: median congruence={x['median_congruence']:.3f}; q10–q90={x['q10']:.3f}–{x['q90']:.3f}.")
        lines.append(f"- off-diagonal correlation RMSE={models[k]['summary']['fit_metrics']['offdiag_rmse']:.4f}.")
        lines.append("")
    lines+=["## Cross-solution mapping",""]
    for _,r in mapping.iterrows():
        lines.append(f"- {r.k3_domain} -> {r.best_k4_domain}: loading congruence={r.absolute_loading_congruence:.3f}.")
    lines+=["","## Recommendation","",f"**{recommendation['preferred_descriptive_solution']}** by the predefined parsimony rule.","",
            "See k3/k4 longitudinal CSV files and trajectory figures for group-week domain behavior."]
    (OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
