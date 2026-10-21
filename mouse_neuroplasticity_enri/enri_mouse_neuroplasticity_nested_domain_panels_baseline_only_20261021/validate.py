import importlib.util,json,warnings
from pathlib import Path
import numpy as np,pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy.stats import rankdata
from sklearn.model_selection import RepeatedStratifiedKFold,KFold
from factor_analyzer import FactorAnalyzer
R=Path(__file__).resolve().parent;O=R/"results";O.mkdir(exist_ok=True)
P=R.parent;F=[x for x in []]
S=20261021;rng=np.random.default_rng(S)
sp=importlib.util.spec_from_file_location("base",P/"enri_mouse_neuroplasticity_feature_selection_all0mean_grip_longitudinal"/"solve_all0mean_grip_longitudinal.py")
base=importlib.util.module_from_spec(sp);sp.loader.exec_module(base)
raw=base.build_long_table(base.load_included_source());raw=raw[raw.week.eq(0)].reset_index(drop=True)
F=[f for f in base.MODEL_FEATURES if f not in {"Learning_T1sum","Learning_T2sum","Learning_T3sum","Average_speed_NOR1","Average_speed_NOR2"}]
assert len(raw)==54 and len(F)==26
meta=raw[["mouse_id","group"]].copy()
refbase=P/"enri_mouse_neuroplasticity_efa26_robust_validation_rank_scores"/"results"
refs={k:pd.read_csv(refbase/f"main26_k{k}_loadings.csv").set_index("feature").loc[F,[f"D{j+1}" for j in range(k)]].to_numpy() for k in [3,4]}
def prep(ids):
    df,diag=base.fit_transform_stage3(raw,fit_mouse_ids=set(ids),random_state=base.IMPUTATION_SEED,sample_posterior=False)
    if diag["errors"]:raise ValueError(str(diag["errors"])[:500])
    x=df[F].to_numpy(float)
    if not np.isfinite(x).all():raise ValueError("nonfinite")
    return x
def fit(xtrain,xtest,k):
    rr=pd.DataFrame(xtrain).corr(method="spearman").to_numpy()
    eig=np.linalg.eigvalsh(rr)
    if eig[0]<1e-8:
        rr+=np.eye(len(rr))*(1e-8-eig[0]);sd=np.sqrt(np.diag(rr));rr/=np.outer(sd,sd)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fa=FactorAnalyzer(n_factors=k,rotation="oblimin",method="minres",is_corr_matrix=True,use_smc=True);fa.fit(rr)
    L=fa.loadings_;Phi=np.array(fa.phi_ if fa.phi_ is not None else np.eye(k))
    c=refs[k].T@L/np.maximum(np.linalg.norm(refs[k],axis=0)[:,None]*np.linalg.norm(L,axis=0)[None,:],1e-12)
    a,b=linear_sum_assignment(-np.abs(c));idx=np.zeros(k,int);sign=np.ones(k)
    for i,j in zip(a,b):idx[i]=j;sign[i]=np.sign(c[i,j]) or 1
    L=L[:,idx]*sign;Phi=Phi[np.ix_(idx,idx)]*sign[:,None]*sign[None,:]
    zt=np.empty_like(xtrain);zv=np.empty_like(xtest)
    for j in range(xtrain.shape[1]):
        r=rankdata(xtrain[:,j]);mu=r.mean();sd=r.std(ddof=1)
        if sd<1e-8:raise ValueError("constant ranks")
        zt[:,j]=(r-mu)/sd
        v=np.sort(xtrain[:,j])
        zv[:,j]=((np.searchsorted(v,xtest[:,j],"left")+np.searchsorted(v,xtest[:,j],"right")+1)/2-mu)/sd
    W=np.linalg.pinv(rr,rcond=1e-8)@L@Phi
    u=zt@W;mu=u.mean(0);sd=u.std(0,ddof=1)
    return zt,zv,(u-mu)/sd,(zv@W-mu)/sd,np.abs(c[a,b])
