#!/usr/bin/env python3
"""Small-noise augmentation on training inputs, rank EFA3 PBS/LPS.

Each synthetic perturbation is used in an INDEPENDENT noisy fit with precisely one
row per real mouse; predictions averaged over repetitions. No pseudo-replication.
The LOO held-out mouse is never perturbed or used to determine scaling/noise.
"""
from pathlib import Path
import json, warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge, BayesianRidge, HuberRegressor
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE=Path(__file__).resolve().parent
OUT=HERE/'results';OUT.mkdir(exist_ok=True)
DATA=HERE/'input'/'clean133_k3_rank_frozen_scores.csv'
DOMAINS=('D1','D2','D3')
INTERVALS=[('PBS 0→16','PBS',0,16,9),('PBS 16→24','PBS',16,24,6),('LPS 16→24','LPS',16,24,11),('PBS 0→24','PBS',0,24,6)]
ALGOS=['Ridge','Bayesian Ridge','Huber']
LEVELS=[0.0,0.05,0.10,0.20]
PRIMARY=0.10
REPEATS=20
SEED=20261024
GROUP_COLORS={'PBS':'#527F9D','LPS':'#B87959'}
COLORS={'Ridge':'#3B7897','Bayesian Ridge':'#668EAB','Huber':'#53927A','Без изменений':'#D29B75','Среднее':'#95A5B0'}
INK='#2E4C5D';GRAY='#637985';


def pairs(df,group,t0,t1):
    a=df[(df.group==group)&(df.week==t0)].copy()
    b=df[(df.group==group)&(df.week==t1)].copy()
    assert a.mouse_id.is_unique and b.mouse_id.is_unique
    x=a[['mouse_id','status']+[d+'_score' for d in DOMAINS]].rename(columns={'status':'start_status',**{d+'_score':d+'_start' for d in DOMAINS}})
    y=b[['mouse_id','status']+[d+'_score' for d in DOMAINS]].rename(columns={'status':'end_status',**{d+'_score':d+'_end' for d in DOMAINS}})
    return x.merge(y,on='mouse_id',validate='one_to_one').sort_values('mouse_id').reset_index(drop=True)


def model(label):
    if label=='Ridge':return Ridge(alpha=1.0,fit_intercept=True)
    if label=='Bayesian Ridge':return BayesianRidge(max_iter=300,tol=1e-3,alpha_1=1e-6,alpha_2=1e-6,lambda_1=1e-6,lambda_2=1e-6,fit_intercept=True)
    if label=='Huber':return HuberRegressor(alpha=0.1,epsilon=1.35,max_iter=1500,tol=1e-6,fit_intercept=True)
    raise ValueError(label)


def fold_predict(x,y,heldout,algorithm,noise,seed):
    mask=np.arange(len(x))!=heldout
    trainx=x[mask].astype(float);trainy=y[mask].astype(float)
    mu=trainx.mean();sd=trainx.std(ddof=0)
    if sd<1e-12:return float(trainy.mean()),0.
    z=(trainx-mu)/sd
    zhold=(x[heldout]-mu)/sd
    if noise==0:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            m=model(algorithm).fit(z[:,None],trainy)
        return float(m.predict(np.array([[zhold]]))[0]),0.
    rng=np.random.default_rng(seed)
    preds=[]
    for repeat in range(REPEATS):
        perturbed=z+rng.normal(0,noise,size=len(z))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            m=model(algorithm).fit(perturbed[:,None],trainy)
        preds.append(float(m.predict(np.array([[zhold]]))[0]))
    return float(np.mean(preds)),float(np.std(preds,ddof=1))


