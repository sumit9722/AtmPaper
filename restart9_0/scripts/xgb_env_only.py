"""Exploratory (amendment A5): XGBoost on the environment-only design of env_only.py (A4).

Same 15 attributes (no past crime), same steps, same 20 Chicago draws, same inner spatial CV.
XGBoost: learning_rate 0.03, subsample 0.8, colsample_bytree 0.8, reg_lambda 1, hist trees, seed 9;
grid max_depth {2,3,4} x min_child_weight {1,5} x n_estimators {100,300}, chosen by inner AP.
Outputs: results/env_only/xgboost/ and an all-learner comparison in summary.md.
"""
import itertools
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import average_precision_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_only as eo  # noqa: E402
import evaluate as ev  # noqa: E402
import transfer_weights as tw  # noqa: E402
from evaluate import p4  # noqa: E402

OUT = ev.R9 / "results/env_only/xgboost"
COLS = eo.COLS
GRID = [dict(max_depth=a, min_child_weight=b, n_estimators=c) for a, b, c in itertools.product((2, 3, 4), (1, 5), (100, 300))]


def model(cfg):
    return xgb.XGBClassifier(learning_rate=0.03, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, tree_method="hist",
                             random_state=9, n_jobs=1, eval_metric="logloss", **cfg)


def fit(x, y, train, test, inner, log, tag):
    scores = []
    for cfg in GRID:
        vals = []
        for f in inner:
            if f["usable"]:
                m = model(cfg)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m.fit(x[f["train"]], y[f["train"]])
                vals.append(average_precision_score(y[f["validation"]], m.predict_proba(x[f["validation"]])[:, 1]))
        scores.append(float(np.mean(vals)))
        log.append({**tag, "config": json.dumps(cfg), "inner_mean_ap": scores[-1]})
    m = model(GRID[int(np.argmax(scores))])
    m.fit(x[train], y[train])
    return m, m.predict_proba(x[test])[:, 1]


