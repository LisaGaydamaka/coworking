from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent / "enri_mouse_neuroplasticity"
OUT = ROOT / "stage7_new"
OUT.mkdir(parents=True, exist_ok=True)

spec = importlib.util.spec_from_file_location("enri_solve", BASE / "solve.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

REMOVED = {("run^24","LPS^24"), ("MCC^24","LPS^24")}
m.ORDER_PAIRS = [p for p in m.ORDER_PAIRS if p not in REMOVED]

fine=json.loads((ROOT/"fine_grid_summary.json").read_text(encoding="utf-8"))
sel=fine["selected"]
beta=float(sel["beta"]); lam=float(sel["lambda"]); C=float(sel["C"])

source=m.load_included_source()
long_raw=m.build_long_table(source)
final_std,stage3_stats=m.fit_transform_stage3(long_raw,fit_mouse_ids=None,random_state=m.IMPUTATION_SEED)
errors=list(stage3_stats.get("errors",[]))
states,xbar,state_stats=m.build_experimental_states(final_std)
errors.extend(m.validate_full_stage4(states,xbar,state_stats))

solution,qp_meta=m.solve_qp_smoke(final_std,states,xbar,rho=m.SMOKE_RHO,beta=beta,ridge_lambda=lam,C=C)
errors.extend(qp_meta.get("errors",[]))
if solution is None:
    raise RuntimeError("Stage7 QP failed: "+" | ".join(errors or ["unknown"]))

weights=np.asarray(solution["w"],dtype=float)
enri=m.build_final_enri_table(final_std,xbar,weights)
validation_errors,output_stats=m.validate_stage7_outputs(enri,weights,solution,states)
errors.extend(validation_errors)

pd.DataFrame({"feature":m.MODEL_FEATURES,"weight":weights}).to_csv(OUT/"weights.csv",index=False)
enri.to_csv(OUT/"enri.csv",index=False)

group=pd.DataFrame([{
    "state":label,"group":states[label]["group"],"week":states[label]["week"],
    "mean_eNRI":float(mu),"N":int(states[label]["N"]),"O":int(states[label]["O"]),
    "D":int(states[label]["D"]),"I":int(states[label]["I"])
} for label,mu in sorted(solution["group_means"].items())])
group.to_csv(OUT/"group_means.csv",index=False)

summary={
    "stage":7,
    "status":"READY" if not errors else "FATAL",
    "validation_errors":errors,
    "removed_order_pairs":[list(x) for x in sorted(REMOVED)],
    "remaining_order_pairs":[list(x) for x in m.ORDER_PAIRS],
    "beta":beta,"lambda":lam,"C":C,"rho":float(m.SMOKE_RHO),
    "solver_status":str(solution["solver_status"]),
    "objective":float(solution["objective"]),
    "objective_components":{k:float(v) for k,v in solution["objective_components"].items()},
    "weight_l2_norm":float(solution["weight_l2_norm"]),
    "weight_max_abs":float(solution["weight_max_abs"]),
    "slack_sum":float(solution["slack_sum"]),
    "slack_max":float(solution["slack_max"]),
    "max_order_violation":float(solution["max_order_violation"]),
    "max_positivity_violation":float(solution["max_positivity_violation"]),
    "living_rows":int(output_stats["living_rows"]),
    "death_rows":int(output_stats["death_rows"]),
    "min_live_enri":float(output_stats["min_live_enri"]),
    "max_live_enri":float(output_stats["max_live_enri"]),
    "pbs0_mean":float(output_stats["pbs0_mean"]),
    "group_means":{k:float(v) for k,v in solution["group_means"].items()},
    "equality_deltas":{k:float(v) for k,v in solution["equality_deltas"].items()},
    "order_results":solution["order_results"],
    "unconstrained_treatment_differences":{
        "run24_minus_LPS24":float(solution["group_means"]["run^24"]-solution["group_means"]["LPS^24"]),
        "MCC24_minus_LPS24":float(solution["group_means"]["MCC^24"]-solution["group_means"]["LPS^24"]),
    }
}
(OUT/"stage7_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("NO_TREATMENT_ORDER_STAGE7="+json.dumps(summary,ensure_ascii=False,sort_keys=True))
if errors:
    raise RuntimeError("Stage7 validation failed: "+" | ".join(errors))
