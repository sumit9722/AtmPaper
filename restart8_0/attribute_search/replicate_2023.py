"""Third-year replication on the separate R7 partial-2023 supplement (NYC + Chicago, point-geometry rows; all rows share 313 supported days)."""
import sys, warnings
from pathlib import Path
import numpy as np, pandas as pd, statsmodels.api as sm
from pyproj import Transformer
from scipy.spatial import cKDTree
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_attributes as ba

P = ba.PROJECT / "restart7_0"
d = pd.read_csv(P / "data/processed/atm_panel_partial_2023.csv", usecols=["row_id", "city", "longitude", "latitude", "osm_geometry_is_centroid"])
d = d.merge(pd.read_csv(P / "results/phase3/data/features_baseline_partial_2023.csv"), on="row_id")
d = d[d.city.isin(["New York City", "Chicago"]) & (d.osm_geometry_is_centroid.astype(str) == "False")].copy()
fdic, crime = ba.load_fdic(), ba.load_atm_crime()
parts = []
for city, g in d.groupby("city"):
    g = g.copy(); tr = Transformer.from_crs(4326, ba.EPSG[city], always_xy=True)
    gx, gy = tr.transform(g.longitude.values, g.latitude.values)
    f = fdic[(fdic.YEAR.astype(int) == 2022) & (fdic.SIMS_LATITUDE.astype(float) != 0)]
    dist, idx = cKDTree(np.column_stack(tr.transform(f.SIMS_LONGITUDE.astype(float).values, f.SIMS_LATITUDE.astype(float).values))).query(np.c_[gx, gy])
    g["log_branch_deposits"] = np.where(dist <= 50, np.log1p(f.DEPSUMBR.values[idx]), 0.0)
    for name, yr in (("y", 2023), ("prior", 2022)):
        c = crime[(crime.city == city) & (crime.year == yr)]
        t = cKDTree(np.column_stack(tr.transform(c.lon.values, c.lat.values)))
        g[name] = [len(v) for v in t.query_ball_point(np.c_[gx, gy], 100)]
    parts.append(g)
d = pd.concat(parts)
d["y"] = (d.y > 0).astype(int)
d["block"] = [f"{c}:{int(x//0.02)}:{int(y//0.02)}" for c, x, y in zip(d.city, d.longitude, d.latitude)]
ref = pd.read_csv(HERE / "attributes.csv"); ref = ref[ref.city.isin(["New York City", "Chicago"])]
m, s = ref.log_branch_deposits.mean(), ref.log_branch_deposits.std()   # same SD scale as effect_sizes.py
for adj in ("baseline", "baseline+prior_atm_crime"):
    X = d[["log1p_prior_local_50m_retrospective", "log1p_prior_annulus_200_500m_retrospective"]].copy()
    if adj != "baseline": X["log1p_prior_atm"] = np.log1p(d.prior)
    X["chicago"] = (d.city == "Chicago").astype(float)
    X["deposits_sd"] = (d.log_branch_deposits - m) / s
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = sm.Logit(d.y.values, sm.add_constant(X.astype(float))).fit(disp=0, cov_type="cluster", cov_kwds={"groups": pd.factorize(d.block)[0]})
    lo, hi = np.exp(r.conf_int().loc["deposits_sd"])
    print(f"2023 partial, {adj}: n={len(d)} events={d.y.sum()} OR/SD={np.exp(r.params['deposits_sd']):.3f} [{lo:.3f}, {hi:.3f}] p={r.pvalues['deposits_sd']:.2g}")
