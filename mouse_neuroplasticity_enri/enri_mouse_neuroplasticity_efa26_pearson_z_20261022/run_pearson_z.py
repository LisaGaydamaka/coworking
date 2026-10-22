#!/usr/bin/env python3
"""Independent EFA with Pearson correlations and frozen raw z-standardization.
Block 1-4 only. Existing rank-based experiments untouched.
"""
from pathlib import Path
import json, warnings
import numpy as np
import pandas as pd
from factor_analyzer import FactorAnalyzer
from scipy.optimize import linear_sum_assignment
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
SOURCE=PARENT/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"
OLD=PARENT/"enri_mouse_neuroplasticity_efa26_robust_validation_rank_scores"/"results"/"clean133_k4_rank_frozen_scores.csv"
OUT=ROOT/"results";OUT.mkdir(exist_ok=True)
REMOVE=["Learning_T1sum","Learning_T2sum","Learning_T3sum","Average_speed_NOR1","Average_speed_NOR2"]
META=["mouse_id","group","week","status"]
RNG=np.random.default_rng(20261022)
NPA=1000;NBOOT=180;THR=.40

def pearson(a):
    R=np.corrcoef(np.asarray(a,float),rowvar=False)
    R=(R+R.T)/2
    small=np.linalg.eigvalsh(R)[0]
    if small<1e-8:
        R+=np.eye(R.shape[0])*(1e-8-small)
        t=np.sqrt(np.diag(R));R/=np.outer(t,t)
    return R

def smc_eigen(R):
    inv=np.linalg.pinv(R,rcond=1e-9)
    smc=np.clip(1-1/np.maximum(np.diag(inv),1e-8),0,1)
    rr=R.copy();np.fill_diagonal(rr,smc)
    return np.linalg.eigvalsh(rr)[::-1]

def pa(x):
    n,p=x.shape;R=pearson(x)
    obs=np.linalg.eigvalsh(R)[::-1];common=smc_eigen(R)
    sims={k:np.zeros((NPA,p)) for k in ["perm_standard","perm_common","normal_standard","normal_common"]}
    for b in range(NPA):
        perm=np.column_stack([RNG.permutation(x[:,j]) for j in range(p)])
        rp=pearson(perm)
        sims["perm_standard"][b]=np.linalg.eigvalsh(rp)[::-1]
        sims["perm_common"][b]=smc_eigen(rp)
        rn=pearson(RNG.normal(size=(n,p)))
        sims["normal_standard"][b]=np.linalg.eigvalsh(rn)[::-1]
        sims["normal_common"][b]=smc_eigen(rn)
    result=pd.DataFrame({"factor":range(1,p+1),"observed_standard":obs,"observed_common":common})
    counts={}
    for key,sim in sims.items():
        q=np.quantile(sim,.95,axis=0);result[key+"_q95"]=q
        values=common if "common" in key else obs
        count=0
        for v,t in zip(values,q):
            if v>0 and v>t:count+=1
            else:break
        counts[key]=count
        result[key+"_margin"]=values-q
    result.to_csv(OUT/"pearson_parallel_analysis.csv",index=False)
    return R,result,counts

def efa(R,k):
    model=FactorAnalyzer(n_factors=k,rotation="oblimin",method="minres",is_corr_matrix=True,use_smc=True)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore",category=RuntimeWarning)
        model.fit(R)
    L=np.asarray(model.loadings_,float)
    P=np.asarray(model.phi_,float) if model.phi_ is not None else np.eye(k)
    for i in range(k):
        imax=np.argmax(np.abs(L[:,i]))
        if L[imax,i]<0:
            L[:,i]*=-1;P[i,:]*=-1;P[:,i]*=-1
    return L,P

def congruence(A,B):
    return A.T@B/(np.linalg.norm(A,axis=0)[:,None]*np.linalg.norm(B,axis=0)[None,:])

def boot(x,L,k,num):
    results=[];failures=0
    for i in range(num):
        idx=RNG.integers(0,len(x),len(x))
        try:
            R=pearson(x[idx])
            new,_=efa(R,k)
            C=congruence(L,new)
            row,col=linear_sum_assignment(-abs(C))
            match=np.zeros(k)
            for r,c in zip(row,col):match[r]=abs(C[r,c])
            results.append(match)
        except Exception:failures+=1
    if not results:raise RuntimeError("All bootstrap fits failed")
    a=np.array(results)
    return {"success":len(a),"failures":failures,"median":[float(x) for x in np.median(a,axis=0)],
            "q10":[float(x) for x in np.quantile(a,.1,axis=0)]}

