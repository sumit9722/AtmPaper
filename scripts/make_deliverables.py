"""Create raw-table exports, source register, data dictionary, report and offline map."""
import collections
import csv
import html
import json
import math
from pathlib import Path
from build_phase12 import ROOT,OUT,CITIES,GEOD,norm,manifest,readpages,write

def read(name):return list(csv.DictReader((OUT/name).open()))

def raw_tables():
    folder=ROOT/'data/raw_tables';folder.mkdir(exist_ok=True)
    for city in ['dfs','nyc','buffalo','rochester']:
        rows=[]
        for raw,path,index in readpages(city):
            a=dict(raw.get('attributes',raw))
            if 'geometry' in raw:
                a['source_geometry_json']=json.dumps(raw['geometry'])
            a={k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in a.items()}
            rows.append(a)
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (folder/f'{city}_source_records.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def map_html():
    bounds=json.loads((ROOT/'data/raw/boundaries/cities.geojson').read_text())
    sites=read('atm_historical_sites_2025.csv');sections=[]
    for f in bounds['features']:
        props=f['properties'];city='New York City' if props['BASENAME']=='New York' else props['BASENAME']
        g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        coords=[p for poly in polys for ring in poly for p in ring]
        factor=math.cos(math.radians(float(props['CENTLAT'])))
        xmin=min(p[0]*factor for p in coords);xmax=max(p[0]*factor for p in coords)
        ymin=min(p[1] for p in coords);ymax=max(p[1] for p in coords)
        scale=min(460/(xmax-xmin),390/(ymax-ymin))
        def xy(p):return (20+(p[0]*factor-xmin)*scale,410-(p[1]-ymin)*scale)
        paths=[]
        for poly in polys:
            path=' '.join('M'+' L'.join(f'{xy(p)[0]:.2f},{xy(p)[1]:.2f}' for p in ring)+' Z' for ring in poly)
            paths.append(f'<path d="{path}" fill="#e8edf1" stroke="#8195a6" stroke-width="0.6" fill-rule="evenodd"/>')
        ss=[s for s in sites if s['city']==city]
        for s in ss:
            x,y=xy((float(s['longitude']),float(s['latitude'])));full=s['supported_days_2025']=='365'
            title=html.escape(f'{s["institution_raw"]} — {s["address_raw"]}\nLat {s["latitude"]}, lon {s["longitude"]}\nSupported exposure: {s["supported_days_2025"]} days; continuity assumed')
            paths.append(f'<circle class="{"full" if full else "partial"}" cx="{x:.2f}" cy="{y:.2f}" r="2.2" fill="{"#087e8b" if full else "#e0781b"}"><title>{title}</title></circle>')
        sections.append(f'<section><h2>{city}</h2><p>{len(ss):,} historical sites with supported intervals</p><svg viewBox="0 0 500 440" role="img" aria-label="Historical ATM locations in {city}">{"".join(paths)}</svg></section>')
    page='''<!doctype html><meta charset="utf-8"><title>Three-city ATM locations</title>
<style>body{font:16px system-ui;color:#193342;margin:28px;background:#f9fbfc}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:20px}section{background:white;border:1px solid #ccd7df;border-radius:10px;padding:16px}svg{width:100%;max-height:600px}circle:hover{r:5;stroke:#111;stroke-width:1}h1{font-size:26px}p{max-width:1000px;line-height:1.5}button{padding:10px;margin:8px;cursor:pointer}</style>
<h1>ATM locations: New York City, Buffalo and Rochester</h1><p>Historical DFS locations reconstructed from 14 snapshots bracketing 2025. Teal: 365 supported days. Orange: partial-year exposure. Hover over a point for its institution, address, latitude and longitude. These are location maps, not crime-risk scores. The three maps use different scales.</p>
<button onclick="document.querySelectorAll('.partial').forEach(e=>e.style.display=e.style.display==='none'?'':'none')">Show/hide partial-year sites</button><main>'''+''.join(sections)+'''</main><p>Sources: NYS Department of Financial Services and Census TIGERweb. Exposure assumes continuity between consecutive snapshots; actual operating days are unknown. Facility review is pending.</p>'''
    (ROOT/'reports/atm_locations_map.html').write_text(page)

def register():
    sources=[
      ('DFS current','NYS Department of Financial Services','Bank-Owned ATM Locations in New York State','ndex-ad5r','https://data.ny.gov/Government-Finance/Bank-Owned-ATM-Locations-in-New-York-State/ndex-ad5r','statewide current snapshot; all six published data fields','data/raw/dfs'),
      ('DFS historical','NYS Department of Financial Services / Socrata','Archived Bank-Owned ATM Locations','versions 270–283','https://data.ny.gov/api/publishing/v1/revision/ndex-ad5r/changes','14 monthly CSV archives, December 2024–January 2026','data/raw/atm_history'),
      ('NYC crime','NYPD / NYC Open Data','NYPD Complaint Data Historic','qgea-i56i','https://data.cityofnewyork.us/Public-Safety/NYPD-Complaint-Data-Historic/qgea-i56i','2024–2025 occurrence dates; robbery, burglary, grand/petit larceny; 17 source fields, no demographic fields','data/raw/nyc'),
      ('Buffalo crime','Buffalo Police / OpenData Buffalo','Crime Incidents','d6g9-xbgu','https://data.buffalony.gov/Public-Safety/Crime-Incidents/d6g9-xbgu','all categories, 2024–2025 incident dates; all returned fields','data/raw/buffalo'),
      ('Rochester crime','Rochester Police / City GIS','RPD Part I Crime - 2011 to Present','MapServer layer 3','https://gis.cityofrochester.gov/arcgis/rest/services/RPD/RPD_Part_I_Crime/MapServer/3','all categories, occurrence year 2024 or 2025; all attributes and WGS84 geometry','data/raw/rochester'),
      ('City boundaries','US Census Bureau','TIGERweb Incorporated Places','3651000 / 3611000 / 3663000','https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4','three current incorporated-place polygons; EPSG:4326','data/raw/boundaries'),
      ('OSM supplement','OpenStreetMap contributors / supplied Overpass exports','ATM and bank nodes','supplied export (1–3).json','https://www.openstreetmap.org/copyright','733 NYC, 19 Buffalo, 13 Rochester candidate nodes; ODbL; snapshot 2026-09-30','original supplied export files'),
    ]
    write('source_register.csv',[dict(zip(['source_id','provider','official_title','dataset_id','source_url','scope','raw_directory'],r)) for r in sources])
    inventory=[]
    for city,(slug,_) in CITIES.items():
        valid=[r for r in read('crime_events_2024_2025.csv') if r['city']==city]
        excluded=[r for r in read('crime_records_excluded.csv') if r['city']==city]
        dates=[r['event_date'] for r in valid]
        inventory.append({'city':city,'valid_unique_records':len(valid),'minimum_valid_event_date':min(dates),'maximum_valid_event_date':max(dates),
            'excluded_records':len(excluded),'missing_coordinate_records':sum(r['exclusion_reason']=='missing_coordinates' for r in excluded),
            'precision_warning':'public coordinates, no verified incident-position accuracy'})
    write('crime_source_inventory.csv',inventory)

def dictionary():
    descriptions={
      'site_id':'SHA-256-derived identifier of city, normalized address and exact coordinate; stable only under unchanged address/coordinate.',
      'site_cluster_id':'Connected component of sites within 10 metres; distinct addresses need facility adjudication.',
      'latitude':'WGS84 latitude in decimal degrees; never city-centre substituted.',
      'longitude':'WGS84 longitude in decimal degrees; negative is west.',
      'supported_days_2025':'Days bracketed by consecutive snapshots containing this exact site, assuming continuity; not known operating days.',
      'full_year_exposure_supported':'True only for 365 supported days during 2025.',
      'exposure_fraction':'supported_days_2025 / 365.',
      'confirmatory_eligible':'False until independent codebook, facility and linkage review and precision assessment pass.',
      'actual_active_days':'Blank: actual machine operating days are not observed.',
      'actual_opening_date':'Blank: first snapshot appearance does not establish opening date.',
      'actual_closing_date':'Blank: last snapshot appearance does not establish closing date.',
      'background_primary_2024_200_500m':'Distinct 2024 robbery/burglary case IDs at geodesic distance >200 m and <=500 m.',
      'background_primary_reported_before_2025':'Same baseline restricted by source report timestamp; Buffalo uses created_at proxy. Current revisions still possible.',
      'background_broad_2024_200_500m':'Broad primary+larceny baseline; coarse theft is exploratory.',
      'cluster_site_count':'Number of distinct site IDs in the 10 m cluster; does not establish they are one facility.',
      'first_observed_snapshot':'Earliest downloaded snapshot listing this exact identity, not opening date.',
      'last_observed_snapshot':'Latest downloaded snapshot listing this exact identity, not closing date.',
      'outcome_year':'2025; count only inside the site exposure intervals.',
      'background_year':'2024; excludes all 2025 outcome events.',
      'analysis_status':'Computationally built; scientific review status remains explicit.',
      'coordinate_precision_flag':'Buffalo rounded/block-address coordinates can be too coarse for a 50 m outcome.',
      'background_vintage_status':'Later record revisions cannot be ruled out using a current historical extract.',
      'exposure_assumption':'Assumption required to infer interval activity between adjacent snapshots.',
      'institution_raw':'Institution string retained from the source snapshot; may change over time.',
      'address_raw':'Unmodified source address used to construct the site identity.',
      'city':'Spatial municipal assignment, not postal city name.'}
    rows=read('atm_panel_2025_historical.csv');dictionary=[]
    for key in rows[0]:
        desc=descriptions.get(key)
        if not desc:
            if key.startswith('primary_any_'):desc='Binary presence of at least one qualifying robbery/burglary within the indicated radius during supported 2025 intervals.'
            elif key.startswith('primary_nearest_count_'):desc='Count assigning each primary case only to its nearest exposure-eligible site within the indicated radius.'
            elif '_count_' in key:desc='Distinct city case count within indicated radius and supported 2025 intervals; primary=robbery+burglary; broad adds non-explicitly-financial larceny.'
            else:desc='See study specification and source field.'
        dictionary.append({'file':'atm_panel_2025_historical.csv / atm_panel_2025_full_year.csv','column':key,'description':desc,'example':rows[0][key],'blank_means':'unknown/not observed, never zero'})
    write('data_dictionary.csv',dictionary)

def historical_identity_audit():
    bydate=collections.defaultdict(dict)
    for r in read('atm_historical_snapshot_membership.csv'):bydate[r['snapshot_date']][r['site_id']]=r
    coverage=[];candidates=[]
    dates=sorted(bydate)
    for i,date in enumerate(dates):
        previous=bydate[dates[i-1]] if i else {}
        current=bydate[date]
        for city in CITIES:
            ids={k for k,r in current.items() if r['city']==city}
            prev={k for k,r in previous.items() if r['city']==city}
            coverage.append({'snapshot_date':date,'city':city,'distinct_exact_site_identities':len(ids),
                'new_identity_since_previous':len(ids-prev) if i else '',
                'absent_identity_since_previous':len(prev-ids) if i else '',
                'interpretation':'identity changes and true openings/closures are not distinguished'})
        if not i:continue
        lost={k:r for k,r in previous.items() if k not in current}
        added={k:r for k,r in current.items() if k not in previous}
        for old in lost.values():
            for new in added.values():
                if old['city']!=new['city']:continue
                same_address=norm(old['address_raw'])==norm(new['address_raw'])
                same_coordinate=old['latitude']==new['latitude'] and old['longitude']==new['longitude']
                if not (same_address or same_coordinate):continue
                distance=GEOD.inv(float(old['longitude']),float(old['latitude']),float(new['longitude']),float(new['latitude']))[2]
                candidates.append({'city':old['city'],'previous_snapshot':dates[i-1],'next_snapshot':date,
                    'old_site_id':old['site_id'],'new_site_id':new['site_id'],'old_address':old['address_raw'],'new_address':new['address_raw'],
                    'old_latitude':old['latitude'],'old_longitude':old['longitude'],'new_latitude':new['latitude'],'new_longitude':new['longitude'],
                    'distance_m':round(distance,4),'same_normalized_address':same_address,'same_exact_coordinates':same_coordinate,
                    'reviewer_decision':'PENDING','auto_merged':False})
    write('historical_snapshot_coverage.csv',coverage)
    write('historical_identity_review.csv',candidates)

def report():
    summary=read('city_summary.csv');hist=read('historical_city_summary.csv');coords=read('city_coordinates.csv')
    lines=['# Phase 1 and phase 2 execution report','',
      'Prepared 2026-10-01. The computational data work is complete. Scientific acceptance remains conditional on the independent review and precision checks listed below. No crime outcomes or ATM coordinates were invented. No predictive model was fitted.','',
      '## Main dataset','',
      'Use `data/processed/atm_panel_2025_full_year.csv` for the full-year historical cohort. `atm_panel_2025_historical.csv` additionally contains partial-year exposure. Both use archived ATM membership, not the 2026 list as presumed 2025 history. All outcome counts are police-recorded robbery/burglary near ATM sites, not verified attacks on machines.','',
      '| City | Historical sites with intervals | Full-year sites | Partial-year sites | Full-year sites with ≥1 primary incident within 50 m |',
      '|---|---:|---:|---:|---:|']
    for r in hist:lines.append(f'| {r["city"]} | {r["historical_sites_with_supported_intervals"]} | {r["full_year_sites"]} | {r["partial_year_sites"]} | {r["full_year_positive_50m"]} |')
    lines+=['','These are descriptive linkage counts, not validated risk predictions. Multiple sites can share the same incident. The full-year restriction is fixed by exposure evidence, not chosen from model performance.','',
      '## Raw-data acquisition','',
      '| City | Downloaded crime records, 2024–2025 | Current DFS site records after exact-site collapse |',
      '|---|---:|---:|']
    for r in summary:lines.append(f'| {r["city"]} | {r["crime_raw_rows"]} | {r["dfs_sites"]} |')
    lines+=['',
      'NYC retrieval includes robbery, burglary, grand larceny and petit larceny with 17 selected native fields; Buffalo and Rochester retain every returned category and field within the date window. These are complete extracts for the stated filters, not complete all-crime NYC history. Every final extract was checked against its API count or object-ID list. An incomplete initial NYC offset download is preserved separately under `initial_offset_attempt` and is not ingested.','',
      'Original source responses are in `data/raw/`. Convenient CSV representations preserving source field names are in `data/raw_tables/`. The original user-supplied files remain unchanged. Fourteen historical DFS CSV archives span 2024-12-15 through 2026-01-15. Request sidecars store retrieval times, URLs and hashes; `source_manifest.csv` hashes all raw inputs. Initial metadata and supplied files do not have a known original retrieval time; the manifest says so.','',
      'The supplied `sorted_data.csv` has 7,537 NYC rows, all with ATM premises, spanning 1998–2025. It is not suitable for the surrounding-crime baseline and was not mixed into the official complete-window extracts. The supplied OSM exports contain 733, 19 and 13 candidate nodes. They are linked to their nearest DFS site for comparison but never automatically added to the primary bank-owned population.','',
      '## Phase 1','',
      'The working specification freezes cities, polygon assignment, bank-owned/in-bank population, robbery+burglary primary outcome, annual period, 50 m primary radius, 25/100 m sensitivities, >200–500 m lagged baseline, model ladder, metrics, transfer comparisons and an analyst-selected AUPRC effect threshold. The codebook lists every observed native offense/code mapping. Theft stays exploratory because its mechanism is not consistently known across cities. The protocol is timestamped working documentation, not an externally registered or signed preregistration.','',
      '## Phase 2','',
      'WGS84 point-in-polygon assignment selects municipalities. UTM coordinates accelerate candidate lookup; final distances use the WGS84 ellipsoid. Exact-address/coordinate duplicate ATM rows collapse to one site. Distinct nearby sites receive a 10 m cluster identifier for facility review. Crime records are de-duplicated by city case identifier, with all dropped rows and rules retained. Primary and broad crime counts remain separate. Backgrounds use only the previous calendar year and exclude the outcome buffer.','',
      'Historical site identity is exact normalized address plus coordinate. Presence in adjacent monthly snapshots supports the intervening interval under a continuity assumption, with gaps limited to 62 days. All intervals are clipped to 2025. Missing membership creates an unsupported interval; no blanket forward or backward filling is used. The full-year file requires 365 supported days. Actual opening dates, closing dates and operating days are blank. Site identity changes can fragment a continuing physical site and require review. `historical_snapshot_coverage.csv` tracks these changes, and `historical_identity_review.csv` lists potential continuations sharing an address or exact point. They are not automatically merged. The full-year cohort is therefore conservative and may be selectively composed.','',
      'Event links record distance, all three radius flags, match multiplicity and nearest-site assignment. Historical outcomes are counted only during supported intervals. `manual_linkage_audit_historical.csv` contains a deterministic sample stratified by city, distance band, offense eligibility and multiple matches. Its reviewer decisions remain PENDING.','',
      'The current-snapshot backcast is retained only as `atm_panel_2025_EXPLORATORY.csv`. `prospective_cohort_PENDING.csv` has blank future outcomes. Neither file should be mistaken for observed prospective results.','',
      '## Coordinates','',
      '| City | Census reference latitude | Census reference longitude |',
      '|---|---:|---:|']
    for r in coords:lines.append(f'| {r["city"]} | {r["latitude"]} | {r["longitude"]} |')
    lines+=['','City reference points are provided for orientation only. The panels contain the latitude and longitude of each individual ATM. Crime tables retain each incident point. `reports/atm_locations_map.html` is a self-contained interactive location map.','',
      '## Remaining research gates','',
      '- Buffalo coordinates are rounded and addresses refer to street blocks. At this latitude, a 0.001-degree grid is roughly 111 m north–south and 81 m east–west; this is comparable to the 50 m radius. Exact-distance arithmetic cannot recover hidden positional precision. Evaluate better geocodes or approve a coarser design before confirmatory cross-city claims.',
      '- Independently adjudicate the primary codebook, stratified event–ATM matches, possible duplicate facilities and historical identity breaks. The generated audit is a work queue, not a completed human review.',
      '- Monthly membership is not proof of uninterrupted machine operation. Review the continuity assumption and address/coordinate changes. Preserve exposure sensitivity analyses.',
      '- Police extracts are current revisions. Report-date filtering reduces late-report leakage but does not reconstruct an as-of-2025 database. Buffalo created_at is a proxy, not a verified report timestamp.',
      '- Municipal boundary clipping can truncate an ATM’s background annulus near the city edge. The current polygons also do not establish historical boundary stability.',
      '- One outcome year does not support forward temporal model evaluation. Additional exposure-supported years or prospective follow-up are required before the blueprint’s modeling stages.',
      '- The working effect threshold, protocol and final category choices still need researcher ratification. `confirmatory_eligible` therefore remains false.','',
      '## Reproduction','',
      'Install `requirements.txt` in a Python virtual environment. Run `scripts/download_sources.py` and `scripts/download_atm_history.py` to populate/cache raw extracts, then `scripts/build_phase12.py`, `scripts/build_historical_panel.py`, `scripts/make_deliverables.py`, and `scripts/validate_phase12.py` in that order. Download commands need network access; builds use only archived inputs. The included raw metadata/history index fixes the snapshot selection. For a fresh acquisition, preserve a separate dated directory rather than replacing this archived release.','',
      'Validation checks are recorded in `reports/validation.json`. The raw-source manifest, generated data dictionary, source register, monthly coverage and exclusion tables are part of the deliverable.','']
    (ROOT/'reports/phase_1_2_report.md').write_text('\n'.join(lines))

def main():
    raw_tables();register();dictionary();historical_identity_audit();map_html();manifest();report()
    print('Raw CSV exports, report, map, dictionary and manifest written.')

if __name__=='__main__':main()
