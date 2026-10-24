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





# Forecast ΔD and reconstruct future level; all preprocessing uses training mice.
MODEL_NAMES=("Bayesian Δ","Huber Δ","Ridge Δ","Bayesian","Huber","Ridge","Без изменений","Среднее")
COLORS.update({"Bayesian Δ":"#124E78","Huber Δ":"#15775D","Ridge Δ":"#73528F","Bayesian":"#6FA4C3","Huber":"#7EAE9B","Ridge":"#AB97BB"})
MAE_KEYS={"Bayesian Δ":"bayes_delta_mae","Huber Δ":"huber_delta_mae","Ridge Δ":"ridge_delta_mae",
          "Bayesian":"bayes_mae","Huber":"huber_mae","Ridge":"ridge_mae",
          "Без изменений":"unchanged_mae","Среднее":"mean_mae"}


def evaluate(x,y):
    n=len(x)
    assert n>=4
    predictions={name:np.zeros(n) for name in MODEL_NAMES}
    delta_std=np.zeros(n)
    for j in range(n):
        train=np.arange(n)!=j
        xtr=x[train]
        ytr=y[train]
        deltr=ytr-xtr
        for method in ["Bayesian","Huber","Ridge"]:
            pred,_=predict_train(xtr,ytr,x[j],{"Bayesian":"Bayesian Ridge","Huber":"Huber","Ridge":"Ridge"}[method])
            d_pred,d_unc=predict_train(xtr,deltr,x[j],{"Bayesian":"Bayesian Ridge","Huber":"Huber","Ridge":"Ridge"}[method])
            predictions[method][j]=pred
            predictions[method+" Δ"][j]=float(x[j]+d_pred)
            if method=="Bayesian":delta_std[j]=d_unc
        predictions["Без изменений"][j]=x[j]
        predictions["Среднее"][j]=ytr.mean()
    err={name:float(np.abs(y-value).mean()) for name,value in predictions.items()}
    rmse={name:float(np.sqrt(np.mean((y-value)**2))) for name,value in predictions.items()}
    minimum=min(err,key=err.get)
    m={"n":n,"best_method":minimum,"best_mae":err[minimum],"mean_change":float((y-x).mean()),
       "bayes_delta_better_direct":err["Bayesian Δ"]<err["Bayesian"],
       "huber_delta_better_direct":err["Huber Δ"]<err["Huber"],
       "delta_ridge_better_direct":err["Ridge Δ"]<err["Ridge"],
       "bayes_delta_best_all_eight":minimum=="Bayesian Δ",
       "huber_delta_best_all_eight":minimum=="Huber Δ",
       "any_new_delta_best":minimum in ["Bayesian Δ","Huber Δ"],
       "bayes_delta_beats_both_simple":err["Bayesian Δ"]<min(err["Без изменений"],err["Среднее"]),
       "huber_delta_beats_both_simple":err["Huber Δ"]<min(err["Без изменений"],err["Среднее"]),
       "bayes_delta_95pct_coverage":float(np.mean((y>=predictions["Bayesian Δ"]-1.96*delta_std)&
                                                  (y<=predictions["Bayesian Δ"]+1.96*delta_std)))}
    for name,key in MAE_KEYS.items():
        m[key]=err[name]
        m[key.replace('_mae','_rmse')]=rmse[name]
    tot=float(np.sum((y-y.mean())**2))
    for nm,k in [("Bayesian Δ","bayes_delta"),("Huber Δ","huber_delta"),("Ridge Δ","ridge_delta")]:
        m[k+"_cv_r2"]=float(1-np.sum((y-predictions[nm])**2)/tot) if tot>1e-12 else float('nan')
    return m,predictions,delta_std


