"""Build Restart 9 attributes A1–A15 and licence features (protocol.md) for the R7 core cohort.

No outcome is read here. Output: results/features_r9.csv and results/feature_coverage.csv.
"""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import shapely
from pyproj import Transformer
from scipy.spatial import cKDTree

R9 = Path(__file__).resolve().parents[1]
PROJECT = R9.parent
RAW = R9 / "data/raw"
R7 = PROJECT / "restart7_0/results/phase3/data"
OSM_SITES = PROJECT / "restart6_0/data/raw/osm_v2"
R8 = PROJECT / "restart8_0/attribute_search/attributes.csv"
OUT = R9 / "results"
CITY_KEY = {"New York City": "nyc", "Chicago": "chicago", "Los Angeles": "la"}
EPSG = {"New York City": 32618, "Chicago": 32616, "Los Angeles": 32611}
CAP = 5000.0
DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
ATM = lambda t: t.get("amenity") == "atm" or (t.get("amenity") == "bank" and t.get("atm") == "yes")


def layer_xy(city, snap, name, tr):
    t = pq.read_table(RAW / f"osm/{CITY_KEY[city]}/{snap}_{name}.parquet").to_pandas()
    geoms = shapely.from_wkb(t.geom.values)
    if name == "highway":
        geoms = shapely.transform(geoms, lambda c: np.c_[tr.transform(c[:, 0], c[:, 1])])
        pts = shapely.get_coordinates(shapely.segmentize(geoms, 10.0))
        return pts, None
    cen = shapely.centroid(geoms)
    x, y = tr.transform(shapely.get_x(cen), shapely.get_y(cen))
    ids = (t.osm_type + "/" + t.osm_id.astype(str)).values
    return np.c_[x, y], ids


def count_and_dist(site_xy, pts, radius, exclude=None, site_ids=None):
    if len(pts) == 0:
        return np.zeros(len(site_xy)), np.full(len(site_xy), CAP)
    tree = cKDTree(pts)
    k = min(2, len(pts))
    d, i = tree.query(site_xy, k=k)
    d, i = np.atleast_2d(d.T).T, np.atleast_2d(i.T).T
    counts = np.array([len(v) for v in tree.query_ball_point(site_xy, radius)], dtype=float)
    nearest = d[:, 0].copy()
    if exclude is not None:  # drop the focal object itself
        for r, sid in enumerate(site_ids):
            hits = [j for j in tree.query_ball_point(site_xy[r], radius) if exclude[j] == sid]
            counts[r] -= len(hits)
            if exclude[i[r, 0]] == sid:
                nearest[r] = d[r, 1] if k > 1 else CAP
    return counts, np.minimum(nearest, CAP)


def day_set(spec):
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")[:2]
            if a in DAYS and b in DAYS:
                ia, ib = DAYS.index(a), DAYS.index(b)
                out |= set(DAYS[ia:ib + 1] if ia <= ib else DAYS[ia:] + DAYS[:ib + 1])
        elif part in DAYS:
            out.add(part)
    return out


def hours_features(tags):
    oh = str(tags.get("opening_hours", "")).strip()
    if not oh:
        return 0, 0, 0
    if oh.lower() in {"24/7", "mo-su 00:00-24:00"}:
        return 1, 1, 1
    weekend = late = 0
    for rule in oh.split(";"):
        rule = rule.strip()
        closed = re.search(r"\b(off|closed)\b", rule, re.I)
        m = re.match(r"^([A-Za-z,\- ]+?)\s+(\d)", rule)
        days = day_set(m.group(1).replace(" ", "")) if m else set(DAYS) if re.match(r"^\d", rule) else set()
        if not closed and days & {"Sa", "Su"}:
            weekend = 1
        for s, e in re.findall(r"(\d{1,2}):\d{2}\s*-\s*(\d{1,2}):\d{2}", rule):
            if not closed and (int(e) >= 18 or int(e) <= int(s)):
                late = 1
    return 1, weekend, late


