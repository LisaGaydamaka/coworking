#!/usr/bin/env python3
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.linear_model import Ridge

BASE=Path(__file__).resolve().parent
INFILE=BASE.parent/"enri_mouse_neuroplasticity_efa26_robust_validation_rank_scores"/"results"/"clean133_k4_rank_frozen_scores.csv"
OUT=BASE/"results"
OUT.mkdir(exist_ok=True)
DOMAINS=("D1","D2","D3","D4")
TRANSITIONS=(("PBS_0_16","PBS",0,16),("PBS_16_24","PBS",16,24),("LPS_16_24","LPS",16,24))
ALPHA=1.0

def predict(x,y,z):
    # Standardize using training mice only. Ridge with one predictor and intercept.
    mu=x.mean();sd=x.std(ddof=0)
    if sd<1e-10:return float(y.mean()),float(y.mean()),0.
    reg=Ridge(alpha=ALPHA)
    reg.fit(((x-mu)/sd).reshape(-1,1),y)
    slope=float(reg.coef_[0]/sd)
    intercept=float(reg.intercept_-slope*mu)
    return float(intercept+slope*z),intercept,slope

def model(x,y):
    n=len(x)
    preds=[];avg=[]
    for i in range(n):
        mask=np.arange(n)!=i
        preds.append(predict(x[mask],y[mask],x[i])[0])
        avg.append(y[mask].mean())
    preds=np.array(preds);avg=np.array(avg)
    mae=lambda a:float(np.mean(np.abs(y-a)))
    rmse=lambda a:float(np.sqrt(np.mean((y-a)**2)))
    total=np.sum((y-y.mean())**2)
    _,intercept,slope=predict(x,y,0.)
    return preds,avg,{
      "n":n,"ridge_mae":mae(preds),"ridge_rmse":rmse(preds),
      "persistence_mae":mae(x),"persistence_rmse":rmse(x),
      "mean_mae":mae(avg),"mean_rmse":rmse(avg),
      "ridge_cv_r2":float(1-np.sum((y-preds)**2)/total) if total>1e-12 else np.nan,
      "ridge_better_both":bool(mae(preds)<min(mae(x),mae(avg))),
      "persistence_minus_ridge_mae":mae(x)-mae(preds),
      "full_fit_intercept":intercept,"full_fit_slope":slope,
      "observed_mean_change":float(np.mean(y-x))
    }

