import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent
rows = list(csv.DictReader((root / "summary_metrics.csv").open()))
out = root / "figures"
out.mkdir(exist_ok=True)
labels = {
    "collision": ("Collision probability", "Collided DATA attempts / DATA attempts"),
    "lbt_busy": ("LBT busy probability", "Busy LBT / all LBT"),
    "attempts_per_delivered": ("Data attempts per delivered packet", "All DATA attempts / unique delivered packets"),
    "delivery_rate": ("Delivery intensity", "Unique delivered packets / symbol"),
}
def draw(ax, metric, title, ylabel):
    for model, color, marker in [("Python", "#215b9a", "o"), ("OMNeT++", "#d45e35", "s")]:
        data = sorted((r for r in rows if r["model"] == model), key=lambda r:float(r["arrprob"]))
        x = [float(r["arrprob"]) for r in data]
        y = [float(r[metric]) for r in data]
        sd = [float(r[metric+"_sd"]) for r in data]
        ax.plot(x, y, marker=marker, linewidth=2, color=color, label=model)
        ax.fill_between(x, [a-b for a,b in zip(y,sd)], [a+b for a,b in zip(y,sd)], color=color, alpha=0.13)
    if metric == "collision":
        py = sorted((r for r in rows if r["model"] == "Python"), key=lambda r:float(r["arrprob"]))
        ax.plot([float(r["arrprob"]) for r in py], [float(r["failed_data_fraction"]) for r in py],
                ":", linewidth=2, color="#548a5b", label="Python: all failed DATA incl. FT busy")
        om = sorted((r for r in rows if r["model"] == "OMNeT++"),
                    key=lambda r: float(r["arrprob"]))
        ax.plot([float(r["arrprob"]) for r in om],
                [float(r["radio_collision_fraction"]) for r in om],
                "--", linewidth=1.8, color="#a05060",
                label="OMNeT++: raw radio overlaps (old metric)")
    ax.set(title=title, xlabel="arrprob per PT per symbol", ylabel=ylabel)
    ax.grid(alpha=.3)
    ax.legend(fontsize=9)

fig, axes = plt.subplots(2,2,figsize=(13,9))
for ax,(m,(title, ylabel)) in zip(axes.flat, labels.items()):
    draw(ax,m,title,ylabel)
fig.suptitle("DECT-2020 random access: Python vs. corrected OMNeT++\n2 PT, 1 cluster, 3000 symbols, 10 seeds; mean and ±1 SD")
fig.tight_layout()
fig.savefig(out / "comparison_4_metrics.png", dpi=160, bbox_inches="tight")
plt.close(fig)
for m,(title,ylabel) in labels.items():
    fig, ax=plt.subplots(figsize=(8,5))
    draw(ax,m,title,ylabel)
    fig.tight_layout()
    fig.savefig(out / (m+".png"), dpi=170, bbox_inches="tight")
    plt.close(fig)
print("Saved 5 figures in", out)