def score(x0,xall,R,L,P,model_tag,features,meta):
    # frozen baseline mean/SD and all-weeks transformation; raw magnitudes preserved
    means=x0.mean(0);sd=x0.std(0,ddof=1)
    z0=(x0-means)/sd;zall=(xall-means)/sd
    assert np.max(abs(np.corrcoef(z0,rowvar=False)-R))<.0001
    W=np.linalg.pinv(R,rcond=1e-8)@L@P
    raw0=z0@W
    center=raw0.mean(0)
    scales=raw0.std(0,ddof=1)
    S=(zall@W-center)/scales
    k=L.shape[1]
    fr=meta.copy()
    for j in range(k):fr[f"D{j+1}_score"]=S[:,j]
    fr.to_csv(OUT/f"{model_tag}_scores.csv",index=False)
    df=pd.DataFrame(W,columns=[f"D{i+1}_weight" for i in range(k)])
    df.insert(0,"feature",features);df.to_csv(OUT/f"{model_tag}_score_weights.csv",index=False)
    return S,center,scales

def draw_loadings(L,feats,name):
    fig,ax=plt.subplots(figsize=(7.4,9.0))
    cap=min(1,max(.8,np.max(abs(L))))
    im=ax.imshow(L,aspect="auto",cmap="RdBu",vmin=-cap,vmax=cap)
    ax.set_xticks(range(L.shape[1]),[f"D{i+1}" for i in range(L.shape[1])])
    ax.set_yticks(range(len(feats)),feats,fontsize=7.1)
    for i in range(len(feats)):
        for j in range(L.shape[1]):
            val=L[i,j]
            ax.text(j,i,f"{val:+.2f}",ha="center",va="center",fontsize=7,
                    color="white" if abs(val)>.62 else "#202020",
                    fontweight="bold" if abs(val)>=THR else "normal")
    ax.set_title(f"EFA Pearson / {name}, нагрузки (n=54)",fontsize=12)
    fig.colorbar(im,ax=ax,fraction=.03,pad=.03);fig.tight_layout()
    fig.savefig(OUT/f"{name}_loadings.png",dpi=165,bbox_inches="tight");plt.close(fig)

def trajectories(data,domains,name):
    for j in range(domains):
        fig,axes=plt.subplots(1,2,figsize=(10,3.6),sharey=True)
        for ax,group in zip(axes,["PBS","LPS"]):
            for mid,g in data[data.group.eq(group)].groupby("mouse_id"):
                v=g.sort_values("week")
                ax.plot(v.week,v[f"D{j+1}_score"],alpha=.55,lw=1,marker="o",markersize=3)
            ax.set_title(f"{group}: {data[data.group.eq(group)].mouse_id.nunique()} мышей")
            ax.set_xticks([0,16,24]);ax.axhline(0,color="gray",ls="--",lw=1)
            ax.grid(alpha=.2);ax.set_xlabel("Неделя")
        axes[0].set_ylabel(f"Баллы D{j+1} (week 0: среднее=0, SD=1)")
        fig.suptitle(f"{name}, D{j+1}: индивидуальные траектории")
        fig.tight_layout();fig.savefig(OUT/f"{name}_D{j+1}_trajectory.png",dpi=150);plt.close(fig)