def analyze(data):
    metrics=[];pred=[];paired_rows=[]
    for title,group,t0,t1 in INTERVALS:
        p=paired(data,group,t0,t1)
        n=len(p)
        expected={('PBS',0,16):9,('PBS',16,24):6,('LPS',16,24):11,('PBS',0,24):6}[(group,t0,t1)]
        assert n==expected,(title,n,expected)
        q=p.copy();q.insert(0,'transition',title);paired_rows.append(q)
        for domain in DOMAINS:
            x=p[f'{domain}_start'].to_numpy(float)
            y=p[f'{domain}_end'].to_numpy(float)
            metric,pr,ds=evaluate(x,y)
            metrics.append({'transition':title,'group':group,'week_from':t0,'week_to':t1,'domain':domain,**metric})
            for j in range(n):
                row={'transition':title,'domain':domain,'mouse_id':p.mouse_id.iat[j],
                     'status_start':p.status_start.iat[j],'status_end':p.status_end.iat[j],
                     'current':x[j],'actual_future':y[j],
                     'bayes_delta_predictive_std':ds[j]}
                for method,values in pr.items():
                    row[{'Bayesian Δ':'bayes_delta','Huber Δ':'huber_delta','Ridge Δ':'ridge_delta',
                         'Bayesian':'bayes','Huber':'huber','Ridge':'ridge',
                         'Без изменений':'unchanged','Среднее':'train_mean'}[method]+'_pred']=values[j]
                pred.append(row)
    metrics=pd.DataFrame(metrics)
    preds=pd.DataFrame(pred)
    assert len(metrics)==12 and len(preds)==96
    old=pd.read_csv(HERE/'input'/'huber_baseline.csv')
    delta_old=pd.read_csv(HERE/'input'/'delta_ridge_baseline.csv')
    common=['transition','group','week_from','week_to','domain']
    oldjoin=metrics.merge(old,on=common,suffixes=('','_historical'),validate='one_to_one')
    djoin=metrics.merge(delta_old,on=common,suffixes=('','_historical'),validate='one_to_one')
    assert len(oldjoin)==12 and len(djoin)==12
    for field in ['huber_mae','bayes_mae','ridge_mae','unchanged_mae','mean_mae']:
        error=float((oldjoin[field]-oldjoin[field+'_historical']).abs().max())
        assert error<1e-7,(field,error)
    assert float((djoin['ridge_delta_mae']-djoin['delta_ridge_mae']).abs().max())<1e-7
    metrics.to_csv(OUT/'model_metrics.csv',index=False)
    preds.to_csv(OUT/'leave_one_mouse_out_predictions.csv',index=False)
    pd.concat(paired_rows,ignore_index=True).to_csv(OUT/'paired_mouse_scores.csv',index=False)
    return metrics,preds

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
    fig,axes=plt.subplots(1,4,figsize=(17.5,5.0),dpi=160,sharey=True)
    nmethods=len(MODEL_NAMES)
    width=.098
    xi=np.arange(3)
    for i,((transition,_,_,_),ax) in enumerate(zip(INTERVALS,axes)):
        sub=m[m.transition==transition].set_index('domain').loc[list(DOMAINS)]
        for j,name in enumerate(MODEL_NAMES):
            shift=(j-(nmethods-1)/2)*width
            yy=sub[MAE_KEYS[name]]
            ax.bar(xi+shift,yy,color=COLORS[name],width=width*.95,zorder=2)
        for j,domain in enumerate(DOMAINS):
            row=sub.loc[domain]
            scores=[row[MAE_KEYS[name]] for name in MODEL_NAMES]
            best=int(np.argmin(scores))
            ax.text(xi[j]+(best-(nmethods-1)/2)*width,scores[best]+.04,'▼',fontsize=8,
                    color=INK,ha='center')
        ax.set_xticks(xi,list(DOMAINS))
        ax.set_title(f'{transition}\nn={int(sub.n.iloc[0])} мышей',fontsize=10.5,fontweight='bold',color=INK)
        ax.set_ylim(0,max(2.4,float(m[list(MAE_KEYS.values())].max().max())*1.19))
        ax.set_ylabel('MAE (меньше — лучше)' if i==0 else '')
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='y',color='#DEE6EB',zorder=0,alpha=.8)
    legend=[Rectangle((0,0),1,1,color=COLORS[name]) for name in MODEL_NAMES]
    fig.legend(legend,list(MODEL_NAMES),loc='upper center',bbox_to_anchor=(.51,.914),
               ncol=8,frameon=False,fontsize=8)
    fig.suptitle('Прогноз ΔD и прямой прогноз  |  8 методов, 12 задач',
                 fontweight='bold',fontsize=13,color=INK,y=.99)
    fig.subplots_adjust(left=.06,right=.99,top=.73,bottom=.16,wspace=.23)
    file=OUT/'eight_method_mae.png';fig.savefig(file,dpi=150);plt.close(fig);return file


