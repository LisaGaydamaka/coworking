from pathlib import Path
import csv, statistics
out=Path(__file__).resolve().parent/"results"
rows=[]
for f in sorted(out.glob("h*/comparison.csv"),key=lambda x:int(x.parent.name[1:])):
    data=list(csv.DictReader(f.open()))
    errors=[abs(float(x["differencePct"])) for x in data]
    rows.append([int(data[0]["horizon"]),statistics.mean(errors),max(errors),all(e<=5 for e in errors)])
with (out/"horizon_trend.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["horizon","meanAbsPctError","maxAbsPctError","allNineWithin5Pct"]);w.writerows(rows)
for a in rows:print("HORIZON_TREND",*a,flush=True)