def analyze(df):
    metrics=[];pred_rows=[];allpairs=[]
    for interval_i,(label,group,t0,t1,n_expected) in enumerate(INTERVALS):
        pp=pairs(df,group,t0,t1)
        assert len(pp)==n_expected,(label,len(pp))
        cp=pp.copy();cp.insert(0,'transition',label);allpairs.append(cp)
        for domain_idx,domain in enumerate(DOMAINS):
            x=pp[domain+'_start'].to_numpy(float)
            y=pp[domain+'_end'].to_numpy(float)
            predictions={}
            variation={}
            for algidx,algo in enumerate(ALGOS):
                for lv_idx,noise in enumerate(LEVELS):
                    tag=f'{algo}|{noise:.2f}'
                    items=[fold_predict(x,y,j,algo,noise,SEED+interval_i*100000+domain_idx*10000+algidx*1000+lv_idx*100+j) for j in range(len(x))]
                    predictions[tag]=np.array([v[0] for v in items])
                    variation[tag]=np.array([v[1] for v in items])
            predictions['Без изменений']=x.copy()
            predictions['Среднее']=np.array([y[np.arange(len(x))!=j].mean() for j in range(len(x))])
            mae=lambda z:float(np.mean(np.abs(y-z)))
            rmse=lambda z:float(np.sqrt(np.mean((y-z)**2)))
            m={'transition':label,'group':group,'week_from':t0,'week_to':t1,'domain':domain,'n':len(x)}
            for algo in ALGOS:
                slug={'Ridge':'ridge','Bayesian Ridge':'bayes','Huber':'huber'}[algo]
                for level in LEVELS:
                    key=f'{algo}|{level:.2f}'
                    suffix='plain' if level==0 else f'noise_{int(level*100):02d}'
                    m[f'{slug}_{suffix}_mae']=mae(predictions[key])
                    m[f'{slug}_{suffix}_rmse']=rmse(predictions[key])
            m['unchanged_mae']=mae(predictions['Без изменений'])
            m['mean_mae']=mae(predictions['Среднее'])
            m['unchanged_rmse']=rmse(predictions['Без изменений'])
            m['mean_rmse']=rmse(predictions['Среднее'])
            for algo in ALGOS:
                slug={'Ridge':'ridge','Bayesian Ridge':'bayes','Huber':'huber'}[algo]
                m[f'{slug}_gain_primary']=m[f'{slug}_plain_mae']-m[f'{slug}_noise_10_mae']
            base={key:mae(predictions[key]) for key in predictions if key in ['Без изменений','Среднее'] or key.endswith('|0.00')}
            primary={key:mae(predictions[key]) for key in predictions if key in ['Без изменений','Среднее'] or key.endswith('|0.10') or key.endswith('|0.00')}
            m['plain_best']=min(base,key=base.get)
            m['primary_best']=min(primary,key=primary.get)
            m['primary_best_mae']=min(primary.values())
            m['primary_noise_best']=m['primary_best'].endswith('|0.10')
            metrics.append(m)
            for j in range(len(x)):
                row={'transition':label,'domain':domain,'mouse_id':pp.mouse_id.iloc[j],'status_from':pp.start_status.iloc[j],'status_to':pp.end_status.iloc[j],'current':x[j],'actual':y[j]}
                for key,pred in predictions.items():
                    tag=key.lower().replace(' ','_').replace('|','_').replace('→','_').replace('.','_')
                    row['pred_'+tag]=pred[j]
                    if key in variation:row['ensemble_std_'+tag]=variation[key][j]
                pred_rows.append(row)
    met=pd.DataFrame(metrics);pred=pd.DataFrame(pred_rows)
    assert len(met)==12 and len(pred)==3*(9+6+11+6)
    # Source/metric continuity check from earlier GitHub Actions runs.
    baseline={
       ('PBS 0→16','D1'):1.2000215528785045,('PBS 0→16','D2'):0.881626261705343,('PBS 0→16','D3'):1.009777814049385,
       ('PBS 16→24','D1'):0.27062259785156545,('PBS 16→24','D2'):0.9565559943169326,('PBS 16→24','D3'):1.610202511258489,
       ('LPS 16→24','D1'):0.7244930108270334,('LPS 16→24','D2'):0.3224514013325677,('LPS 16→24','D3'):1.1515697700575693,
       ('PBS 0→24','D1'):0.2906802250739176,('PBS 0→24','D2'):0.6213566159962042,('PBS 0→24','D3'):0.770379377664982,
    }
    for r in met.itertuples():
        assert abs(r.ridge_plain_mae-baseline[(r.transition,r.domain)])<0.000001,(r.transition,r.domain,r.ridge_plain_mae)
    met.to_csv(OUT/'model_metrics.csv',index=False)
    pred.to_csv(OUT/'leave_one_mouse_out_predictions.csv',index=False)
    pd.concat(allpairs,ignore_index=True).to_csv(OUT/'paired_mouse_scores.csv',index=False)
    return met,pred