def lighting_points(city, year):
    key = {"New York City": "nyc", "Chicago": "chicago", "Los Angeles": f"la_{year}"}[city]
    x = pd.DataFrame(json.loads((RAW / f"lighting_311/{key}.json").read_text()))
    date = x.get("created_date", x.get("createddate"))
    x = x[pd.to_numeric(date.str[:4], errors="coerce") == year]
    if city == "New York City":
        x = x[x.descriptor.fillna("").str.contains("Out|Dim|Missing|Cycling", case=True)]
    x = x.assign(lat=pd.to_numeric(x.latitude, errors="coerce"), lon=pd.to_numeric(x.longitude, errors="coerce")).dropna(subset=["lat", "lon"])
    return x[(x.lat != 0)]


def licences(city, snap):
    d = pd.Timestamp(snap)
    if city == "New York City":
        a = pd.DataFrame(json.loads((RAW / "licences/ny_active.json").read_text()))
        i = pd.DataFrame(json.loads((RAW / "licences/ny_inactive.json").read_text()))
        a = a.assign(start=pd.to_datetime(a.originalissuedate, errors="coerce"), end=pd.Timestamp("2100-01-01"), lid=a.licensepermitid)
        i = i.assign(start=pd.to_datetime(i.original_issue_date, errors="coerce"), end=pd.to_datetime(i.expiration_date, errors="coerce"),
                     lid=i.license_permit_id)
        x = pd.concat([a, i], ignore_index=True)
        x = x[x.georeference.notna()]
        x["lon"] = [g["coordinates"][0] for g in x.georeference]
        x["lat"] = [g["coordinates"][1] for g in x.georeference]
        desc = x.description.fillna("")
        on = desc.str.contains("restaurant|food & beverage|club|tavern|bar|hotel|cabaret|brew", case=False)
        off = desc.isin(["Liquor Store", "Grocery Store", "Drug Store"])
    else:
        x = pd.DataFrame(json.loads((RAW / "licences/chicago.json").read_text()))
        x = x.assign(start=pd.to_datetime(x.license_start_date, errors="coerce"), end=pd.to_datetime(x.expiration_date, errors="coerce"),
                     lid=x.license_number, lat=pd.to_numeric(x.latitude, errors="coerce"), lon=pd.to_numeric(x.longitude, errors="coerce"))
        on = x.license_description.isin(["Tavern", "Consumption on Premises - Incidental Activity"])
        off = x.license_description == "Package Goods"
    x["kind"] = np.where(on, "on", np.where(off, "off", ""))
    x = x[(x.kind != "") & (x.start <= d) & (x.end >= d)].dropna(subset=["lat", "lon"])
    return x.drop_duplicates(["lid", "kind"])


def first_atm_version(hist):
    if not hist:
        return pd.NaT
    ts = [pd.Timestamp(v["timestamp"]) for v in hist if ATM(v["tags"])]
    return min(ts) if ts else pd.NaT


