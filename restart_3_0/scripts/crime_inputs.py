"""Build auditable three-city ATM records, incident links and exploratory panel.

Run offline after download_sources.py. Raw inputs are never changed.
"""
import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
from zoneinfo import ZoneInfo
import numpy as np
from pyproj import Transformer, Geod
from scipy.spatial import cKDTree
from shapely.geometry import shape, Point
from shapely.prepared import prep

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed'
OUT.mkdir(parents=True,exist_ok=True)
GEOD=Geod(ellps='WGS84')
CITIES={'New York City':('nyc',32618),'Buffalo':('buffalo',32617),'Rochester':('rochester',32617)}
TRANS={k:Transformer.from_crs(4326,v[1],always_xy=True) for k,v in CITIES.items()}
STATS={k:collections.Counter() for k in CITIES}

def write(name,rows,fields=None):
    rows=list(rows)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def readpages(city):
    folders=[ROOT/'data/raw/temporal_extension/crime2023'/city, ROOT/'data/raw'/city]
    for folder in folders:
        for f in sorted(folder.glob('page_*.json')):
            if '.request.' in f.name: continue
            data=json.loads(f.read_text())
            for i,r in enumerate(data['features'] if isinstance(data,dict) else data):
                yield r, str(f.relative_to(ROOT)), i

def norm(s):return re.sub(r'[^A-Z0-9]+',' ',str(s).upper()).strip()
def sid(s):return hashlib.sha256(s.encode()).hexdigest()[:16]
def number(v):
    try:
        x=float(v)
        return x if math.isfinite(x) else None
    except (ValueError,TypeError):return None

boundaries=json.loads((ROOT/'data/raw/boundaries/cities.geojson').read_text())
POLYS={}
cityrefs=[]
for feature in boundaries['features']:
    p=feature['properties'];city='New York City' if p['BASENAME']=='New York' else p['BASENAME']
    POLYS[city]=prep(shape(feature['geometry']))
    cityrefs.append({'city':city,'geoid':p['GEOID'],'latitude':p['CENTLAT'],'longitude':p['CENTLON'],
        'internal_point_latitude':p['INTPTLAT'],'internal_point_longitude':p['INTPTLON'],
        'analysis_crs':f'EPSG:{CITIES[city][1]}','coordinate_use':'Census city reference only; matching uses individual points'})
write('city_coordinates.csv',cityrefs)

def locate(lon,lat):
    if lon is None or lat is None or not -180<=lon<=180 or not -90<=lat<=90:return ''
    p=Point(lon,lat)
    return next((city for city,poly in POLYS.items() if poly.covers(p)),'')

FINANCIAL=re.compile(r'CREDIT CARD|DEBIT CARD|IDENTITY|FRAUD|ACCOUNT|ELECTRONIC|UNAUTHORIZED.*ATM',re.I)
def classify(offense,desc):
    t=offense.strip().upper()
    if t=='ROBBERY':return 'robbery',1,1,'primary_physical_category'
    if t=='BURGLARY':return 'burglary',1,1,'primary_physical_category'
    if t in ['GRAND LARCENY','PETIT LARCENY','LARCENY/THEFT','LARCENY']:
        if FINANCIAL.search(desc):return 'financial_theft',0,0,'explicit_financial_descriptor'
        return 'larceny',0,1,'broad_only_mechanism_not_fully_verified'
    return 'other',0,0,'outside_primary_and_broad_definition'

def iso_epoch(ms):
    if ms is None:return ''
    return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).astimezone(ZoneInfo('America/New_York')).isoformat()

