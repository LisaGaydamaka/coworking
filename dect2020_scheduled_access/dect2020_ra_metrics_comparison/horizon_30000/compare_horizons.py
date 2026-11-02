"""Compare 3,000- and 30,000-symbol experiments using independent PRNGs."""
import csv,json
from pathlib import Path
here=Path(__file__).resolve().parent
before=json.loads((here.parent/"figures"/"independent_rng"/"errors_independent_rng.json").read_text())
after=json.loads((here/"figures"/"errors_independent_rng.json").read_text())
a={r["metric"]:r for r in before["metrics"]}
b={r["metric"]:r for r in after["metrics"]}
rows=[]
for k in ("collision","lbt_busy","attempts_per_delivered","delivery_rate"):
    x=a[k]["mape_percent"];y=b[k]["mape_percent"]
    rows.append(dict(metric=k,mape_3000_percent=x,mape_30000_percent=y,
                     delta_percentage_points=y-x,relative_change_percent=100*(y/x-1)))
with (here/"comparison_horizons.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print("Independent PRNG experiment: horizon 3000 -> 30000 symbols")
for r in rows:
    print(f'{r["metric"]}: {r["mape_3000_percent"]:.4f}% -> {r["mape_30000_percent"]:.4f}%')
