#!/usr/bin/env python3
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from factor_analyzer import FactorAnalyzer
from scipy.optimize import linear_sum_assignment

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"; OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT.parent/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"
META=["mouse_id","group","week","status"]; THR=.40; NPA=1000; NB=500; SEED=20261007

def scorr(x):
    r=x.corr(method="spearman").to_numpy(float); r=(r+r.T)/2
    m=np.linalg.eigvalsh(r).min()
    if m<1e-8:
        r+=np.eye(len(r))*(1e-8-m); d=np.sqrt(np.diag(r)); r=r/np.outer(d,d)
    return r

def fit(r,k):
    f=FactorAnalyzer(n_factors=k,rotation="oblimin",method="minres",is_corr_matrix=True,use_smc=True); f.fit(r)
    L=np.asarray(f.loadings_,float); P=np.asarray(f.phi_,float) if getattr(f,"phi_",None) is not None else np.eye(k)
    for d in range(k):
        j=np.argmax(np.abs(L[:,d]))
        if L[j,d]<0: L[:,d]*=-1; P[d,:]*=-1; P[:,d]*=-1
    return L,P

def align(A,B):
    S=np.zeros((A.shape[1],B.shape[1]))
    for i in range(A.shape[1]):
        for j in range(B.shape[1]):
            den=np.linalg.norm(A[:,i])*np.linalg.norm(B[:,j]); S[i,j]=0 if den==0 else A[:,i]@B[:,j]/den
    rr,cc=linear_sum_assignment(-np.abs(S)); C=np.zeros_like(A); cg=np.zeros(A.shape[1])
    for r,c in zip(rr,cc):
        v=B[:,c].copy()
        if S[r,c]<0: v*=-1
        C[:,r]=v; den=np.linalg.norm(A[:,r])*np.linalg.norm(v); cg[r]=0 if den==0 else A[:,r]@v/den
    return C,cg

df=pd.read_csv(SRC); feats=[c for c in df.columns if c not in META]
base=df[df.week.eq(0)].reset_index(drop=True)
assert len(feats)==31 and len(base)==54
rng=np.random.default_rng(SEED); R=scorr(base[feats]); obs=np.linalg.eigvalsh(R)[::-1]
rand=np.empty((NPA,31))
for b in range(NPA):
    rand[b]=np.linalg.eigvalsh(scorr(pd.DataFrame(rng.normal(size=(54,31)))))[::-1]
q95=np.quantile(rand,.95,axis=0); k=max(1,int(np.sum(obs>q95)))
pd.DataFrame({"component":np.arange(1,32),"observed_eigenvalue":obs,"random_mean":rand.mean(0),"random_q95":q95,"retain":obs>q95}).to_csv(OUT/"parallel_analysis.csv",index=False)

L,P=fit(R,k)
ld=pd.DataFrame({"feature":feats,**{f"D{d+1}":L[:,d] for d in range(k)}})
ld["max_abs_loading"]=np.max(np.abs(L),axis=1)
ld["primary_domain"]=[f"D{np.argmax(np.abs(L[j]))+1}" if np.max(np.abs(L[j]))>=THR else "unassigned" for j in range(31)]
ld["cross_loading_count_ge_0_40"]=np.sum(np.abs(L)>=THR,axis=1)
ld.to_csv(OUT/"efa_loadings.csv",index=False)

BL=[]; CG=[]; tries=0
while len(BL)<NB and tries<NB*3:
    tries+=1; idx=rng.integers(0,54,size=54)
    try:
        lb,_=fit(scorr(base.iloc[idx][feats].reset_index(drop=True)),k); a,c=align(L,lb)
        if np.isfinite(a).all(): BL.append(a); CG.append(c)
    except Exception: pass
if len(BL)<400: raise RuntimeError(f"valid bootstrap={len(BL)}")
BL=np.stack(BL); CG=np.stack(CG); np.save(OUT/"bootstrap_aligned_loadings.npy",BL)