def main():
    df=pd.read_csv(SOURCE,dtype={"mouse_id":str})
    assert len(df)==133
    feats=[c for c in df if c not in META+REMOVE]
    assert len(feats)==26
    base=df[df.week.eq(0)].reset_index(drop=True)
    observed=base[base.status.eq("observed")].reset_index(drop=True)
    assert len(base)==54 and len(observed)==52
    assert df.week.value_counts().to_dict()=={0:54,16:41,24:38}
    a=base[feats].to_numpy(float)
    z=(a-a.mean(0))/a.std(0,ddof=1)
    R,tab,counts=pa(z)
    corr=pd.DataFrame(R,index=feats,columns=feats)
    corr.to_csv(OUT/"pearson_correlation_matrix.csv")
    evals={}
    current=df[feats].to_numpy(float)
    for k in (2,3,4,5):
        L,P=efa(R,k)
        fitted=L@P@L.T
        err=R-fitted;mask=~np.eye(26,dtype=bool)
        assignments=np.argmax(abs(L),axis=1)
        good=np.max(abs(L),axis=1)>=THR
        unique=[int(np.sum(good & (assignments==j))) for j in range(k)]
        cross=int(np.sum(np.sum(abs(L)>=THR,axis=1)>=2))
        ld=pd.DataFrame(L,columns=[f"D{i+1}" for i in range(k)])
        ld.insert(0,"feature",feats)
        ld["main_domain"]=[f"D{assignments[i]+1}" if good[i] else "-" for i in range(26)]
        ld["crossloading_n"]=np.sum(abs(L)>=THR,axis=1)
        ld.to_csv(OUT/f"k{k}_loadings.csv",index=False)
        pd.DataFrame(P).to_csv(OUT/f"k{k}_phi.csv",index=False)
        scores,cent,sd=score(a,current,R,L,P,f"k{k}",feats,df[META])
        record={"k":k,"rmse_corr":float(np.sqrt(np.mean(err[mask]**2))),"assigned":[int(v) for v in unique],
             "unassigned":int(np.sum(~good)),"crossloaded":cross,
             "primary":{f"D{j+1}":ld.loc[ld.main_domain.eq(f"D{j+1}"),"feature"].tolist() for j in range(k)},
             "max_features":{f"D{j+1}":{"feature":str(feats[int(np.argmax(abs(L[:,j])))]),"loading":float(L[int(np.argmax(abs(L[:,j]))),j])} for j in range(k)},
             "baseline_score_sd_before_final":sd.tolist()}
        if k in (3,4):
            record["bootstrap"]=boot(z,L,k,NBOOT)
            draw_loadings(L,feats,f"k{k}")
            trajectories(pd.concat([df[META],pd.DataFrame(scores,columns=[f"D{i+1}_score" for i in range(k)])],axis=1),k,f"k{k}")
        evals[f"k{k}"]=record
    # Sensitivity: EFA on 52 observed-only baseline animals
    z52=(observed[feats].to_numpy(float)-observed[feats].to_numpy(float).mean(0))/observed[feats].to_numpy(float).std(0,ddof=1)
    R52=pearson(z52)
    sens={}
    for k in (3,4):
        Ln,_=efa(R,k);Ls,_=efa(R52,k);C=congruence(Ln,Ls);ri,ci=linear_sum_assignment(-abs(C))
        sens[f"k{k}"]=[float(abs(C[i,j])) for i,j in sorted(zip(ri,ci))]
    old=pd.read_csv(OLD,dtype={"mouse_id":str})
    old=old.merge(df[META],on=META,validate="one_to_one")
    for k in (3,4):
        scores=pd.read_csv(OUT/f"k{k}_scores.csv")
        if k==4:
            merged=scores.merge(old,on=META,suffixes=("_pearson","_rank"))
            nr=np.column_stack([merged[f"D{i}_score_pearson"] for i in range(1,k+1)])
            orr=np.column_stack([merged[f"D{i}_score_rank"] for i in range(1,k+1)])
            cross=np.corrcoef(nr.T,orr.T)[:k,k:]
            pd.DataFrame(cross,index=[f"new_D{i}" for i in range(1,k+1)],
                         columns=[f"old_D{i}" for i in range(1,k+1)]).to_csv(OUT/"new_vs_old_k4_correlations.csv")
    result={"source":str(SOURCE),"n":{"week0":54,"week16":41,"week24":38,"all":133,"observed_baseline":52},
          "nfeatures":26,"transform":"baseline-frozen ordinary z (not rank) from processed raw-z matrix",
          "imputation_caveat":"historical preprocessing was fit on all living weeks, not leakage-free prospective",
          "parallel_analysis_counts":counts,"top5":tab.head(5).round(6).to_dict("records"),
          "efa":evals,"sensitivity_observed52_congruence":sens,
          "outliers_seven_excluded":"same 7 late rows as previous analysis; raw readings not verified",
          "no_prediction_done":True}
    (OUT/"SUMMARY.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    with open(OUT/"SUMMARY.md","w",encoding="utf8") as f:
        f.write("# Pearson-z EFA: blocks 1-4\n\n")
        f.write(f"n=54 baseline, 26 features; 133 living states; parallel counts: {counts}\n\n")
        for kk,m in evals.items():
            f.write(f"## {kk}: RMSE={m['rmse_corr']:.5f}; primary counts {m['assigned']}; unassigned={m['unassigned']}; crossloaded={m['crossloaded']}\n\n")
            f.write(str(m["max_features"])+"\n\n")
        f.write("Outliers and stage3 baseline-derived z/imputation inherited from the previous source. No forecasting; no feature selection was redone.\n")
    print(json.dumps({"parallel":counts,"efa":{k:{"rmse":v["rmse_corr"],"assigned":v["assigned"],"unassigned":v["unassigned"],"crossloaded":v["crossloaded"],"max":v["max_features"],"boot":v.get("bootstrap",{}).get("median",[])} for k,v in evals.items()},"sensitivity":sens},ensure_ascii=False))
if __name__=="__main__":main()
