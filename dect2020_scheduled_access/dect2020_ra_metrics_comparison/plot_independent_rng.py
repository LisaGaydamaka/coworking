"""Four Python vs OMNeT++ graphs using *independent*, default framework PRNGs.

Input: 90 new Python and 90 OMNeT++ runs from compare_metrics.py, written as
summary_metrics.csv; 10 replications per arrprob. MAPE is computed across the
nine *mean* metric values (Python denominator), NOT across individual seeds.
No PRNG pairing is assumed, even when numeric seed values are identical.
"""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent
OUT=HERE/"figures"/"independent_rng"
OUT.mkdir(parents=True,exist_ok=True)
KEYS={
    "collision": ("Вероятность физической коллизии DATA",
                  "P(DATA пересекает DATA или ACK)"),
    "lbt_busy": ("Вероятность LBT busy", "P(LBT busy)"),
    "attempts_per_delivered": ("Попытки DATA на доставленный пакет",
                               "Попытки DATA / доставленные пакеты"),
    "delivery_rate": ("Интенсивность доставки",
                       "Доставленные пакеты / символ"),
}
with (HERE/"summary_metrics.csv").open(newline="") as f:
    rows=list(csv.DictReader(f))
assert len(rows)==18, ("expected 9 load points * 2 models",len(rows))
series={}
for model in ("Python","OMNeT++"):
    series[model]=sorted((r for r in rows if r["model"]==model),
                         key=lambda r:float(r["arrprob"]))
    assert len(series[model])==9
    assert all(int(r["runs"])==10 for r in series[model])
ps=[float(r["arrprob"]) for r in series["Python"]]
assert ps==[round(i/100,2) for i in range(1,10)]
assert ps==[float(r["arrprob"]) for r in series["OMNeT++"]]

errors=[]
for k,(title,label) in KEYS.items():
    ypy=[float(r[k]) for r in series["Python"]]
    yom=[float(r[k]) for r in series["OMNeT++"]]
    diffs=[abs(o-p) for p,o in zip(ypy,yom)]
    mape=100*sum(d/p for d,p in zip(diffs,ypy))/len(diffs)
    mae=sum(diffs)/len(diffs)
    errors.append(dict(metric=k,label=title,mape_percent=mape,
                       mean_absolute_error=mae,
                       error_unit="percentage points" if k in ("collision","lbt_busy") else ("attempts" if k=="attempts_per_delivered" else "packets/symbol"),
                       error_at_0_05_percent=100*abs(yom[4]-ypy[4])/ypy[4],
                       python_at_0_05=ypy[4],omnet_at_0_05=yom[4]))
with (OUT/"errors_independent_rng.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=errors[0].keys())
    w.writeheader();w.writerows(errors)
(OUT/"errors_independent_rng.json").write_text(
    json.dumps({"run_design":"Independent default Python and OMNeT++ PRNGs",
                "pt_count":2,"symbol_horizon":3000,"loads":ps,
                "replicates_per_load":10,
                "error_definition":"MAPE across 9 per-load sample means, Python reference",
                "metrics":errors},indent=2,ensure_ascii=False)+"\n",
    encoding="utf-8")
with (OUT/"summary_independent_rng.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]))
    w.writeheader();w.writerows(rows)

plt.rcParams.update({
    "font.family":"DejaVu Sans","font.size":10.5,
    "axes.titlesize":12,"axes.titleweight":"semibold",
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.edgecolor":"#CBD3DE","grid.color":"#E3E7EC",
    "savefig.facecolor":"white","figure.facecolor":"white"
})
NAVY="#245D8C"
ORANGE="#C25B30"
def graph(ax,key):
    for model,color,marker in [("Python",NAVY,"o"),("OMNeT++",ORANGE,"s")]:
        data=series[model]
        x=[float(r["arrprob"]) for r in data]
        y=[float(r[key]) for r in data]
        sd=[float(r[key+"_sd"]) for r in data]
        ax.plot(x,y,color=color,linewidth=2.2,marker=marker,markersize=4.8,
                markeredgecolor="white",markeredgewidth=.6,label=model,zorder=3)
        ax.fill_between(x,[a-b for a,b in zip(y,sd)],
                        [a+b for a,b in zip(y,sd)],color=color,alpha=.11,zorder=2,
                        linewidth=0)
    ax.grid(alpha=.95,linewidth=.7)
    ax.set_xticks(ps);ax.set_xlim(.005,.095)
    ax.set_title(KEYS[key][0],loc="left",pad=10)
    ax.set_ylabel(KEYS[key][1])
    ax.set_xlabel("arrprob (на PT и символ)")
    if key in ("collision","lbt_busy"):
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{100*x:.0f}%"))
    if key=="delivery_rate":
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f"{x:.3f}"))
    mape=next(r["mape_percent"] for r in errors if r["metric"]==key)
    ax.text(.99,.03,f"MAPE: {mape:.2f}%",transform=ax.transAxes,
            ha="right",va="bottom",fontsize=10,weight="bold",color="#4E5868",
            bbox=dict(facecolor="white",alpha=.85,edgecolor="none",pad=3))

for key in KEYS:
    fig,ax=plt.subplots(figsize=(8.8,5.2))
    graph(ax,key)
    ax.legend(frameon=False,loc="upper left",ncol=2)
    fig.tight_layout(pad=1.9)
    fig.savefig(OUT/(key+".png"),dpi=180,bbox_inches="tight")
    plt.close(fig)

fig,axes=plt.subplots(2,2,figsize=(14.8,10))
for ax,key in zip(axes.flat,KEYS):
    graph(ax,key)
fig.suptitle("DECT-2020 RA: Python и OMNeT++ | независимые генераторы",
             weight="semibold",fontsize=17,y=.992)
fig.text(.5,.963,"2 PT · 3000 символов · 9 нагрузок · 10 прогонов на точку · среднее ±1 SD",
         ha="center",color="#546474",fontsize=10)
handles=[Line2D([0],[0],color=NAVY,marker="o",lw=2.2,label="Python"),
         Line2D([0],[0],color=ORANGE,marker="s",lw=2.2,label="OMNeT++")]
fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.5,.945),
           ncol=2,frameon=False)
fig.subplots_adjust(top=.878,bottom=.075,left=.085,right=.976,wspace=.28,hspace=.40)
fig.text(.5,.025,"Ошибки рассчитаны по 9 средним точкам каждого графика; за базу взят Python.",
         ha="center",fontsize=10,color="#56677A")
fig.savefig(OUT/"comparison_all_4.png",dpi=180,bbox_inches="tight")
plt.close(fig)
print("INDEPENDENT-RNG MAPE (%):")
for r in errors:
    print(f"  {r['metric']}: {r['mape_percent']:.5f}; MAE={r['mean_absolute_error']:.8f}")
print("Saved",OUT)
