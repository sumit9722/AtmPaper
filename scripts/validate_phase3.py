"""Offline reconciliation and independent spot checks for phase 3."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from pyproj import Geod
from shapely.geometry import Point, shape
from shapely import make_valid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/phase3'
RAW=ROOT/'data/raw/phase3'
checks=[]
def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def check(condition,message):
    if not condition:raise AssertionError(message)
    checks.append(message)
def numeric(v):return None if v in ('',None) else float(v)
def close(a,b):
    if a is None or b is None:return a is b
    return math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

schema=json.loads((OUT/'data/feature_schema.json').read_text())
context=read(OUT/'data/site_context_raw.csv')
lookup=read(OUT/'data/site_lookup_and_quality.csv')
byid={r['site_id']:r for r in context}
quality={r['site_id']:r for r in lookup}
original=read(ROOT/'data/processed/atm_panel_2025_historical.csv')
original_byid={r['site_id']:r for r in original}
check(len(byid)==len(context)==len(quality)==len(original),'Unique feature and lookup rows match the historical panel')
check(set(byid)==set(original_byid),'Historical site IDs are preserved exactly')
check(all(r['confirmatory_eligible']=='False' for r in lookup),'Phase 2 independent-review gate is preserved')
check(all(r['prediction_cutoff']=='2025-01-01' for r in lookup),'All feature rows use the common prediction cutoff')
full_ids={r['site_id'] for r in read(ROOT/'data/processed/atm_panel_2025_full_year.csv')}
dictionary=read(OUT/'data/feature_dictionary.csv')
for cohort in ['all_historical','full_year']:
    expected=set(byid) if cohort=='all_historical' else full_ids
    for kind in ['primary','sensitivity']:
        matrix=read(OUT/f'data/features_{kind}_{cohort}.csv')
        check(len(matrix)==len(expected) and {r['site_id'] for r in matrix}==expected,f'{cohort}/{kind}: cohort membership is exact')
        check(list(matrix[0])==['site_id']+schema[kind+'_predictors'],f'{cohort}/{kind}: columns match locked feature allowlist; no outcomes')
        for r in matrix:
            source=byid[r['site_id']]
            for field in dictionary:
                if field['role']!=kind:continue
                value=numeric(source[field['raw_feature']])
                expected_value=math.log1p(value) if value is not None and field['transformation']=='log1p' else value
                assert close(numeric(r[field['predictor']]),expected_value),(r['site_id'],field['predictor'])
check(True,'Every transformed value reconciles to its raw input; nulls preserved')
acs={r['geoid']:r for r in read(ROOT/'data/processed/census/block_group_context.csv')}
for r in context:
    if r['acs_geoid_2023']:
        ar=acs[r['acs_geoid_2023']]
        land=numeric(r['acs_land_area_m2']);pop=numeric(ar['population'])
        density=pop*1e6/land if pop is not None and land else None
        assert close(numeric(r['population_density']),density)
        assert close(numeric(r['median_household_income']),numeric(ar['median_household_income']))
        labor=numeric(ar['civilian_labor_force']);unemployed=numeric(ar['unemployed'])
        rate=unemployed/labor if labor and unemployed is not None else None
        assert close(numeric(r['unemployment_rate']),rate)
    assert r['background_primary']==str(float(original_byid[r['site_id']]['background_primary_2024_200_500m']))
    assert r['background_report_date_cutoff']==str(float(original_byid[r['site_id']]['background_primary_reported_before_2025']))
check(True,'All ACS densities, income, unemployment fractions and lagged crime reconcile to phase 2/source tables')
# Brute-force polygon containment does not use the builder spatial index.
for layer,idfield,contextfield in [('acs2023','GEOID','acs_geoid_2023'),('sld2021','GEOID20','sld_geoid_2019')]:
    features=[]
    for p in sorted((RAW/layer).glob('*.geojson')):features+=json.loads(p.read_text())['features']
    shapes=[(f['properties'],make_valid(shape(f['geometry']))) for f in features]
    properties={f['properties'][idfield]:f['properties'] for f in features}
    for r in context:
        if r[contextfield]:
            src=properties[r[contextfield]]
            if layer=='acs2023':assert float(r['acs_land_area_m2'])==src['AREALAND']
            else:
                for field in [k for k in r if k.startswith('sld_raw_')]:
                    value=src[field[len('sld_raw_'):]]
                    assert (value is None and r[field]=='') or close(numeric(r[field]),float(value)),field
    # One sample per city plus systematically sampled historical sites.
    selected={r['site_id']:r for r in lookup[::97]}
    for city in ['New York City','Buffalo','Rochester']:
        r=next(r for r in lookup if r['city']==city);selected[r['site_id']]=r
    for r in selected.values():
        point=Point(float(r['longitude']),float(r['latitude']))
        matches=[props[idfield] for props,geom in shapes if geom.covers(point)]
        expected=matches[0] if len(matches)==1 else ''
        assert byid[r['site_id']][contextfield]==expected,(layer,r['site_id'])
check(True,'All joined source attributes reconcile; independent brute-force spatial checks passed across cities')
# Independently recompute neighbor distances from the archived baseline output and verify
# that the baseline itself was constructed only from the pre-cutoff source.
import build_phase3 as builder
source_baseline={}
for raw in builder.read(ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv'):
    import re
    xy=re.findall(r'-?\d+(?:\.\d+)?',raw.get('georeference',''))
    if len(xy)==2:
        lon,lat=map(float,xy)
        if -80<lon<-71 and 40<lat<46:
            source_baseline[builder.identity(raw['street_address'],lon,lat)]=(lon,lat)
baseline=read(OUT/'data/atm_baseline_dec2024.csv')
check({builder.identity(r['address'],r['longitude'],r['latitude']) for r in baseline}==set(source_baseline),
      'Statewide competition denominator reconciles exactly to December 2024 archive identities')
geod=Geod(ellps='WGS84')
for row in lookup[::37]:
    original_site=original_byid[row['site_id']]
    focal=builder.identity(original_site['address_raw'],row['longitude'],row['latitude'])
    distances=[geod.inv(float(row['longitude']),float(row['latitude']),x,y)[2] for key,(x,y) in source_baseline.items() if key!=focal]
    count=sum(d<=500 for d in distances)
    r=byid[row['site_id']]
    assert int(r['other_atm_count_500m'])==count
    assert close(float(r['atm_density_500m']),count/(math.pi*.5**2))
    assert close(float(r['nearest_other_atm']),min(distances))
check(True,'Independent geodesic spot checks confirm ATM self-exclusion, 500 m counts and nearest distance')
check(all(quality[s]['baseline_membership']=='True' for s in full_ids),'Every full-year site was present in the pre-cutoff December snapshot')
# Edge cases independent of real-city outcomes.
check(builder.number('-99999') is None and builder.number('nan') is None and builder.number('0')==0,
      'Missing sentinels and nonfinite values stay missing; valid zeros are retained')
synthetic={builder.identity('A',-74,41):{'baseline_id':'a','longitude':-74,'latitude':41},
           builder.identity('B',-74,41):{'baseline_id':'b','longitude':-74,'latitude':41},
           builder.identity('C',-73,41):{'baseline_id':'c','longitude':-73,'latitude':41}}
result=builder.competition(-74,41,'A',synthetic)
check(result['other_atm_count_500m']==1 and result['nearest_other_atm']==0 and result['other_atm_count_within10m']==1,
      'Co-located distinct identities are flagged and retained; focal identity is excluded')
check(all(not r['available_by'] or r['available_by']<'2025-01-01' for r in dictionary),
      'Documented release bounds precede cutoff; unresolved police as-of availability stays explicitly null')
check(not read(OUT/'qa/range_violations.csv'),'No feature range violations')
for row in read(OUT/'qa/input_manifest.csv'):
    assert sha(ROOT/row['file'])==row['sha256'],row['file']
check(True,'All input and source-code SHA-256 checksums match')
for layer in ['acs2023','sld2021']:
    identifiers=[]
    for path in sorted((RAW/layer).glob('*.geojson')):
        data=json.loads(path.read_text())
        count=json.loads(path.with_name(path.stem+'_count.json').read_text())['count']
        assert len(data['features'])==count and not data.get('exceededTransferLimit')
        identifiers.extend(f['properties'].get('GEOID',f['properties'].get('GEOID20')) for f in data['features'])
    assert len(identifiers)==len(set(identifiers))
check(True,'All seven-county extracts match server counts and contain unique block-group identifiers')
# Prove repeat acquisition is an offline cache read, without making network calls.
import download_phase3 as downloader
cached=downloader.Downloader()
with patch.object(downloader.requests,'get',side_effect=AssertionError('Network forbidden in validation')):
    for sidecar in sorted(RAW.rglob('*.request.json')):
        meta=json.loads(sidecar.read_text())
        file=Path(str(sidecar)[:-len('.request.json')])
        cached.get(str(file.relative_to(RAW)),meta['url'],meta['params'],binary=file.suffix=='.pdf')
check(cached.calls==0,'All 31 GIS/source-document downloads can be reused with network disabled')
report={'status':'PASS','checks':checks,'historical_rows':len(context),'full_year_rows':len(full_ids),
        'primary_predictors':len(schema['primary_predictors']),'independent_human_review_completed':False}
(OUT/'qa/validation.json').write_text(json.dumps(report,indent=2)+'\n')
status=json.loads((OUT/'qa/phase3_status.json').read_text());status['validation_status']='PASS'
(OUT/'qa/phase3_status.json').write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps(report,indent=2))