def winner_chart(m):
    fig,ax=plt.subplots(figsize=(15.5,3.85),dpi=150)
    ax.axis('off');ax.set_xlim(-.9,4.06);ax.set_ylim(-.45,3.05)
    background={"Bayesian Δ":"#C7E4F1","Huber Δ":"#D6EAE1","Ridge Δ":"#E4DCF0",
                "Bayesian":"#DFEDF3","Huber":"#E4F1EB","Ridge":"#E9E2F0",
                "Без изменений":"#F1E0D4","Среднее":"#E9EDF0"}
    for j,(title,_,_,_) in enumerate(INTERVALS):
        ax.text(j+.5,2.82,title,ha='center',fontsize=11,fontweight='bold',color=INK)
    for i,domain in enumerate(DOMAINS):
        y=2.20-i*.91
        ax.text(-.06,y,{'D1':'D1 — OFT','D2':'D2 — Learning','D3':'D3 — NOR1/2'}[domain],
                ha='right',va='center',color=INK,fontweight='bold')
        for j,(title,_,_,_) in enumerate(INTERVALS):
            r=m[(m.transition==title)&(m.domain==domain)].iloc[0]
            x=j+.03
            ax.add_patch(Rectangle((x,y-.37),.94,.76,fc=background[r.best_method],ec='white',lw=2))
            ax.text(x+.47,y+.12,r.best_method,ha='center',fontsize=9.0,fontweight='bold',color=INK)
            ax.text(x+.47,y-.19,f'MAE = {r.best_mae:.3f}',ha='center',fontsize=9,color=SUB)
    fig.tight_layout(pad=.4)
    file=OUT/'winners.png';fig.savefig(file,dpi=150);plt.close(fig);return file