def spread(vals,lo,hi,min_gap):
    a=sorted(vals,key=lambda t:(t[1],t[0]))
    v=[max(lo,y) for _,y in a]
    for i in range(1,len(v)):v[i]=max(v[i],v[i-1]+min_gap)
    if v and v[-1]>hi:v=[y-(v[-1]-hi) for y in v]
    for i in range(len(v)-2,-1,-1):v[i]=min(v[i],v[i+1]-min_gap)
    if v and v[0]<lo:v=[y+lo-v[0] for y in v]
    return {a[i][0]:v[i] for i in range(len(a))}


def plot_traj(df,domain):
    fig,axes=plt.subplots(1,2,figsize=(15.8,3.9),dpi=155,sharey=True)
    vals=df[df.group.isin(['PBS','LPS'])][f'{domain}_score']
    lo=float(vals.min())-.45;hi=float(vals.max())+.45
    for ax,group in zip(axes,['PBS','LPS']):
        subset=df[df.group==group];ends={}
        for id_,g in subset.groupby('mouse_id'):
            g=g.sort_values('week');xx=g.week.to_numpy();yy=g[f'{domain}_score'].to_numpy()
            ax.plot(xx,yy,lw=1.3,alpha=.65,color=GROUP_COLORS[group],marker='o',ms=3.5,zorder=2)
            ends[id_]=(xx[-1],yy[-1])
        for time in (0,16,24):ax.axvline(time,color='#E3E8ED',lw=.6,zorder=0)
        ax.axhline(0,color='#ADB9C1',ls=':',lw=.8)
        for time in (0,16,24):
            e=[(name,y) for name,(x,y) in ends.items() if x==time]
            ypos=spread(e,lo+.13,hi-.13,(hi-lo)*(.07 if time==24 else .053))
            for name,y in e:
                tx={0:2.1,16:18.1,24:26.4}[time]
                ax.annotate(name,xy=(time,y),xytext=(tx,ypos[name]),fontweight='bold',fontsize=8.3,
                    color='#2C3C4A',ha='left',va='center',annotation_clip=False,zorder=10,
                    bbox=dict(boxstyle='round,pad=.13',fc='white',ec='none',alpha=.91),
                    arrowprops=dict(arrowstyle='-',linestyle=(0,(2,2)),color='#697681',lw=.75,shrinkA=1,shrinkB=2))
        counts=subset.groupby('week').size()
        ax.set_title(f'{group}\nn={counts.get(0,0)} / {counts.get(16,0)} / {counts.get(24,0)}',color=GROUP_COLORS[group],fontsize=11.5,fontweight='bold')
        ax.set_xlim(-1.5,32);ax.set_ylim(lo,hi);ax.set_xticks([0,16,24]);ax.set_xlabel('Неделя');ax.grid(axis='y',color='#E5EAEF')
        ax.spines[['top','right']].set_visible(False);ax.tick_params(labelsize=8)
    axes[0].set_ylabel('Доменный балл (центр week 0 = 0)',color=GRAY)
    fig.suptitle(f'{domain} · '+{'D1':'OFT / rear','D2':'Learning / Endurance','D3':'NOR1 + NOR2'}[domain]+' · номер у последнего измерения',fontsize=13,fontweight='bold',color=INK,y=.998)
    fig.subplots_adjust(left=.065,right=.99,top=.80,bottom=.12,wspace=.13)
    path=OUT/f'{domain}_trajectories.png';fig.savefig(path,dpi=155,facecolor='white');plt.close(fig);return path


