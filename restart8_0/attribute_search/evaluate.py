"""Evaluate frozen candidates C1–C8 against R7 baseline M0 using the R7 Phase 4 machinery."""
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pyproj import Transformer
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "restart7_0/phase4"))
import run as p4  # noqa: E402  (reuses hashfold, distances, purge, class_ok, logistic, weighted_ap, bootstrap_weights)

BASELINE = ["log1p_prior_local_50m_retrospective", "log1p_prior_annulus_200_500m_retrospective"]
CANDIDATES = {"C1": "standalone_atm", "C2": "drive_through", "C3": "open_24_7", "C4": "log_branch_deposits",
              "C5": "fdic_branch_50m", "C6": "megabank", "C7": "log1p_atm_density_500m", "C8": "branch_age_years"}
OUTCOMES = {"primary_recorded_any_50m": ("recorded_any_50m", ("New York City", "Chicago", "Los Angeles")),
            "atm_premise_any_100m": ("atm_premise_any_100m", ("New York City", "Chicago"))}
EXTRA = dict(a.split("=") for a in sys.argv[1:])  # e.g. candidates=post_hoc.json tag=posthoc
TAG = EXTRA.get("tag", "frozen")
if "candidates" in EXTRA:
    CANDIDATES = json.loads(Path(EXTRA["candidates"]).read_text())


def scenario(frame, label):
    meta = []
    for r in frame.to_dict("records"):
        r = {k: ("" if (isinstance(v, float) and math.isnan(v)) else v) for k, v in r.items()}
        xx, yy = Transformer.from_crs(4326, {"New York City": 32618, "Chicago": 32616, "Los Angeles": 32611}[r["city"]],
                                      always_xy=True).transform(r["longitude"], r["latitude"])
        r["spatial_block_5km"] = f"{r['city']}:{math.floor(xx / 5000)}:{math.floor(yy / 5000)}"
        meta.append({k: (str(v) if k in p4.GROUP_FIELDS else v) for k, v in r.items()})
    return {"name": "attr_" + label, "meta": meta, "y": frame[label].astype(int).values}


def fit_predict(x, y, plan, cols):
    scores = []
    for c in p4.CS:
        vals = []
        for inner in plan["inner"]:
            if inner["usable"]:
                m = p4.logistic(c)
                p4.fit_checked(m, x[np.ix_(inner["train"], cols)], y[inner["train"]])
                vals.append(average_precision_score(y[inner["validation"]], m.predict_proba(x[np.ix_(inner["validation"], cols)])[:, 1]))
        scores.append(np.mean(vals))
    m = p4.logistic(p4.CS[int(np.argmax(scores))])
    p4.fit_checked(m, x[np.ix_(plan["train"], cols)], y[plan["train"]])
    return m.predict_proba(x[np.ix_(plan["test"], cols)])[:, 1]