rows=[]
for j,f in enumerate(feats):
    p=int(np.argmax(np.abs(L[j]))); B=BL[:,j,:]
    rows.append({"feature":f,"reference_primary_domain":f"D{p+1}" if np.max(np.abs(L[j]))>=THR else "unassigned","reference_primary_loading":float(L[j,p]),"reference_cross_loading_count":int(np.sum(np.abs(L[j])>=THR)),"bootstrap_prob_loading_ge_0_40_in_reference_domain":float(np.mean(np.abs(B[:,p])>=THR)),"bootstrap_prob_any_loading_ge_0_40":float(np.mean(np.max(np.abs(B),axis=1)>=THR)),"bootstrap_prob_reference_domain_is_dominant":float(np.mean(np.argmax(np.abs(B),axis=1)==p))})
pd.DataFrame(rows).to_csv(OUT/"feature_domain_stability.csv",index=False)
com=np.sum((L@P)*L,axis=1)
pd.DataFrame({"feature":feats,"communality":com,"uniqueness":1-com}).to_csv(OUT/"communalities_uniqueness.csv",index=False)
pd.DataFrame(P,index=[f"D{i+1}" for i in range(k)],columns=[f"D{i+1}" for i in range(k)]).to_csv(OUT/"factor_correlations_phi.csv")

mu=base[feats].mean().to_numpy(float); sd=base[feats].std(ddof=1).to_numpy(float); sd[sd==0]=1
W=np.linalg.pinv(R)@L@P; s0=((base[feats].to_numpy(float)-mu)/sd)@W; sm=s0.mean(0); ss=s0.std(0,ddof=1); ss[ss==0]=1
S=((((df[feats].to_numpy(float)-mu)/sd)@W)-sm)/ss
score=df[META].copy()
for d in range(k): score[f"D{d+1}_score"]=S[:,d]
score.to_csv(OUT/"factor_scores_all_weeks.csv",index=False)
gcols=[f"D{d+1}_score" for d in range(k)]
score.groupby(["group","week"],observed=True)[gcols].agg(["count","mean","std"]).reset_index().to_csv(OUT/"factor_scores_group_week.csv",index=False)

fs=[{"domain":d+1,"median_congruence":float(np.median(CG[:,d])),"q10_congruence":float(np.quantile(CG[:,d],.1)),"q90_congruence":float(np.quantile(CG[:,d],.9))} for d in range(k)]
members={f"D{d}":ld.loc[ld.primary_domain.eq(f"D{d}"),"feature"].tolist() for d in range(1,k+1)}
summary={"experiment":"EFA31_BASELINE_DOMAINS_DROP_7_OUTLIER_STATES","baseline_rows":54,"all_retained_living_rows":int(len(df)),"features":31,"correlation":"Spearman","parallel_analysis":{"simulations":NPA,"criterion":"observed eigenvalue > random 95th percentile"},"n_factors":int(k),"efa_method":"MINRES","rotation":"oblimin","loading_threshold":THR,"bootstrap_target":NB,"bootstrap_valid":int(len(BL)),"bootstrap_attempts":int(tries),"factor_stability":fs,"domain_members_reference":members,"unassigned_reference":ld.loc[ld.primary_domain.eq("unassigned"),"feature"].tolist(),"cross_loading_features_reference":ld.loc[ld.cross_loading_count_ge_0_40.gt(1),"feature"].tolist()}
(OUT/"EFA_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=["# Baseline EFA domains","",f"Parallel analysis retained **{k} factors**.","",f"Bootstrap: **{len(BL)} valid resamples**.","","## Domain membership (|loading| >= 0.40)",""]
for d in range(1,k+1): lines.append(f"- **D{d}:** "+(", ".join(members[f"D{d}"]) if members[f"D{d}"] else "(none at threshold)"))
lines+=["","## Factor stability",""]
for x in fs: lines.append(f"- D{x['domain']}: median congruence={x['median_congruence']:.3f}, q10–q90={x['q10_congruence']:.3f}–{x['q90_congruence']:.3f}.")
(OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