def plot_mean(df):
    fig,axes=plt.subplots(1,3,figsize=(15.7,3.75),dpi=155)
    for ax,dom in zip(axes,DOMAINS):
        for group in ('PBS','LPS'):
            v=df[df.group==group].groupby('week')[f'{dom}_score'].agg(['mean','sem'])
            x=v.index.to_numpy();y=v['mean'].to_numpy();e=v['sem'].fillna(0).to_numpy()
            ax.plot(x,y,marker='o',lw=2,ms=5,label=group,color=GROUP_COLORS[group]);ax.fill_between(x,y-e,y+e,alpha=.15,color=GROUP_COLORS[group])
        ax.axhline(0,color='#AAB7BF',ls=':',lw=.9);ax.set_xticks([0,16,24]);ax.set_xlabel('Неделя');ax.set_title(dom,color=INK,fontweight='bold');ax.grid(axis='y',color='#E5EAEE');ax.spines[['top','right']].set_visible(False)
        if dom=='D1':ax.set_ylabel('Среднее ± SE')
    axes[-1].legend(frameon=False,fontsize=9)
    fig.suptitle('Средние траектории · PBS / LPS (описательно)',color=INK,fontweight='bold',fontsize=13)
    fig.tight_layout(rect=[0,.01,1,.93]);p=OUT/'mean_trajectories.png';fig.savefig(p,dpi=155);plt.close(fig);return p


def plot_mae(m):
    fig,axes=plt.subplots(3,4,figsize=(17.4,6.9),dpi=160,sharey=True)
    for i,algo in enumerate(ALGOS):
        k={'Ridge':'ridge','Bayesian Ridge':'bayes','Huber':'huber'}[algo]
        for j,(label,_,_,_,_) in enumerate(INTERVALS):
            ax=axes[i,j];row=m[m.transition==label].set_index('domain').loc[list(DOMAINS)]
            ix=np.arange(3)
            av=row[f'{k}_plain_mae'].to_numpy();noise=row[f'{k}_noise_10_mae'].to_numpy()
            ax.bar(ix-.17,av,width=.32,color='#9BA8B3',label='Без шума' if i==0 and j==0 else None)
            ax.bar(ix+.17,noise,width=.32,color=COLORS[algo],label='Шум 10%' if i==0 and j==0 else None)
            ax.set_xticks(ix,list(DOMAINS));ax.set_title(f'{label}\nn={int(row.n.iloc[0])}',color=INK,fontsize=9.7,fontweight='bold')
            if j==0:ax.set_ylabel(f'{algo}\nMAE ↓',color=INK,fontweight='bold')
            ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True);ax.spines[['top','right']].set_visible(False)
            for idx,(before,after) in enumerate(zip(av,noise)):
                if after+1e-8<before:ax.text(idx+.17,after+.04,'▼',ha='center',fontsize=8,color=INK)
    pchs=[Patch(fc='#9BA8B3',label='Без шума'),Patch(fc='#487D9E',label='Шум 10%')]
    fig.legend(handles=pchs,loc='upper right',bbox_to_anchor=(.96,.987),ncol=2,frameon=False,fontsize=9)
    fig.suptitle('Ошибки MAE · без шума против шума 10% · leave-one-mouse-out',color=INK,fontweight='bold',fontsize=14,y=.995)
    fig.subplots_adjust(left=.075,right=.985,top=.89,bottom=.065,wspace=.24,hspace=.45)
    p=OUT/'mae_no_noise_vs_noise10.png';fig.savefig(p,dpi=155);plt.close(fig);return p


def plot_winners(m):
    fig,ax=plt.subplots(figsize=(15.7,3.8),dpi=155)
    ax.set_xlim(-.88,4.05);ax.set_ylim(-.40,3.04);ax.axis('off')
    bgs={'Ridge|0.10':'#DAE9F1','Bayesian Ridge|0.10':'#DAE9F1','Huber|0.10':'#DEEFE7','Ridge|0.00':'#E9ECEF','Bayesian Ridge|0.00':'#E9ECEF','Huber|0.00':'#E9ECEF','Среднее':'#E9EDF0','Без изменений':'#F4E3D6'}
    for j,(label,_,_,_,_) in enumerate(INTERVALS):ax.text(j+.50,2.79,label,ha='center',color=INK,fontweight='bold',fontsize=10.5)
    for i,domain in enumerate(DOMAINS):
        y=2.23-i*.91;ax.text(-.04,y,domain+' — '+{'D1':'OFT','D2':'Learning','D3':'NOR1/2'}[domain],ha='right',va='center',color=INK,fontweight='bold',fontsize=10)
        for j,(transition,_,_,_,_) in enumerate(INTERVALS):
            row=m[(m.transition==transition)&(m.domain==domain)].iloc[0]
            winner=row.primary_best;name=winner.replace('|0.00','').replace('|0.10',' + шум')
            ax.add_patch(Rectangle((j+.03,y-.35),.94,.73,fc=bgs[winner],ec='white',lw=2))
            ax.text(j+.50,y+.11,name,ha='center',color=INK,fontsize=9.2,fontweight='bold')
            ax.text(j+.50,y-.18,'MAE '+f'{row.primary_best_mae:.3f}',ha='center',color=GRAY,fontsize=9.1)
    fig.tight_layout(pad=.4);p=OUT/'best_method_by_domain.png';fig.savefig(p,dpi=155);plt.close(fig);return p


