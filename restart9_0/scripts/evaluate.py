"""Restart 9 frozen evaluation (protocol.md): D1 NYC→Chicago/LA, D2 NYC+Chicago→Chicago, D3 pooled.

Learners: L2 logistic (R7 pipeline) and LightGBM, both tuned by inner purged spatial CV on AP.
Outputs in results/: metrics.csv, contrasts.csv, predictions.csv, importance.csv, tuning.csv.
"""
import itertools
import json
import sys
import warnings
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

R9 = Path(__file__).resolve().parents[1]
PROJECT = R9.parent
sys.path.insert(0, str(PROJECT / "restart7_0/phase4"))
import run as p4  # noqa: E402  R7 hashfold, distances, purge, class_ok, logistic, weighted_ap, bootstrap_weights

OUT = R9 / "results"
R7 = PROJECT / "restart7_0/results/phase3/data"
BASE = ["log1p_prior_local_50m_retrospective", "log1p_prior_annulus_200_500m_retrospective"]
A = ["log1p_bars_250m", "log1p_dist_bar_m", "log1p_liquor_250m", "log1p_dist_liquor_m", "log1p_light_outage_311_100m",
     "log1p_night_poi_250m", "log1p_poi_24_7_250m", "log1p_dist_rail_m", "log1p_dist_police_m", "log1p_dist_highway_m",
     "hours_known", "open_weekend", "open_late", "atm_mapped_age_years", "fdic_branch_age_years"]
LIC = ["log1p_lic_on_250m", "log1p_dist_lic_on_m", "log1p_lic_off_250m", "log1p_dist_lic_off_m"]
SETS = {"M0": BASE, "M9": BASE + A, "M9F": BASE + A + ["log_branch_deposits", "fdic_branch_50m"]}  # M9L withdrawn (amendment A2)
OUTCOMES = {"O1": "recorded_any_50m", "O2": "atm_premise_any_100m"}
GRID = [dict(num_leaves=nl, min_child_samples=mc, n_estimators=ne) for nl, mc, ne in itertools.product((4, 8, 16), (20, 40), (100, 300))]
NYC, CHI, LA = "New York City", "Chicago", "Los Angeles"


def lgbm(params):
    return lgb.LGBMClassifier(objective="binary", learning_rate=0.03, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
                              reg_lambda=1.0, random_state=9, n_jobs=1, deterministic=True, force_row_wise=True, verbose=-1, **params)


def inner_plan(fitting, meta, y, dist):
    folds = []
    for k in range(3):
        val = fitting[[p4.hashfold(meta[i]["spatial_block_2km"], True) == k for i in fitting]]
        pool = fitting[[p4.hashfold(meta[i]["spatial_block_2km"], True) != k for i in fitting]]
        fit = p4.purge(pool, val, dist, meta)
        folds.append({"train": fit, "validation": val, "usable": bool(p4.class_ok(y[fit], 30, 5) and p4.class_ok(y[val], 10, 1))})
    return folds


def fit_predict(learner, x, y, train, test, inner, tuning_log, tag):
    configs = [{"C": c} for c in p4.CS] if learner == "LR" else GRID
    make = (lambda c: p4.logistic(c["C"])) if learner == "LR" else lgbm
    scores = []
    for cfg in configs:
        vals = []
        for f in inner:
            if f["usable"]:
                m = make(cfg)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m.fit(x[f["train"]], y[f["train"]])
                vals.append(average_precision_score(y[f["validation"]], m.predict_proba(x[f["validation"]])[:, 1]))
        scores.append(float(np.mean(vals)))
        tuning_log.append({**tag, "learner": learner, "config": json.dumps(cfg), "inner_mean_ap": scores[-1], "inner_folds": len(vals)})
    best = configs[int(np.argmax(scores))]
    m = make(best)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m.fit(x[train], y[train])
    return m, m.predict_proba(x[test])[:, 1]


def load():
    lookup = pd.read_csv(R7 / "site_lookup_and_quality.csv", dtype=str)
    feats = pd.read_csv(R9 / "results/features_r9.csv").drop(columns=["city", "outcome_year"])
    o1 = pd.read_csv(R7 / "outcomes.csv", usecols=["row_id", "recorded_any_50m"])
    o2 = pd.read_csv(PROJECT / "restart8_0/attribute_search/attributes.csv", usecols=["row_id", "atm_premise_any_100m"])
    d = feats.merge(lookup, on="row_id").merge(o1, on="row_id").merge(o2, on="row_id", how="left")
    d["outcome_year"] = d.outcome_year.astype(int)
    d = d.sort_values("row_id").reset_index(drop=True)
    meta = [{k: ("" if pd.isna(v) else v) for k, v in r.items()} for r in d[["row_id", "city", "longitude", "latitude", "outcome_year",
            "spatial_block_2km", *p4.GROUP_FIELDS]].to_dict("records")]
    return d, meta


def designs(d):
    """Yield (design, target, outer folds as list of (train_idx_candidates, test_idx))."""
    idx = np.arange(len(d))
    yr, city = d.outcome_year.values, d.city.values
    nyc24 = idx[(city == NYC) & (yr == 2024)]
    for target in (CHI, LA):
        yield "D1", target, [(nyc24, idx[(city == target) & (yr == 2025)], False)]
    chi25 = idx[(city == CHI) & (yr == 2025)]
    folds = [(np.r_[nyc24, idx[(city == CHI) & (yr == 2024)]], chi25[[p4.hashfold(d.spatial_block_2km[i]) == f for i in chi25]], True)
             for f in range(5)]
    yield "D2", CHI, folds
    test = idx[yr == 2025]
    yield "D3", "ALL", [(idx[yr == 2024], test[[p4.hashfold(d.spatial_block_2km[i]) == f for i in test]], True) for f in range(5)]


