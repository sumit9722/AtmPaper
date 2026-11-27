"""Download Restart 9 raw layers (protocol.md). Idempotent: skips files that exist.

OSM (ohsome v2 extraction), city 311 street-light failures, NY SLA / Chicago alcohol licences,
OSM API object history of cohort ATM objects. Writes data/raw/... and data/raw/manifest.csv.
"""
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

R9 = Path(__file__).resolve().parents[1]
PROJECT = R9.parent
RAW = R9 / "data/raw"
LOOKUP = PROJECT / "restart7_0/results/phase3/data/site_lookup_and_quality.csv"
SNAPSHOTS = ("2023-12-15", "2024-12-15")  # preceding December for outcome years 2024, 2025
CITY_KEY = {"New York City": "nyc", "Chicago": "chicago", "Los Angeles": "la"}
MARGIN_DEG = 0.07  # ~6 km, covers the 5 km distance cap

OSM_LAYERS = {
    "bars": "amenity in (bar, pub, nightclub, biergarten)",
    "liquor": "shop in (alcohol, wine)",
    "night_poi": "amenity in (fast_food, cinema, theatre, casino, fuel) or shop=convenience",
    "poi_24_7": 'opening_hours="24/7"',
    "rail": "railway=station or (public_transport=station and (train=yes or subway=yes or light_rail=yes))",
    "police": "amenity=police",
}
HIGHWAY = "highway in (motorway, trunk, motorway_link, trunk_link) and type:way"
ATM_FILTER = "amenity=atm or (amenity=bank and atm=yes)"

S = requests.Session()
S.headers["User-Agent"] = "atm-crime-research-client/1.0"


def call(method, url, **kw):
    for attempt in range(6):
        try:
            r = S.request(method, url, timeout=600, **kw)
            if r.status_code == 200:
                return r
            print("HTTP", r.status_code, url, r.text[:200], flush=True)
        except requests.RequestException as e:
            print("retry", e, flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"failed: {url}")


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def bboxes():
    lk = pd.read_csv(LOOKUP)
    lk = lk[lk.core_eligible.astype(str) == "True"]
    out = {}
    for city, g in lk.groupby("city"):
        out[CITY_KEY[city]] = (g.longitude.min() - MARGIN_DEG, g.latitude.min() - MARGIN_DEG,
                               g.longitude.max() + MARGIN_DEG, g.latitude.max() + MARGIN_DEG)
    return out


V2 = "https://api.heigit.org/ohsome-api/v2/extraction/features.parquet"
KEY_FILE = PROJECT / "restart6_0/apikey.txt"  # gitignored; value never printed or saved


def ohsome_v2(path, bbox, snap, filt):
    """Single-snapshot extraction (ohsome v1 extraction endpoints now return 403)."""
    params = {"aoi": ",".join(f"{v:.5f}" for v in bbox), "time": snap + "T00:00:00Z", "filter": filt, "clip": "false"}
    r = call("GET", V2, params=params, headers={"Authorization": KEY_FILE.read_text().strip()})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    save_json(Path(str(path) + ".request.json"), {"url": V2, "params": params, "authentication": "header; not retained"})
    time.sleep(4.2)  # basic plan: <=15 requests per minute


def osm_history(ids, path):
    """First-version timestamps from the public OSM API (one light request per object)."""
    out = json.loads(path.read_text()) if path.exists() else {}
    for k in ids:
        if k in out:
            continue
        r = S.get(f"https://api.openstreetmap.org/api/0.6/{k}/history.json", timeout=120)
        if r.status_code in (404, 410):
            out[k] = None  # unavailable history; A14 left missing
        else:
            if r.status_code != 200:
                r = call("GET", f"https://api.openstreetmap.org/api/0.6/{k}/history.json")
            out[k] = [{"version": e["version"], "timestamp": e["timestamp"], "tags": e.get("tags", {})} for e in r.json()["elements"]]
        if len(out) % 50 == 0:
            save_json(path, out)
            print("history", len(out), flush=True)
        time.sleep(1.0)
    save_json(path, out)