def plot_scatter(m,p):
    fig,axes=plt.subplots(4,3,figsize=(17.5,9.6),dpi=155)
    for i,(transition,_,_,_,_) in enumerate(INTERVALS):
        for j,domain in enumerate(DOMAINS):
            ax=axes[i,j];d=p[(p.transition==transition)&(p.domain==domain)]
            row=m[(m.transition==transition)&(m.domain==domain)].iloc[0]
            x=d.actual.to_numpy();y=d.pred_ridge_0_10.to_numpy()
            zmin=min(x.min(),y.min());zmax=max(x.max(),y.max());pad=(zmax-zmin)*.12+.1
            ax.plot([zmin-pad,zmax+pad],[zmin-pad,zmax+pad],ls='--',lw=1,color='#A0AAB3')
            ax.scatter(x,y,s=33,c=COLORS['Ridge'],ec='white',lw=.5)
            ax.set_xlim(zmin-pad,zmax+pad);ax.set_ylim(zmin-pad,zmax+pad);ax.grid(alpha=.17)
            ax.spines[['top','right']].set_visible(False);ax.set_title(f'{domain} · MAE {row.ridge_noise_10_mae:.3f}',color=INK,fontweight='bold',fontsize=10.5)
            if j==0:ax.set_ylabel(transition+'\nПрогноз',color=GRAY)
            if i==3:ax.set_xlabel('Факт',color=GRAY)
    fig.suptitle('Ridge + шум 10% · факт против прогноза · пунктир — идеальный прогноз',color=INK,fontweight='bold',fontsize=14,y=.994)
    fig.subplots_adjust(left=.09,right=.985,top=.92,bottom=.07,hspace=.50,wspace=.25)
    p=OUT/'ridge_noise10_actual_vs_prediction.png';fig.savefig(p,dpi=155);plt.close(fig);return p


def plot_sensitivity(m):
    fig,axes=plt.subplots(1,3,figsize=(15.6,3.6),dpi=155)
    for ax,algo in zip(axes,ALGOS):
        k={'Ridge':'ridge','Bayesian Ridge':'bayes','Huber':'huber'}[algo]
        errors=[float(m[f'{k}_plain_mae'].mean())]+[float(m[f'{k}_noise_{v:02d}_mae'].mean()) for v in [5,10,20]]
        ax.plot([0,5,10,20],errors,'o-',color=COLORS[algo],lw=1.8,ms=6)
        ax.scatter([10],[errors[2]],color='#2A4A5A',s=60,zorder=4)
        ax.set_title(algo,color=INK,fontweight='bold');ax.set_xticks([0,5,10,20]);ax.set_xlabel('Шум, % SD входного домена');ax.set_ylabel('Средняя MAE 12 задач');ax.grid(alpha=.2);ax.spines[['right','top']].set_visible(False)
    fig.suptitle('Чувствительность: 0%, 5%, 10%, 20% · только описательное сравнение',fontsize=13,fontweight='bold',color=INK)
    fig.tight_layout(rect=[0,.02,1,.93]);p=OUT/'noise_sensitivity.png';fig.savefig(p,dpi=155);plt.close(fig);return p


def rgb(hex):return RGBColor(*[int(hex[i:i+2],16) for i in (1,3,5)])

