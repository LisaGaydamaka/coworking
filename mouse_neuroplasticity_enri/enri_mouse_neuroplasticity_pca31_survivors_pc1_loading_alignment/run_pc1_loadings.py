#!/usr/bin/env python3
"""Independent PC1 loading-similarity analysis: end-of-experiment survivors."""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"results"
OUT.mkdir(parents=True,exist_ok=True)
PARENT=ROOT.parent
FULL=PARENT/"enri_mouse_neuroplasticity_pca31_processed"/"results"/"processed_matrix_31_living.csv"
CLEAN=PARENT/"enri_mouse_neuroplasticity_pca31_processed_drop_7_outlier_states"/"results"/"processed_matrix_31_living.csv"
META=["mouse_id","group","week","status"]
GROUPS=["PBS","LPS","run","MCC"]
WEEKS=[0,16,24]
PAIRS=[(0,16),(0,24),(16,24)]
NBOOT=1000
SEED=20261008

def fit_pc1(x):
    if len(x)<3 or len(np.unique(x,axis=0))<3:
        return None
    m=PCA(svd_solver="full").fit(x)
    vec=m.components_[0].copy()
    if not np.all(np.isfinite(vec)) or not np.isfinite(m.explained_variance_ratio_[0]):
        return None
    return {"vec":vec,
            "pc1_pct":float(100*m.explained_variance_ratio_[0]),
            "pc2_pct":float(100*m.explained_variance_ratio_[1]),
            "pc1_pc2_ratio":float(m.explained_variance_[0]/m.explained_variance_[1]) if m.explained_variance_[1]>0 else None,
            "n":len(x)}

def similarity(a,b):
    return float(min(1.0,max(0.0,abs(a@b)/(np.linalg.norm(a)*np.linalg.norm(b)))))

def top_features(v,features,n=5):
    ix=np.argsort(-np.abs(v))[:n]
    return [{"feature":str(features[j]),"loading":float(v[j]),"abs_loading":float(abs(v[j]))} for j in ix]

full=pd.read_csv(FULL,dtype={"mouse_id":str})
clean=pd.read_csv(CLEAN,dtype={"mouse_id":str})
features=[c for c in clean.columns if c not in META]
assert len(features)==31 and len(clean)==133 and len(full)==140
surv=full[full.week.eq(24)][["mouse_id","group"]].drop_duplicates()
assert len(surv)==42 and surv.mouse_id.nunique()==42
assert surv.groupby("group").size().to_dict()=={"PBS":8,"LPS":11,"MCC":11,"run":12}
df=clean.merge(surv,on=["mouse_id","group"],how="inner",validate="many_to_one")

