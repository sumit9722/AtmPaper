"""Generate restart-specific summaries, research gates, dictionary and offline ATM map."""
import collections
import html
import json
from shapely.ops import transform
from common import *

SOURCES=[
    ('NYC crime','Inherited Restart 5 historical plus late-report supplement','https://data.cityofnewyork.us/Public-Safety/NYPD-Complaint-Data-Historic/qgea-i56i','2022–2025','Same verified NYC observations; original retrieval vintage retained'),
    ('Chicago crime','Chicago Police Department','https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2','2022–2025','Public block geocodes; original report date unavailable'),
    ('LA legacy crime','Los Angeles Police Department','https://data.lacity.org/Public-Safety/Crime-Data-from-2020-to-2024/2nrs-mtv8','2022–2024','Frozen legacy system; no 2025 records'),
    ('LA NIBRS crime','Los Angeles Police Department','https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep','2022–2025 occurrences','Consolidated feed; March 2024 reporting-system transition; block geocodes'),
    ('Exploratory ATM history','© OpenStreetMap contributors, via HeiGIT ohsome API v2','https://docs.ohsome.org/ohsome-api/stable/','2023-02-22–2026-01-15','ODbL; mapping history does not establish operating history'),
    ('Municipal boundaries','US Census TIGERweb','https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4','Current downloaded polygons','LA city, not county; historical boundary stability unverified'),
    ('NYC official ATM reference','NYS Department of Financial Services via Restart 5','https://data.ny.gov/Government-Finance/Bank-Owned-ATM-Locations-in-New-York-State/ndex-ad5r','Partial 2023; full 2024–2025','Separate population; never pooled with OSM'),
]

def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+[
        '| '+' | '.join(str(v) for v in row)+' |' for row in rows])

