"""Isolated Phase 3 paths, frozen feature definitions and source utilities."""
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from common import CITIES, GEOD, TRANS, ROOT, PROJECT, sha, read, savejson

RAW=ROOT/'phase3/raw'
OUT=ROOT/'results/phase3'
COUNTIES={'36':['005','047','061','081','085'],'17':['031','043'],'06':['037']}
NYCOUNTIES=COUNTIES['36']
LAGS=['prior_crime_25m','prior_crime_50m','prior_crime_100m',
      'prior_robbery_50m','prior_burglary_50m','prior_recent_crime_50m']
ANNOTATIONS={'-666666666':'-','-999999999':'N','-888888888':'(X)',
             '-222222222':'**','-333333333':'***','-555555555':'*****'}

def write(path,rows,fields=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    rows=list(rows);fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    assert fields, path
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def definitions():return json.loads((ROOT/'protocol/phase3_variables.json').read_text())['features']

def number(value):
    try:
        result=float(value)
        return result if math.isfinite(result) and result>=0 else None
    except (ValueError,TypeError):return None

def acs_value(feature,attributes,area):
    values={v:number(attributes.get(v+'E')) for v in feature['components']}
    if any(v is None for v in values.values()):return None
    if 'denominator' in feature:
        denominator=values[feature['denominator']]
        if not denominator:return None
        result=sum(values[v] for v in feature['numerator'])/denominator
        assert 0<=result<=1.000001,feature['name']
        return result
    result=values[feature['components'][0]]
    if 'area_denominator' in feature:return result/area*1e6 if area and area>0 else None
    if 'subtract_from' in feature:
        return feature['subtract_from']-result if 1600<=result<=feature['subtract_from'] else None
    return result

def freeze():
    files={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'protocol/phase3_feature_spec.md',ROOT/'protocol/phase3_variables.json']}
    p=OUT/'qa/protocol_freeze.json'
    if p.exists():assert json.loads(p.read_text())['files']==files,'Phase 3 specification changed after freeze'
    else:savejson(p,{'files':files,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'approval':'working_specification; independent review pending'})
    policy=ROOT/'protocol/phase3_geometry_policy.md'
    if policy.exists():
        target=OUT/'qa/geometry_policy_freeze.json'
        if target.exists():assert json.loads(target.read_text())['sha256']==sha(policy)
        else:savejson(target,{'file':str(policy.relative_to(ROOT)),'sha256':sha(policy),'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat()})

def verified(path,side=None):
    path=Path(path)
    if side is None:side=Path(str(path)+'.request.json')
    assert sha(path)==json.loads(Path(side).read_text())['sha256'],path
    return path

def bulk_path(table):
    name=f'acsdt5y2022-{table.lower()}.dat'
    old=PROJECT/'restart_3_0/data/raw/environment_acs2022/bulk'/name
    p=old if old.exists() else RAW/'acs_bulk'/name
    return verified(p,Path(str(p)+'.source.json'))

def geometry_path(state):
    p=(PROJECT/'data/raw/temporal_extension/acs2022' if state=='36' else RAW/'tiger2022')/f'tl_2022_{state}_bg.zip'
    return verified(p)

def sld_paths():
    return [verified(PROJECT/f'data/raw/phase3/sld2021/county_{co}.geojson') for co in NYCOUNTIES]+[
        verified(p) for p in sorted((RAW/'sld2021').glob('*.geojson'))]

def panel():
    return read(ROOT/'data/processed/atm_panel_full_year_2024_2025.csv')+read(ROOT/'data/processed/atm_panel_partial_2023.csv')

def fingerprint(paths):
    return [{'file':str(p.relative_to(PROJECT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(paths))]

def manifest_check(path):
    rows=read(path)
    for r in rows:
        p=PROJECT/r['file'];assert p.stat().st_size==int(r['bytes']) and sha(p)==r['sha256'],p
    return rows

def verify_phase12():
    assert json.loads((ROOT/'reports/validation.json').read_text())['status']=='PASS'
    for r in read(ROOT/'reports/artifact_manifest.csv'):
        p=ROOT/r['file'];assert sha(p)==r['sha256'],p
    for r in read(ROOT/'data/processed/source_manifest.csv'):
        p=ROOT/r['file'];assert sha(p)==r['sha256'],p
    for name,entry in json.loads((ROOT/'large_artifacts.json').read_text())['files'].items():
        p=ROOT/name;assert p.stat().st_size==entry['bytes'] and sha(p)==entry['sha256'],p