rng=np.random.default_rng(SEED)
main_rows=[]; pair_rows=[]; loading_rows=[]; top_rows=[]; boot_rows=[]; matching_rows=[]; matched_pair_rows=[]
all_details={}
for g in GROUPS:
    group_ids=sorted(surv.loc[surv.group.eq(g),"mouse_id"].tolist())
    groupsub=df[df.group.eq(g)].copy()
    lookup={}
    fits={}
    for w in WEEKS:
        rows=groupsub[groupsub.week.eq(w)]
        assert not rows.mouse_id.duplicated().any()
        lookup[w]={str(r.mouse_id):r[features].to_numpy(dtype=float) for _,r in rows.iterrows()}
        x=rows[features].to_numpy(float)
        fit=fit_pc1(x)
        assert fit is not None
        fits[w]=fit
    assert {w:fits[w]["n"] for w in WEEKS}=={
        "PBS":{0:8,16:8,24:6},
        "LPS":{0:11,16:11,24:11},
        "run":{0:12,16:12,24:11},
        "MCC":{0:11,16:8,24:10}
    }[g]

    # Stable sign orientation solely for presentation. Similarity is sign-invariant.
    v0=fits[0]["vec"]
    if v0[np.argmax(np.abs(v0))]<0:
        v0=-v0
    oriented={0:v0}
    for w in [16,24]:
        v=fits[w]["vec"].copy()
        if v@v0<0:
            v=-v
        oriented[w]=v

    for w in WEEKS:
        f=fits[w]
        main_rows.append({"group":g,"week":w,"n":f["n"],
                         "pc1_percent":f["pc1_pct"],"pc2_percent":f["pc2_pct"],
                         "pc1_to_pc2_eigenvalue_ratio":f["pc1_pc2_ratio"]})
        for j,feature in enumerate(features):
            loading_rows.append({"group":g,"week":w,"feature":feature,
                                 "pc1_coefficient_aligned_to_baseline":float(oriented[w][j]),
                                 "abs_pc1_coefficient":float(abs(oriented[w][j])),
                                 "pc1_squared_coefficient_share_percent":float(100*oriented[w][j]**2)})
        for rank,item in enumerate(top_features(oriented[w],features,10),1):
            top_rows.append({"group":g,"week":w,"rank":rank,**item})

    for w1,w2 in PAIRS:
        s=similarity(fits[w1]["vec"],fits[w2]["vec"])
        top1=set(f["feature"] for f in top_features(fits[w1]["vec"],features))
        top2=set(f["feature"] for f in top_features(fits[w2]["vec"],features))
        pair_rows.append({"group":g,"week_from":w1,"week_to":w2,
                          "n_from":fits[w1]["n"],"n_to":fits[w2]["n"],
                          "pc1_absolute_cosine":s,
                          "pc1_principal_angle_degrees":float(np.degrees(np.arccos(s))),
                          "top5_overlap_count":len(top1&top2),
                          "top5_overlap_features":"; ".join(sorted(top1&top2))})

    # Paired animal bootstrap: each sampled mouse ID is reused across all weeks.
    bs_sim={pair:[] for pair in PAIRS}
    bs_ref={w:[] for w in WEEKS}
    bs_pct={w:[] for w in WEEKS}
    valid=0
    for b in range(NBOOT):
        sampled=rng.choice(group_ids,size=len(group_ids),replace=True)
        fitted={}
        for w in WEEKS:
            z=np.vstack([lookup[w][i] for i in sampled if i in lookup[w]])
            fitted[w]=fit_pc1(z)
        if any(fitted[w] is None for w in WEEKS):
            continue
        valid+=1
        for w in WEEKS:
            bs_ref[w].append(similarity(fitted[w]["vec"],fits[w]["vec"]))
            bs_pct[w].append(fitted[w]["pc1_pct"])
        for p in PAIRS:
            bs_sim[p].append(similarity(fitted[p[0]]["vec"],fitted[p[1]]["vec"]))
    if valid<700:
        raise RuntimeError(f"{g}: only {valid}/{NBOOT} bootstrap draws valid")
    all_details[g]={"n_survivors":len(group_ids),"bootstrap_valid":valid,"bootstrap_target":NBOOT}

    for w in WEEKS:
        a=np.array(bs_ref[w])
        mainrow=next(r for r in main_rows if r["group"]==g and r["week"]==w)
        mainrow.update({
            "bootstrap_pc1_alignment_median":float(np.median(a)),
            "bootstrap_pc1_alignment_q10":float(np.quantile(a,.1)),
            "bootstrap_pc1_alignment_q90":float(np.quantile(a,.9)),
            "bootstrap_pc1_percent_q025":float(np.quantile(bs_pct[w],.025)),
            "bootstrap_pc1_percent_q975":float(np.quantile(bs_pct[w],.975)),
        })
    for w1,w2 in PAIRS:
        bs=np.array(bs_sim[(w1,w2)])
        out=next(r for r in pair_rows if r["group"]==g and r["week_from"]==w1 and r["week_to"]==w2)
        out.update({
            "paired_bootstrap_valid":valid,
            "bootstrap_abs_cosine_median":float(np.median(bs)),
            "bootstrap_abs_cosine_q025":float(np.quantile(bs,.025)),
            "bootstrap_abs_cosine_q975":float(np.quantile(bs,.975)),
            "bootstrap_fraction_similarity_ge_0_8":float(np.mean(bs>=.8)),
        })
        boot_rows.append({"group":g,"week_from":w1,"week_to":w2,
                          "bootstrap_abs_cosine_values":";".join(f"{v:.5f}" for v in bs)})

    # Matched complete-case sensitivity: exactly the same animals at every week.
    complete_ids=sorted(set.intersection(*[set(lookup[w]) for w in WEEKS]))
    assert len(complete_ids)>=5
    matched={}
    for w in WEEKS:
        X=np.vstack([lookup[w][i] for i in complete_ids])
        matched[w]=fit_pc1(X)
    matching_rows.append({"group":g,"total_week24_survivors":len(group_ids),
                          "n_with_all_three_cleaned_visits":len(complete_ids),
                          "mouse_ids_all_three":"; ".join(complete_ids)})
    for w1,w2 in PAIRS:
        s=similarity(matched[w1]["vec"],matched[w2]["vec"])
        matched_pair_rows.append({"group":g,"week_from":w1,"week_to":w2,
                                  "n_same_mice":len(complete_ids),
                                  "matched_pc1_absolute_cosine":s,
                                  "matched_principal_angle_degrees":float(np.degrees(np.arccos(s))),
                                  "matched_pc1_pct_from":matched[w1]["pc1_pct"],
                                  "matched_pc1_pct_to":matched[w2]["pc1_pct"]})

