"""Exploratory (amendment A3): LightGBM attribute weightage and NYC -> Chicago 2025 prediction.

Step 1: train on NYC 2024 only (same fit as frozen D1 LGBM-M9), report weightage, predict Chicago 2025.
Step 2: train on NYC 2024 + a random 10% of Chicago 2024 site-years, predict Chicago 2025.
        Chicago 2025 is split into the five R7 2 km spatial folds; for each fold the 10% sample is drawn
        only from Chicago 2024 sites >=1,500 m from (and sharing no geography group with) that fold's
        test sites. Repeated for 20 random seeds.
Baselines on identical data: logistic M0 and LightGBM M0 (past crime only).
Outputs: results/weightage/*.csv and summary.md.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate as ev  # noqa: E402
from evaluate import p4  # noqa: E402

OUT = ev.R9 / "results/weightage"
LABEL = "recorded_any_50m"
COLS = ev.SETS["M9"]
SEEDS = range(20)
FRACTION = 0.10
NICE = {
    "log1p_prior_local_50m_retrospective": "Past crime within 50 m (previous year)",
    "log1p_prior_annulus_200_500m_retrospective": "Past crime 200-500 m (previous year)",
    "log1p_bars_250m": "Bars within 250 m", "log1p_dist_bar_m": "Distance to nearest bar",
    "log1p_liquor_250m": "Liquor stores within 250 m", "log1p_dist_liquor_m": "Distance to nearest liquor store",
    "log1p_light_outage_311_100m": "Streetlight outages within 100 m (311)",
    "log1p_night_poi_250m": "Late-night places within 250 m", "log1p_poi_24_7_250m": "24/7 places within 250 m",
    "log1p_dist_rail_m": "Distance to rail/subway station", "log1p_dist_police_m": "Distance to police station",
    "log1p_dist_highway_m": "Distance to highway", "hours_known": "Branch hours listed",
    "open_weekend": "Open at weekends", "open_late": "Open late", "atm_mapped_age_years": "ATM age (years mapped)",
    "fdic_branch_age_years": "Bank-branch age",
}


def fit(learner, cols, d, meta, dist, y, train, test):
    x = d[cols].astype(float).values
    m, p = ev.fit_predict(learner, x, y, train, test, ev.inner_plan(train, meta, y, dist), [], {})
    return m, p, x


def weightage(model, x_rows):
    gain = model.booster_.feature_importance("gain")
    split = model.booster_.feature_importance("split")
    shap = model.booster_.predict(x_rows, pred_contrib=True)[:, :-1]
    direction = [np.corrcoef(x_rows[:, j], shap[:, j])[0, 1] if np.nanstd(x_rows[:, j]) > 0 and shap[:, j].std() > 0 else np.nan
                 for j in range(x_rows.shape[1])]
    return pd.DataFrame({"feature": COLS, "gain": gain, "split": split, "mean_abs_shap": np.abs(shap).mean(axis=0),
                         "direction_corr": direction})


def as_percent(w):
    w = w.copy()
    for c in ("gain", "split", "mean_abs_shap"):
        w[c + "_pct"] = 100 * w[c] / w[c].sum() if w[c].sum() > 0 else 0.0
    w["attribute"] = w.feature.map(NICE)
    w["effect"] = np.where(w.direction_corr > 0.1, "higher value -> more risk",
                           np.where(w.direction_corr < -0.1, "higher value -> less risk", "mixed / none"))
    return w.sort_values("gain_pct", ascending=False)


def scores(yt, p):
    return {"ap": average_precision_score(yt, p), "roc_auc": roc_auc_score(yt, p), "brier": brier_score_loss(yt, p)}


def paired_ci(yt, rows, a, b):
    w = p4.bootstrap_weights(rows, "spatial_block_2km")
    w = w[(w @ yt > 0) & (w @ (1 - yt) > 0)]
    diff = p4.weighted_ap(yt, a, w) - p4.weighted_ap(yt, b, w)
    return np.quantile(diff, .025), np.quantile(diff, .975)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, meta = ev.load()
    dist = p4.distances(meta)
    y = d[LABEL].astype(int).values
    idx = np.arange(len(d))
    city, yr = d.city.values, d.outcome_year.values
    nyc24, chi24, chi25 = (idx[(city == c) & (yr == t)] for c, t in ((ev.NYC, 2024), (ev.CHI, 2024), (ev.CHI, 2025)))
    yt = y[chi25]
    rows = [meta[i] for i in chi25]
    results, lines = [], []

    # Step 1 — NYC only
    m9, p9, x9 = fit("LGBM", COLS, d, meta, dist, y, nyc24, chi25)
    _, p0, _ = fit("LGBM", ev.BASE, d, meta, dist, y, nyc24, chi25)
    _, pl, _ = fit("LR", ev.BASE, d, meta, dist, y, nyc24, chi25)
    w1 = as_percent(weightage(m9, x9[nyc24]))
    w1_test = as_percent(weightage(m9, x9[chi25]))[["feature", "mean_abs_shap_pct"]].rename(columns={"mean_abs_shap_pct": "shap_pct_on_chicago_2025"})
    w1 = w1.merge(w1_test, on="feature")
    w1.to_csv(OUT / "step1_weightage_nyc_only.csv", index=False, float_format="%.4f")
    step1 = {"LightGBM + attributes": p9, "LightGBM past crime only": p0, "Logistic past crime only (baseline)": pl}
    for k, p in step1.items():
        results.append({"step": "1 NYC only", "model": k, "seed": "", **scores(yt, p)})
    pd.DataFrame({"row_id": d.row_id.values[chi25], "observed": yt} | step1).to_csv(OUT / "step1_predictions_chicago_2025.csv", index=False)
    ci1 = paired_ci(yt, rows, p9, pl)

    # Step 2 — NYC + 10% Chicago 2024, 20 seeds x 5 spatial folds
    n_sample = int(round(FRACTION * len(chi24)))
    w2, seed_preds = [], {k: [] for k in step1}
    fold_of = np.array([p4.hashfold(d.spatial_block_2km[i]) for i in chi25])
    pool_sizes = []
    for seed in SEEDS:
        rng = np.random.default_rng(9000 + seed)
        preds = {k: np.full(len(chi25), np.nan) for k in step1}
        for f in range(5):
            test = chi25[fold_of == f]
            pool = p4.purge(chi24, test, dist, meta)
            pool_sizes.append(len(pool))
            sample = rng.choice(pool, size=min(n_sample, len(pool)), replace=False)
            train = np.r_[nyc24, sample]
            m, p, x = fit("LGBM", COLS, d, meta, dist, y, train, test)
            preds["LightGBM + attributes"][fold_of == f] = p
            w2.append(weightage(m, x[train]).assign(seed=seed, fold=f))
            preds["LightGBM past crime only"][fold_of == f] = fit("LGBM", ev.BASE, d, meta, dist, y, train, test)[1]
            preds["Logistic past crime only (baseline)"][fold_of == f] = fit("LR", ev.BASE, d, meta, dist, y, train, test)[1]
        for k, p in preds.items():
            results.append({"step": "2 NYC + 10% Chicago 2024", "model": k, "seed": seed, **scores(yt, p)})
            seed_preds[k].append(p)
        print("seed", seed, "done", flush=True)
    w2 = pd.concat(w2)
    w2.to_csv(OUT / "step2_weightage_by_seed_fold.csv", index=False, float_format="%.4f")
    w2pct = w2.groupby(["seed", "fold"], group_keys=False).apply(as_percent)
    w2sum = w2pct.groupby("feature").agg(gain_pct=("gain_pct", "mean"), gain_pct_sd=("gain_pct", "std"), split_pct=("split_pct", "mean"),
                                         mean_abs_shap_pct=("mean_abs_shap_pct", "mean"), direction_corr=("direction_corr", "mean")).reset_index()
    w2sum = as_percent(w2sum.rename(columns={"gain_pct": "gain", "split_pct": "split", "mean_abs_shap_pct": "mean_abs_shap"}))
    w2sum = w2sum.merge(w2pct.groupby("feature").gain_pct.std().rename("gain_pct_sd_across_models"), on="feature")
    w2sum.to_csv(OUT / "step2_weightage_nyc_plus_10pct_chicago.csv", index=False, float_format="%.4f")
    res = pd.DataFrame(results)
    res.to_csv(OUT / "results_by_seed.csv", index=False, float_format="%.4f")
    avg = {k: np.mean(v, axis=0) for k, v in seed_preds.items()}
    ci2 = paired_ci(yt, rows, avg["LightGBM + attributes"], avg["Logistic past crime only (baseline)"])
    s2 = res[res.step.str.startswith("2")]
    gains = (s2[s2.model == "LightGBM + attributes"].set_index("seed").ap - s2[s2.model.str.startswith("Logistic")].set_index("seed").ap)

    lines += ["# LightGBM weightage and NYC → Chicago 2025 prediction (exploratory, amendment A3)", "",
              f"Outcome: any robbery/burglary within 50 m in 2025. Chicago test: {len(chi25)} ATMs, {int(yt.sum())} with crime "
              f"({yt.mean():.0%}). AP = average precision (random guessing ≈ {yt.mean():.2f}).", "",
              "## Step 1 — trained on NYC 2024 only", "", "| model | AP | ROC-AUC | Brier |", "|---|---|---|---|"]
    for r in res[res.step.str.startswith("1")].itertuples():
        lines.append(f"| {r.model} | {r.ap:.3f} | {r.roc_auc:.3f} | {r.brier:.3f} |")
    lines += ["", f"LightGBM + attributes vs baseline: {res.ap[0] - res.ap[2]:+.3f} AP (95% CI {ci1[0]:+.3f} to {ci1[1]:+.3f}).", "",
              "## Step 2 — trained on NYC 2024 + 10% of Chicago 2024", "",
              f"{n_sample} Chicago 2024 site-years per draw (10% of {len(chi24)}), 20 random draws, 5 spatial folds. "
              f"Eligible Chicago pool per fold after the 1,500 m purge: {min(pool_sizes)}–{max(pool_sizes)} site-years.", "",
              "| model | mean AP | AP range over 20 draws | mean ROC-AUC | mean Brier |", "|---|---|---|---|---|"]
    for k, g in s2.groupby("model", sort=False):
        lines.append(f"| {k} | {g.ap.mean():.3f} | {g.ap.min():.3f}–{g.ap.max():.3f} | {g.roc_auc.mean():.3f} | {g.brier.mean():.3f} |")
    lines += ["", f"LightGBM + attributes vs baseline: mean {gains.mean():+.3f} AP; better in {(gains > 0).sum()} of 20 draws; "
              f"95% CI of the draw-averaged gain {ci2[0]:+.3f} to {ci2[1]:+.3f}.", "",
              "## Weightage (% of LightGBM total gain)", "", "| attribute | Step 1 NYC only | Step 2 NYC + 10% Chicago | effect direction (Step 1) |",
              "|---|---|---|---|"]
    m = w1.merge(w2sum[["feature", "gain_pct"]].rename(columns={"gain_pct": "g2"}), on="feature")
    for r in m.itertuples():
        lines.append(f"| {r.attribute} | {r.gain_pct:.1f}% | {r.g2:.1f}% | {r.effect} |")
    (OUT / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