def socrata(host, dataset, where, select=None, page=50000):
    rows, offset = [], 0
    while True:
        params = {"$where": where, "$limit": page, "$offset": offset, "$order": ":id"}
        if select:
            params["$select"] = select
        batch = call("GET", f"https://{host}/resource/{dataset}.json", params=params).json()
        rows += batch
        if len(batch) < page:
            return rows
        offset += page


def main():
    if "--city-data-only" not in sys.argv:  # allows 311/licence downloads in parallel with OSM history
        boxes = bboxes()
        for city, box in boxes.items():
            for snap in SNAPSHOTS:
                for name, filt in list(OSM_LAYERS.items()) + [("highway", HIGHWAY)]:
                    p = RAW / f"osm/{city}/{snap}_{name}.parquet"
                    if not p.exists():
                        ohsome_v2(p, box, snap, filt)
                        print("osm", city, snap, name, flush=True)
        lk = pd.read_csv(LOOKUP)
        ids = sorted(set(lk[lk.core_eligible.astype(str) == "True"].osm_id))
        osm_history(ids, RAW / "osm/atm_object_history.json")

    # 311 street-light failures, preceding calendar years 2023 and 2024
    jobs = {
        "nyc": ("data.cityofnewyork.us", "erm2-nwe9",
                "complaint_type='Street Light Condition' AND created_date between '2023-01-01T00:00:00' and '2024-12-31T23:59:59'",
                "unique_key,created_date,descriptor,latitude,longitude"),
        "chicago": ("data.cityofchicago.org", "v6vf-nfxy",
                    "sr_type in ('Street Light Out Complaint','Alley Light Out Complaint','Viaduct Light Out Complaint') "
                    "AND created_date between '2023-01-01T00:00:00' and '2024-12-31T23:59:59'",
                    "sr_number,created_date,sr_type,latitude,longitude,duplicate"),
        "la_2023": ("data.lacity.org", "4a4x-mna2", "requesttype in ('Single Streetlight Issue','Multiple Streetlight Issue')",
                    "srnumber,createddate,requesttype,latitude,longitude"),
        "la_2024": ("data.lacity.org", "b7dx-7gc3", "requesttype in ('Single Streetlight Issue','Multiple Streetlight Issue')",
                    "srnumber,createddate,requesttype,latitude,longitude"),
    }
    for name, (host, ds, where, sel) in jobs.items():
        p = RAW / f"lighting_311/{name}.json"
        if not p.exists():
            save_json(p, socrata(host, ds, where, sel))
            print("311", name, flush=True)

    # Alcohol licences
    nyc_counties = "premisescounty in ('New York','Kings','Queens','Bronx','Richmond')"
    lic = {
        "ny_active": ("data.ny.gov", "9s3h-dpkz", nyc_counties, None),
        "ny_inactive": ("data.ny.gov", "6dg3-2z7i", nyc_counties.replace("premisescounty", "premises_county"), None),
        "chicago": ("data.cityofchicago.org", "r5kz-chrr",
                    "license_description in ('Tavern','Consumption on Premises - Incidental Activity','Package Goods') "
                    "AND expiration_date >= '2023-01-01T00:00:00'", None),
    }
    for name, (host, ds, where, sel) in lic.items():
        p = RAW / f"licences/{name}.json"
        if not p.exists():
            save_json(p, socrata(host, ds, where, sel))
            print("licences", name, flush=True)

    with open(RAW / "manifest.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "bytes", "sha256"])
        for p in sorted(x for x in RAW.rglob("*") if x.is_file() and x.name != "manifest.csv"):
            w.writerow([str(p.relative_to(R9)), p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest()])
    print("done")


if __name__ == "__main__":
    main()