def scatter_chart(m,p):
    fig,axes=plt.subplots(4,3,figsize=(17.6,9.45),dpi=150)
    for i,(title,_,_,_) in enumerate(INTERVALS):
        for j,domain in enumerate(DOMAINS):
            ax=axes[i,j]
            q=p[(p.transition==title)&(p.domain==domain)]
            r=m[(m.transition==title)&(m.domain==domain)].iloc[0]
            actual=q.actual_future.to_numpy(float)
            bay=q.bayes_delta_pred.to_numpy(float)
            hub=q.huber_delta_pred.to_numpy(float)
            lo=min(actual.min(),bay.min(),hub.min())
            hi=max(actual.max(),bay.max(),hub.max())
            ext=(hi-lo)*.1+.10
            ax.plot([lo-ext,hi+ext],[lo-ext,hi+ext],'--',lw=1,color='#A1ABB3')
            ax.scatter(actual,bay,c=COLORS['Bayesian Δ'],s=32,alpha=.72,label='Bayesian Δ',edgecolor='white',lw=.3)
            ax.scatter(actual,hub,c=COLORS['Huber Δ'],s=34,alpha=.78,label='Huber Δ',edgecolor='white',lw=.3,marker='s')
            ax.set_xlim(lo-ext,hi+ext);ax.set_ylim(lo-ext,hi+ext)
            ax.set_title(f'{domain}: Bayes Δ {r.bayes_delta_mae:.2f}  |  Huber Δ {r.huber_delta_mae:.2f}',
                         fontsize=9.5,fontweight='bold',color=INK)
            ax.grid(alpha=.15)
            ax.spines[['top','right']].set_visible(False)
            ax.tick_params(labelsize=8)
            if j==0:ax.set_ylabel(f'{title}\nПРОГНОЗ',color=SUB,fontsize=9)
            if i==3:ax.set_xlabel('Фактический будущий балл',color=SUB,fontsize=8.6)
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper right',bbox_to_anchor=(.94,.987),ncol=2,frameon=False,fontsize=10)
    fig.suptitle('Bayesian Δ и Huber Δ: факт против прогноза  |  каждая точка — мышь',
                 fontsize=13.2,fontweight='bold',color=INK,y=.997)
    fig.subplots_adjust(left=.095,right=.985,top=.927,bottom=.08,hspace=.60,wspace=.25)
    file=OUT/'delta_models_actual_vs_prediction.png'
    fig.savefig(file,dpi=150);plt.close(fig);return file


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
    trajectories_png={dom:trajectories(data,dom) for dom in DOMAINS}
    means=group_means(data);bars=error_chart(m);winners=winner_chart(m);scatter=scatter_chart(m,p)
    doc=Document()
    sec=doc.sections[0]
    sec.page_width=Inches(11.69);sec.page_height=Inches(8.27)
    sec.left_margin=Inches(.44);sec.right_margin=Inches(.44)
    sec.top_margin=Inches(.38);sec.bottom_margin=Inches(.40)
    sec.header_distance=Inches(.13);sec.footer_distance=Inches(.14)
    styles=doc.styles;styles['Normal'].font.name='Calibri';styles['Normal'].font.size=Pt(9)
    foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    run=foot.add_run('24.10.2026 · eNRI / 3 домена · ΔD')
    run.font.size=Pt(8);run.font.color.rgb=rgb('#7B8790')

    heading(doc,'Динамика трёх доменов · PBS и LPS')
    size=data[data.group.isin(['PBS','LPS'])].mouse_id.nunique()
    observations=len(data[data.group.isin(['PBS','LPS'])])
    paragraph(doc,f'{size} мышей · {observations} живых состояний · недели 0 / 16 / 24. Сплошная цветная линия — мышь; тёмно-серый пунктир — соединение с её номером. Номер у последней доступной точки.',size=9,color=SUB,space=6)
    paragraph(doc,'D1 · двигательная активность — OFT / rear',bold=True,size=11,color=INK)
    picture(doc,trajectories_png['D1'],width=10.40)
    paragraph(doc,'D2 · обучение и выносливость — Learning / Endurance',bold=True,size=11,color=INK)
    picture(doc,trajectories_png['D2'],width=10.40)
    paragraph(doc,'Вывод: индивидуальные траектории различаются; 0 — среднее исходное положение, а не отсутствие функции.',size=8.5,color=SUB)
    doc.add_page_break()
    heading(doc,'Динамика доменов · продолжение')
    paragraph(doc,'D3 · исследовательское поведение — NOR1 + NOR2',bold=True,size=11,color=INK)
    picture(doc,trajectories_png['D3'],width=10.4)
    paragraph(doc,'Средние баллы D1–D3 · PBS / LPS',bold=True,size=11,color=INK)
    picture(doc,means,width=10.35)
    paragraph(doc,'D3 рассчитан по отдельной трёхфакторной Spearman-EFA. На графиках показана наблюдаемая динамика; причинный эффект не оценивается.',size=8.5,color=SUB)
    doc.add_page_break()
    heading(doc,'Точность прогноза · ΔD против прогноза будущего балла')
    paragraph(doc,'12 задач: 3 домена × 4 интервала. Leave-one-mouse-out. MAE — средняя абсолютная ошибка, меньше — лучше. ▼ — лучший метод. Regularization и параметры неизменны.',size=8.8,color=SUB)
    picture(doc,bars,width=10.5)
    paragraph(doc,'Кто выиграл по каждому домену?',size=11,bold=True,color=INK)
    picture(doc,winners,width=10.5)
    b=int(m.bayes_delta_better_direct.sum());h=int(m.huber_delta_better_direct.sum());
    top=int(m.any_new_delta_best.sum())
    paragraph(doc,f'Итог: Bayesian Δ точнее прямой Bayesian в {b}/12 задач; Huber Δ точнее прямой Huber в {h}/12. Новые Δ-методы — лучшие из восьми в {top}/12.',size=9,bold=True,color=INK)
    doc.add_page_break()
    heading(doc,'Факт против прогноза · 12 независимых проверок')
    paragraph(doc,'Ряды: PBS 0→16 (n=9), PBS 16→24 (n=6), LPS 16→24 (n=11), PBS 0→24 (n=6). Столбцы: D1–D3; кружки — Bayesian Δ, квадраты — Huber Δ; пунктир — идеальный прогноз.',size=8.6,color=SUB)
    picture(doc,scatter,width=10.6)
    paragraph(doc,'Вывод: при n=6–11 разница в MAE нестабильна. Выбирать модель по отдельным выигрышам на LOOCV нельзя.',size=8.4,bold=True,color=INK)
    paragraph(doc,'Источник: GitHub / LisaGaydamaka/coworking / mouse_neuroplasticity_enri. EFA-баллы и исходная импутация рассчитаны до CV. LOOCV валидирует только регрессию на фиксированных баллах. Только мыши с обеими живыми точками.',size=7.7,color=SUB)
    out=OUT/'Otchet_Bayesian_Huber_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx'
    doc.save(out)
    return out