def main():
    base = pd.read_csv(R7 / "features_primary_core_2024_2025.csv", usecols=[0, 1, 2])
    lookup = pd.read_csv(R7 / "site_lookup_and_quality.csv", dtype=str)
    d = base.merge(lookup[["row_id", "city", "longitude", "latitude", "osm_id", "outcome_year"]], on="row_id")
    d["outcome_year"] = d.outcome_year.astype(int)
    r8 = pd.read_csv(R8, usecols=["row_id", "log_branch_deposits", "fdic_branch_50m", "branch_age_years"])
    d = d.merge(r8, on="row_id", how="left")
    history = json.loads((RAW / "osm/atm_object_history.json").read_text())
    first = {k: first_atm_version(v) for k, v in history.items()}
    pieces = []
    for (city, year), g in d.groupby(["city", "outcome_year"]):
        g = g.copy()
        snap = f"{year - 1}-12-15"
        tr = Transformer.from_crs(4326, EPSG[city], always_xy=True)
        xy = np.c_[tr.transform(g.longitude.astype(float).values, g.latitude.astype(float).values)]
        for name, cnt, dist in (("bars", "log1p_bars_250m", "log1p_dist_bar_m"), ("liquor", "log1p_liquor_250m", "log1p_dist_liquor_m")):
            pts, _ = layer_xy(city, snap, name, tr)
            c, n = count_and_dist(xy, pts, 250)
            g[cnt], g[dist] = np.log1p(c), np.log1p(n)
        pts, _ = layer_xy(city, snap, "night_poi", tr)
        g["log1p_night_poi_250m"] = np.log1p(count_and_dist(xy, pts, 250)[0])
        pts, ids = layer_xy(city, snap, "poi_24_7", tr)
        g["log1p_poi_24_7_250m"] = np.log1p(count_and_dist(xy, pts, 250, exclude=ids, site_ids=g.osm_id.values)[0])
        for name, col in (("rail", "log1p_dist_rail_m"), ("police", "log1p_dist_police_m"), ("highway", "log1p_dist_highway_m")):
            pts, _ = layer_xy(city, snap, name, tr)
            g[col] = np.log1p(count_and_dist(xy, pts, 1)[1])
        lp = lighting_points(city, year - 1)
        lx = np.c_[tr.transform(lp.lon.values, lp.lat.values)]
        g["log1p_light_outage_311_100m"] = np.log1p(count_and_dist(xy, lx, 100)[0])
        g["n_311_light_records_city_year"] = len(lp)
        frame = pq.read_table(OSM_SITES / CITY_KEY[city] / f"{snap}.parquet").to_pandas()
        tags = {f"{t}/{i}": dict(x) for t, i, x in zip(frame.osm_type, frame.osm_id, frame.tags)}
        h = np.array([hours_features(tags.get(o, {})) for o in g.osm_id])
        g["hours_known"], g["open_weekend"], g["open_late"] = h[:, 0], h[:, 1], h[:, 2]
        ts = pd.Timestamp(snap, tz="UTC")
        g["atm_mapped_age_years"] = [((ts - first[o]).days / 365.25) if pd.notna(first.get(o, pd.NaT)) else np.nan for o in g.osm_id]
        g["fdic_branch_age_years"] = g.branch_age_years
        if city in ("New York City", "Chicago"):
            lic = licences(city, snap)
            for kind in ("on", "off"):
                k = lic[lic.kind == kind]
                kx = np.c_[tr.transform(k.lon.astype(float).values, k.lat.astype(float).values)]
                c, n = count_and_dist(xy, kx, 250)
                g[f"log1p_lic_{kind}_250m"], g[f"log1p_dist_lic_{kind}_m"] = np.log1p(c), np.log1p(n)
                g[f"n_lic_{kind}_city"] = len(k)
        pieces.append(g)
        print(city, year, "done", flush=True)
    a = pd.concat(pieces).sort_values("row_id")
    keep = ["row_id", "city", "outcome_year"] + [c for c in a.columns if c.startswith(("log1p_", "hours_", "open_", "atm_mapped", "fdic_", "log_branch", "n_"))]
    a = a[[c for c in dict.fromkeys(keep)]]
    OUT.mkdir(exist_ok=True)
    a.to_csv(OUT / "features_r9.csv", index=False)
    num = [c for c in a.columns if c not in ("row_id", "city", "outcome_year")]
    cov = a.groupby(["city", "outcome_year"])[num].agg(["mean", lambda s: s.isna().mean()])
    cov.columns = [f"{c}__{'mean' if s == 'mean' else 'missing_share'}" for c, s in cov.columns]
    cov.T.to_csv(OUT / "feature_coverage.csv")
    print(cov.T.round(3).to_string())


if __name__ == "__main__":
    main()
