"""Build frozen candidate site attributes (protocol.md C1–C8) and the ATM-premise outcome.

Inputs are read-only: Restart 7 phase-3 matrices, Restart 6 OSM snapshots,
Restart 8 raw FDIC SOD and ATM-premise crime pulls. Output: attributes.csv.
"""
import glob
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
R7 = PROJECT / "restart7_0/results/phase3/data"
OSM = PROJECT / "restart6_0/data/raw/osm_v2"
RAW8 = PROJECT / "restart8_0/data/raw"
CITY_KEY = {"New York City": "nyc", "Chicago": "chicago", "Los Angeles": "la"}
EPSG = {"New York City": 32618, "Chicago": 32616, "Los Angeles": 32611}
MEGA = {"chase", "bank of america", "bank of america corporation", "citibank", "citi", "wells fargo"}


def osm_tags(city, year):
    """Tags from the December snapshot preceding the outcome year."""
    frame = pd.read_parquet(OSM / CITY_KEY[city] / f"{year - 1}-12-15.parquet")
    return {f"{t}/{i}": dict(tags) for t, i, tags in zip(frame.osm_type, frame.osm_id, frame.tags)}


def is_247(tags):
    return any(str(tags.get(k, "")).strip().lower() in {"24/7", "mo-su 00:00-24:00"} for k in ("opening_hours", "opening_hours:atm"))


def load_fdic():
    rows = []
    for f in glob.glob(str(RAW8 / "fdic_sod/*/county_*[0-9].json")):
        rows += [r["data"] for r in json.load(open(f))["data"]]
    x = pd.DataFrame(rows)
    x["DEPSUMBR"] = pd.to_numeric(x["DEPSUMBR"], errors="coerce").fillna(0)
    x["est_year"] = pd.to_datetime(x["SIMS_ESTABLISHED_DATE"], format="%m/%d/%Y", errors="coerce").dt.year
    return x.dropna(subset=["SIMS_LATITUDE", "SIMS_LONGITUDE"])


CRIME = {  # source -> (lat, lon, date field, premise field)
    "nyc_historic": ("latitude", "longitude", "cmplnt_fr_dt", "New York City"),
    "nyc_current_ytd": ("latitude", "longitude", "cmplnt_fr_dt", "New York City"),
    "chicago": ("latitude", "longitude", "date", "Chicago"),
    "la_2010_2019": ("lat", "lon", "date_occ", "Los Angeles"),
    "la_2020_2024": ("lat", "lon", "date_occ", "Los Angeles"),
    "la_nibrs": ("hndrdth_lat", "hndrdth_lon", "date_occ", "Los Angeles"),
}
ID_FIELD = {"nyc_historic": "cmplnt_num", "nyc_current_ytd": "cmplnt_num", "chicago": "case_number",
            "la_2010_2019": "dr_no", "la_2020_2024": "dr_no", "la_nibrs": "caseno"}


def load_atm_crime():
    parts = []
    for source, (lat, lon, date, city) in CRIME.items():
        rows = []
        for f in sorted(glob.glob(str(RAW8 / f"crime/{source}/atm_rows/page_*[0-9].json"))):
            rows += json.load(open(f))
        x = pd.DataFrame(rows)
        idf = ID_FIELD[source] if ID_FIELD[source] in x else ":id"
        parts.append(pd.DataFrame({"city": city, "source": source, "case": x[idf].astype(str),
            "lat": pd.to_numeric(x.get(lat), errors="coerce"), "lon": pd.to_numeric(x.get(lon), errors="coerce"),
            "year": pd.to_numeric(x[date].str[:4], errors="coerce")}))
    c = pd.concat(parts).dropna()
    c = c[(c.lat != 0) & c.year.between(2022, 2025)]
    # LA: the 2020-2024 file and NIBRS overlap in 2024; de-duplicate on case number within city/year.
    return c.drop_duplicates(["city", "case", "year"])