def main():
    data=pd.read_csv(SOURCE,dtype={'mouse_id':str})
    assert len(data)==133
    assert data.week.value_counts().to_dict()=={0:54,16:41,24:38}
    m,p=analyze(data)
    out=report(data,m,p)
    n={"Bayesian Δ beats direct":int(m.bayes_delta_better_direct.sum()),
       "Huber Δ beats direct":int(m.huber_delta_better_direct.sum()),
       "Bayesian Δ beats both simple":int(m.bayes_delta_beats_both_simple.sum()),
       "Huber Δ beats both simple":int(m.huber_delta_beats_both_simple.sum()),
       "Bayesian Δ best of 8":int(m.bayes_delta_best_all_eight.sum()),
       "Huber Δ best of 8":int(m.huber_delta_best_all_eight.sum()),
       "Either new method best of 8":int(m.any_new_delta_best.sum()),
       "prior models verified":True}
    overview={'n_tasks':12,'per_interval_pairs':{'PBS 0→16':9,'PBS 16→24':6,'LPS 16→24':11,'PBS 0→24':6},'outcomes':n,
              'caveats':['very small survivor-only samples','EFA fitted pre-CV, source imputation could use future visits','no external validation']}
    (OUT/'SUMMARY.json').write_text(json.dumps(overview,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# Bayesian Ridge and Huber on ΔD versus previous direct forecasts','',
       'Baseline: 3 domains (Spearman rank EFA / 26 features), PBS and LPS only; 12 tasks on paired surviving mice.','',
       'Targets: ΔD = D_future - D_now. Final prediction D_future_hat = D_now + ΔD_hat. Same start-domain predictor, same parameters and same leave-one-mouse-out splits as direct models. No model hyperparameter tuning on held-out mice.','',
       '| Interval | Domain | n | Bayesian Δ | Huber Δ | Ridge Δ | Bayesian | Huber | Ridge | Unchanged | Mean | Best |',
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in m.itertuples():
        lines.append(f'| {r.transition} | {r.domain} | {r.n} | {r.bayes_delta_mae:.3f} | {r.huber_delta_mae:.3f} | {r.ridge_delta_mae:.3f} | {r.bayes_mae:.3f} | {r.huber_mae:.3f} | {r.ridge_mae:.3f} | {r.unchanged_mae:.3f} | {r.mean_mae:.3f} | {r.best_method} |')
    lines+=['',f'Comparisons: {json.dumps(n,ensure_ascii=False)}','',
           'Important: cross-validation only of regressions given fixed EFA scores. Upstream imputation can leak future data. Survivor selection. n=6–11. 12 tasks × many methods: individual wins can be accidental. No external dataset.','',
           f'Word report: results/{out.name}. CSV tables and all plots are in results/.']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(overview,ensure_ascii=False))
    print(m[['transition','domain','n','bayes_delta_mae','huber_delta_mae','ridge_delta_mae','bayes_mae','huber_mae','ridge_mae','unchanged_mae','mean_mae','best_method']].to_string(index=False))
    print('REPORT:',out, out.stat().st_size)

if __name__=='__main__':main()