def main():
    df=pd.read_csv(INFILE,dtype={"mouse_id":str})
    assert len(df)==133, f"Expected 133: {len(df)}"
    predictions=[];metrics=[];pairs=[];sizes=[]
    for title,group,start,end in TRANSITIONS:
        data=df[df.group==group]
        old=data[data.week==start][["mouse_id"]+[f"{d}_score" for d in DOMAINS]]
        new=data[data.week==end][["mouse_id"]+[f"{d}_score" for d in DOMAINS]]
        assert old.mouse_id.is_unique and new.mouse_id.is_unique
        old=old.rename(columns={f"{d}_score":f"{d}_start" for d in DOMAINS})
        new=new.rename(columns={f"{d}_score":f"{d}_end" for d in DOMAINS})
        both=old.merge(new,on="mouse_id",validate="one_to_one").sort_values("mouse_id")
        n=len(both)
        if n<4:raise ValueError(f"Too few mouse pairs for {title}: {n}")
        sizes.append({"transition":title,"initial_states":len(old),"final_states":len(new),"paired_survivors":n})
        bp=both.copy();bp.insert(0,"transition",title);pairs.append(bp)
        for domain in DOMAINS:
            x=both[f"{domain}_start"].to_numpy(float)
            y=both[f"{domain}_end"].to_numpy(float)
            r,mean,summary=model(x,y)
            metrics.append({"transition":title,"domain":domain,**summary})
            for idx in range(n):
                predictions.append({"transition":title,"domain":domain,"mouse_id":both.mouse_id.iloc[idx],
                   "start_score":x[idx],"observed_future":y[idx],"loo_ridge_prediction":r[idx],
                   "unchanged_prediction":x[idx],"loo_mean_prediction":mean[idx],
                   "ridge_abs_error":abs(y[idx]-r[idx]),"unchanged_abs_error":abs(y[idx]-x[idx])})
    m=pd.DataFrame(metrics);p=pd.DataFrame(predictions)
    assert len(m)==12
    pd.concat(pairs,ignore_index=True).to_csv(OUT/"paired_mouse_scores.csv",index=False)
    m.to_csv(OUT/"model_metrics.csv",index=False)
    p.to_csv(OUT/"loo_predictions.csv",index=False)
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9})
    for title,_,_,_ in TRANSITIONS:
        sub=m[m.transition==title]
        pos=np.arange(4)
        fig,ax=plt.subplots(figsize=(8,4))
        for dx,col,name in [(-.25,"ridge_mae","Ridge"),(0,"persistence_mae","Без изменений"),(.25,"mean_mae","Среднее")]:
            ax.bar(pos+dx,sub[col],width=.24,label=name)
        ax.set_xticks(pos,DOMAINS)
        ax.set_title(f"{title}: {sub.n.iloc[0]} мышей, проверка leave-one-out")
        ax.set_ylabel("MAE (меньше = лучше)")
        ax.legend(frameon=False)
        ax.grid(axis="y",alpha=.2);ax.set_axisbelow(True)
        fig.tight_layout();fig.savefig(OUT/f"{title}_errors.png",dpi=150);plt.close(fig)
        fig,axes=plt.subplots(2,2,figsize=(8,7))
        for ax,domain in zip(axes.flat,DOMAINS):
            q=p[(p.transition==title)&(p.domain==domain)]
            y=q.observed_future.to_numpy();pred=q.loo_ridge_prediction.to_numpy()
            lo=min(y.min(),pred.min())-.2;hi=max(y.max(),pred.max())+.2
            ax.scatter(y,pred,s=28);ax.plot([lo,hi],[lo,hi],ls="--",color="gray")
            ax.set_xlim(lo,hi);ax.set_ylim(lo,hi);ax.set_title(domain)
            ax.set_xlabel("Фактический балл");ax.set_ylabel("Прогноз")
            ax.grid(alpha=.15)
        fig.suptitle(title)
        fig.tight_layout();fig.savefig(OUT/f"{title}_predictions.png",dpi=150);plt.close(fig)
    lines=["# Отдельный прогноз четырёх доменов","",
      "Три интервала при сохранении условий: PBS 0→16, PBS 16→24, LPS 16→24. Для каждого перехода четыре независимые одномерные регрессии Dk(позже) = a + b·Dk(раньше).",
      "Источник: EFA26, 26 исходных признаков, 54 мыши на baseline; 133 живых наблюдения после удаления 7 экстремальных поздних состояний.","",
      "## Сопоставленные по идентификатору живые мыши","",
      "| Переход | На исходной неделе | На конечной | С обеими точками |",
      "|---|---:|---:|---:|"]
    for q in sizes:lines.append(f"| {q['transition']} | {q['initial_states']} | {q['final_states']} | {q['paired_survivors']} |")
    lines+=["","## Ошибки вне обучающей выборки","",
      "Метод: Ridge с одним предиктором, alpha=1.0 фиксировано до проверки. Стандартизация входа — только на обучающих мышах. Leave-one-mouse-out: каждую мышь прогнозируем по остальным. Два сравнения: прогноз без изменения балла и средний балл будущей недели, рассчитанный на обучающих мышах.",
      "","| Переход | Домен | n | Ridge MAE | Без изменений MAE | Среднее MAE | Ridge лучше обеих? |",
      "|---|---|---:|---:|---:|---:|---|"]
    for _,q in m.iterrows():
        lines.append(f"| {q.transition} | {q.domain} | {q.n} | {q.ridge_mae:.3f} | {q.persistence_mae:.3f} | {q.mean_mae:.3f} | {'Да' if q.ridge_better_both else 'Нет'} |")
    lines+=["",f"**Итог:** Ridge точнее обеих простых альтернатив в {int(m.ridge_better_both.sum())} из 12 прогнозов.","",
      "## Интерпретация и ограничения","",
      "- Только парные наблюдения одной и той же выжившей мыши; выбывание и смерть вызывают селекционное смещение. Эта регрессия не предсказывает выживаемость.",
      "- При таком числе животных результаты нестабильны: нельзя утверждать прогностическую пригодность индекса без новых данных.",
      "- Все четыре доменных балла ранее рассчитаны по EFA на всех 54 baseline-мышах; исходная импутация могла использовать другие недели. Cross-validation здесь проверяет регрессию при фиксированных баллах, а НЕ независимость полной цепочки EFA + прогноз.",
      "- Знак фактора произвольный: рост доменного балла сам по себе не означает улучшение здоровья.",
      "- run и MCC не участвуют в обучении.",
      "- Неподтвержденные связи с клиническим нейропластическим резервом не следует выводить из этих результатов.","",
      "## Файлы","",
      "- model_metrics.csv: все ошибки и окончательные коэффициенты a,b после обучения на доступных парах.",
      "- loo_predictions.csv: фактический и прогнозируемый балл каждой отложенной мыши.",
      "- paired_mouse_scores.csv: все совпадающие по идентификатору пары.",
      "- *errors.png и *predictions.png: графики для каждого интервала.",""]
    (OUT/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    (OUT/"metadata.json").write_text(json.dumps({"data_path":str(INFILE),"alpha":ALPHA,
      "transitions":sizes,"models":12,"method":"Univariate per-domain Ridge, leave-one-mouse-out",
      "caveat":"Domain scores extracted before CV, not full pipeline CV"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PAIRS:",json.dumps(sizes,ensure_ascii=False))
    print(m[["transition","domain","n","ridge_mae","persistence_mae","mean_mae","ridge_cv_r2"]].to_string(index=False))

if __name__=="__main__":
    main()