def main():
    lookup = pd.read_csv(R7 / "site_lookup_and_quality.csv", dtype=str)
    base = pd.read_csv(R7 / "features_primary_core_2024_2025.csv", usecols=[0, 1, 2])
    sens = pd.read_csv(R7 / "features_sensitivity_core_2024_2025.csv")
    out = pd.read_csv(R7 / "outcomes.csv", usecols=["row_id", "recorded_any_50m", "recorded_any_100m"])
    d = base.merge(lookup, on="row_id").merge(sens[["row_id", "log1p_atm_density_500m"]], on="row_id").merge(out, on="row_id")
    d["outcome_year"] = d.outcome_year.astype(int)
    d["latitude"] = d.latitude.astype(float)
    d["longitude"] = d.longitude.astype(float)
    fdic, crime = load_fdic(), load_atm_crime()
    pieces = []
    for (city, year), g in d.groupby(["city", "outcome_year"]):
        g = g.copy()
        tags = osm_tags(city, year)
        t = [tags.get(o, {}) for o in g.osm_id]
        g["osm_tag_found"] = [bool(x) for x in t]
        g["standalone_atm"] = (g.osm_amenity == "atm").astype(int)
        g["drive_through"] = [int(str(x.get("drive_through", "")).lower() == "yes") for x in t]
        g["drive_through_tagged"] = [int("drive_through" in x) for x in t]
        g["open_24_7"] = [int(is_247(x)) for x in t]
        brand = [str(x.get("brand") or x.get("name") or x.get("operator") or "").strip().lower() for x in t]
        g["megabank"] = [int(b in MEGA) for b in brand]
        tr = Transformer.from_crs(4326, EPSG[city], always_xy=True)
        gx, gy = tr.transform(g.longitude.values, g.latitude.values)
        f = fdic[(fdic.YEAR.astype(int) == year - 1)]
        fx, fy = tr.transform(f.SIMS_LONGITUDE.astype(float).values, f.SIMS_LATITUDE.astype(float).values)
        tree = cKDTree(np.c_[fx, fy])
        dist, idx = tree.query(np.c_[gx, gy], k=1)
        near = dist <= 50
        g["fdic_branch_50m"] = near.astype(int)
        g["fdic_nearest_m"] = dist
        dep = f.DEPSUMBR.values[idx]
        g["log_branch_deposits"] = np.where(near, np.log1p(dep), 0.0)
        g["branch_age_years"] = np.where(near, (year - f.est_year.values[idx]).astype(float), np.nan)
        # ATM-premise outcomes: outcome year (label) and preceding year (optional prior).
        for label, yr in (("atm_premise", year), ("prior_atm_premise", year - 1)):
            c = crime[(crime.city == city) & (crime.year == yr)]
            cx, cy = tr.transform(c.lon.values, c.lat.values)
            ct = cKDTree(np.c_[cx, cy])
            for r in (50, 100):
                g[f"{label}_count_{r}m"] = [len(v) for v in ct.query_ball_point(np.c_[gx, gy], r)]
        pieces.append(g)
    a = pd.concat(pieces).sort_values("row_id")
    a["atm_premise_any_100m"] = (a.atm_premise_count_100m > 0).astype(int)
    a["atm_premise_any_50m"] = (a.atm_premise_count_50m > 0).astype(int)
    a.to_csv(HERE / "attributes.csv", index=False)
    cols = ["osm_tag_found", "standalone_atm", "drive_through", "drive_through_tagged", "open_24_7", "megabank",
            "fdic_branch_50m", "log_branch_deposits", "branch_age_years", "recorded_any_50m", "atm_premise_any_100m", "atm_premise_any_50m"]
    print(a.groupby(["city", "outcome_year"])[cols].mean().round(3).T.to_string())
    print(crime.groupby(["city", "year"]).size().to_string())


if __name__ == "__main__":
    main()
