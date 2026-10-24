#!/usr/bin/env python3
"""Compare domain-only Ridge with domain + current weight using mouse-level LOOCV."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

HERE = Path(__file__).resolve().parent
DATA = HERE / "input" / "clean133_k3_rank_frozen_scores_with_weight.csv"
OUT = HERE / "results"
OUT.mkdir(exist_ok=True)
TASKS = [("PBS 0→16", "PBS", 0, 16, 9),
         ("PBS 16→24", "PBS", 16, 24, 6),
         ("LPS 16→24", "LPS", 16, 24, 11),
         ("PBS 0→24", "PBS", 0, 24, 6)]
DOMAINS = ("D1", "D2", "D3")
PREVIOUS_RIDGE = {
 ("PBS 0→16","D1"):1.200022, ("PBS 0→16","D2"):0.881626, ("PBS 0→16","D3"):1.009778,
 ("PBS 16→24","D1"):0.270623, ("PBS 16→24","D2"):0.956556, ("PBS 16→24","D3"):1.610203,
 ("LPS 16→24","D1"):0.724493, ("LPS 16→24","D2"):0.322451, ("LPS 16→24","D3"):1.151570,
 ("PBS 0→24","D1"):0.290680, ("PBS 0→24","D2"):0.621357, ("PBS 0→24","D3"):0.770379
}

def fit_predict(train_x, train_y, test_x):
    mean = train_x.mean(axis=0)
    sd = train_x.std(axis=0, ddof=0)
    sd = np.where(sd < 1e-10, 1.0, sd)
    mdl = Ridge(alpha=1.0, fit_intercept=True)
    mdl.fit((train_x - mean) / sd, train_y)
    return float(mdl.predict(((test_x - mean) / sd).reshape(1, -1))[0])

def main():
    df = pd.read_csv(DATA, dtype={"mouse_id":str})
    assert len(df) == 133
    assert df[["mouse_id","group","week"]].duplicated().sum() == 0
    assert df[["D1_score","D2_score","D3_score","Weight"]].notna().all().all()
    metrics, predictions = [], []
    for transition, group, first, last, expected_n in TASKS:
        base = df[(df.group==group)&(df.week==first)].copy()
        future = df[(df.group==group)&(df.week==last)].copy()
        paired = base.merge(future, on=["mouse_id","group"],suffixes=("_start","_end"),validate="one_to_one")
        paired = paired.sort_values("mouse_id").reset_index(drop=True)
        assert len(paired) == expected_n, (transition,len(paired))
        for domain in DOMAINS:
            x = paired[[f"{domain}_score_start","Weight_start"]].to_numpy(float)
            y = paired[f"{domain}_score_end"].to_numpy(float)
            pred = {key:np.zeros(len(y)) for key in ("ridge_domain","ridge_plus_weight","persistence","training_mean")}
            for i in range(len(y)):
                mask = np.arange(len(y)) != i
                pred["ridge_domain"][i] = fit_predict(x[mask,:1], y[mask], x[i,:1].ravel())
                pred["ridge_plus_weight"][i] = fit_predict(x[mask,:], y[mask], x[i,:].ravel())
                pred["persistence"][i] = x[i,0]
                pred["training_mean"][i] = y[mask].mean()
            mae = {name:float(np.mean(abs(y-val))) for name,val in pred.items()}
            rmse = {name:float(np.sqrt(np.mean((y-val)**2))) for name,val in pred.items()}
            assert abs(mae["ridge_domain"] - PREVIOUS_RIDGE[(transition,domain)]) < 3e-6
            metrics.append({"transition":transition,"group":group,"week_from":first,"week_to":last,
                            "domain":domain,"n":len(y),"ridge_domain_mae":mae["ridge_domain"],
                            "ridge_plus_weight_mae":mae["ridge_plus_weight"],
                            "persistence_mae":mae["persistence"],"training_mean_mae":mae["training_mean"],
                            "ridge_domain_rmse":rmse["ridge_domain"],
                            "ridge_plus_weight_rmse":rmse["ridge_plus_weight"],
                            "persistence_rmse":rmse["persistence"],"training_mean_rmse":rmse["training_mean"],
                            "difference_mae_weight_minus_plain":mae["ridge_plus_weight"]-mae["ridge_domain"],
                            "better_than_plain":mae["ridge_plus_weight"]<mae["ridge_domain"],
                            "better_than_both_benchmarks":mae["ridge_plus_weight"]<min(mae["persistence"],mae["training_mean"]),
                            "best_of_four":{"ridge_domain":"ridge_domain_pred","ridge_plus_weight":"ridge_domain_weight_pred","persistence":"persistence_pred","training_mean":"training_mean_pred"}[min(mae,key=mae.get)]})
            for i in range(len(y)):
                predictions.append({"transition":transition,"group":group,"week_from":first,"week_to":last,
                                    "domain":domain,"mouse_id":paired.mouse_id.iloc[i],
                                    "status_start":paired.status_start.iloc[i],"status_end":paired.status_end.iloc[i],
                                    "current_domain":x[i,0],"current_weight_standardized":x[i,1],
                                    "actual":y[i],
                                    "ridge_domain_pred":pred["ridge_domain"][i],
                                    "ridge_domain_weight_pred":pred["ridge_plus_weight"][i],
                                    "persistence_pred":pred["persistence"][i],
                                    "training_mean_pred":pred["training_mean"][i]})
    m = pd.DataFrame(metrics)
    pd.DataFrame(predictions).to_csv(OUT/"leave_one_mouse_out_predictions.csv",index=False)
    m.to_csv(OUT/"model_metrics.csv",index=False)
    summary = {"num_tasks":len(m),"prediction_count":len(predictions),
               "plus_weight_better_ridge":int(m.better_than_plain.sum()),
               "plus_weight_better_both_baselines":int(m.better_than_both_benchmarks.sum()),
               "plus_weight_best_of_four":int((m.best_of_four=="ridge_domain_weight_pred").sum()),
               "mean_mae_plain":float(m.ridge_domain_mae.mean()),
               "mean_mae_plus_weight":float(m.ridge_plus_weight_mae.mean())}
    (OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__ == "__main__":
    main()