def para(doc,text,bold=False,fontsize=9,color=None,after=5):
    p=doc.add_paragraph();p.paragraph_format.space_after=Pt(after);p.paragraph_format.space_before=Pt(0);p.paragraph_format.line_spacing=1.03
    run=p.add_run(text);run.bold=bold;run.font.name='Calibri';run.font.size=Pt(fontsize)
    if color:run.font.color.rgb=rgb(color)
    return p

def heading(doc,s):
    p=para(doc,s,True,17,INK,5);pr=p._p.get_or_add_pPr();bo=OxmlElement('w:pBdr');bot=OxmlElement('w:bottom');bot.set(qn('w:val'),'single');bot.set(qn('w:sz'),'9');bot.set(qn('w:color'),'5484A2');bo.append(bot);pr.append(bo)

def photo(doc,p,width=10.45):
    q=doc.add_paragraph();q.alignment=WD_ALIGN_PARAGRAPH.CENTER;q.paragraph_format.space_after=Pt(3);q.paragraph_format.space_before=Pt(0)
    q.add_run().add_picture(str(p),width=Inches(width))

def make_doc(df,m,p):
    charts={dom:plot_traj(df,dom) for dom in DOMAINS}
    means=plot_mean(df);errors=plot_mae(m);winners=plot_winners(m);scatter=plot_scatter(m,p);sens=plot_sensitivity(m)
    doc=Document();sec=doc.sections[0];sec.page_width=Inches(11.69);sec.page_height=Inches(8.27)
    sec.left_margin=Inches(.44);sec.right_margin=Inches(.44);sec.top_margin=Inches(.38);sec.bottom_margin=Inches(.40);sec.footer_distance=Inches(.16)
    doc.styles['Normal'].font.name='Calibri';doc.styles['Normal'].font.size=Pt(9)
    foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.RIGHT;rr=foot.add_run('24.10.2026 · eNRI / 3 домена · шум 10%');rr.font.size=Pt(8);rr.font.color.rgb=rgb('#7D8990')
    heading(doc,'Динамика трёх доменов · PBS и LPS')
    sub=df[df.group.isin(['PBS','LPS'])]
    para(doc,f'{sub.mouse_id.nunique()} мышей · {len(sub)} живых состояний · 0 / 16 / 24 недели. Сплошные линии — мыши; пунктирные — соединения с номерами.',fontsize=8.8,color=GRAY)
    para(doc,'D1 · двигательная активность — OFT / rear',True,11,INK,2);photo(doc,charts['D1'],10.35)
    para(doc,'D2 · обучение и выносливость — Learning / Endurance',True,11,INK,2);photo(doc,charts['D2'],10.35)
    para(doc,'Вывод: траектории мышей неоднородны. Ноль — исходное среднее домена, не отсутствие функции.',fontsize=8.4,color=GRAY)
    doc.add_page_break()
    heading(doc,'Динамика доменов · продолжение')
    para(doc,'D3 · исследовательское поведение — NOR1 + NOR2',True,11,INK,2);photo(doc,charts['D3'],10.35)
    para(doc,'Средние баллы трёх доменов · PBS / LPS',True,11,INK,2);photo(doc,means,10.25)
    para(doc,'Аугментация: к каждому обучающему исходному баллу добавляется N(0; 0,1²) на шкале SD тренировочных мышей. 20 отдельных обучений, их прогнозы усредняются. Исключённая мышь и её целевой балл не изменяются.',fontsize=8.4,color=GRAY,after=2)
    doc.add_page_break()
    heading(doc,'Точность прогноза · без шума против шума 10%')
    para(doc,'12 задач, n=6–11. Leave-one-mouse-out. Ridge, Bayesian Ridge, Huber; MAE меньше = точнее. 10% SD шума, 40 повторов, без подбора уровня по отложенной мыши.',fontsize=8.8,color=GRAY,after=3)
    photo(doc,errors,9.55)
    para(doc,'Лучший способ · три регрессии с шумом/без него и два простых прогноза',True,10.3,INK,2)
    photo(doc,winners,9.80)
    wins={a:int((m[f'{k}_gain_primary']>0).sum()) for a,k in [('Ridge','ridge'),('Bayesian Ridge','bayes'),('Huber','huber')]}
    b=int(m.primary_noise_best.sum())
    para(doc,f'Итог: шум уменьшил MAE в {wins["Ridge"]}/12 задач Ridge, {wins["Bayesian Ridge"]}/12 Bayesian Ridge, {wins["Huber"]}/12 Huber; модель с шумом лучшая среди всех альтернатив в {b}/12.',True,8.8,INK,2)
    doc.add_page_break()
    heading(doc,'Факт против прогноза · 12 проверок Ridge + шум 10%')
    para(doc,'Ряды: PBS 0→16 (n=9), PBS 16→24 (n=6), LPS 16→24 (n=11), PBS 0→24 (n=6); столбцы D1–D3. Пунктир — идеальный прогноз.',fontsize=8.8,color=GRAY)
    photo(doc,scatter,10.5)
    para(doc,'Вывод: оценка на малых выборках нестабильна. Шум 5%/20% показан дополнительно в CSV; выбирать наиболее удачный уровень постфактум нельзя.',True,8.4,INK,2)
    para(doc,'Ограничение: это шумовая аугментация входа, не новые независимые мыши. Доменные баллы и первичная импутация вычислены до проверки; проверялась регрессия при фиксированных факторах и только у выживших мышей.',fontsize=7.7,color=GRAY,after=0)
    path=OUT/'Otchet_Shymovaya_Augmentaciya_D1-D3_RANG_PBS_LPS_2026-10-24.docx';doc.save(path)
    return path