def build_crimes():
    events=[];excluded=[];codebook={};duplicates=[];quality=[]
    for city,(slug,_) in CITIES.items():
        grouped={};months=collections.Counter()
        for raw,path,idx in readpages(slug):
            STATS[city]['crime_raw_rows']+=1
            a=raw.get('attributes',raw)
            if slug=='nyc':
                eid=a.get('cmplnt_num');date=a.get('cmplnt_fr_dt','');report=a.get('rpt_dt','');offense=a.get('ofns_desc','');desc=a.get('pd_desc','');code=a.get('pd_cd','')
                lon,lat=number(a.get('longitude')),number(a.get('latitude'));attempt=a.get('crm_atpt_cptd_cd','');address='';native=a.get('cmplnt_num','')
            elif slug=='buffalo':
                eid=a.get('case_number');date=a.get('incident_datetime','');report=a.get('created_at','');offense=a.get('incident_type_primary','');desc=a.get('incident_description','');code=offense
                lon,lat=number(a.get('longitude')),number(a.get('latitude'));attempt='not_published';address=a.get('address_1','');native=a.get('incident_id','')
            else:
                eid=a.get('Case_Number');date=iso_epoch(a.get('OccurredFrom_Timestamp'));report=iso_epoch(a.get('Reported_Timestamp'));offense=a.get('Statute_Text','');desc=a.get('Statute_Description','').strip();code=str(a.get('Statute_Section','')).strip()
                geom=raw.get('geometry') or {};lon,lat=number(geom.get('x')),number(geom.get('y'));attempt=a.get('Statute_Attempted','');address=a.get('Address_StreetFull','');native=a.get('OBJECTID','')
            common,primary,broad,reason=classify(offense,desc)
            ck=(city,str(code),offense,desc)
            if ck not in codebook:codebook[ck]={'city':city,'native_code':code,'native_offense':offense,'native_description':desc,'common_category':common,'primary_included':primary,'broad_included':broad,'rule':reason,'review_status':'pending_independent_review','source_rows':0}
            codebook[ck]['source_rows']+=1
            r={'city':city,'event_id':f'{slug}:{eid}' if eid else '', 'native_row_id':native,'event_datetime_local':date,'event_date':date[:10],
               'report_datetime':report,'native_offense':offense,'native_code':code,'native_description':desc,'common_category':common,
               'primary_included':primary,'broad_included':broad,'attempt_status':attempt,'latitude':lat,'longitude':lon,
               'address_raw':address,'source_file':path,'source_row_index':idx,'coordinate_precision_flag':'rounded_block_address' if city=='Buffalo' else 'public_geocode_unverified',
               'available_before_2024_by_report_date':bool(report and report[:10]<'2024-01-01')}
            exclusion=''
            try:
                year=dt.date.fromisoformat(date[:10]).year
                if year not in [2023,2024,2025]:exclusion='outside_2023_2025'
            except ValueError:exclusion='invalid_event_date'
            if not eid:exclusion='missing_case_id'
            if lon is None or lat is None:exclusion='missing_coordinates'
            elif locate(lon,lat)!=city:exclusion='outside_city_polygon'
            if exclusion:
                excluded.append({**r,'exclusion_reason':exclusion});STATS[city]['crime_excluded_'+exclusion]+=1;continue
            key=r['event_id']
            if key in grouped:
                old=grouped[key]
                # One complaint counts once; prioritize robbery, burglary, then broad larceny.
                priority=lambda x:({'robbery':4,'burglary':3,'larceny':2}.get(x['common_category'],0),x['event_datetime_local'])
                keep,drop=(r,old) if priority(r)>priority(old) else (old,r)
                grouped[key]=keep
                duplicates.append({**drop,'duplicate_rule':'one_city_case; robbery>burglary>larceny>other',
                    'coordinate_conflict':old['longitude']!=r['longitude'] or old['latitude']!=r['latitude']})
                STATS[city]['duplicate_case_rows']+=1
            else:grouped[key]=r
        for r in grouped.values():
            months[r['event_date'][:7]]+=1
            x,y=TRANS[city].transform(r['longitude'],r['latitude']);r.update(easting_m=x,northing_m=y,analysis_crs=f'EPSG:{CITIES[city][1]}')
            events.append(r);STATS[city]['crime_unique_valid']+=1
            STATS[city]['primary_'+r['event_date'][:4]]+=r['primary_included']
            STATS[city]['broad_'+r['event_date'][:4]]+=r['broad_included']
        for year in [2023,2024,2025]:
            for month in range(1,13):quality.append({'city':city,'month':f'{year}-{month:02d}','unique_valid_events':months[f'{year}-{month:02d}']})
    write('crime_events_2023_2025.csv',events)
    write('crime_records_excluded.csv',excluded)
    write('crime_duplicate_rows.csv',duplicates,['city','event_id','native_row_id','event_datetime_local','event_date','report_datetime','native_offense','native_code','native_description','common_category','primary_included','broad_included','attempt_status','latitude','longitude','address_raw','source_file','source_row_index','coordinate_precision_flag','available_before_2024_by_report_date','duplicate_rule','coordinate_conflict'])
    write('crime_codebook.csv',codebook.values())
    write('crime_monthly_coverage.csv',quality)
    return events

