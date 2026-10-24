#!/usr/bin/env python3
"""Huber + Bayesian Ridge + Ridge + two simple baselines, PBS/LPS rank-EFA3.

HuberRegressor(alpha=0.1, epsilon=1.35): fixed before validation.
Previously reported Bayes/Ridge benchmark is reproduced and verified.
No intervention, external cohort, synthetic mice or feature selection.
All evaluation by leave-one-MOUSE-out. Generates Word report through GitHub Actions.
"""
from pathlib import Path
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.patches import Rectangle
from sklearn.linear_model import Ridge,BayesianRidge,HuberRegressor
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION_START
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


HERE=Path(__file__).resolve().parent
SOURCE=HERE/"input"/"clean133_k3_rank_frozen_scores.csv"
OUT=HERE/"results"
OUT.mkdir(parents=True,exist_ok=True)
DATE="24.10.2026"
DOMAINS=("D1","D2","D3")
INTERVALS=(("PBS 0→16","PBS",0,16),("PBS 16→24","PBS",16,24),("LPS 16→24","LPS",16,24),("PBS 0→24","PBS",0,24))
COLORS={"Huber":"#55917A","Bayesian Ridge":"#397EA1","Ridge":"#7199AF","Без изменений":"#CE9872","Среднее":"#9AA8B4"}
GROUP_COLORS={"PBS":"#5282A2","LPS":"#BC7C59"}
INK="#274658";SUB="#526977";BG="#ECF0F3"


def paired(df,group,first,last):
    z=df[df.group==group]
    a=z[z.week==first][["mouse_id","status"]+[f"{d}_score" for d in DOMAINS]].copy()
    b=z[z.week==last][["mouse_id","status"]+[f"{d}_score" for d in DOMAINS]].copy()
    assert a.mouse_id.is_unique and b.mouse_id.is_unique
    a=a.rename(columns={"status":"status_start",**{f"{d}_score":f"{d}_start" for d in DOMAINS}})
    b=b.rename(columns={"status":"status_end",**{f"{d}_score":f"{d}_end" for d in DOMAINS}})
    return a.merge(b,on="mouse_id",validate="one_to_one").sort_values("mouse_id").reset_index(drop=True)