def ridge(x,y):
    xm=x.mean(0);ym=y.mean();b=np.linalg.solve((x-xm).T@(x-xm)+np.eye(x.shape[1])*.03,(x-xm).T@(y-ym))
    return ym-xm@b,b
def pred(model,x):return model[0]+x@model[1]
def select(x,y,seed,maxn=5):
    splits=list(KFold(3,shuffle=True,random_state=seed).split(x))
    chosen=[];result=[]
    for q in range(y.shape[1]):
        cols=[];curve=[]
        for n in range(1,maxn+1):
            best=None;low=np.inf
            for j in range(x.shape[1]):
                if j in cols:continue
                ii=cols+[j];yp=np.empty(len(y))
                for a,b in splits:yp[b]=pred(ridge(x[a][:,ii],y[a,q]),x[b][:,ii])
                err=np.sqrt(np.mean((yp-y[:,q])**2))
                if err<low:low=err;best=j;bestp=yp
            cols.append(best)
            corr=np.corrcoef(bestp,y[:,q])[0,1] if np.std(bestp)>0 else 0
            curve.append((cols.copy(),float(low),float(corr)))
        minimum=min(c[1] for c in curve)
        winners=[c for c in curve if c[1]<=1.1*minimum and c[2]>=.9]
        ch=(winners[0] if winners else min(curve,key=lambda t:t[1]))
        chosen.append((ch[0],ridge(x[:,ch[0]],y[:,q]),len(winners)>0,ch[1],ch[2]))
        for nn,c in enumerate(curve,1):result.append((q,nn,c[1],c[2]))
    return chosen,result
cv=RepeatedStratifiedKFold(5,n_repeats=2,random_state=S)
res=[];scores=[];picked=[];curves=[]
ids=meta.mouse_id.to_numpy();groups=meta.group.to_numpy()
for fold,(tr,te) in enumerate(cv.split(ids,groups)):
    x=prep(ids[tr])
    for k in (3,4):
        ztrain,ztest,yt,yv,sim=fit(x[tr],x[te],k)
        sels,cvcurve=select(ztrain,yt,S+fold*31+k)
        for j,n,e,c in cvcurve:curves.append(dict(fold=fold,k=k,domain=f"D{j+1}",n=n,inner_rmse=e,inner_r=c))
        for j,(cols,model,passed,innererr,innerr) in enumerate(sels):
            predv=pred(model,ztest[:,cols]);target=yv[:,j]
            err=float(np.sqrt(np.mean((predv-target)**2)))
            rr=float(np.corrcoef(predv,target)[0,1]) if len(te)>2 and np.std(predv)>0 else np.nan
            res.append(dict(fold=fold,k=k,domain=f"D{j+1}",n=len(cols),r=rr,rmse=err,pass_rule=passed,inner_rmse=innererr,inner_r=innerr,similarity=float(sim[j]),features=";".join(F[c] for c in cols)))
            for m,y,yp in zip(ids[te],target,predv):scores.append(dict(fold=fold,k=k,domain=f"D{j+1}",mouse_id=m,target=y,prediction=yp))
            for c in cols:picked.append(dict(fold=fold,k=k,domain=f"D{j+1}",feature=F[c]))
    print("CV",fold+1,flush=True)
for f,rows in [("outer_folds.csv",res),("heldout_predictions.csv",scores),("selected_features.csv",picked),("inner_curves.csv",curves)]:
    pd.DataFrame(rows).to_csv(O/f,index=False)
print("Bootstrap start",flush=True)
boot=[];bootfail=[];bootsel=[]
for b in range(150):
    ix=rng.integers(0,len(ids),len(ids))
    try:
        x=prep(ids[np.unique(ix)])
        for k in (3,4):
            z,_,y,_,sim=fit(x[ix],x[ix],k)
            sel,_=select(z,y,S+10000+b*13+k)
            for j,(cols,model,passed,innererr,innerr) in enumerate(sel):
                boot.append(dict(repeat=b,k=k,domain=f"D{j+1}",n=len(cols),pass_rule=passed,similarity=float(sim[j]),features=";".join(F[c] for c in cols)))
                for c in cols:bootsel.append(dict(repeat=b,k=k,domain=f"D{j+1}",feature=F[c]))
    except Exception as e:bootfail.append(dict(repeat=b,error=str(e)[:250]))
    if b%25==24:print("BOOT",b+1,"failed",len(bootfail),flush=True)
