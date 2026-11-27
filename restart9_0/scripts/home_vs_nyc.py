"""Exploratory (amendment A7): Chicago-trained vs NYC-trained models on the same Restart 7 Chicago test set.

Re-runs the teammate's Chicago XGBoost method (draft/xgboost_model, restart6_0/analysis/chicago_xgboost/pipeline.py:
same estimator, 8-config grid, 4-fold StratifiedGroupKFold with 1 km + census-area purge, training-only column
exclusions, seed 17) on the corrected Restart 7 core cohort and labels. Logistic regression (Restart 9 pipeline)
is run alongside.

Test: Chicago 2025 core (212 ATMs, recorded robbery/burglary within 50 m).
Training sources:
  chicago        Chicago 2024, all rows (the teammate's design: the same ATMs can recur in the test year)
  chicago_purged Chicago 2024, purged per test fold (5 x 2 km folds; >=1,500 m and no shared object/census group);
                 XGBoost hyperparameters fixed from the unpurged 2024 tuning
  nyc            NYC 2024 (no Chicago data)
Feature sets: CRIME (R7 baseline), E19 (A6), E107 (R7 cleaned expanded environment = the teammate's 116 minus
duplicates and metro constants), CRIME+E19, CRIME+E107.
Outputs: results/home_vs_nyc/.
"""
import importlib.util
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_density as ed  # noqa: E402
import env_only as eo  # noqa: E402
import evaluate as ev  # noqa: E402
from evaluate import p4  # noqa: E402

spec = importlib.util.spec_from_file_location("team", ev.PROJECT / "restart6_0/analysis/chicago_xgboost/pipeline.py")
team = importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)

OUT = ev.R9 / "results/home_vs_nyc"
R7 = ev.PROJECT / "restart7_0/results/phase3/data"
E107 = __import__("json").loads((R7 / "feature_schema.json").read_text())["expanded_environment_predictors"]
E19 = eo.COLS + ed.NEW
SETS = {"CRIME": ev.BASE, "E19": E19, "E107": E107, "CRIME+E19": ev.BASE + E19, "CRIME+E107": ev.BASE + E107}
EPSG = {ev.NYC: 32618, ev.CHI: 32616, ev.LA: 32611}


def prepare():
    d, meta = ev.load()
    d = ed.add_factors(d)
    e = pd.read_csv(R7 / "features_expanded_environment_core_2024_2025.csv").set_index("row_id")
    for c in E107:
        if c not in d:
            d[c] = d.row_id.map(e[c]).values
    xs, ys = np.zeros(len(d)), np.zeros(len(d))
    for c, code in EPSG.items():
        m = d.city.values == c
        xs[m], ys[m] = Transformer.from_crs(4326, code, always_xy=True).transform(d.longitude[m].astype(float), d.latitude[m].astype(float))
    d["x_m"], d["y_m"] = xs, ys
    d["spatial_block"] = team.blocks(d, 2000)
    return d, meta


def xgb_team(d, y, train, test, cols, fixed=None):
    """Teammate method: tune on `train` with their spatial folds (unless fixed), fit, predict `test`."""
    tr = d.iloc[train].reset_index(drop=True)
    yt = y[train]
    if fixed is None:
        folds, _ = team.spatial_folds(tr, yt)
        params, _, _, _, _ = team.tune(tr, cols, yt, folds, 4)
    else:
        params = fixed
    kept, _ = team.training_columns(tr, cols)
    m = team.estimator(params, 17, 4)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m.fit(tr[kept], yt)
    return m.predict_proba(d.iloc[test][kept])[:, 1], params


def lr(d, meta, dist, y, train, test, cols):
    x = d[cols].astype(float).values
    return ev.fit_predict("LR", x, y, train, test, ev.inner_plan(train, meta, y, dist), [], {})[1]