def predict_train(x,y,xq,model_name):
    mu=float(np.mean(x))
    sd=float(np.std(x,ddof=0))
    if sd<1e-10:
        return float(np.mean(y)),float(np.std(y,ddof=1)) if len(y)>1 else 0.
    xx=((x-mu)/sd).reshape(-1,1)
    query=np.array([[(xq-mu)/sd]])
    if model_name=="Ridge":
        mod=Ridge(alpha=1.0,fit_intercept=True)
        mod.fit(xx,y)
        return float(mod.predict(query)[0]),np.nan
    if model_name=="Huber":
        mod=HuberRegressor(epsilon=1.35,alpha=0.1,fit_intercept=True,max_iter=1500,tol=1e-6)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mod.fit(xx,y)
        return float(mod.predict(query)[0]),np.nan
    mod=BayesianRidge(max_iter=300,tol=1e-3,
                      alpha_1=1e-6,alpha_2=1e-6,
                      lambda_1=1e-6,lambda_2=1e-6,fit_intercept=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        mod.fit(xx,y)
    yh,unc=mod.predict(query,return_std=True)
    return float(yh[0]),float(unc[0])


def evaluate(x,y):
    n=len(x); assert n>=4
    hub=np.zeros(n);bay=np.zeros(n);ridge=np.zeros(n);avg=np.zeros(n);sd=np.zeros(n)
    for i in range(n):
        sel=np.arange(n)!=i
        hub[i],_=predict_train(x[sel],y[sel],x[i],"Huber")
        bay[i],sd[i]=predict_train(x[sel],y[sel],x[i],"Bayesian Ridge")
        ridge[i],_=predict_train(x[sel],y[sel],x[i],"Ridge")
        avg[i]=float(y[sel].mean())
    pool={"Huber":hub,"Bayesian Ridge":bay,"Ridge":ridge,"Без изменений":x.copy(),"Среднее":avg}
    mae={k:float(np.abs(y-v).mean()) for k,v in pool.items()}
    rmse={k:float(np.sqrt(np.mean((y-v)**2))) for k,v in pool.items()}
    result={"n":n,
        "huber_mae":mae["Huber"],"bayes_mae":mae["Bayesian Ridge"],"ridge_mae":mae["Ridge"],
        "unchanged_mae":mae["Без изменений"],"mean_mae":mae["Среднее"],
        "huber_rmse":rmse["Huber"],"bayes_rmse":rmse["Bayesian Ridge"],"ridge_rmse":rmse["Ridge"],
        "unchanged_rmse":rmse["Без изменений"],"mean_rmse":rmse["Среднее"],
        "best_method":min(mae,key=mae.get),"best_mae":min(mae.values()),
        "huber_better_ridge":bool(mae["Huber"]<mae["Ridge"]),
        "huber_better_bayes":bool(mae["Huber"]<mae["Bayesian Ridge"]),
        "huber_better_both_baselines":bool(mae["Huber"]<min(mae["Без изменений"],mae["Среднее"])),
        "huber_best_all_five":bool(mae["Huber"]==min(mae.values())),
        "bayes_better_ridge":bool(mae["Bayesian Ridge"]<mae["Ridge"]),
        "bayes_best_all_five":bool(mae["Bayesian Ridge"]==min(mae.values())),
        "mean_change":float((y-x).mean()),
        "loo_bayes_95pct_interval_coverage":float(np.mean((y>=bay-1.96*sd)&(y<=bay+1.96*sd))) }
    residual=float(((y-y.mean())**2).sum())
    for name,arr in [("huber",hub),("bayes",bay),("ridge",ridge)]:
        result[name+"_cv_r2"]=float(1-((y-arr)**2).sum()/residual) if residual>1e-10 else np.nan
    return result,{"Huber":hub,"Bayesian Ridge":bay,"Ridge":ridge,"Без изменений":x.copy(),"Среднее":avg,"Bayes SD":sd}


def analyze(data):
    metrics=[];pred=[];pairsets=[]
    for title,group,t0,t1 in INTERVALS:
        p=paired(data,group,t0,t1)
        n=len(p)
        assert n=={("PBS",0,16):9,("PBS",16,24):6,("LPS",16,24):11,("PBS",0,24):6}[(group,t0,t1)],(title,n)
        q=p.copy();q.insert(0,"transition",title);pairsets.append(q)
        for domain in DOMAINS:
            x=p[f"{domain}_start"].to_numpy(float)
            y=p[f"{domain}_end"].to_numpy(float)
            stats,ff=evaluate(x,y)
            metrics.append({"transition":title,"group":group,"week_from":t0,"week_to":t1,"domain":domain,**stats})
            for i in range(n):
                pred.append({"transition":title,"domain":domain,"mouse_id":p.mouse_id.iat[i],
                             "status_start":p.status_start.iat[i],"status_end":p.status_end.iat[i],
                             "current":x[i],"actual":y[i],"huber_pred":ff["Huber"][i],"bayes_pred":ff["Bayesian Ridge"][i],
                             "ridge_pred":ff["Ridge"][i],"unchanged_pred":x[i],
                             "mean_pred":ff["Среднее"][i],"bayes_predictive_std":ff["Bayes SD"][i],
                             "huber_abs_err":abs(y[i]-ff["Huber"][i]),
                             "bayes_abs_err":abs(y[i]-ff["Bayesian Ridge"][i]),
                             "ridge_abs_err":abs(y[i]-ff["Ridge"][i])})
    m=pd.DataFrame(metrics)
    p=pd.DataFrame(pred)
    assert len(m)==12 and len(p)==3*(9+6+11+6)
    m.to_csv(OUT/"model_metrics.csv",index=False)
    p.to_csv(OUT/"leave_one_mouse_out_predictions.csv",index=False)
    pd.concat(pairsets,ignore_index=True).to_csv(OUT/"paired_mouse_scores.csv",index=False)
    # Preserve prior Ridge experiment independently in GitHub (12 tasks).
    ridgecols=["transition","group","week_from","week_to","domain","n","ridge_mae","ridge_rmse","unchanged_mae","unchanged_rmse","mean_mae","mean_rmse"]
    m[ridgecols].to_csv(OUT/"previous_ridge_reproduced.csv",index=False)
    historic={
      ("PBS 0→16","D1"):1.200022,("PBS 0→16","D2"):.881626,("PBS 0→16","D3"):1.009778,
      ("PBS 16→24","D1"):.270623,("PBS 16→24","D2"):.956556,("PBS 16→24","D3"):1.610203,
      ("LPS 16→24","D1"):.724493,("LPS 16→24","D2"):.322451,("LPS 16→24","D3"):1.151570,
      ("PBS 0→24","D1"):.290680,("PBS 0→24","D2"):.621357,("PBS 0→24","D3"):.770379
    }
    assert all(abs(float(r.ridge_mae)-historic[(r.transition,r.domain)])<0.000003 for r in m.itertuples()),"Prior Ridge benchmark mismatch"
    # Exact historical equivalence: old Bayesian Ridge and Ridge on the same leave-one-out mice.
    old=pd.read_csv(HERE/"input"/"previous_bayesian_model_metrics.csv")
    merged=m.merge(old,on=["transition","group","week_from","week_to","domain"],
                   suffixes=("","_history"),validate="one_to_one")
    assert len(merged)==12
    for k in ["bayes_mae","ridge_mae","unchanged_mae","mean_mae"]:
        maxdiff=float(np.max(np.abs(merged[k]-merged[k+"_history"])))
        assert maxdiff < 1e-8,(k,maxdiff)
    return m,p


def spread(values,lower,upper,gap):
    items=sorted(values,key=lambda x:(x[1],x[0]))
    if not items:return {}
    ys=[max(lower,float(v[1])) for v in items]
    for i in range(1,len(ys)):ys[i]=max(ys[i],ys[i-1]+gap)
    if ys[-1]>upper:
        delta=ys[-1]-upper
        ys=[v-delta for v in ys]
    for i in range(len(ys)-2,-1,-1):ys[i]=min(ys[i],ys[i+1]-gap)
    if ys[0]<lower:ys=[v+lower-ys[0] for v in ys]
    return {it[0]:ys[i] for i,it in enumerate(items)}


def trajectories(data,domain):
    fig,axes=plt.subplots(1,2,figsize=(15.6,3.90),dpi=150,sharey=True)
    allv=data[data.group.isin(["PBS","LPS"])][f"{domain}_score"]
    lo,hi=float(allv.min())-.5,float(allv.max())+.5
    for ax,grp in zip(axes,["PBS","LPS"]):
        d=data[data.group==grp].copy()
        col=GROUP_COLORS[grp]
        endpoints={}
        for id_,g in d.groupby("mouse_id"):
            g=g.sort_values("week")
            x=g.week.to_numpy(float);y=g[f"{domain}_score"].to_numpy(float)
            ax.plot(x,y,lw=1.3,alpha=.60,color=col,marker="o",ms=3.8,zorder=2)
            endpoints[id_]=(x[-1],y[-1])
        for t in (0,16,24):ax.axvline(t,lw=.5,color="#E2E8EC",zorder=0)
        ax.axhline(0,ls=":",lw=.8,color="#ADB9C1")
        groups={}
        for name,(last,y) in endpoints.items():groups.setdefault(last,[]).append((name,y))
        for last,groupends in groups.items():
            gap=(hi-lo)*(0.070 if last==24 else 0.053)
            pos=spread(groupends,lo+.12,hi-.12,gap)
            for name,y in groupends:
                text_x={0:2.3,16:18.1,24:26.5}[last]
                ax.annotate(str(name),xy=(last,y),xytext=(text_x,pos[name]),
                            fontsize=8.7,color="#293746",fontweight="bold",zorder=9,
                            va="center",ha="left",
                            bbox=dict(boxstyle="round,pad=.16",facecolor="white",
                                      edgecolor="none",alpha=.88),
                            arrowprops=dict(arrowstyle="-",linestyle=(0,(2.2,2.0)),
                                            color="#6D7782",lw=.8,alpha=.9,
                                            shrinkA=2,shrinkB=2),
                            annotation_clip=False)
        counts=d.groupby("week").size()
        ax.set_title(f"{grp}\nn={int(counts.get(0,0))} / {int(counts.get(16,0))} / {int(counts.get(24,0))}",
                     fontsize=12,fontweight="bold",color=col)
        ax.set_xlim(-1.5,32);ax.set_ylim(lo,hi)
        ax.set_xticks([0,16,24]);ax.set_xlabel("Неделя",fontsize=10)
        ax.grid(axis="y",color="#E8ECEF",lw=.6)
        ax.spines[["top","right"]].set_visible(False)
        ax.tick_params(labelsize=8.5)
    axes[0].set_ylabel("Доменный балл (центр week 0 = 0)",fontsize=10,color=SUB)
    fig.suptitle(f"{domain}  |  {'OFT / rear' if domain=='D1' else 'Learning / Endurance' if domain=='D2' else 'NOR1 + NOR2'}  |  номер у последнего измерения",
                 fontsize=13,color=INK,fontweight="bold",y=.995)
    fig.subplots_adjust(left=.06,right=.99,bottom=.12,top=.80,wspace=.12)
    path=OUT/f"{domain}_trajectories.png"
    fig.savefig(path,dpi=150,facecolor="white");plt.close(fig)
    return path


def group_means(data):
    fig,axes=plt.subplots(1,3,figsize=(15.7,3.75),dpi=150)
    for ax,domain in zip(axes,DOMAINS):
        for group in ["PBS","LPS"]:
            z=data[data.group==group].groupby("week")[f"{domain}_score"].agg(["mean","sem","count"])
            xv=z.index.to_numpy(float);yv=z["mean"].to_numpy(float)
            ax.plot(xv,yv,marker="o",lw=2,ms=6,label=group,color=GROUP_COLORS[group])
            ax.fill_between(xv,yv-z["sem"].fillna(0).to_numpy(),yv+z["sem"].fillna(0).to_numpy(),alpha=.13,color=GROUP_COLORS[group])
        ax.axhline(0,color="#AAB7BF",ls=":",lw=1)
        ax.set_xticks([0,16,24]);ax.set_title(domain,fontweight="bold",color=INK)
        ax.grid(axis="y",color="#E5EAEE",lw=.6)
        ax.spines[["right","top"]].set_visible(False)
        ax.set_xlabel("Неделя");ax.set_ylabel("Среднее ± SE" if domain=="D1" else "")
    axes[2].legend(frameon=False,loc="best",fontsize=10)
    fig.suptitle("Средние баллы D1–D3 · PBS / LPS  |  описательная динамика",fontsize=12.7,color=INK,fontweight="bold")
    fig.tight_layout(rect=[0,.02,1,.91])
    out=OUT/"mean_trajectories.png";fig.savefig(out,dpi=150);plt.close(fig)
    return out


def error_chart(m):
    fig,axes=plt.subplots(1,4,figsize=(17.5,5.0),dpi=150,sharey=True)
    keys=[("huber_mae","Huber"),("bayes_mae","Bayesian Ridge"),("ridge_mae","Ridge"),("unchanged_mae","Без изменений"),("mean_mae","Среднее")]
    w=.172;loc=np.arange(3)
    for j,((title,_,_,_),ax) in enumerate(zip(INTERVALS,axes)):
        v=m[m.transition==title].set_index("domain").loc[list(DOMAINS)]
        for i,(key,label) in enumerate(keys):
            ax.bar(loc+(i-2)*w,v[key],color=COLORS[label],width=w*.96,zorder=2)
        for k,d in enumerate(DOMAINS):
            row=v.loc[d]
            nums=[row[key] for key,_ in keys]
            im=int(np.argmin(nums))
            ax.text(loc[k]+(im-2)*w,nums[im]+.045,"▼",ha="center",fontsize=9,color=INK)
        ax.set_title(f"{title}\nn={int(v.n.iloc[0])} мышей",fontweight="bold",fontsize=10.5,color=INK)
        ax.set_xticks(loc,list(DOMAINS));ax.set_ylim(0,max(2.4,float(m[[k for k,_ in keys]].max().max())*1.14))
        ax.set_ylabel("MAE (меньше — лучше)" if j==0 else "")
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y",color="#DEE6EB",alpha=.8,zorder=0)
    patches=[Rectangle((0,0),1,1,color=COLORS[n]) for _,n in keys]
    fig.legend(patches,[n for _,n in keys],loc="upper center",bbox_to_anchor=(.51,.915),ncol=5,frameon=False,fontsize=8.5)
    fig.suptitle("Huber / Bayesian Ridge / Ridge / без изменений / среднее  |  12 задач",fontweight="bold",fontsize=13,color=INK,y=.99)
    fig.subplots_adjust(left=.06,right=.99,top=.73,bottom=.16,wspace=.23)
    out=OUT/"five_method_mae.png";fig.savefig(out,dpi=150);plt.close(fig);return out


def winner_chart(m):
    fig,ax=plt.subplots(figsize=(15.5,3.85),dpi=150)
    ax.axis("off");ax.set_xlim(-.9,4.06);ax.set_ylim(-.45,3.05)
    bg={"Bayesian Ridge":"#D8EBF4","Huber":"#D8EDE5","Ridge":"#E4EFF5","Без изменений":"#F1E0D4","Среднее":"#E9EDF0"}
    for j,(title,_,_,_) in enumerate(INTERVALS):
        ax.text(j+.5,2.82,title,ha="center",fontsize=11,fontweight="bold",color=INK)
    for i,dom in enumerate(DOMAINS):
        y=2.20-i*.91
        ax.text(-.06,y,{"D1":"D1 — OFT","D2":"D2 — Learning","D3":"D3 — NOR1/2"}[dom],ha="right",va="center",color=INK,fontweight="bold")
        for j,(title,_,_,_) in enumerate(INTERVALS):
            row=m[(m.transition==title)&(m.domain==dom)].iloc[0]
            x=j+.03
            ax.add_patch(Rectangle((x,y-.37),.94,.76,fc=bg[row.best_method],ec="white",lw=2))
            ax.text(x+.47,y+.12,row.best_method,ha="center",fontsize=9.6,fontweight="bold",color=INK)
            ax.text(x+.47,y-.19,f"MAE = {row.best_mae:.3f}",ha="center",fontsize=9,color=SUB)
    fig.tight_layout(pad=.4)
    out=OUT/"winners.png";fig.savefig(out,dpi=150);plt.close(fig);return out


def scatter_chart(m,p):
    fig,axes=plt.subplots(4,3,figsize=(17.6,9.45),dpi=150)
    for i,(title,_,_,_) in enumerate(INTERVALS):
        for j,domain in enumerate(DOMAINS):
            ax=axes[i,j]
            v=p[(p.transition==title)&(p.domain==domain)]
            r=m[(m.transition==title)&(m.domain==domain)].iloc[0]
            x=v.actual.to_numpy(float);y=v.huber_pred.to_numpy(float)
            lo=min(x.min(),y.min());hi=max(x.max(),y.max());margin=(hi-lo)*.1+.12
            ax.plot([lo-margin,hi+margin],[lo-margin,hi+margin],"--",lw=1,color="#A1ABB3")
            ax.scatter(x,y,c=COLORS["Huber"],edgecolor="white",lw=.5,s=36,zorder=2)
            ax.set_xlim(lo-margin,hi+margin);ax.set_ylim(lo-margin,hi+margin)
            ax.set_title(f"{domain} · MAE {r.huber_mae:.3f}",fontsize=11,fontweight="bold",color=INK)
            ax.grid(alpha=.16);ax.spines[["top","right"]].set_visible(False)
            ax.tick_params(labelsize=8.5)
            if j==0:ax.set_ylabel(f"{title}\nПРОГНОЗ",fontsize=10,color=SUB)
            if i==3:ax.set_xlabel("Фактический будущий балл",fontsize=9,color=SUB)
    fig.suptitle("Huber: факт против прогноза  |  каждая точка — мышь",
                 fontweight="bold",color=INK,fontsize=14.5,y=.998)
    fig.subplots_adjust(left=.095,right=.985,top=.93,bottom=.08,hspace=.56,wspace=.25)
    out=OUT/"huber_actual_vs_prediction.png";fig.savefig(out,dpi=150);plt.close(fig);return out


def rgb(code):
    c=mcolors.to_rgb(code);return RGBColor(*[int(255*v) for v in c])


def set_cell_fill(cell,code):
    tcpr=cell._tc.get_or_add_tcPr()
    sh=OxmlElement("w:shd");sh.set(qn("w:fill"),code.strip("#"))
    tcpr.append(sh)


def add_line(p):
    ppr=p._p.get_or_add_pPr()
    borders=OxmlElement("w:pBdr")
    bt=OxmlElement("w:bottom")
    for key,val in [("val","single"),("sz","9"),("space","3"),("color","5484A2")]:
        bt.set(qn("w:"+key),val)
    borders.append(bt);ppr.append(borders)


def paragraph(doc,text,bold=False,size=9,color=None,space=3):
    p=doc.add_paragraph()
    p.paragraph_format.space_after=Pt(space)
    p.paragraph_format.space_before=Pt(0)
    p.paragraph_format.line_spacing=1.07
    r=p.add_run(text)
    r.bold=bold;r.font.name="Calibri";r.font.size=Pt(size)
    if color:r.font.color.rgb=rgb(color)
    return p


def heading(doc,text,size=17):
    p=paragraph(doc,text,bold=True,size=size,color=INK,space=6);add_line(p)
    return p


def picture(doc,path,width=10.5):
    p=doc.add_paragraph()
    p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after=Pt(4)
    p.paragraph_format.space_before=Pt(0)
    p.add_run().add_picture(str(path),width=Inches(width))
    return p


def report(data,m,p):
    files={dom:trajectories(data,dom) for dom in DOMAINS}
    avg=group_means(data);bars=error_chart(m);winners=winner_chart(m);scatter=scatter_chart(m,p)
    doc=Document()
    sec=doc.sections[0]
    sec.page_width=Inches(11.69);sec.page_height=Inches(8.27)
    sec.left_margin=Inches(.44);sec.right_margin=Inches(.44)
    sec.top_margin=Inches(.38);sec.bottom_margin=Inches(.40)
    sec.header_distance=Inches(.13);sec.footer_distance=Inches(.14)
    styles=doc.styles;styles["Normal"].font.name="Calibri";styles["Normal"].font.size=Pt(9)
    footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    run=footer.add_run(f"24.10.2026 · eNRI / 3 домена · Huber")
    run.font.size=Pt(8);run.font.color.rgb=rgb("#7B8790")
    heading(doc,"Динамика трёх доменов · PBS и LPS")
    num=data[data.group.isin(["PBS","LPS"])].mouse_id.nunique()
    states=len(data[data.group.isin(["PBS","LPS"])])
    paragraph(doc,f"{num} мышей · {states} живых состояний · недели 0 / 16 / 24. Сплошная цветная линия — мышь; тёмно-серый пунктир — соединение с её номером. Номер у последней доступной точки.",size=9,color=SUB,space=6)
    paragraph(doc,"D1 · двигательная активность — OFT / rear",bold=True,size=11,color=INK)
    picture(doc,files["D1"],width=10.40)
    paragraph(doc,"D2 · обучение и выносливость — Learning / Endurance",bold=True,size=11,color=INK)
    picture(doc,files["D2"],width=10.40)
    paragraph(doc,"Вывод: индивидуальные траектории неодинаковы; 0 — среднее положение на исходной неделе, а не отсутствие функции.",size=8.5,color=SUB)
    doc.add_page_break()
    heading(doc,"Динамика доменов · продолжение")
    paragraph(doc,"D3 · исследовательское поведение — NOR1 + NOR2",bold=True,size=11,color=INK)
    picture(doc,files["D3"],width=10.4)
    paragraph(doc,"Средние баллы D1–D3 · PBS / LPS",bold=True,size=11,color=INK)
    picture(doc,avg,width=10.35)
    paragraph(doc,"В анализ прогноза входят только PBS и LPS; D3 рассчитан отдельной EFA на трёх факторах. На графиках показана наблюдаемая динамика, не причинный эффект.",size=8.5,color=SUB)
    doc.add_page_break()
    heading(doc,"Точность прогноза · Huber / Bayesian Ridge / Ridge / без изменений / среднее")
    paragraph(doc,"12 задач: 3 домена × 4 интервала. Leave-one-mouse-out, MAE — средняя абсолютная ошибка (меньше — лучше). Huber: ε=1,35, α=0,1, параметры фиксированы до проверки. ▼ — лучший метод.",size=8.9,color=SUB)
    picture(doc,bars,width=10.5)
    paragraph(doc,"Кто выиграл по каждому домену?",size=11,bold=True,color=INK)
    picture(doc,winners,width=10.5)
    best=int(m.huber_best_all_five.sum())
    improvements=int(m.huber_better_ridge.sum())
    bayeswins=int(m.huber_better_bayes.sum())
    basewins=int(m.huber_better_both_baselines.sum())
    paragraph(doc,f"Итог: Huber точнее Ridge в {improvements}/12, Bayesian Ridge — в {bayeswins}/12, обеих простых альтернатив — в {basewins}/12; лучший из пяти методов — в {best}/12.",size=9,bold=True,color=INK)
    doc.add_page_break()
    heading(doc,"Факт против прогноза · 12 независимых проверок")
    paragraph(doc,"Ряды: PBS 0→16 (n=9), PBS 16→24 (n=6), LPS 16→24 (n=11), PBS 0→24 (n=6). Столбцы: D1–D3. Пунктир — идеальный прогноз.",size=8.9,color=SUB)
    picture(doc,scatter,width=10.6)
    paragraph(doc,"Вывод: при n=6–11 даже выигрыш на LOOCV нестабилен. Huber уменьшает влияние выбросов, но не гарантирует более точный прогноз на новых мышах.",size=8.5,bold=True,color=INK)
    paragraph(doc,"Источник: GitHub / LisaGaydamaka/coworking / mouse_neuroplasticity_enri. Факторные баллы EFA рассчитаны заранее; LOOCV проверяет только регрессии, а не всю цепочку EFA и импутации. Только мыши с обеими точками; результат условен на выживании.",size=7.7,color=SUB)
    out=OUT/"Otchet_Huber_D1-D3_RANG_PBS_LPS_2026-10-24.docx"
    doc.save(out)
    return out


def main():
    data=pd.read_csv(SOURCE,dtype={"mouse_id":str})
    assert len(data)==133 and data.week.value_counts().to_dict()=={0:54,16:41,24:38}
    m,p=analyze(data)
    output=report(data,m,p)
    report_txt=[
       "# Huber vs Bayesian Ridge vs Ridge / 3 rank-EFA domains / PBS+LPS", "",
       "**Inputs**: k=3 baseline-frozen Spearman EFA on full 26 features. 54 baseline mice and 133 living visits. PBS and LPS only. Four transitions: PBS 0→16, PBS 16→24, LPS 16→24, PBS 0→24.", "",
       "**Models**: HuberRegressor(epsilon=1.35, alpha=0.1) fixed beforehand, BayesianRidge(Gamma priors 1e-6), Ridge(alpha=1), persistence, training-only future mean. One starting domain predictor, x scaled within training fold; leave-one-mouse-out. Historical Bayesian and Ridge errors checked to 1e-8.", "",
       "| Interval | Domain | n | Huber MAE | Bayes MAE | Ridge MAE | Persistence MAE | Train-mean MAE | Winner |",
       "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in m.itertuples():
        report_txt.append(f"| {r.transition} | {r.domain} | {r.n} | {r.huber_mae:.3f} | {r.bayes_mae:.3f} | {r.ridge_mae:.3f} | {r.unchanged_mae:.3f} | {r.mean_mae:.3f} | {r.best_method} |")
    report_txt += ["",
       f"Huber < Ridge: {int(m.huber_better_ridge.sum())}/12; Huber < Bayesian: {int(m.huber_better_bayes.sum())}/12; Huber < both simple baselines: {int(m.huber_better_both_baselines.sum())}/12; Huber best out of five: {int(m.huber_best_all_five.sum())}/12.", "",
       "**Caveats**: n=6–11. LOOCV only on fixed precomputed EFA scores, not end-to-end leakage-free baseline preprocessing. Only surviving paired mice; no external validation; no synthetic augmentation. Pooled interpretation across different experimental exposures is not supported.","",
       "Report: results/Otchet_Huber_D1-D3_RANG_PBS_LPS_2026-10-24.docx."]
    (OUT/"REPORT.md").write_text("\n".join(report_txt)+"\n",encoding="utf-8")
    summary={"n_total_states":len(data),"transitions":[{"transition":name,"n":int(m[m.transition==name].n.iloc[0])} for name,_,_,_ in INTERVALS],
             "huber_beats_ridge":int(m.huber_better_ridge.sum()),
             "huber_beats_bayesian":int(m.huber_better_bayes.sum()),
             "huber_beats_both_simple_baselines":int(m.huber_better_both_baselines.sum()),
             "huber_best_of_five":int(m.huber_best_all_five.sum()),
             "reference_ridge_and_bayesian_all12_matched":True,"n_tasks":len(m)}
    (OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False))
    print(m[["transition","domain","n","huber_mae","bayes_mae","ridge_mae","unchanged_mae","mean_mae","best_method"]].to_string(index=False))
    print("REPORT",output.name,output.stat().st_size)


if __name__=="__main__":main()