for f,rows in [("bootstrap_panels.csv",boot),("bootstrap_selected_features.csv",bootsel),("bootstrap_failures.csv",bootfail)]:
    pd.DataFrame(rows).to_csv(O/f,index=False)
if len({x["repeat"] for x in boot})<110:raise RuntimeError("Too many bootstrap failures")
sf=pd.DataFrame(scores);rf=pd.DataFrame(res);sel=pd.DataFrame(picked);bf=pd.DataFrame(bootsel)
summ=[];freq=[]
for k in (3,4):
    for j in range(k):
        dom=f"D{j+1}";x=sf[(sf.k==k)&(sf.domain==dom)];z=rf[(rf.k==k)&(rf.domain==dom)]
        cor=float(np.corrcoef(x.target,x.prediction)[0,1]);err=float(np.sqrt(np.mean((x.target-x.prediction)**2)))
        summ.append(dict(k=k,domain=dom,heldout_r=cor,heldout_rmse=err,median_fold_r=float(z.r.median()),median_n=float(z.n.median()),mean_n=float(z.n.mean()),n_folds=len(z),pass_fraction=float(z.pass_rule.mean())))
        for f in F:
            freq.append(dict(k=k,domain=dom,feature=f,outer_frequency=float((sel.k.eq(k)&sel.domain.eq(dom)&sel.feature.eq(f)).sum()/len(z)),bootstrap_frequency=float((bf.k.eq(k)&bf.domain.eq(dom)&bf.feature.eq(f)).sum()/len({v["repeat"] for v in boot}))))
pd.DataFrame(summ).to_csv(O/"SUMMARY.csv",index=False)
pd.DataFrame(freq).to_csv(O/"feature_frequencies.csv",index=False)
(O/"SUMMARY.json").write_text(json.dumps(dict(outer=summ,bootstrap_success=len({v["repeat"] for v in boot}),bootstrap_failure=len(bootfail),n_mice=54,n_features=26,outer_fold_count=10),indent=2,ensure_ascii=False))
report=["# Fully nested baseline-only EFA panel validation","",
"Baseline 54 mice, 26 predictors. All preprocessing refit using outer-training mouse IDs; no future visits used. 2x5 outer stratified folds. Full EFA MINRES oblimin refit separately for k=3/4 in every outer fold. Rank transformations and regression score weights learned from training mice, forward Ridge alpha=.03, inner 3-fold CV choosing 1-5 predictors, r>=.90 and RMSE <=110% min. Holdout tested exactly once per repetition. 150 bootstrap repeats refit whole procedure on resampled mice.",
"",
"## Results","",
"| k | Domain | Out-of-fold r | RMSE | Median selected predictors | Accepted inner size rule |",
"|--:|---|---:|---:|---:|---:|"]
for row in summ:report.append(f"| {row['k']} | {row['domain']} | {row['heldout_r']:.3f} | {row['heldout_rmse']:.3f} | {row['median_n']:.1f} | {row['pass_fraction']:.0%} |")
report.extend(["","## Limitations","",
"Factor labeling uses prior full-data EFA for orientation only; earlier feature-list engineering from these mice remains a source of exploratory optimism.",
"Reference full scores for heldout mice use all 26 observed predictors as ground truth; this tests reduction, not prospective biological validity.",
"Repeated folds share mice, hence pooled heldout correlation is not an independent-sample confidence interval.",
"No longitudinal prediction, intervention contrasts, survival prediction or independent external cohort validation has been performed.",
"See SUMMARY.csv, feature_frequencies.csv and fold/bootstrap CSVs for details."])
(O/"REPORT.md").write_text("\n".join(report)+"\n")
print(json.dumps(summ,ensure_ascii=False,indent=2),flush=True)