def make_map(panels):
    sections=[]
    for city,poly in polygons().items():
        projected=transform(TRANS[city].transform,poly)
        xmin,ymin,xmax,ymax=projected.bounds
        scale=min(540/(xmax-xmin),540/(ymax-ymin))
        xy=lambda x,y:((x-xmin)*scale+30,570-(y-ymin)*scale)
        paths=[]
        for polygon in getattr(projected,'geoms',[projected]):
            for ring in [polygon.exterior,*polygon.interiors]:
                points=[xy(x,y) for x,y in ring.coords]
                paths.append('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in points)+'Z')
        circles=[]
        for p in panels:
            if p['city']!=city:continue
            x,y=xy(*TRANS[city].transform(float(p['longitude']),float(p['latitude'])))
            tooltip=html.escape(f"{p['osm_id']} | {p['institution']} | {p['address_raw']} | {p['outcome_year']} | supported mapping days: {p['supported_days']} | centroid: {p['osm_geometry_is_centroid']}")
            circles.append(f'<circle class="site" data-year="{p["outcome_year"]}" cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{"#e28c26" if p["osm_geometry_is_centroid"]=="True" else "#166b8a"}"><title>{tooltip}</title></circle>')
        sections.append(f'<section><h2>{city}</h2><svg viewBox="0 0 600 600" role="img" aria-label="{city} historical OSM ATM sites"><path d="{" ".join(paths)}" fill="#e9eef0" stroke="#7e949c" fill-rule="evenodd"/>{"".join(circles)}</svg></section>')
    (REPORTS/'atm_locations_map.html').write_text('''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Restart 6 — historical OSM ATM locations</title>
<style>body{font:16px system-ui;margin:24px;background:#f8fafb;color:#17333e}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}section{background:white;border:1px solid #ccd8dc;border-radius:12px;padding:14px}svg{width:100%}select{font:inherit;padding:6px}p{max-width:1000px;line-height:1.5}</style>
<h1>NYC · Chicago · Los Angeles</h1><p>Historical OpenStreetMap ATM candidates. Blue: point objects. Orange: centroids of larger mapped objects. Hover over a site for its identity. Each city is drawn at its own scale.</p>
<label for="year">Cohort: </label><select id="year" onchange="filterSites()"><option value="2025">2025 full year</option><option value="2024">2024 full year</option><option value="2023">2023 partial, February 22–December 31</option></select>
<main>'''+''.join(sections)+'''</main><p>These locations are an exploratory mapped sample, not a complete ATM inventory. Mapping continuity is not verified operation. NYC's separate official DFS reference population is not displayed here. No incident locations are displayed.</p><p>© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors (ODbL)</a>, via HeiGIT ohsome; municipal outlines: US Census TIGERweb. This map works offline.</p>
<script>function filterSites(){let y=document.getElementById('year').value;document.querySelectorAll('.site').forEach(e=>e.style.display=e.dataset.year===y?'':'none')}filterSites()</script></html>''')

def main():
    validation=json.loads((REPORTS/'validation.json').read_text())
    assert validation['status']=='PASS'
    full=read(OUT/'atm_panel_full_year_2024_2025.csv');early=read(OUT/'atm_panel_partial_2023.csv')
    summary=read(OUT/'city_summary.csv');quality=read(OUT/'qa/crime_quality_by_city_year.csv')
    write('source_register.csv',[dict(zip(['source','publisher','url','coverage','limitation'],row)) for row in SOURCES])
    gates=[
        ('OSM selection','Coverage is incomplete and differs by city; mapping edits do not identify operation.'),
        ('Facility identity','Nearby OSM nodes and bank polygons may refer to the same physical facility.'),
        ('Crime location precision','Chicago/LA public block geocodes do not establish 25–100 m incident precision.'),
        ('LA reporting transition','Legacy/NIBRS case overlap and cross-system identifiers require source review.'),
        ('Chicago historical availability','Original report dates are absent; unfiltered counts are retrospective.'),
        ('Crime codebook and linkage','Independent review of categories, attempted offenses and sampled links is pending.'),
        ('Historical geography','Current municipal polygons may differ from historical boundaries.'),
        ('Future modeling','No modeling acceptance, pristine holdout, environmental increment or transfer claim has been established.'),
    ]
    write('qa/research_review_gates.csv',[{'gate':name,'status':'PENDING','reason':reason,'reviewer':''} for name,reason in gates])
    sensitivity=[]
    for city in CITIES:
        for year in (2024,2025):
            rows=[p for p in full if p['city']==city and int(p['outcome_year'])==year]
            for label,selected in [('all',rows),('point_only',[p for p in rows if p['osm_geometry_is_centroid']=='False']),
                ('boundary_clear',[p for p in rows if p['boundary_buffer_clear_500m']=='True']),
                ('drift_le_10m',[p for p in rows if float(p['max_coordinate_drift_m'])<=10]),
                ('drift_le_25m',[p for p in rows if float(p['max_coordinate_drift_m'])<=25])]:
                for radius in (25,50,100):
                    sensitivity.append({'city':city,'outcome_year':year,'restriction':label,'radius_m':radius,'site_years':len(selected),
                        'positive_sites':sum(int(p[f'primary_any_{radius}m']) for p in selected),
                        'incident_site_links':sum(int(p[f'primary_count_{radius}m']) for p in selected),
                        'nearest_incident_links':sum(int(p[f'primary_nearest_count_{radius}m']) for p in selected)})
    write('qa/sensitivity_summary.csv',sensitivity)
    descriptions={
        'site_id':'OSM city/type-ID/exact-coordinate hash; continuity can bridge <=50 m drift.',
        'osm_id':'Original OSM type/ID; unit is a mapped object, not a verified physical facility.',
        'cohort':'Alternative continuity or exact-coordinate exposure definition; never stack cohorts.',
        'supported_days':'Days supported by the mapping-continuity assumption, not observed operating days.',
        'background_primary_200_500m':'Prior-year cases >200–500 m with usable report date before outcome-year Jan 1; blank for Chicago.',
        'background_unfiltered_200_500m':'Retrospective prior-year occurrence count, including reports unavailable at historical cutoff.',
        'osm_geometry_is_centroid':'True when source object is not a point; point-only sensitivity provided.',
        'confirmatory_eligible':'Always false; scientific acceptance is separate from computational validation.',
        'annulus_fraction_inside_city':'Fraction of the >200–500 m projected ring inside the municipal polygon.',
    }
    dictionary=[]
    for field in full[0]:
        description=descriptions.get(field)
        if not description:
            if field.startswith('primary_reported_count'):description='Nearby cases reported by next Jan 1; blank when report dates are unavailable (Chicago).'
            elif field.startswith('primary_nearest_count'):description='Nearby cases assigned to this nearest eligible site in this cohort/year; deterministic ties.'
            elif field.startswith('multiple_match_count'):description='Nearby cases that also match at least one other eligible mapped object.'
            elif '_count_' in field:description='Count at the specified radius in metres; distances use public geocodes and supported outcome dates.'
            elif field.startswith('primary_any_'):description='One when the corresponding nearby robbery/burglary count is positive; zero otherwise.'
            else:description=field.replace('_',' ')+'; see protocol/study_spec.md and producing script.'
        dictionary.append({'field':field,'description':description,'missing_value':'empty string means unavailable/not applicable; never substitute zero'})
    write('data_dictionary.csv',dictionary)
    make_map(full+early)
    counts=table(['City','2024 full-year sites','2025 full-year sites','2023 partial sites'],[
        [city,*[sum(p['city']==city and int(p['outcome_year'])==year for p in full) for year in (2024,2025)],sum(p['city']==city for p in early)] for city in CITIES])
    crime=table(['City','2022 baseline','2023','2024','2025'],[[city,*[next(r['primary_cases'] for r in quality if r['city']==city and int(r['year'])==year) for year in range(2022,2026)]] for city in CITIES])
    report=f'''# Restart 6 — phases 1–2 execution report

Computational build and automated validation passed. Independent scientific review remains pending; `confirmatory_eligible=false`. No models were fitted.

## Population and exposure

The requested cities are **New York City, Chicago, and Los Angeles city**. The common exploratory cohort uses historical OpenStreetMap ATM objects and banks explicitly tagged `atm=yes`. The inherited official NYC DFS cohort remains separately available under `data/raw/inherited/dfs_nyc_*.csv`.

{counts}

There are {len(full):,} full-year site-years for 2024–2025 and {len(early):,} partial-2023 site-periods. Partial 2023 covers February 22–December 31 (313 days). The 36 snapshot dates match Restart 5. All 14 observations must support a full year; OSM type/ID continuity allows at most 50 m coordinate drift. Exact-coordinate, <=10/25 m drift, point-only and boundary-clear sensitivities are published separately. Mapping history is not verified operating history. Do not stack the alternative panels.

## Crime inputs

{crime}

Counts are unique valid robbery/burglary cases after clipping, exclusions and declared duplicate resolution. LA combines legacy and consolidated NIBRS data; the legacy feed alone has no 2025 records. Case-number matches are collapsed, but an authoritative cross-system ID mapping is unavailable, so residual duplicates/comparability remain a review gate. Chicago's original report date is unavailable; its report-filtered background and reported-outcome counts are blank. Its unfiltered background remains labeled retrospective context.

## Reuse

Reused verified Restart 5 NYC crime and official reference panels, monthly dates, full/partial-year design, exposure-continuity algorithm, WGS84 distance matching, 25/50/100 m outcomes, >200–500 m prior-year background, nearest-site sensitivity, boundary diagnostics and site-month aggregation. `inherited_sources.csv` records source and filtered-copy hashes. Chicago/LA need new sources, city-specific UTM projections and crime adapters. Older releases and model results were preserved.

## Validation and limitations

{len(validation['checks'])} validation groups passed, including source hashes and pagination, raw OSM reconciliation, independently reconstructed full-year membership, all {validation['link_rows']:,} link distances/time windows, full count replay, {validation['bruteforce_sites']} sampled sites checked against every eligible event without the builder's spatial index, and monthly/annual reconciliation. These are automated checks performed in this session, not independent human scientific approval.

Chicago and LA crime points are public block geocodes. Small-radius counts describe proximity to those released points and cannot establish exact ATM exposure or ATM-targeted crime. OSM coverage and duplicate physical facilities, LA's March 2024 reporting break, unavailable Chicago report dates, latest-extract timing, and current municipal boundaries limit interpretation. See `qa/research_review_gates.csv` and the saved source metadata.

## Files

- [Full-year panel](../data/processed/atm_panel_full_year_2024_2025.csv)
- [Partial 2023 panel](../data/processed/atm_panel_partial_2023.csv)
- [Monthly panel](../data/processed/atm_site_month_panel.csv)
- [Offline ATM map](atm_locations_map.html)
- [Validation](validation.json)
- [Reproduction](reproduce.md)
- [Source register](../data/processed/source_register.csv)

OSM data © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), extracted via HeiGIT ohsome API v2. Crime sources: [Chicago]({SOURCES[1][2]}), [LA legacy]({SOURCES[2][2]}), [LA NIBRS]({SOURCES[3][2]}), and the inherited [NYPD release]({SOURCES[0][2]}).
'''
    (REPORTS/'phase_1_2_report.md').write_text(report)
    (REPORTS/'reproduce.md').write_text('''# Reproduce Restart 6

From the repository root, use the existing virtual environment or install `restart6_0/requirements.txt` into a new one.

```bash
.venv/bin/python restart6_0/scripts/run_all.py
```

This verifies frozen raw inputs, reconstructs exposure and crimes, rebuilds annual/monthly panels, validates them, renders the report/map and splits large CSVs into checksum-verified parts. The complete offline rebuild needs no API key. The downloaded raw sources and inherited filtered NYC inputs are self-contained.

For a first acquisition, the original Restart 5 inputs must be present. Use the hidden prompt (the key is never echoed or saved):

```bash
.venv/bin/python restart6_0/scripts/run_all.py --acquire --key-stdin
```

Alternatively set `OHSOME_API_KEY` in the invoking process environment and omit `--key-stdin`. Only historical OSM downloads require it. Successful requests are cached and verified. Stop on quota errors; preserve the cache. Frozen inputs cannot be silently refreshed; changed raw files require a separately reviewed release.

To restore large CSVs without rebuilding:

```bash
.venv/bin/python restart6_0/scripts/large_artifacts.py restore
```

Old NYC raw source references in the harmonized crime table are relative to the repository root and remain traceable in Restart 5. The cached filtered NYC input suffices for this release's offline rebuild. NYC source vintage is inherited; Chicago and LA were newly extracted. Do not call the three extracts a synchronized historical snapshot.
''')
    (ROOT/'README.md').write_text(f'''# Restart 6 — NYC, Chicago and Los Angeles

Phases 1–2 are computationally complete and automatically validated. Scientific review remains pending. No models were fitted.

{counts}

Historical OSM snapshots: February 22, 2023–January 15, 2026. **{len(full):,} full-year site-years** and **{len(early):,} partial-2023 site-periods**. NYC's prior official DFS cohort is preserved as a separate reference; it is not pooled with OSM.

[Execution report](reports/phase_1_2_report.md) · [Offline map](reports/atm_locations_map.html) · [Full-year panel](data/processed/atm_panel_full_year_2024_2025.csv) · [Partial 2023](data/processed/atm_panel_partial_2023.csv) · [Monthly panel](data/processed/atm_site_month_panel.csv) · [Validation](reports/validation.json) · [Reproduce](reports/reproduce.md)

```bash
.venv/bin/python restart6_0/scripts/run_all.py
```

The offline rebuild needs no key. Historical OSM acquisition uses `OHSOME_API_KEY` or a hidden prompt. Large crime/link CSVs are stored as checksum-verified parts; the rebuild recreates them, or run `python restart6_0/scripts/large_artifacts.py restore`.

OSM is an incomplete mapped sample; continuity does not establish ATM operation. Chicago/LA block geocodes limit small-radius interpretation. LA's reporting transition and Chicago's missing original report dates are explicitly flagged. Nearby robbery/burglary is not verified ATM-targeted crime. `confirmatory_eligible=false`.

© OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), via HeiGIT ohsome. Source URLs, hashes, reuse provenance and review gates are included.
''')
    print('Reports, sensitivities, dictionary and offline map written',flush=True)

if __name__=='__main__':
    main()
