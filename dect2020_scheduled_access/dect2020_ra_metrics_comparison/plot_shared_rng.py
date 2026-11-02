"""Plot four metrics from 90 paired common-random-stream experiments.
Source: omnet_new/shared_rng_grid_comparison.csv (not the independent-RNG summary).
"""
import csv
import statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent
OUT=HERE/"figures"/"shared_rng"
OUT.mkdir(parents=True,exist_ok=True)
rows=list(csv.DictReader((HERE/"omnet_new"/"shared_rng_grid_comparison.csv").open()))
assert len(rows)==810, f"Expected 810 metric comparisons, got {len(rows)}"
counts=defaultdict(dict)
for r in rows:
    key=(float(r["arrprob"]),int(r["seed"]))
    assert int(r["difference"])==0, ("Mismatch",r)
    counts[key][r["metric"]]=(int(r["python"]),int(r["omnet"]))
assert len(counts)==90

def metrics(per,model_index):
    get=lambda name:per[name][model_index]
    return dict(collision=get("radio_collisions")/get("attempts"),
                lbt_busy=get("busy_lbt")/get("all_lbt"),
                attempts_per_delivered=get("attempts")/get("delivered"),
                delivery_rate=get("delivered")/3000)

summary=[]
for p in sorted({k[0] for k in counts}):
    group=[counts[(p,seed)] for seed in range(1,11)]
    for model,j in [("Python",0),("OMNeT++",1)]:
        row=dict(arrprob=p,model=model,runs=10)
        observations=[metrics(per,j) for per in group]
        for key in observations[0]:
            values=[obs[key] for obs in observations]
            row[key+"_mean"]=statistics.mean(values)
            row[key+"_sd"]=statistics.stdev(values)
        summary.append(row)
with (OUT/"summary_shared_rng.csv").open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=list(summary[0]))
    writer.writeheader();writer.writerows(summary)

plt.rcParams.update({
    "font.family":"DejaVu Sans","font.size":11,"axes.titlesize":12.5,
    "axes.titleweight":"semibold","axes.labelsize":10,
    "axes.spines.top":False,"axes.spines.right":False,
    "axes.edgecolor":"#C8D0D9","grid.color":"#DEE4EA",
    "grid.linewidth":0.7,"savefig.facecolor":"white","figure.facecolor":"white"
})
titles={
    "collision":("Вероятность коллизии DATA","P(DATA пересекает DATA или ACK)"),
    "lbt_busy":("Вероятность LBT busy","P(LBT busy)"),
    "attempts_per_delivered":("Попытки DATA на доставленный пакет","N попыток DATA / N доставленных пакетов"),
    "delivery_rate":("Интенсивность доставки","Доставлено пакетов / символ"),
}
NAVY="#215887"
ORANGE="#C35F31"
LIGHT="#52718B"
def draw(ax,key):
    py=sorted([r for r in summary if r["model"]=="Python"],key=lambda r:r["arrprob"])
    om=sorted([r for r in summary if r["model"]=="OMNeT++"],key=lambda r:r["arrprob"])
    x=[r["arrprob"] for r in py]
    y=[r[key+"_mean"] for r in py]
    sd=[r[key+"_sd"] for r in py]
    assert x==[r["arrprob"] for r in om]
    assert y==[r[key+"_mean"] for r in om]
    ax.fill_between(x,[a-b for a,b in zip(y,sd)],[a+b for a,b in zip(y,sd)],
                    color=LIGHT,alpha=.15,linewidth=0)
    ax.plot(x,y,color=NAVY,linewidth=3.1,marker="o",markersize=7,
            markerfacecolor="white",markeredgewidth=1.8)
    ax.plot(x,y,color=ORANGE,linestyle="--",linewidth=1.8,
            marker="x",markersize=6,markeredgewidth=1.6)
    ax.set_title(titles[key][0],loc="left",pad=12)
    ax.set_xlabel("Вероятность поступления пакета arrprob")
    ax.set_ylabel(titles[key][1])
    ax.set_xticks(x);ax.set_xlim(.006,.094)
    ax.grid(alpha=.85)
    if key in ("collision","lbt_busy"):
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f"{100*v:.0f}%"))
    elif key=="delivery_rate":
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f"{v:.3f}"))
    limits={"collision":(.18,.39),"lbt_busy":(.25,.43),
            "attempts_per_delivered":(1.65,3.0),"delivery_rate":(.012,.024)}
    ax.set_ylim(*limits[key])
    ax.text(.99,.02,"Python = OMNeT++ для каждого seed",transform=ax.transAxes,
            ha="right",va="bottom",fontsize=8.5,color="#506A7F")

for key in titles:
    fig,ax=plt.subplots(figsize=(9,5.25))
    draw(ax,key);fig.tight_layout(pad=1.8)
    fig.savefig(OUT/(key+".png"),dpi=190,bbox_inches="tight")
    plt.close(fig)

fig,axs=plt.subplots(2,2,figsize=(14.8,9.8))
for ax,key in zip(axs.flat,titles):draw(ax,key)
handles=[Line2D([0],[0],color=NAVY,marker="o",markerfacecolor="white",lw=3,label="Python"),
         Line2D([0],[0],color=ORANGE,marker="x",ls="--",lw=2,label="OMNeT++"),
         plt.Rectangle((0,0),1,1,facecolor=LIGHT,alpha=.15,label="±1 SD (10 прогонов)")]
fig.legend(handles=handles,loc="upper center",bbox_to_anchor=(.5,.942),frameon=False,ncol=3,fontsize=11)
fig.suptitle("DECT-2020 RA | Python и OMNeT++ с общим случайным потоком",
             fontsize=18,weight="semibold",y=.992)
fig.text(.5,.959,"2 PT · 1 кластер · 3000 символов · 9 уровней нагрузки · 10 парных прогонов на точку",
         ha="center",fontsize=10.5,color="#56677A")
fig.subplots_adjust(top=.88,bottom=.105,left=.086,right=.97,wspace=.28,hspace=.39)
fig.text(.5,.035,"Кривые полностью совпадают: 810 из 810 проверенных целочисленных счётчиков равны.",
         ha="center",fontsize=11.5,weight="semibold",color="#24516D")
fig.savefig(OUT/"comparison_all_4.png",dpi=180,bbox_inches="tight")
plt.close(fig)
print("Saved five PNG figures and summary CSV to",OUT)