def weightage(m, xr):
    b = m.get_booster()
    gain, split = b.get_score(importance_type="total_gain"), b.get_score(importance_type="weight")
    shap = b.predict(xgb.DMatrix(xr), pred_contribs=True)[:, :-1]
    direction = [np.corrcoef(xr[:, j], shap[:, j])[0, 1] if np.nanstd(xr[:, j]) > 0 and shap[:, j].std() > 0 else np.nan
                 for j in range(xr.shape[1])]
    return pd.DataFrame({"feature": COLS, "gain": [gain.get(f"f{j}", 0.0) for j in range(len(COLS))],
                         "split": [split.get(f"f{j}", 0.0) for j in range(len(COLS))],
                         "mean_abs_shap": np.abs(shap).mean(axis=0), "direction_corr": direction})


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, meta = ev.load()
    dist = p4.distances(meta)
    y = d[eo.LABEL].astype(int).values
    x = d[COLS].astype(float).values
    idx = np.arange(len(d))
    city, yr = d.city.values, d.outcome_year.values
    nyc24, chi24 = (idx[(city == c) & (yr == 2024)] for c in (ev.NYC, ev.CHI))
    tests = {"Chicago": idx[(city == ev.CHI) & (yr == 2025)], "Los Angeles": idx[(city == ev.LA) & (yr == 2025)]}
    res, preds, log = [], [], []

    allt = np.r_[tests["Chicago"], tests["Los Angeles"]]
    m, p = fit(x, y, nyc24, allt, ev.inner_plan(nyc24, meta, y, dist), log, {"step": 1})
    p = pd.Series(p, index=allt)
    for tgt, te in tests.items():
        res.append(eo.row("1 NYC only", tgt, "XGB", y[te], p[te].values, [meta[i] for i in te]))
        preds.append(pd.DataFrame({"step": "1 NYC only", "target": tgt, "model": "XGB", "row_id": d.row_id.values[te],
                                   "observed": y[te], "score": p[te].values}))
    w1 = tw.as_percent(weightage(m, x[nyc24]))
    w1.to_csv(OUT / "step1_weightage_nyc_only.csv", index=False, float_format="%.4f")
    print("step 1 done", flush=True)

    chi25 = tests["Chicago"]
    fold_of = np.array([p4.hashfold(d.spatial_block_2km[i]) for i in chi25])
    n_sample = int(round(tw.FRACTION * len(chi24)))
    w2, draws = [], []
    for seed in tw.SEEDS:
        rng = np.random.default_rng(9000 + seed)  # identical draws to A3/A4
        sp = np.full(len(chi25), np.nan)
        for f in range(5):
            test = chi25[fold_of == f]
            pool = p4.purge(chi24, test, dist, meta)
            sample = rng.choice(pool, size=min(n_sample, len(pool)), replace=False)
            train = np.r_[nyc24, sample]
            m, sp[fold_of == f] = fit(x, y, train, test, ev.inner_plan(train, meta, y, dist), log, {"step": 2, "seed": seed, "fold": f})
            w2.append(weightage(m, x[train]).assign(seed=seed, fold=f))
        res.append(eo.row("2 NYC + 10% Chicago 2024", "Chicago", "XGB", y[chi25], sp, seed=seed))
        draws.append(sp)
        print("seed", seed, "done", flush=True)
    pavg = np.mean(draws, axis=0)
    res.append(eo.row("2 NYC + 10% Chicago 2024 (draw-averaged)", "Chicago", "XGB", y[chi25], pavg, [meta[i] for i in chi25]))
    preds.append(pd.DataFrame({"step": "2 draw-averaged", "target": "Chicago", "model": "XGB", "row_id": d.row_id.values[chi25],
                               "observed": y[chi25], "score": pavg}))
    w2pct = pd.concat(w2).groupby(["seed", "fold"], group_keys=False).apply(tw.as_percent)
    w2sum = tw.as_percent(w2pct.groupby("feature").agg(gain=("gain_pct", "mean"), split=("split_pct", "mean"),
                          mean_abs_shap=("mean_abs_shap_pct", "mean"), direction_corr=("direction_corr", "mean")).reset_index())
    w2sum.to_csv(OUT / "step2_weightage_nyc_plus_10pct_chicago.csv", index=False, float_format="%.4f")
    r = pd.DataFrame(res)
    r.to_csv(OUT / "results.csv", index=False, float_format="%.4f")
    pd.concat(preds).to_csv(OUT / "predictions.csv", index=False, float_format="%.5f")
    pd.DataFrame(log).to_csv(OUT / "tuning.csv", index=False)

    allr = pd.concat([pd.read_csv(OUT.parent / "results.csv"), r])
    allr = allr[allr.ap_lo.notna()]
    name = {"LGBM": "LightGBM", "LR": "Logistic", "XGB": "XGBoost"}
    L = ["# XGBoost, environment only (no past crime) — exploratory, amendment A5", "",
         "Same features, designs and Chicago draws as A4. Chance: AUC 0.50; AP 0.410 (Chicago), 0.330 (LA).", "",
         "| training | test city | model | AUC [95% CI] | AP [95% CI] | top-10% hit rate |", "|---|---|---|---|---|---|"]
    for x_ in allr.sort_values(["step", "target", "model"]).itertuples():
        L.append(f"| {x_.step} | {x_.target} | {name[x_.model]} | {x_.roc_auc:.3f} [{x_.auc_lo:.3f}, {x_.auc_hi:.3f}] | "
                 f"{x_.ap:.3f} [{x_.ap_lo:.3f}, {x_.ap_hi:.3f}] | {x_.top10_hit_rate:.0%} |")
    s2 = r[r.step == "2 NYC + 10% Chicago 2024"]
    L += ["", f"XGBoost per-draw spread (20 draws): AUC {s2.roc_auc.mean():.3f} (range {s2.roc_auc.min():.3f}–{s2.roc_auc.max():.3f}), "
          f"AP {s2.ap.mean():.3f} (range {s2.ap.min():.3f}–{s2.ap.max():.3f}).", "",
          "## XGBoost weightage (% of total gain)", "", "| attribute | Step 1 NYC only | Step 2 NYC + 10% Chicago | direction (Step 1) |",
          "|---|---|---|---|"]
    mm = w1.merge(w2sum[["feature", "gain_pct"]].rename(columns={"gain_pct": "g2"}), on="feature")
    for x_ in mm.itertuples():
        L.append(f"| {x_.attribute} | {x_.gain_pct:.1f}% | {x_.g2:.1f}% | {x_.effect} |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