def main():
    d, meta = load()
    dist = p4.distances(meta)
    preds, metrics, contrasts, tuning, importance = [], [], [], [], []
    for (design, target, folds), (oname, label) in itertools.product(list(designs(d)), OUTCOMES.items()):
        if oname == "O2" and target == LA:
            continue  # LA excluded from O2 (R8: coordinates rounded to ~1 km)
        rows = d[label].notna().to_numpy().copy()
        if oname == "O2":
            rows &= d.city.isin([NYC, CHI]).values
        y = d[label].fillna(0).astype(int).values
        sets = {k: v for k, v in SETS.items() if not (k == "M9L" and (target in (LA, "ALL")))}
        out = {}
        for k, cols in sets.items():
            x = d[cols].astype(float).values
            for learner in ("LR", "LGBM"):
                p = np.full(len(d), np.nan)
                for f, (cand, test, purge) in enumerate(folds):
                    cand, test = cand[rows[cand]], test[rows[test]]
                    train = p4.purge(cand, test, dist, meta) if purge else cand
                    if not p4.class_ok(y[train], 50, 10):
                        raise RuntimeError(f"infeasible {design} {oname} fold {f}")
                    tag = {"design": design, "target": target, "outcome": oname, "set": k, "fold": f}
                    m, p[test] = fit_predict(learner, x, y, train, test, inner_plan(train, meta, y, dist), tuning, tag)
                    if design == "D1" and oname == "O1" and k == "M9":
                        pi = permutation_importance(m, x[test], y[test], scoring="average_precision", n_repeats=20, random_state=9)
                        for c, mu, sd in zip(cols, pi.importances_mean, pi.importances_std):
                            importance.append({"design": design, "target": target, "learner": learner, "feature": c,
                                               "perm_ap_drop_mean": mu, "perm_ap_drop_sd": sd})
                        if learner == "LGBM":
                            shap = m.booster_.predict(x[test], pred_contrib=True)[:, :-1]
                            for c, v in zip(cols, np.abs(shap).mean(axis=0)):
                                importance.append({"design": design, "target": target, "learner": "LGBM_SHAP", "feature": c,
                                                   "mean_abs_shap": v})
                out[f"{learner}-{k}"] = p
        test_all = np.flatnonzero(~np.isnan(out["LR-M0"]))
        yt = y[test_all]
        w = p4.bootstrap_weights([meta[i] for i in test_all], "spatial_block_2km")
        w = w[(w @ yt > 0) & (w @ (1 - yt) > 0)]
        boot = {m: p4.weighted_ap(yt, p[test_all], w) for m, p in out.items()}
        for m, p in out.items():
            pt = p[test_all]
            top = np.argsort(-pt, kind="stable")[: max(1, len(pt) // 10)]
            metrics.append({"design": design, "target": target, "outcome": oname, "model": m, "n": len(yt), "positives": int(yt.sum()),
                            "ap": average_precision_score(yt, pt), "roc_auc": roc_auc_score(yt, pt), "brier": brier_score_loss(yt, pt),
                            "top_decile_precision": yt[top].mean()})
            for ref in ("LR-M0", "LGBM-M0"):
                if m == ref or (ref == "LGBM-M0" and not m.startswith("LGBM")):
                    continue
                diff = boot[m] - boot[ref]
                contrasts.append({"design": design, "target": target, "outcome": oname, "model": m, "vs": ref,
                                  "ap_gain": average_precision_score(yt, pt) - average_precision_score(yt, out[ref][test_all]),
                                  "ci95_low": np.quantile(diff, .025), "ci95_high": np.quantile(diff, .975),
                                  "bonf_low": np.quantile(diff, .0125), "bonf_high": np.quantile(diff, .9875),
                                  "brier_diff": brier_score_loss(yt, pt) - brier_score_loss(yt, out[ref][test_all]),
                                  "valid_resamples": len(w)})
        preds.append(pd.DataFrame({"design": design, "target": target, "outcome": oname, "row_id": d.row_id.values[test_all],
                                   "city": d.city.values[test_all], "observed": yt} | {m: p[test_all] for m, p in out.items()}))
        print("done", design, target, oname, flush=True)
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(metrics).to_csv(OUT / "metrics.csv", index=False)
    c = pd.DataFrame(contrasts)
    prim = (c.design == "D1") & (c.target == CHI) & (c.outcome == "O1") & (c.vs == "LR-M0") & c.model.isin(["LR-M9", "LGBM-M9"])
    c["primary"] = prim
    c["passes_rule"] = (c.ap_gain >= 0.01) & (np.where(prim, c.bonf_low, c.ci95_low) > 0) & (c.brier_diff <= 0)
    c.to_csv(OUT / "contrasts.csv", index=False)
    pd.concat(preds).to_csv(OUT / "predictions.csv", index=False)
    pd.DataFrame(importance).to_csv(OUT / "importance.csv", index=False)
    pd.DataFrame(tuning).to_csv(OUT / "tuning.csv", index=False)
    status = {"primary_success": bool(c[prim].passes_rule.any()),
              "primary": c[prim][["model", "ap_gain", "bonf_low", "bonf_high", "brier_diff", "passes_rule"]].to_dict("records"),
              "packages": {"lightgbm": lgb.__version__, "numpy": np.__version__, "pandas": pd.__version__}}
    (OUT / "status.json").write_text(json.dumps(status, indent=2, default=float))
    pd.set_option("display.width", 220)
    print(c.round(4).to_string())


if __name__ == "__main__":
    main()