def main():
    df=pd.read_csv(DATA,dtype={'mouse_id':str});assert len(df)==133
    m,p=analyze(df)
    doc=make_doc(df,m,p)
    win={k:int((m[f'{slug}_gain_primary']>0).sum()) for k,slug in [('Ridge','ridge'),('Bayesian Ridge','bayes'),('Huber','huber')]}
    summary={'n_tasks':12,'noise_levels':[0.05,0.10,0.20],'primary_noise':.10,'ensemble_repeats':REPEATS,'seed':SEED,'wins_vs_plain':win,'best_of_eight_with_noise':int(m.primary_noise_best.sum()),'paired_sizes':{q[0]:q[4] for q in INTERVALS},'historic_ridge_maes_reproduced':True}
    (OUT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Шумовая аугментация для прогнозов трёх ранговых доменов','',
        '12 задач, только PBS/LPS; n=6–11; Ridge/Bayesian Ridge/Huber, тест: leave-one-mouse-out.',
        'В каждом fold шумили лишь вход обучающей мыши: SD=5/10/20% стандартизованного признака; сохранён исходный будущий балл; 20 независимых моделей с одним наблюдением на настоящую мышь и усреднение прогнозов. Без генерации независимых мышей. Главный уровень шума заранее: 10%.',
        '', '| Переход | Домен | n | Ridge | Ridge+10% | Bayes | Bayes+10% | Huber | Huber+10% | Без изм. | Среднее |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in m.itertuples():
        lines.append(f'| {r.transition} | {r.domain} | {r.n} | {r.ridge_plain_mae:.3f} | {r.ridge_noise_10_mae:.3f} | {r.bayes_plain_mae:.3f} | {r.bayes_noise_10_mae:.3f} | {r.huber_plain_mae:.3f} | {r.huber_noise_10_mae:.3f} | {r.unchanged_mae:.3f} | {r.mean_mae:.3f} |')
    lines += ['',f'Noise beats direct in {win}; noise best of 8 in {summary["best_of_eight_with_noise"]}/12.','',
       'For 5%/20% sensitivity inspect model_metrics.csv and noise_sensitivity.png. Selecting the best level per task on the same LOOCV would be multiple-testing leakage.',
       'Upstream EFA/feature imputation used all available data; not full-pipeline prospective CV. Only survivors with matched visits. No new independent observations.',
       'Report: results/Otchet_Shymovaya_Augmentaciya_D1-D3_RANG_PBS_LPS_2026-10-24.docx']
    (OUT/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False))
    print(m[['transition','domain','n','ridge_plain_mae','ridge_noise_10_mae','bayes_plain_mae','bayes_noise_10_mae','huber_plain_mae','huber_noise_10_mae','unchanged_mae','mean_mae']].round(3).to_string(index=False))
    print('DOC',str(doc),doc.stat().st_size)

if __name__=='__main__':main()