def training_test(frame, label, feature):
    """2024-only logit, city FE + baseline, cluster-robust (2 km block) Wald test of the candidate."""
    t = frame[frame.outcome_year == 2024].copy()
    t[feature] = t[feature].fillna(t[feature].median())
    X = pd.concat([t[BASELINE + [feature]], pd.get_dummies(t.city, drop_first=True, dtype=float)], axis=1)
    sd = X[feature].std()
    X[feature] = (X[feature] - X[feature].mean()) / (sd if sd > 0 else 1)
    X = sm.add_constant(X.astype(float))
    groups = pd.factorize(t.spatial_block_2km)[0]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        res = sm.Logit(t[label].values, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": groups})
    return float(res.params[feature]), float(res.pvalues[feature])


def holm(p):
    order = np.argsort(p)
    adj = np.empty(len(p))
    running = 0
    for rank, i in enumerate(order):
        running = max(running, (len(p) - rank) * p[i])
        adj[i] = min(1, running)
    return adj


def main():
    attrs = pd.read_csv(HERE / "attributes.csv", dtype={"acs_geoid_2022": str, "sld_geoid_2019": str})
    summary, per_city = [], []
    for oname, (label, cities) in OUTCOMES.items():
        frame = attrs[attrs.city.isin(cities)].sort_values("row_id").reset_index(drop=True)
        sc = scenario(frame, label)
        plans = p4.plans_for(sc)
        assert all(p["usable"] for p in plans), "feasibility failed"
        y = sc["y"]
        feats = BASELINE + list(CANDIDATES.values())
        x = frame[feats].astype(float).values
        models = {"M0": [0, 1]} | {k: [0, 1, 2 + j] for j, k in enumerate(CANDIDATES)} | {"M_all": list(range(len(feats)))}
        preds = {m: np.full(len(y), np.nan) for m in models}
        for plan in plans:
            for m, cols in models.items():
                preds[m][plan["test"]] = fit_predict(x, y, plan, cols)
        test = np.flatnonzero(frame.outcome_year.values == 2025)
        rows = [sc["meta"][i] for i in test]
        yt = y[test]
        weights = p4.bootstrap_weights(rows, "spatial_block_2km")
        valid = (weights @ yt > 0) & (weights @ (1 - yt) > 0)
        w = weights[valid]
        base_boot = p4.weighted_ap(yt, preds["M0"][test], w)
        pvals = []
        for m in models:
            pt = preds[m][test]
            ap = average_precision_score(yt, pt)
            d = p4.weighted_ap(yt, pt, w) - base_boot
            coef, pv = training_test(frame, label, CANDIDATES[m]) if m in CANDIDATES else (np.nan, np.nan)
            pvals.append(pv)
            city_gain = {}
            for c in cities:
                mask = np.array([r["city"] == c for r in rows])
                g = average_precision_score(yt[mask], pt[mask]) - average_precision_score(yt[mask], preds["M0"][test][mask])
                city_gain[c] = g
                per_city.append({"outcome": oname, "model": m, "city": c, "n": int(mask.sum()), "positive": int(yt[mask].sum()),
                                 "ap": average_precision_score(yt[mask], pt[mask]), "ap_gain_vs_M0": g})
            summary.append({"outcome": oname, "model": m, "feature": CANDIDATES.get(m, "+".join(feats) if m == "M_all" else "baseline"),
                "n_test": len(yt), "prevalence": yt.mean(), "ap": ap, "roc_auc": roc_auc_score(yt, pt), "brier": brier_score_loss(yt, pt),
                "ap_gain": ap - average_precision_score(yt, preds["M0"][test]),
                "gain_ci_low": np.quantile(d, .025) if m != "M0" else np.nan, "gain_ci_high": np.quantile(d, .975) if m != "M0" else np.nan,
                "train_std_coef": coef, "train_p": pv,
                "cities_positive_gain": sum(v > 0 for v in city_gain.values()), "cities": len(cities)})
        s = [r for r in summary if r["outcome"] == oname]
        idx = [i for i, r in enumerate(s) if r["model"] in CANDIDATES]
        adj = holm(np.array([s[i]["train_p"] for i in idx]))
        b0 = next(r for r in s if r["model"] == "M0")["brier"]
        for i, a in zip(idx, adj):
            r = s[i]
            r["train_p_holm"] = a
            r["accept"] = bool(r["ap_gain"] > 0 and r["gain_ci_low"] > 0 and r["brier"] <= b0 and a < .05
                               and r["cities_positive_gain"] >= min(2, len(cities)))
        pd.DataFrame({"row_id": frame.row_id[test], "city": frame.city[test], "observed": yt} |
                     {m: preds[m][test] for m in models}).to_csv(HERE / f"predictions_{TAG}_{oname}.csv", index=False)
        print(f"done {oname}", flush=True)
    out = pd.DataFrame(summary)
    out.to_csv(HERE / f"results_{TAG}.csv", index=False)
    pd.DataFrame(per_city).to_csv(HERE / f"results_{TAG}_by_city.csv", index=False)
    pd.set_option("display.width", 250)
    print(out.drop(columns=["n_test"]).round(4).to_string())
    pc = pd.DataFrame(per_city)
    print(pc.pivot_table(index=["outcome", "model"], columns="city", values="ap_gain_vs_M0").round(4).to_string())


if __name__ == "__main__":
    main()
