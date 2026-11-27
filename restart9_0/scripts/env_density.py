"""Exploratory (amendment A6): add population density, housing density and public transport to the
environment-only models (no past crime). Same designs, Chicago draws and tuning as A4/A5.

New factors (block-group context, already in the Restart 7 matrices; no new downloads):
  log1p_population_density      ACS 2022 population per km^2 (R7 primary)
  log1p_housing_density         log1p(EPA SLD D1A, housing units per acre)
  log1p_transit_service_density EPA SLD transit service frequency per area (R7 primary)
  log1p_transit_stop_distance   log1p(EPA SLD D4A distance from block group to nearest transit stop, m)
Feature sets: E19 = 15 R9 attributes + 4 new; E4 = the 4 new factors only.
Outputs: results/env_only/density_transit/.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_only as eo  # noqa: E402
import evaluate as ev  # noqa: E402
import transfer_weights as tw  # noqa: E402
import xgb_env_only as xe  # noqa: E402
from evaluate import p4  # noqa: E402

OUT = ev.R9 / "results/env_only/density_transit"
R7 = ev.PROJECT / "restart7_0/results/phase3/data"
NEW = ["log1p_population_density", "log1p_housing_density", "log1p_transit_service_density", "log1p_transit_stop_distance"]
SETS = {"E19": eo.COLS + NEW, "E4": NEW}
tw.NICE.update({"log1p_population_density": "Population density", "log1p_housing_density": "Housing density",
                "log1p_transit_service_density": "Transit service frequency", "log1p_transit_stop_distance": "Distance to transit stop"})
NAME = {"LR": "Logistic", "LGBM": "LightGBM", "XGB": "XGBoost"}


def add_factors(d):
    p = pd.read_csv(R7 / "features_primary_core_2024_2025.csv", usecols=["row_id", "log1p_population_density", "log1p_transit_service_density"])
    e = pd.read_csv(R7 / "features_expanded_environment_core_2024_2025.csv", usecols=["row_id", "sld_D1A", "transit_centroid_distance"])
    x = p.merge(e, on="row_id").set_index("row_id")
    x["log1p_housing_density"] = np.log1p(x.sld_D1A)
    x["log1p_transit_stop_distance"] = np.log1p(x.transit_centroid_distance)
    for c in NEW:
        d[c] = d.row_id.map(x[c]).values
    return d


def fit(learner, cols, d, meta, dist, y, train, test):
    if learner == "XGB":
        xe.COLS = cols
        x = d[cols].astype(float).values
        m, p = xe.fit(x, y, train, test, ev.inner_plan(train, meta, y, dist), [], {})
        return m, p, x
    return tw.fit(learner, cols, d, meta, dist, y, train, test)


def weights(learner, m, xr):
    return xe.weightage(m, xr) if learner == "XGB" else tw.weightage(m, xr)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d, meta = ev.load()
    d = add_factors(d)
    dist = p4.distances(meta)
    y = d[eo.LABEL].astype(int).values
    idx = np.arange(len(d))
    city, yr = d.city.values, d.outcome_year.values
    nyc24, chi24 = (idx[(city == c) & (yr == 2024)] for c in (ev.NYC, ev.CHI))
    tests = {"Chicago": idx[(city == ev.CHI) & (yr == 2025)], "Los Angeles": idx[(city == ev.LA) & (yr == 2025)]}
    chi25 = tests["Chicago"]
    fold_of = np.array([p4.hashfold(d.spatial_block_2km[i]) for i in chi25])
    n_sample = int(round(tw.FRACTION * len(chi24)))
    allt = np.r_[chi25, tests["Los Angeles"]]
    res, wt = [], []
    for sname, cols in SETS.items():
        tw.COLS = cols
        for learner in ("LR", "LGBM", "XGB"):
            m, p, x = fit(learner, cols, d, meta, dist, y, nyc24, allt)
            p = pd.Series(p, index=allt)
            for tgt, te in tests.items():
                res.append(eo.row("1 NYC only", tgt, learner, y[te], p[te].values, [meta[i] for i in te]) | {"set": sname})
            if learner != "LR" and sname == "E19":
                wt.append(tw.as_percent(weights(learner, m, x[nyc24])).assign(learner=learner, step="1 NYC only"))
            draws, w2 = [], []
            for seed in tw.SEEDS:
                rng = np.random.default_rng(9000 + seed)  # identical draws to A3-A5
                sp = np.full(len(chi25), np.nan)
                for f in range(5):
                    test = chi25[fold_of == f]
                    pool = p4.purge(chi24, test, dist, meta)
                    sample = rng.choice(pool, size=min(n_sample, len(pool)), replace=False)
                    train = np.r_[nyc24, sample]
                    m, sp[fold_of == f], x = fit(learner, cols, d, meta, dist, y, train, test)
                    if learner != "LR" and sname == "E19":
                        w2.append(tw.as_percent(weights(learner, m, x[train])))
                draws.append(sp)
            res.append(eo.row("2 NYC + 10% Chicago 2024 (draw-averaged)", "Chicago", learner, y[chi25], np.mean(draws, axis=0),
                              [meta[i] for i in chi25]) | {"set": sname})
            if w2:
                w2 = pd.concat(w2).groupby("feature")[["gain_pct", "direction_corr"]].mean().reset_index()
                wt.append(w2.assign(learner=learner, step="2 NYC + 10% Chicago", attribute=w2.feature.map(tw.NICE)))
            print(sname, learner, "done", flush=True)
    r = pd.DataFrame(res)
    r.to_csv(OUT / "results.csv", index=False, float_format="%.4f")
    w = pd.concat(wt)
    w.to_csv(OUT / "weightage.csv", index=False, float_format="%.4f")

    prev = pd.concat([pd.read_csv(ev.R9 / "results/env_only/results.csv"), pd.read_csv(ev.R9 / "results/env_only/xgboost/results.csv")])
    prev = prev[prev.ap_lo.notna()].assign(set="E15")
    allr = pd.concat([prev, r])
    L = ["# Environment only + population density, housing density, public transport — exploratory, amendment A6", "",
         "E15 = the 15 Restart 9 attributes (A4/A5). E19 = E15 + population density, housing density, transit service "
         "frequency, distance to transit stop. E4 = those 4 only. No past-crime inputs. Chance: AUC 0.50; AP 0.410 (Chicago), "
         "0.330 (LA).", ""]
    for step, tgt in (("1 NYC only", "Chicago"), ("2 NYC + 10% Chicago 2024 (draw-averaged)", "Chicago"), ("1 NYC only", "Los Angeles")):
        L += [f"## {step} → {tgt} 2025", "", "| model | E15 AUC | E19 AUC [95% CI] | E4 AUC [95% CI] | E19 AP | E4 AP | E19 top-10% |",
              "|---|---|---|---|---|---|---|"]
        for lr in ("LR", "LGBM", "XGB"):
            g = allr[(allr.step == step) & (allr.target == tgt) & (allr.model == lr)].set_index("set")
            a, b, c = g.loc["E15"], g.loc["E19"], g.loc["E4"]
            L.append(f"| {NAME[lr]} | {a.roc_auc:.3f} | {b.roc_auc:.3f} [{b.auc_lo:.3f}, {b.auc_hi:.3f}] | "
                     f"{c.roc_auc:.3f} [{c.auc_lo:.3f}, {c.auc_hi:.3f}] | {b.ap:.3f} | {c.ap:.3f} | {b.top10_hit_rate:.0%} |")
        L.append("")
    L += ["## Weightage with E19 (% of total gain, NYC only)", "", "| attribute | LightGBM | XGBoost | direction (LightGBM) |", "|---|---|---|---|"]
    s1 = w[w.step == "1 NYC only"]
    piv = s1.pivot_table(index="feature", columns="learner", values="gain_pct").sort_values("LGBM", ascending=False)
    eff = s1[s1.learner == "LGBM"].set_index("feature").effect
    for f, v in piv.iterrows():
        L.append(f"| {tw.NICE[f]} | {v.LGBM:.1f}% | {v.XGB:.1f}% | {eff[f]} |")
    (OUT / "summary.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