def ci(yt, rows, p, q=None):
    w = p4.bootstrap_weights(rows, "spatial_block_2km")
    w = w[(w @ yt > 0) & (w @ (1 - yt) > 0)]
    ap = p4.weighted_ap(yt, p, w)
    auc = np.array([roc_auc_score(yt, p, sample_weight=wi) for wi in w])
    if q is None:
        return np.quantile(ap, [.025, .975]), np.quantile(auc, [.025, .975])
    ap_q = p4.weighted_ap(yt, q, w)
    auc_q = np.array([roc_auc_score(yt, q, sample_weight=wi) for wi in w])
    return np.quantile(ap - ap_q, [.025, .975]), np.quantile(auc - auc_q, [.025, .975])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, meta = prepare()
    dist = p4.distances(meta)
    y = d[eo.LABEL].astype(int).values
    idx = np.arange(len(d))
    city, yr = d.city.values, d.outcome_year.values
    nyc24, chi24, chi25 = (idx[(city == c) & (yr == t)] for c, t in ((ev.NYC, 2024), (ev.CHI, 2024), (ev.CHI, 2025)))
    yt, rows = y[chi25], [meta[i] for i in chi25]
    fold_of = np.array([p4.hashfold(d.spatial_block_2km[i]) for i in chi25])
    recurring = np.isin(d.object_group_id.values[chi25], d.object_group_id.values[chi24])
    preds, chosen = {}, []
    for sname, cols in SETS.items():
        # XGBoost (teammate method)
        preds[("XGBoost", "chicago", sname)], params = xgb_team(d, y, chi24, chi25, cols)
        chosen.append({"set": sname, "source": "chicago", **params})
        p = np.full(len(chi25), np.nan)
        for f in range(5):
            te = chi25[fold_of == f]
            p[fold_of == f] = xgb_team(d, y, p4.purge(chi24, te, dist, meta), te, cols, fixed=params)[0]
        preds[("XGBoost", "chicago_purged", sname)] = p
        preds[("XGBoost", "nyc", sname)], params = xgb_team(d, y, nyc24, chi25, cols)
        chosen.append({"set": sname, "source": "nyc", **params})
        # Logistic regression (Restart 9 pipeline)
        preds[("Logistic", "chicago", sname)] = lr(d, meta, dist, y, chi24, chi25, cols)
        p = np.full(len(chi25), np.nan)
        for f in range(5):
            te = chi25[fold_of == f]
            p[fold_of == f] = lr(d, meta, dist, y, p4.purge(chi24, te, dist, meta), te, cols)
        preds[("Logistic", "chicago_purged", sname)] = p
        preds[("Logistic", "nyc", sname)] = lr(d, meta, dist, y, nyc24, chi25, cols)
        print(sname, "done", flush=True)

    res, diffs = [], []
    for (learner, source, sname), p in preds.items():
        (al, ah), (ul, uh) = ci(yt, rows, p)
        res.append({"learner": learner, "training": source, "set": sname, "ap": average_precision_score(yt, p), "ap_lo": al, "ap_hi": ah,
                    "roc_auc": roc_auc_score(yt, p), "auc_lo": ul, "auc_hi": uh, "brier": brier_score_loss(yt, p),
                    "auc_recurring_sites": roc_auc_score(yt[recurring], p[recurring]),
                    "auc_new_sites": roc_auc_score(yt[~recurring], p[~recurring]) if len(set(yt[~recurring])) == 2 else np.nan})
        if source != "nyc":
            q = preds[(learner, "nyc", sname)]
            (dl, dh), (el, eh) = ci(yt, rows, p, q)
            diffs.append({"learner": learner, "home_training": source, "set": sname,
                          "ap_home_minus_nyc": average_precision_score(yt, p) - average_precision_score(yt, q), "ap_lo": dl, "ap_hi": dh,
                          "auc_home_minus_nyc": roc_auc_score(yt, p) - roc_auc_score(yt, q), "auc_lo": el, "auc_hi": eh})
    r, df = pd.DataFrame(res), pd.DataFrame(diffs)
    r.to_csv(OUT / "results.csv", index=False, float_format="%.4f")
    df.to_csv(OUT / "home_minus_nyc.csv", index=False, float_format="%.4f")
    pd.DataFrame(chosen).to_csv(OUT / "xgboost_selected_parameters.csv", index=False)
    pd.DataFrame({"row_id": d.row_id.values[chi25], "observed": yt, "recurring_site": recurring} |
                 {"|".join(k): v for k, v in preds.items()}).to_csv(OUT / "predictions.csv", index=False, float_format="%.5f")

    lab = {"chicago": "Chicago 2024", "chicago_purged": "Chicago 2024, purged", "nyc": "NYC 2024"}
    L = ["# Chicago-trained vs NYC-trained, same Chicago 2025 test (exploratory, amendment A7)", "",
         f"Test: Restart 7 core Chicago 2025, {len(yt)} ATMs, {int(yt.sum())} with robbery/burglary within 50 m (chance AP {yt.mean():.3f}, "
         f"AUC 0.500). {recurring.sum()} of {len(yt)} test ATMs also appear in Chicago 2024 training. XGBoost uses the teammate's "
         "draft/xgboost_model method; logistic uses the Restart 9 pipeline. CRIME = prior-year crime within 50 m and 200–500 m.", ""]
    for learner in ("XGBoost", "Logistic"):
        L += [f"## {learner}", "", "| features | trained on | AUC [95% CI] | AP [95% CI] |", "|---|---|---|---|"]
        for sname in SETS:
            for source in ("chicago", "chicago_purged", "nyc"):
                x = r[(r.learner == learner) & (r.training == source) & (r.set == sname)].iloc[0]
                L.append(f"| {sname} | {lab[source]} | {x.roc_auc:.3f} [{x.auc_lo:.3f}, {x.auc_hi:.3f}] | {x.ap:.3f} [{x.ap_lo:.3f}, {x.ap_hi:.3f}] |")
        L.append("")
    L += ["## Home advantage: Chicago-trained minus NYC-trained (paired, 2 km block bootstrap)", "",
          "| learner | Chicago training | features | AUC difference [95% CI] | AP difference [95% CI] |", "|---|---|---|---|---|"]
    for x in df.itertuples():
        L.append(f"| {x.learner} | {lab[x.home_training]} | {x.set} | {x.auc_home_minus_nyc:+.3f} [{x.auc_lo:+.3f}, {x.auc_hi:+.3f}] | "
                 f"{x.ap_home_minus_nyc:+.3f} [{x.ap_lo:+.3f}, {x.ap_hi:+.3f}] |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
