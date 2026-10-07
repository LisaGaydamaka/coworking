#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def readj(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

model = readj("base_results/model.json")
s0 = readj("stage_0/stage_0_summary.json")
sb = readj("stage_b/stage_b_summary.json")
sc = readj("stage_c/stage_c_summary.json")
sg = readj("stage_g/stage_g_summary.json")
sh = readj("stage_h_production/stage_h_summary.json")
sk = readj("stage_k/stage_k_summary.json")

summary = {
    "experiment": "ALL0MEAN_GRIP31_LONGITUDINAL_ONLY",
    "order_pairs": s0["order_pairs"],
    "base_hyperparameters": {
        "beta": model["beta"],
        "lambda2": model["lambda"],
        "C": model["C"],
        "rho": model["rho"],
    },
    "base_group_means": s0["group_means"],
    "development_lambda1": sb["development_selection"]["lambda1_star"],
    "stability_core_features": sc.get("core_features", sc.get("stability_core_features")),
    "development_selected_k": sg.get("selected_k", sg.get("development_selection", {}).get("selected_k")),
    "nested_completed_outer": sh["completed_outer_splits"],
    "nested_k_distribution": sh["k_distribution"],
    "nested_lambda1_distribution": sh["lambda1_distribution"],
    "nested_top_feature_frequency": sh["top_feature_frequency"],
    "nested_top_subset_frequency": sh["top_subset_frequency"],
    "stage_k_status": sk["status"],
    "stage_k_final_subset_fixed": sk["final_subset_fixed"],
    "stage_k_reason": sk["reason"],
    "stage_k_nested_evidence": sk["nested_evidence"],
    "validation_errors": {
        "stage0": s0.get("validation_errors", []),
        "stage_b": sb.get("validation_errors", []),
        "stage_c": sc.get("validation_errors", []),
        "stage_g": sg.get("validation_errors", []),
        "stage_h": sh.get("validation_errors", []),
        "stage_k": sk.get("validation_errors", []),
    },
}
(ROOT / "EXPERIMENT_SUMMARY.json").write_text(
    json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