main=pd.DataFrame(main_rows)
pairs=pd.DataFrame(pair_rows)
match=pd.DataFrame(matched_pair_rows)
main.to_csv(OUT/"pc1_explained_variance_and_stability.csv",index=False)
pairs.to_csv(OUT/"pc1_loading_similarity_by_group_weeks.csv",index=False)
pd.DataFrame(loading_rows).to_csv(OUT/"pc1_loadings_all_features.csv",index=False)
pd.DataFrame(top_rows).to_csv(OUT/"pc1_top10_features_each_group_week.csv",index=False)
pd.DataFrame(matching_rows).to_csv(OUT/"matched_complete_case_counts.csv",index=False)
match.to_csv(OUT/"matched_complete_case_pc1_similarity.csv",index=False)

table=pairs.pivot(index="group",columns=["week_from","week_to"],values="pc1_absolute_cosine").reindex(GROUPS)
table.columns=[f"{a}_vs_{b}" for a,b in table.columns]
table.to_csv(OUT/"pc1_absolute_cosine_table.csv")

summary={
    "source":"Cleaned 31-feature processed matrix, 7 extreme mouse-week states excluded",
    "survivor_definition":"Presence of living week-24 row in PRE-exclusion processed living matrix",
    "n_survivors":42,"features":31,"groups":GROUPS,"weeks":WEEKS,
    "pca":"Separate sklearn PCA in each group-week; within-cell centering only, no extra scaling",
    "similarity":"Absolute cosine of unit-norm PC1 component vectors; 1=same direction ignoring sign; 0=orthogonal",
    "bootstrap":"1000 mouse-level paired bootstrap samples within group, reusing mouse IDs across weeks; describe percentile distribution, not definitive CI",
    "bootstrap_details":all_details,
    "group_week":main.to_dict(orient="records"),
    "pair_similarity":pairs.to_dict(orient="records"),
    "matched_complete_case":match.to_dict(orient="records"),
}
(OUT/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
lines=[
    "# PC1 loading similarity across weeks in end-surviving mice","",
    "Each group×week PCA was fit independently on 31 baseline-standardized processed variables,",
    "without restandardization; PC1 loadings are sklearn PCA unit eigenvector coefficients.","",
    "Similarity is absolute cosine (sign-invariant); its arccos gives principal angle in degrees.","",
    "## Similarity table","",
    table.round(3).to_markdown(),"",
    "## Paired-bootstrap diagnostics","",
]
for _,r in pairs.iterrows():
    lines.append(f"- {r['group']} {int(r.week_from)}→{int(r.week_to)}: cos={r.pc1_absolute_cosine:.3f}, angle={r.pc1_principal_angle_degrees:.1f}°, bootstrap median={r.bootstrap_abs_cosine_median:.3f}, q2.5–q97.5={r.bootstrap_abs_cosine_q025:.3f}–{r.bootstrap_abs_cosine_q975:.3f}.")
lines+=["","## Interpretation caveats","",
        "Independent PCA at each week can change direction. High PC1% does not itself show persistent PC1 loadings.",
        "Very small n relative to 31 features makes each PC1 loading vector noisy.",
        "Bootstrap distributions are descriptive and may be unstable with this sample size.",
        "Matched complete-case sensitivity recomputes every weekly PCA on exactly the same survivor mice with all 3 retained visits; see CSV.",
        "Only animals alive at week 24 enter the analysis. This conditions on survival and is not a population-wide aging estimate."]
(OUT/"REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
print(table.round(4).to_string())
print("\nGroup-week PC1 and bootstrap alignment:\n",main[["group","week","n","pc1_percent","bootstrap_pc1_alignment_median"]].round(3).to_string(index=False))
print("\nMatched complete cases:\n",match[["group","week_from","week_to","n_same_mice","matched_pc1_absolute_cosine"]].round(3).to_string(index=False))
