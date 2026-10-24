#!/usr/bin/env python3
"""Prospective-split forecasting comparison, baseline rank EFA k=3, PBS/LPS.

Direct Ridge: future_score ~ initial_score.
Change Ridge: (future_score - initial_score) ~ initial_score,
    then future_score_prediction = initial_score + predicted_change.
Identical Ridge(alpha=1), training-fold x standardization, and LOOCV folds.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors
from matplotlib.patches import Rectangle
from sklearn.linear_model import Ridge
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"input"/"clean133_k3_rank_frozen_scores.csv"
OUT=HERE/"results";OUT.mkdir(parents=True,exist_ok=True)
DATE="24.10.2026"
DOMAINS=("D1","D2","D3")
INTERVALS=(("PBS 0→16","PBS",0,16),("PBS 16→24","PBS",16,24),("LPS 16→24","LPS",16,24),("PBS 0→24","PBS",0,24))
ALPHA=1.0
COLORS={"ΔD Ridge":"#367E9C","Ridge":"#8BB3C8","Без изменений":"#D19D76","Среднее":"#939FA9"}
GROUP_COLORS={"PBS":"#5282A2","LPS":"#BC7C59"}
INK="#274658";SUB="#526977"


def paired(df,group,start,end):
    z=df[df.group==group]
    a=z[z.week==start][["mouse_id","status"]+[f"{d}_score" for d in DOMAINS]].copy()
    b=z[z.week==end][["mouse_id","status"]+[f"{d}_score" for d in DOMAINS]].copy()
    assert a.mouse_id.is_unique and b.mouse_id.is_unique
    a=a.rename(columns={"status":"status_start",**{f"{d}_score":f"{d}_start" for d in DOMAINS}})
    b=b.rename(columns={"status":"status_end",**{f"{d}_score":f"{d}_end" for d in DOMAINS}})
    out=a.merge(b,on="mouse_id",validate="one_to_one").sort_values("mouse_id").reset_index(drop=True)
    assert np.isfinite(out[[f"{k}_{e}" for k in DOMAINS for e in ("start","end")]].to_numpy(float)).all()
    return out


def ridge_prediction(x_train,y_train,x_test):
    """Only training mice define predictor scale, target is not standardized."""
    mu=float(x_train.mean());sd=float(x_train.std(ddof=0))
    if sd<1e-12:return float(y_train.mean())
    clf=Ridge(alpha=ALPHA,fit_intercept=True)
    clf.fit(((x_train-mu)/sd).reshape(-1,1),y_train)
    return float(clf.predict(np.array([[(x_test-mu)/sd]]))[0])


def validate(x,y):
    n=len(x)
    direct=np.zeros(n);delta=np.zeros(n);avg=np.zeros(n)
    for j in range(n):
        keep=np.arange(n)!=j
        direct[j]=ridge_prediction(x[keep],y[keep],x[j])
        predicted_change=ridge_prediction(x[keep],y[keep]-x[keep],x[j])
        delta[j]=x[j]+predicted_change
        avg[j]=float(y[keep].mean())
    predictions={"ΔD Ridge":delta,"Ridge":direct,"Без изменений":x.copy(),"Среднее":avg}
    maes={k:float(np.mean(abs(y-p))) for k,p in predictions.items()}
    rmses={k:float(np.sqrt(np.mean((y-p)**2))) for k,p in predictions.items()}
    v=float(np.sum((y-y.mean())**2))
    r2={k:float(1-np.sum((y-p)**2)/v) if v>1e-10 else np.nan for k,p in predictions.items()}
    win=min(maes,key=maes.get)
    summary={"n":n,"delta_ridge_mae":maes["ΔD Ridge"],"ridge_mae":maes["Ridge"],
       "unchanged_mae":maes["Без изменений"],"mean_mae":maes["Среднее"],
       "delta_ridge_rmse":rmses["ΔD Ridge"],"ridge_rmse":rmses["Ridge"],
       "unchanged_rmse":rmses["Без изменений"],"mean_rmse":rmses["Среднее"],
       "delta_ridge_cv_r2":r2["ΔD Ridge"],"ridge_cv_r2":r2["Ridge"],
       "best_method":win,"best_mae":maes[win],
       "delta_ridge_beats_ridge":bool(maes["ΔD Ridge"]<maes["Ridge"]),
       "delta_ridge_beats_both_baselines":bool(maes["ΔD Ridge"]<min(maes["Без изменений"],maes["Среднее"])),
       "delta_ridge_best_of_four":bool(win=="ΔD Ridge"),
       "mae_gain_ridge_minus_delta":maes["Ridge"]-maes["ΔD Ridge"],
       "mean_observed_change":float(np.mean(y-x))}
    return summary,predictions


def analyze(df):
    ms=[];preds=[];pairs=[]
    for title,group,w0,w1 in INTERVALS:
        p=paired(df,group,w0,w1)
        expected={('PBS',0,16):9,('PBS',16,24):6,('LPS',16,24):11,('PBS',0,24):6}[(group,w0,w1)]
        assert len(p)==expected,(title,len(p))
        pp=p.copy();pp.insert(0,"transition",title);pairs.append(pp)
        for domain in DOMAINS:
            x=p[f"{domain}_start"].to_numpy(float);y=p[f"{domain}_end"].to_numpy(float)
            summary,forecasts=validate(x,y)
            ms.append(dict(transition=title,group=group,week_from=w0,week_to=w1,domain=domain,**summary))
            for i in range(len(p)):
                preds.append({"transition":title,"domain":domain,"mouse_id":p.mouse_id.iat[i],
                              "status_start":p.status_start.iat[i],"status_end":p.status_end.iat[i],
                              "current":float(x[i]),"observed_future":float(y[i]),
                              "observed_change":float(y[i]-x[i]),
                              "ridge_future_prediction":float(forecasts["Ridge"][i]),
                              "delta_ridge_change_prediction":float(forecasts["ΔD Ridge"][i]-x[i]),
                              "delta_ridge_future_prediction":float(forecasts["ΔD Ridge"][i]),
                              "unchanged_prediction":float(x[i]),"mean_prediction":float(forecasts["Среднее"][i]),
                              "ridge_abs_error":float(abs(y[i]-forecasts["Ridge"][i])),
                              "delta_ridge_abs_error":float(abs(y[i]-forecasts["ΔD Ridge"][i]))})
    m=pd.DataFrame(ms);p=pd.DataFrame(preds)
    assert len(m)==12 and len(p)==96
    # Verify original direct Ridge matches previously published 12 MAE values.
    historic={("PBS 0→16","D1"):1.200022,("PBS 0→16","D2"):.881626,("PBS 0→16","D3"):1.009778,
      ("PBS 16→24","D1"):.270623,("PBS 16→24","D2"):.956556,("PBS 16→24","D3"):1.610203,
      ("LPS 16→24","D1"):.724493,("LPS 16→24","D2"):.322451,("LPS 16→24","D3"):1.151570,
      ("PBS 0→24","D1"):.290680,("PBS 0→24","D2"):.621357,("PBS 0→24","D3"):.770379}
    assert all(abs(row.ridge_mae-historic[(row.transition,row.domain)])<.000003 for row in m.itertuples()),"Historical ridge MAE changed!"
    # Independent identity check: delta Ridge equivalent to shrinking direct slope toward 1.
    for title,g,a,b in INTERVALS:
        sub=paired(df,g,a,b)
        for domain in DOMAINS:
            x=sub[f"{domain}_start"].to_numpy(float);y=sub[f"{domain}_end"].to_numpy(float)
            tr=np.arange(len(x))!=0
            mu=x[tr].mean();scale=x[tr].std(ddof=0)
            if scale<1e-12:continue
            fit=Ridge(alpha=ALPHA).fit(((x[tr]-mu)/scale).reshape(-1,1),y[tr]-x[tr])
            alt=x[0]+fit.predict([[(x[0]-mu)/scale]])[0]
            v=p[(p.transition==title)&(p.domain==domain)&(p.mouse_id==sub.mouse_id.iat[0])].iloc[0]
            assert abs(alt-v.delta_ridge_future_prediction)<1e-10
    m.to_csv(OUT/"model_metrics.csv",index=False)
    p.to_csv(OUT/"leave_one_mouse_out_predictions.csv",index=False)
    pd.concat(pairs,ignore_index=True).to_csv(OUT/"paired_mouse_scores.csv",index=False)
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
    fig,axes=plt.subplots(1,4,figsize=(17.5,4.75),dpi=150,sharey=True)
    keys=[("delta_ridge_mae","ΔD Ridge"),("ridge_mae","Ridge"),("unchanged_mae","Без изменений"),("mean_mae","Среднее")]
    loc=np.arange(3);w=.205
    for j,((title,_,_,_),ax) in enumerate(zip(INTERVALS,axes)):
        v=m[m.transition==title].set_index("domain").loc[list(DOMAINS)]
        for k,(col,name) in enumerate(keys):
            ax.bar(loc+(k-1.5)*w,v[col],width=w*.96,color=COLORS[name],zorder=2)
        for i,domain in enumerate(DOMAINS):
            nums=[v.loc[domain,col] for col,_ in keys]
            winner=int(np.argmin(nums))
            ax.text(loc[i]+(winner-1.5)*w,nums[winner]+.045,'▼',fontsize=9,ha='center',color=INK)
        ax.set_title(f'{title}\nn={int(v.n.iloc[0])} мышей',fontweight='bold',fontsize=10.4,color=INK)
        ax.set_xticks(loc,list(DOMAINS));ax.set_ylim(0,max(2.5,m[[k for k,_ in keys]].max().max()*1.13))
        if j==0:ax.set_ylabel('MAE (меньше — лучше)')
        ax.spines[['right','top']].set_visible(False);ax.grid(axis='y',color='#DEE6EB',zorder=0)
    fig.legend([Rectangle((0,0),1,1,color=COLORS[n]) for _,n in keys],[n for _,n in keys],
               loc='upper right',bbox_to_anchor=(.98,.99),ncol=4,frameon=False,fontsize=9)
    fig.suptitle('Ridge для ΔD и будущего балла  |  12 задач',fontweight='bold',fontsize=13,color=INK,y=.985)
    fig.subplots_adjust(left=.06,right=.99,top=.73,bottom=.16,wspace=.23)
    f=OUT/'four_method_mae.png';fig.savefig(f,dpi=150);plt.close(fig);return f


def winners(m):
    fig,ax=plt.subplots(figsize=(15.5,3.85),dpi=150)
    ax.axis('off');ax.set_xlim(-.9,4.06);ax.set_ylim(-.45,3.05)
    bg={'ΔD Ridge':'#D9EBF4','Ridge':'#E7F0F5','Без изменений':'#F1E0D4','Среднее':'#E9EDF0'}
    for j,(title,_,_,_) in enumerate(INTERVALS):ax.text(j+.5,2.82,title,ha='center',fontsize=11,fontweight='bold',color=INK)
    for i,domain in enumerate(DOMAINS):
        y=2.20-i*.91
        ax.text(-.06,y,{'D1':'D1 — OFT','D2':'D2 — Learning','D3':'D3 — NOR1/2'}[domain],ha='right',va='center',color=INK,fontweight='bold')
        for j,(title,_,_,_) in enumerate(INTERVALS):
            r=m[(m.transition==title)&(m.domain==domain)].iloc[0]
            x=j+.03
            ax.add_patch(Rectangle((x,y-.37),.94,.76,fc=bg[r.best_method],ec='white',lw=2))
            ax.text(x+.47,y+.12,r.best_method,fontsize=9.4,fontweight='bold',ha='center',color=INK)
            ax.text(x+.47,y-.19,f'MAE = {r.best_mae:.3f}',fontsize=9,ha='center',color=SUB)
    fig.tight_layout(pad=.4)
    f=OUT/'winners.png';fig.savefig(f,dpi=150);plt.close(fig);return f


def scatter(m,p):
    fig,axes=plt.subplots(4,3,figsize=(17.6,9.30),dpi=150)
    for i,(title,_,_,_) in enumerate(INTERVALS):
        for j,domain in enumerate(DOMAINS):
            ax=axes[i,j]
            r=m[(m.transition==title)&(m.domain==domain)].iloc[0]
            q=p[(p.transition==title)&(p.domain==domain)]
            x=q.observed_future.to_numpy(float);yd=q.delta_ridge_future_prediction.to_numpy(float)
            yr=q.ridge_future_prediction.to_numpy(float)
            lo=min(x.min(),yd.min(),yr.min());hi=max(x.max(),yd.max(),yr.max());h=(hi-lo)*.1+.14
            ax.plot([lo-h,hi+h],[lo-h,hi+h],'--',lw=.9,color='#929FA8')
            ax.scatter(x,yr,c=COLORS['Ridge'],edgecolors='white',lw=.4,s=36,marker='o',label='Ridge')
            ax.scatter(x,yd,c=COLORS['ΔD Ridge'],edgecolors='white',lw=.4,s=42,marker='D',label='ΔD Ridge')
            ax.set_xlim(lo-h,hi+h);ax.set_ylim(lo-h,hi+h)
            ax.set_title(f'{domain}: Δ {r.delta_ridge_mae:.3f} / прямой {r.ridge_mae:.3f}',fontsize=10.2,fontweight='bold',color=INK)
            ax.grid(alpha=.14);ax.spines[['right','top']].set_visible(False)
            ax.tick_params(labelsize=8)
            if j==0:ax.set_ylabel(f'{title}\nПРОГНОЗ',fontsize=9,color=SUB)
            if i==3:ax.set_xlabel('Фактический будущий балл',fontsize=8.8,color=SUB)
    handles=[Rectangle((0,0),1,1,color=COLORS['ΔD Ridge']),Rectangle((0,0),1,1,color=COLORS['Ridge'])]
    fig.legend(handles,['ΔD Ridge (ромб)','Ridge (круг)'],loc='upper right',bbox_to_anchor=(.98,.998),ncol=2,frameon=False,fontsize=10)
    fig.suptitle('Факт и прогноз: две Ridge-модели  |  каждая точка — мышь',fontweight='bold',color=INK,fontsize=14,y=.994)
    fig.subplots_adjust(left=.09,right=.99,top=.925,bottom=.08,hspace=.52,wspace=.22)
    f=OUT/'two_ridge_actual_vs_prediction.png';fig.savefig(f,dpi=150);plt.close(fig);return f


def rgb(color):
    r=mcolors.to_rgb(color);return RGBColor(*[int(v*255) for v in r])


def paragraph(doc,text,bold=False,size=9,color=None,after=3):
    p=doc.add_paragraph()
    p.paragraph_format.space_after=Pt(after)
    p.paragraph_format.space_before=Pt(0)
    p.paragraph_format.line_spacing=1.06
    r=p.add_run(text);r.bold=bold;r.font.name='Calibri';r.font.size=Pt(size)
    if color:r.font.color.rgb=rgb(color)
    return p


def heading(doc,text):
    p=paragraph(doc,text,True,17,INK,6)
    ppr=p._p.get_or_add_pPr();border=OxmlElement('w:pBdr');line=OxmlElement('w:bottom')
    for key,val in [('val','single'),('sz','9'),('space','3'),('color','5484A2')]:line.set(qn('w:'+key),val)
    border.append(line);ppr.append(border)
    return p


def picture(doc,file,width=10.42):
    p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(0)
    p.add_run().add_picture(str(file),width=Inches(width));return p


def make_report(df,m,p):
    names={d:trajectories(df,d) for d in DOMAINS}
    avg=group_means(df);bars=error_chart(m);win=winners(m);spots=scatter(m,p)
    doc=Document();section=doc.sections[0]
    section.page_width=Inches(11.69);section.page_height=Inches(8.27)
    section.top_margin=Inches(.38);section.bottom_margin=Inches(.40)
    section.left_margin=Inches(.44);section.right_margin=Inches(.44)
    section.header_distance=Inches(.13);section.footer_distance=Inches(.14)
    doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=Pt(9)
    ft=section.footer.paragraphs[0];ft.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    rr=ft.add_run(f'{DATE} · eNRI / 3 домена · Ridge для ΔD');rr.font.size=Pt(8);rr.font.color.rgb=rgb('#7B8790')

    heading(doc,'Динамика трёх доменов · PBS и LPS')
    n=df[df.group.isin(['PBS','LPS'])].mouse_id.nunique()
    states=len(df[df.group.isin(['PBS','LPS'])])
    paragraph(doc,f'{n} мышей · {states} живых состояний · недели 0 / 16 / 24. Сплошная линия — мышь; тёмный пунктир — номер у последней доступной точки.',size=9,color=SUB,after=5)
    paragraph(doc,'D1 · двигательная активность — OFT / rear',True,11,INK)
    picture(doc,names['D1'])
    paragraph(doc,'D2 · обучение и выносливость — Learning / Endurance',True,11,INK)
    picture(doc,names['D2'])
    paragraph(doc,'Вывод: траектории мышей различаются; 0 — центр шкалы week 0, не граница нормы.',size=8.6,color=SUB)
    doc.add_page_break()

    heading(doc,'Динамика доменов · продолжение')
    paragraph(doc,'D3 · исследовательское поведение — NOR1 + NOR2',True,11,INK)
    picture(doc,names['D3'])
    paragraph(doc,'Средние баллы D1–D3 · PBS / LPS',True,11,INK)
    picture(doc,avg,width=10.35)
    paragraph(doc,'Группы run и MCC исключены из прогнозов. Признаки — ранговые; D3 получен в отдельной трёхфакторной EFA.',size=8.6,color=SUB)
    doc.add_page_break()

    heading(doc,'Точность прогноза · Ridge для ΔD и будущего балла')
    paragraph(doc,'12 задач · 3 домена × 4 интервала. Leave-one-mouse-out: каждая мышь проверяется вне обучения. Оба варианта Ridge используют α=1. MAE — средняя абсолютная ошибка.',size=8.9,color=SUB)
    picture(doc,bars,width=10.5)
    paragraph(doc,'Кто выиграл по каждому домену?',True,11,INK)
    picture(doc,win,width=10.5)
    wins=int(m.delta_ridge_best_of_four.sum());beats=int(m.delta_ridge_beats_ridge.sum());both=int(m.delta_ridge_beats_both_baselines.sum())
    paragraph(doc,f'Итог: Ridge для ΔD точнее прежней Ridge в {beats}/12 задач; лучше обоих простых методов в {both}/12; лучший из четырёх в {wins}/12.',True,9,INK)
    doc.add_page_break()

    heading(doc,'Факт против прогноза · 12 независимых проверок')
    paragraph(doc,'Ряды: PBS 0→16 (n=9), PBS 16→24 (n=6), LPS 16→24 (n=11), PBS 0→24 (n=6). Столбцы: D1–D3. Диагональ — идеальный прогноз. Ромб — ΔD Ridge, круг — прежняя Ridge.',size=8.9,color=SUB)
    picture(doc,spots,width=10.54)
    paragraph(doc,'Вывод: сравнение проведено на тех же мышах, но при n=6–11 преимущество отдельных методов может быть случайным.',size=8.5,color=INK,bold=True)
    paragraph(doc,'Ограничение: EFA и первоначальная импутация рассчитаны до CV; проверена только регрессия на фиксированных доменных баллах. Прогнозы условны на наличии двух измерений у выжившей мыши.',size=7.8,color=SUB)
    file=OUT/'Otchet_Ridge_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx';doc.save(file);return file


def main():
    df=pd.read_csv(SOURCE,dtype={'mouse_id':str})
    assert len(df)==133 and df.week.value_counts().to_dict()=={0:54,16:41,24:38}
    m,p=analyze(df)
    report=make_report(df,m,p)
    summary={'model':'Ridge(alpha=1) direct vs same Ridge for delta target',
             'n_tasks':len(m),'transitions':[{'transition':k,'n':int(m[m.transition==k].n.iloc[0])} for k,_,_,_ in INTERVALS],
             'delta_beats_ridge':int(m.delta_ridge_beats_ridge.sum()),
             'delta_beats_both_baselines':int(m.delta_ridge_beats_both_baselines.sum()),
             'delta_best_of_four':int(m.delta_ridge_best_of_four.sum()),
             'historic_ridge_all12_matched':True,'notes':'Scoring EFA previously fit globally; not fully end-to-end cross-validation.'}
    (OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Ridge direct versus Ridge for target ΔD','',
       'Ridge direct: yhat = a + bx. Ridge for change: delta_hat = a + bx, yhat=x+delta_hat. Both alpha=1 and input standardized only on training mice.','',
       'All 12 matched PBS/LPS tasks; baseline-frozen separate rank Spearman 3-factor EFA on 26 features. Same folds. No synthetic data.','',
       '| Transition | Domain | n | ΔD Ridge MAE | Direct Ridge MAE | Unchanged MAE | Mean MAE | Best |',
       '|---|---|---:|---:|---:|---:|---:|---|']
    for r in m.itertuples():
       lines.append(f'| {r.transition} | {r.domain} | {r.n} | {r.delta_ridge_mae:.3f} | {r.ridge_mae:.3f} | {r.unchanged_mae:.3f} | {r.mean_mae:.3f} | {r.best_method} |')
    lines.extend(['',f'ΔD beats direct Ridge: {summary["delta_beats_ridge"]}/12; best of all four: {summary["delta_best_of_four"]}/12.','',
       '**Limitations**: preprocessing and EFA learned before CV; no test independent of EFA. Paired survivors only, n=6–11, no intervention claims.','',
       'Word report: results/Otchet_Ridge_Delta_D1-D3_RANG_PBS_LPS_2026-10-24.docx. Other result CSVs and PNGs in same directory.'])
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False))
    print(m[['transition','domain','n','delta_ridge_mae','ridge_mae','unchanged_mae','mean_mae','best_method']].to_string(index=False))
    print('Saved',report,report.stat().st_size)

if __name__=='__main__':main()
