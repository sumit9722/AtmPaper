"""Exploratory (amendment A4): environment-only models, no past-crime inputs.

Features: the 15 Restart 9 situational attributes only (A1-A15). No prior-crime counts.
Step 1: train NYC 2024 -> predict Chicago 2025 and LA 2025.
Step 2: train NYC 2024 + random 10% of Chicago 2024 -> predict Chicago 2025
        (5 spatial folds, 1,500 m + geography purge, 20 seeds), as in transfer_weights.py.
Learners: LightGBM and logistic regression, tuned exactly as in evaluate.py.
Reference = chance (AUC 0.5; AP = share of test ATMs with crime). 95% intervals: 2 km block bootstrap.
Outputs: results/env_only/.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate as ev  # noqa: E402
import transfer_weights as tw  # noqa: E402
from evaluate import p4  # noqa: E402

OUT = ev.R9 / "results/env_only"
COLS = list(ev.A)
tw.COLS = COLS  # weightage() labels features from tw.COLS
LABEL = "recorded_any_50m"


def boot_ci(yt, p, rows):
    w = p4.bootstrap_weights(rows, "spatial_block_2km")
    w = w[(w @ yt > 0) & (w @ (1 - yt) > 0)]
    aps = p4.weighted_ap(yt, p, w)
    aucs = np.array([roc_auc_score(yt, p, sample_weight=wi) for wi in w])
    return np.quantile(aps, [.025, .975]), np.quantile(aucs, [.025, .975])


def row(step, target, model, yt, p, rows=None, seed=""):
    top = np.argsort(-p, kind="stable")[: max(1, len(p) // 10)]
    r = {"step": step, "target": target, "model": model, "seed": seed, "n": len(yt), "positives": int(yt.sum()),
         "chance_ap": yt.mean(), "ap": average_precision_score(yt, p), "roc_auc": roc_auc_score(yt, p),
         "brier": brier_score_loss(yt, p), "top10_hit_rate": yt[top].mean()}
    if rows is not None:
        (r["ap_lo"], r["ap_hi"]), (r["auc_lo"], r["auc_hi"]) = boot_ci(yt, p, rows)
    return r


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, meta = ev.load()
    dist = p4.distances(meta)
    y = d[LABEL].astype(int).values
    idx = np.arange(len(d))
    city, yr = d.city.values, d.outcome_year.values
    nyc24, chi24 = (idx[(city == c) & (yr == 2024)] for c in (ev.NYC, ev.CHI))
    tests = {"Chicago": idx[(city == ev.CHI) & (yr == 2025)], "Los Angeles": idx[(city == ev.LA) & (yr == 2025)]}
    res, preds = [], []

    # Step 1 — NYC only (one model per learner, applied to both target cities)
    allt = np.r_[tests["Chicago"], tests["Los Angeles"]]
    for learner in ("LGBM", "LR"):
        m, p, x = tw.fit(learner, COLS, d, meta, dist, y, nyc24, allt)
        p = pd.Series(p, index=allt)
        for tgt, te in tests.items():
            res.append(row("1 NYC only", tgt, learner, y[te], p[te].values, [meta[i] for i in te]))
            preds.append(pd.DataFrame({"step": "1 NYC only", "target": tgt, "model": learner, "row_id": d.row_id.values[te],
                                       "observed": y[te], "score": p[te].values}))
        if learner == "LGBM":
            w1 = tw.as_percent(tw.weightage(m, x[nyc24]))
            w1c = tw.as_percent(tw.weightage(m, x[tests["Chicago"]]))[["feature", "mean_abs_shap_pct"]]
            w1 = w1.merge(w1c.rename(columns={"mean_abs_shap_pct": "shap_pct_on_chicago_2025"}), on="feature")
            w1.to_csv(OUT / "step1_weightage_nyc_only.csv", index=False, float_format="%.4f")
    print("step 1 done", flush=True)

    # Step 2 — NYC + 10% Chicago 2024
    chi25 = tests["Chicago"]
    fold_of = np.array([p4.hashfold(d.spatial_block_2km[i]) for i in chi25])
    n_sample = int(round(tw.FRACTION * len(chi24)))
    w2, avg = [], {"LGBM": [], "LR": []}
    for seed in tw.SEEDS:
        rng = np.random.default_rng(9000 + seed)  # same draws as transfer_weights.py
        sp = {k: np.full(len(chi25), np.nan) for k in avg}
        for f in range(5):
            test = chi25[fold_of == f]
            pool = p4.purge(chi24, test, dist, meta)
            sample = rng.choice(pool, size=min(n_sample, len(pool)), replace=False)
            train = np.r_[nyc24, sample]
            m, p, x = tw.fit("LGBM", COLS, d, meta, dist, y, train, test)
            sp["LGBM"][fold_of == f] = p
            w2.append(tw.weightage(m, x[train]).assign(seed=seed, fold=f))
            sp["LR"][fold_of == f] = tw.fit("LR", COLS, d, meta, dist, y, train, test)[1]
        for k, p in sp.items():
            res.append(row("2 NYC + 10% Chicago 2024", "Chicago", k, y[chi25], p, seed=seed))
            avg[k].append(p)
        print("seed", seed, "done", flush=True)
    rows = [meta[i] for i in chi25]
    for k, v in avg.items():
        p = np.mean(v, axis=0)
        res.append(row("2 NYC + 10% Chicago 2024 (draw-averaged)", "Chicago", k, y[chi25], p, rows))
        preds.append(pd.DataFrame({"step": "2 draw-averaged", "target": "Chicago", "model": k, "row_id": d.row_id.values[chi25],
                                   "observed": y[chi25], "score": p}))
    w2 = pd.concat(w2)
    w2pct = w2.groupby(["seed", "fold"], group_keys=False).apply(tw.as_percent)
    w2sum = w2pct.groupby("feature").agg(gain=("gain_pct", "mean"), split=("split_pct", "mean"),
                                         mean_abs_shap=("mean_abs_shap_pct", "mean"), direction_corr=("direction_corr", "mean")).reset_index()
    w2sum = tw.as_percent(w2sum)
    w2sum.to_csv(OUT / "step2_weightage_nyc_plus_10pct_chicago.csv", index=False, float_format="%.4f")

    r = pd.DataFrame(res)
    r.to_csv(OUT / "results.csv", index=False, float_format="%.4f")
    pd.concat(preds).to_csv(OUT / "predictions.csv", index=False, float_format="%.5f")
    seeds = r[r.step == "2 NYC + 10% Chicago 2024"]

    L = ["# Environment-only prediction (no past-crime inputs) — exploratory, amendment A4", "",
         "Features: the 15 Restart 9 situational attributes only. Outcome: any robbery/burglary within 50 m in 2025. "
         "Reference is chance: AUC 0.50 and AP equal to the share of test ATMs with crime.", "",
         "| training | test city | model | AP [95% CI] | chance AP | ROC-AUC [95% CI] | top-10% hit rate |", "|---|---|---|---|---|---|---|"]
    name = {"LGBM": "LightGBM", "LR": "Logistic"}
    for x in r[r.ap_lo.notna()].itertuples():
        L.append(f"| {x.step} | {x.target} | {name[x.model]} | {x.ap:.3f} [{x.ap_lo:.3f}, {x.ap_hi:.3f}] | {x.chance_ap:.3f} | "
                 f"{x.roc_auc:.3f} [{x.auc_lo:.3f}, {x.auc_hi:.3f}] | {x.top10_hit_rate:.0%} |")
    L += ["", "Step 2 per-draw spread (20 draws of 19 Chicago 2024 site-years):", ""]
    for k, g in seeds.groupby("model"):
        L.append(f"* {name[k]}: AP {g.ap.mean():.3f} (range {g.ap.min():.3f}–{g.ap.max():.3f}), "
                 f"AUC {g.roc_auc.mean():.3f} (range {g.roc_auc.min():.3f}–{g.roc_auc.max():.3f})")
    L += ["", "## LightGBM weightage (% of total gain)", "", "| attribute | Step 1 NYC only | Step 2 NYC + 10% Chicago | direction (Step 1) |",
          "|---|---|---|---|"]
    mm = w1.merge(w2sum[["feature", "gain_pct"]].rename(columns={"gain_pct": "g2"}), on="feature")
    for x in mm.itertuples():
        L.append(f"| {x.attribute} | {x.gain_pct:.1f}% | {x.g2:.1f}% | {x.effect} |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
