"""Stress tests for the C4/C5 result on the ATM-premise outcome (all run after the frozen evaluation; labelled as such)."""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evaluate as ev  # noqa: E402
import build_attributes as ba  # noqa: E402
p4 = ev.p4
R7 = ev.HERE.parent.parent / "restart7_0/results/phase3/data"
ENV = json.loads((R7 / "feature_schema.json").read_text())["environment_predictors"]


def offence_outcomes(attrs):
    """Re-link ATM-premise incidents split by offence family (person-targeted vs fraud)."""
    parts = []
    off = {"nyc_historic": "ofns_desc", "nyc_current_ytd": "ofns_desc", "chicago": "primary_type"}
    for source, (lat, lon, date, city) in ba.CRIME.items():
        if source not in off:
            continue
        rows = []
        for f in sorted(glob.glob(str(ba.RAW8 / f"crime/{source}/atm_rows/page_*[0-9].json"))):
            rows += json.load(open(f))
        x = pd.DataFrame(rows)
        parts.append(pd.DataFrame({"city": city, "case": x[ba.ID_FIELD[source]].astype(str), "off": x[off[source]].str.upper(),
            "lat": pd.to_numeric(x[lat], errors="coerce"), "lon": pd.to_numeric(x[lon], errors="coerce"),
            "year": pd.to_numeric(x[date].str[:4], errors="coerce")}))
    c = pd.concat(parts).dropna().drop_duplicates(["city", "case", "year"])
    fraud = c.off.str.contains("FRAUD|FORGERY|DECEPTIVE|IDENTITY")
    c["family"] = np.where(fraud, "fraud", "theft_robbery_other")
    for fam in ("fraud", "theft_robbery_other"):
        col = f"atm_{fam}_any_100m"
        attrs[col] = 0
        for (city, year), g in attrs[attrs.city.isin(["New York City", "Chicago"])].groupby(["city", "outcome_year"]):
            tr = Transformer.from_crs(4326, ba.EPSG[city], always_xy=True)
            cc = c[(c.city == city) & (c.year == year) & (c.family == fam)]
            t = cKDTree(np.c_[tr.transform(cc.lon.values, cc.lat.values)])
            gx, gy = tr.transform(g.longitude.values, g.latitude.values)
            attrs.loc[g.index, col] = [int(len(v) > 0) for v in t.query_ball_point(np.c_[gx, gy], 100)]
    return attrs


def compare(frame, label, base_cols, add_cols, name):
    frame = frame.sort_values("row_id").reset_index(drop=True)
    sc = ev.scenario(frame, label)
    plans = p4.plans_for(sc)
    if not all(p["usable"] for p in plans):
        return {"check": name, "status": "infeasible"}
    y = sc["y"]
    x = frame[base_cols + add_cols].astype(float).values
    b, a = list(range(len(base_cols))), list(range(len(base_cols) + len(add_cols)))
    pb, pa = np.full(len(y), np.nan), np.full(len(y), np.nan)
    for plan in plans:
        pb[plan["test"]] = ev.fit_predict(x, y, plan, b)
        pa[plan["test"]] = ev.fit_predict(x, y, plan, a)
    test = np.flatnonzero(frame.outcome_year.values == 2025)
    rows, yt = [sc["meta"][i] for i in test], y[test]
    w = p4.bootstrap_weights(rows, "spatial_block_2km")
    w = w[(w @ yt > 0) & (w @ (1 - yt) > 0)]
    d = p4.weighted_ap(yt, pa[test], w) - p4.weighted_ap(yt, pb[test], w)
    return {"check": name, "n_test": len(yt), "positives": int(yt.sum()),
            "ap_base": average_precision_score(yt, pb[test]), "ap_with": average_precision_score(yt, pa[test]),
            "ap_gain": average_precision_score(yt, pa[test]) - average_precision_score(yt, pb[test]),
            "ci_low": np.quantile(d, .025), "ci_high": np.quantile(d, .975),
            "auc_base": roc_auc_score(yt, pb[test]), "auc_with": roc_auc_score(yt, pa[test]),
            "brier_base": brier_score_loss(yt, pb[test]), "brier_with": brier_score_loss(yt, pa[test])}


