"""Independent reconciliation checks for the generated research data."""
import collections
import csv
import hashlib
import json
from pathlib import Path
from pyproj import Geod

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed'
def read(name):return list(csv.DictReader((OUT/name).open()))
def check(condition,message):
    if not condition:raise AssertionError(message)
    checks.append(message)
checks=[]

panel=read('atm_panel_2025_historical.csv');full=read('atm_panel_2025_full_year.csv')
sites={r['site_id']:r for r in read('atm_historical_sites_2025.csv')}
check(len(panel)==len(sites),'One historical panel row per interval-supported site')
check(len({p['site_id'] for p in panel})==len(panel),'Historical site-year identifiers are unique')
check(all(p['supported_days_2025']=='365' for p in full),'Full-year cohort has exactly 365 supported days')
check(all(p['confirmatory_eligible']=='False' for p in panel),'Independent-review gate is preserved')
intervals=collections.defaultdict(list)
for r in read('atm_exposure_intervals_2025.csv'):intervals[r['site_id']].append((r['interval_start_inclusive'],r['interval_end_exclusive']))
counts=collections.Counter();background=collections.Counter();geod=Geod(ellps='WGS84');n=0
for r in csv.DictReader((OUT/'event_atm_links_historical.csv').open()):
    check_key=r['site_id'];distance=float(r['distance_m']);n+=1
    if r['link_role'].startswith('outcome'):
        if not any(a<=r['event_date']<b for a,b in intervals[check_key]):raise AssertionError('Outcome outside exposure')
        if r['primary_included']=='True':
            for radius in [25,50,100]:
                if r[f'within_{radius}m']=='True':counts[(check_key,radius)]+=1
    else:
        if not (r['event_date'].startswith('2024') and 200<distance<=500.0001):raise AssertionError('Background time/distance overlap')
        if r['primary_included']=='True':background[check_key]+=1
    if n%997==0:
        expected=geod.inv(float(r['event_longitude']),float(r['event_latitude']),float(r['atm_longitude']),float(r['atm_latitude']))[2]
        if abs(expected-distance)>.001:raise AssertionError('Distance mismatch')
check(n>0,'Linked distances sampled against independent WGS84 ellipsoid calculations')
check(True,'Every outcome link is inside its supported exposure interval; backgrounds are 2024 and >200–500 m')
check(all(int(p[f'primary_count_{r}m'])==counts[(p['site_id'],r)] for p in panel for r in [25,50,100]),'Panel primary counts reconcile exactly to links at all three radii')
check(all(int(p['background_primary_2024_200_500m'])==background[p['site_id']] for p in panel),'Background counts reconcile exactly to annulus links')
for city in ['nyc','buffalo','rochester']:
    rows=0
    for f in (ROOT/'data/raw'/city).glob('page_*.json'):
        if '.request.' in f.name:continue
        j=json.loads(f.read_text());rows+=len(j['features'] if isinstance(j,dict) else j)
    expected=len(json.loads((ROOT/'data/raw/rochester/object_ids.json').read_text())['objectIds']) if city=='rochester' else int(json.loads((ROOT/'data/raw'/city/'count.json').read_text())[0]['count'])
    check(rows==expected,f'{city}: downloaded record total matches API count ({rows})')
for r in read('source_manifest.csv'):
    p=ROOT/r['file'];digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if digest!=r['sha256']:raise AssertionError(f'Changed raw input {p}')
check(True,'All raw-input SHA-256 hashes match the manifest')
check(all(r['reviewer_decision']=='PENDING' for r in read('manual_linkage_audit_historical.csv')),'No independent human review has been fabricated')
report={'status':'PASS','checks':checks,'historical_sites':len(panel),'full_year_sites':len(full),'link_rows':n}
(ROOT/'reports/validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
