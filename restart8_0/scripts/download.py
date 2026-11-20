"""Restart 8 feasibility pull: ATM-coded police incidents, all offences, all years.

Downloads only. No filtering beyond the premise condition, no modelling.
Every response is saved unmodified with a request sidecar and SHA-256 entry.
Run from anywhere:  python3 restart8_0/scripts/download.py
"""
import csv
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
AGENT = "research-data-client/1.0"
PAGE = 50000

# name -> (portal, dataset id, premise field, offence field, year expression)
SOURCES = {
    "nyc_historic": ("data.cityofnewyork.us", "qgea-i56i", "prem_typ_desc", "ofns_desc", "date_extract_y(cmplnt_fr_dt)"),
    "nyc_current_ytd": ("data.cityofnewyork.us", "5uac-w243", "prem_typ_desc", "ofns_desc", "date_extract_y(cmplnt_fr_dt)"),
    "chicago": ("data.cityofchicago.org", "ijzp-q8t2", "location_description", "primary_type", "year"),
    "la_2010_2019": ("data.lacity.org", "63jg-8b9z", "premis_desc", "crm_cd_desc", "date_extract_y(date_occ)"),
    "la_2020_2024": ("data.lacity.org", "2nrs-mtv8", "premis_desc", "crm_cd_desc", "date_extract_y(date_occ)"),
    "la_nibrs": ("data.lacity.org", "k7nn-b2ep", "premis_desc", "nibr_description", "date_extract_y(date_occ)"),
}
FDIC_COUNTIES = {"nyc": ["36005", "36047", "36061", "36081", "36085"], "chicago_cook": ["17031"], "la_county": ["06037"]}
FDIC_FIELDS = "YEAR,CERT,NAMEFULL,BRNUM,UNINUMBR,NAMEBR,ADDRESBR,CITYBR,STALPBR,ZIPBR,STCNTYBR,BRSERTYP,DEPSUMBR,SIMS_LATITUDE,SIMS_LONGITUDE,SIMS_ESTABLISHED_DATE,SIMS_ACQUIRED_DATE"


def fetch(url, target, attempts=5, timeout=600):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.with_name(target.name + ".request.json").exists():
        return target.read_bytes()
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read()
                status = response.status
            json.loads(body)
            target.write_bytes(body)
            target.with_name(target.name + ".request.json").write_text(json.dumps({
                "url": url, "http_status": status, "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2) + "\n")
            return body
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as error:
            last = error
            detail = error.read().decode(errors="replace")[:300] if isinstance(error, urllib.error.HTTPError) else ""
            print(f"  retry {attempt + 1}/{attempts}: {error} {detail}", flush=True)
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Failed: {url}: {last}")


def soql(host, dataset, query):
    return f"https://{host}/resource/{dataset}.json?" + urllib.parse.urlencode({"$query": query})


def atm_condition(field):
    return f"(upper({field}) like '%ATM%' or upper({field}) like '%TELLER%')"


def pull_source(name, host, dataset, premise, offence, year):
    folder = RAW / "crime" / name
    summary = {"source": name, "host": host, "dataset": dataset}
    fetch(f"https://{host}/api/views/{dataset}.json", folder / "metadata.json")
    # 1. Every ATM-coded incident, complete source rows, all offences.
    rows, offset = [], 0
    while True:
        query = f"select :*, * where {atm_condition(premise)} order by :id limit {PAGE} offset {offset}"
        page = json.loads(fetch(soql(host, dataset, query), folder / "atm_rows" / f"page_{offset:07d}.json"))
        rows += page
        if len(page) < PAGE:
            break
        offset += PAGE
    count = json.loads(fetch(soql(host, dataset, f"select count(*) as n where {atm_condition(premise)}"),
                             folder / "atm_count.json"))[0]["n"]
    if int(count) != len(rows) or len({r[":id"] for r in rows}) != len(rows):
        raise RuntimeError(f"{name}: row reconciliation failed ({len(rows)} rows vs API count {count})")
    summary["atm_rows"] = len(rows)
    # 2. Coding stability: every premise value by year (all premises).
    # 3. Background: every offence by year (all premises).
    for label, field in (("premise_by_year", premise), ("offence_by_year", offence)):
        query = f"select {year} as yr, {field} as value, count(*) as n group by yr, value order by yr, value limit {PAGE}"
        try:
            table = json.loads(fetch(soql(host, dataset, query), folder / f"{label}.json"))
            if len(table) >= PAGE:
                raise RuntimeError("aggregate truncated")
            summary[label + "_cells"] = len(table)
        except RuntimeError as error:
            summary[label + "_cells"] = f"FAILED: {error}"
            print(f"  {name} {label} FAILED: {error}", flush=True)
    print(f"{name}: {len(rows)} ATM-coded rows", flush=True)
    return summary


def pull_fdic():
    """Annual bank-branch locations (FDIC Summary of Deposits) as a historical denominator."""
    results = []
    for area, counties in FDIC_COUNTIES.items():
        for county in counties:
            total, offset, got = None, 0, 0
            while total is None or offset < total:
                url = "https://api.fdic.gov/banks/sod?" + urllib.parse.urlencode({
                    "filters": f"STCNTYBR:{county}", "fields": FDIC_FIELDS, "sort_by": "YEAR", "sort_order": "ASC",
                    "limit": 10000, "offset": offset, "format": "json"})
                body = json.loads(fetch(url, RAW / "fdic_sod" / area / f"county_{county}_offset_{offset:07d}.json"))
                total = body["meta"]["total"]
                got += len(body["data"])
                offset += 10000
            if got != total:
                raise RuntimeError(f"FDIC {county}: {got} rows vs total {total}")
            results.append({"source": f"fdic_sod_{county}", "area": area, "branch_year_rows": got})
            print(f"FDIC {area} {county}: {got} branch-year rows", flush=True)
    return results


def main():
    only = set(sys.argv[1:])
    summaries, failures = [], []
    for name, spec in SOURCES.items():
        if only and name not in only:
            continue
        try:
            summaries.append(pull_source(name, *spec))
        except RuntimeError as error:
            failures.append({"source": name, "error": str(error)})
            print(f"{name} FAILED: {error}", flush=True)
    if not only or "fdic" in only:
        try:
            summaries += pull_fdic()
        except (RuntimeError, KeyError) as error:
            failures.append({"source": "fdic_sod", "error": str(error)})
            print(f"fdic FAILED: {error}", flush=True)
    files = sorted(p for p in RAW.rglob("*") if p.is_file() and not p.name.endswith(".request.json") and p.name != "manifest.csv")
    with (RAW / "manifest.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["file", "bytes", "sha256"])
        for path in files:
            writer.writerow([str(path.relative_to(ROOT)), path.stat().st_size, hashlib.sha256(path.read_bytes()).hexdigest()])
    (RAW / "download_summary.json").write_text(json.dumps({"completed": summaries, "failed": failures}, indent=2) + "\n")
    print(f"Done: {len(files)} raw files; {len(failures)} failures", flush=True)


if __name__ == "__main__":
    main()