def main():
    attrs = pd.read_csv(HERE / "attributes.csv", dtype={"acs_geoid_2022": str, "sld_geoid_2019": str})
    env = pd.read_csv(R7 / "features_primary_core_2024_2025.csv")[["row_id"] + ENV]
    attrs = attrs.merge(env, on="row_id")
    attrs["log1p_prior_atm_premise_100m"] = np.log1p(attrs.prior_atm_premise_count_100m)
    attrs["log1p_prior_atm_premise_50m"] = np.log1p(attrs.prior_atm_premise_count_50m)
    attrs = offence_outcomes(attrs)
    nc = attrs[attrs.city.isin(["New York City", "Chicago"])]
    B = ev.BASELINE
    PRIOR = ["log1p_prior_atm_premise_100m"]
    checks = [
        (nc, "atm_premise_any_100m", B, ["log_branch_deposits"], "R0 replicate C4"),
        (nc, "atm_premise_any_100m", B + PRIOR, [], "R1a prior ATM-premise crime alone added to baseline"),
        (nc, "atm_premise_any_100m", B + PRIOR, ["log_branch_deposits"], "R1 C4 over baseline + prior ATM-premise crime"),
        (nc, "atm_premise_any_100m", B + PRIOR, ["fdic_branch_50m"], "R1 C5 over baseline + prior ATM-premise crime"),
        (nc, "atm_premise_any_100m", B + ENV, ["log_branch_deposits"], "R2 C4 over baseline + 19 environmental"),
        (nc, "atm_premise_any_100m", B + PRIOR + ENV, ["log_branch_deposits"], "R2b C4 over baseline + prior ATM crime + 19 env"),
        (nc, "atm_premise_any_100m", B + ["fdic_branch_50m"], ["log_branch_deposits"], "R3 deposits beyond branch presence"),
        (nc[nc.fdic_branch_50m == 1], "atm_premise_any_100m", B, ["log_branch_deposits"], "R3b deposits among branch-co-located sites only"),
        (nc, "atm_theft_robbery_other_any_100m", B, ["log_branch_deposits"], "R4a C4 on theft/robbery/other ATM crime"),
        (nc, "atm_fraud_any_100m", B, ["log_branch_deposits"], "R4b C4 on fraud/forgery ATM crime"),
        (nc, "atm_premise_any_50m", B, ["log_branch_deposits"], "R5 C4 with 50 m ATM-premise outcome"),
        (nc, "recorded_any_50m", B, ["log_branch_deposits"], "R6 C4 on primary outcome, NYC+Chicago (falsification)"),
        (nc[nc.city == "New York City"], "atm_premise_any_100m", B, ["log_branch_deposits"], "R7 NYC only"),
        (nc[nc.city == "Chicago"], "atm_premise_any_100m", B, ["log_branch_deposits"], "R7 Chicago only"),
    ]
    # R8 winsorised deposits (HQ-booking outliers): cap at training-year 99th percentile per city.
    w = nc.copy()
    for city, g in w.groupby("city"):
        cap = np.nanquantile(g.loc[(g.outcome_year == 2024) & (g.fdic_branch_50m == 1), "log_branch_deposits"], .95)
        w.loc[g.index, "log_dep_w"] = np.minimum(g.log_branch_deposits, cap)
    checks.append((w, "atm_premise_any_100m", B, ["log_dep_w"], "R8 deposits winsorised at 95th pct"))
    results = []
    for frame, label, base, add, name in checks:
        r = compare(frame.copy(), label, base, add, name)
        results.append(r)
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    pd.DataFrame(results).to_csv(HERE / "robustness.csv", index=False)
    # Dose-response (descriptive): ATM-premise rate by deposit quintile, both years, NYC+Chicago.
    nc = nc.copy()
    nc["deposit_group"] = "no branch within 50 m"
    br = nc.fdic_branch_50m == 1
    nc.loc[br, "deposit_group"] = pd.qcut(nc.loc[br, "log_branch_deposits"], 5, labels=[f"Q{i} deposits" for i in range(1, 6)]).astype(str)
    dose = nc.groupby("deposit_group").agg(site_years=("row_id", "size"), atm_premise_rate=("atm_premise_any_100m", "mean"),
        robbery_burglary_50m_rate=("recorded_any_50m", "mean"), median_deposits_musd=("log_branch_deposits", lambda s: np.expm1(s.median()) / 1000),
        prior_local_crime_mean=("log1p_prior_local_50m_retrospective", "mean"))
    dose.to_csv(HERE / "dose_response.csv")
    print(dose.round(3).to_string())
    # Ascertainment check: fraction of ATM-premise incidents with no mapped site within 100 m.
    print("standalone vs branch ATM-premise rates:", nc.groupby(["city", "standalone_atm"]).atm_premise_any_100m.mean().round(3).to_dict())


if __name__ == "__main__":
    main()
