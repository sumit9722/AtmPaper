"""Per-year / per-city adjusted odds ratios for deposits on ATM-premise crime (cluster-robust by 2 km block)."""
import warnings
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm

HERE = Path(__file__).resolve().parent
a = pd.read_csv(HERE / "attributes.csv")
a = a[a.city.isin(["New York City", "Chicago"])].copy()
a["log1p_prior_atm_premise_100m"] = np.log1p(a.prior_atm_premise_count_100m)
B = ["log1p_prior_local_50m_retrospective", "log1p_prior_annulus_200_500m_retrospective"]
rows = []
for label in ("atm_premise_any_100m", "recorded_any_50m"):
    for base_name, base in (("baseline", B), ("baseline+prior_atm_crime", B + ["log1p_prior_atm_premise_100m"])):
        for scope in ("pooled", "New York City", "Chicago"):
            for year in (2024, 2025):
                t = a[(a.outcome_year == year) & ((a.city == scope) | (scope == "pooled"))]
                X = t[base].copy()
                X["deposits_sd"] = (t.log_branch_deposits - a.log_branch_deposits.mean()) / a.log_branch_deposits.std()
                if scope == "pooled":
                    X["chicago"] = (t.city == "Chicago").astype(float)
                X = sm.add_constant(X.astype(float))
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    r = sm.Logit(t[label].values, X).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(t.spatial_block_2km)[0]})
                lo, hi = r.conf_int().loc["deposits_sd"]
                rows.append({"outcome": label, "adjustment": base_name, "scope": scope, "year": year, "n": len(t), "events": int(t[label].sum()),
                             "OR_per_SD": np.exp(r.params["deposits_sd"]), "ci_low": np.exp(lo), "ci_high": np.exp(hi), "p": r.pvalues["deposits_sd"]})
out = pd.DataFrame(rows)
out.to_csv(HERE / "effect_sizes.csv", index=False)
pd.set_option("display.width", 200)
print(out.round(4).to_string())
