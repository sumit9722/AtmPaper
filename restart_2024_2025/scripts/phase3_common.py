"""Offline, outcome-blind construction of common 2025 environmental predictors."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np
from pyproj import Geod, Transformer
from scipy.stats import spearmanr
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree
from shapely import make_valid
from shapely.validation import explain_validity

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/phase3'
OUT=ROOT/'results/phase3'
PROC=ROOT/'data/processed'
GEOD=Geod(ellps='WGS84')
CITIES=['New York City','Buffalo','Rochester']
TRANS={c:Transformer.from_crs(4326,32618 if c=='New York City' else 32617,always_xy=True) for c in CITIES}
CUTOFF='2025-01-01'
# Dictionary fixed before extraction; order also defines the locked predictor order.
DEFS=[
 ('background_primary','log1p','count','police_2024','primary','2024 incidents'),
 ('population_density','log1p','residents/km2 land','acs2023','primary','2019-2023'),
 ('median_household_income','log1p','2023 USD','acs2023','primary','2019-2023'),
 ('unemployment_rate','identity','fraction','acs2023','primary','2019-2023'),
 ('employment_density','log1p','jobs/unprotected acre','sld2021','primary','2017 LEHD / 2019 geography'),
 ('retail_employment_density','log1p','retail jobs/unprotected acre','sld2021','primary','2017 LEHD / 2019 geography'),
 ('employment_mix','identity','entropy 0-1','sld2021','primary','2017 LEHD / 2019 geography'),
 ('road_network_density','log1p','facility miles/mi2 land','sld2021','primary','2018 HERE / 2019 geography'),
 ('auto_road_density','log1p','auto-oriented facility miles/mi2 land','sld2021','primary','2018 HERE / 2019 geography'),
 ('intersection_density','log1p','weighted intersections/mi2','sld2021','primary','2018 HERE / 2019 geography'),
 ('transit_service_density','log1p','departures/hour/mi2','sld2021','primary','2020 GTFS / 2019 geography'),
 ('auto_job_accessibility','log1p','time-weighted jobs','sld2021','primary','2020 travel times / 2017 LEHD'),
 ('atm_density_500m','log1p','other sites/km2 circle','dfs2024','primary','2024-12-15 snapshot'),
 ('nearest_other_atm','log1p','metres WGS84','dfs2024','primary','2024-12-15 snapshot'),
 ('transit_centroid_distance','log1p','metres from CBG centroid','sld2021','sensitivity','2020 GTFS / 2019 geography'),
 ('transit_job_accessibility','log1p','time-weighted jobs','sld2021','sensitivity','2020 transit / 2017 LEHD'),
 ('background_report_date_cutoff','log1p','count','police_2024','sensitivity','2024 incidents with report cutoff'),
]
SLD_FIELDS={'employment_density':'D1C','retail_employment_density':'D1C5_RET','employment_mix':'D2B_E5MIXA',
 'road_network_density':'D3A','auto_road_density':'D3AAO','intersection_density':'D3B','transit_service_density':'D4D',
 'auto_job_accessibility':'D5AR','transit_centroid_distance':'D4A','transit_job_accessibility':'D5BR'}
SOURCE_FIELDS={**SLD_FIELDS,'background_primary':'background_primary_2024_200_500m',
 'population_density':'B01003_001E / AREALAND * 1000000','median_household_income':'B19013_001E',
 'unemployment_rate':'B23025_005E / B23025_003E','atm_density_500m':'other_site_count_500m / (pi * 0.5**2)',
 'nearest_other_atm':'min WGS84 distance to other Dec 2024 DFS identities',
 'background_report_date_cutoff':'background_primary_reported_before_2025'}
AVAILABLE={'acs2023':'2024-12-12','sld2021':'2021-12-31','dfs2024':'2024-12-15','police_2024':None}

def read(path):
    with path.open(newline='',encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
def write(path,rows,fields=None):
    rows=list(rows)
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def norm(s):return re.sub(r'[^A-Z0-9]+',' ',s.upper()).strip()
def identity(address,lon,lat):return (norm(address),f'{float(lon):.7f}',f'{float(lat):.7f}')
def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (TypeError,ValueError):return None

class PolygonLayer:
    def __init__(self,name,paths=None):
        self.features=[]
        for path in paths if paths is not None else sorted((RAW/name).glob('county_*.geojson')):
            self.features.extend(json.loads(path.read_text())['features'])
        assert self.features, name
        self.polygons=[shape(f['geometry']) for f in self.features]
        repairs=[]
        for i,p in enumerate(self.polygons):
            if not p.is_valid:
                fixed=make_valid(p)
                change=abs(fixed.area-p.area)/max(p.area,1e-20)
                assert fixed.geom_type in ['Polygon','MultiPolygon'] and change<1e-6, 'Material geometry repair requires review'
                repairs.append({'layer':name,'geoid':self.features[i]['properties'].get('GEOID',self.features[i]['properties'].get('GEOID20')),
                    'issue':explain_validity(p),'repair':'GEOS make_valid; raw geometry preserved',
                    'relative_area_change':change})
                self.polygons[i]=fixed
        write(OUT/f'qa/geometry_repairs_{name}.csv',repairs,['layer','geoid','issue','repair','relative_area_change'])
        assert all(p.is_valid and not p.is_empty for p in self.polygons),f'Invalid {name} geometry; review before joining'
        self.tree=STRtree(self.polygons)
        self.projected={}
    def join(self,point,city):
        candidates=sorted(int(i) for i in self.tree.query(point,predicate='covered_by'))
        if len(candidates)!=1:return None,candidates,None
        i=candidates[0]
        key=(i,city)
        if key not in self.projected:self.projected[key]=transform(TRANS[city].transform,self.polygons[i])
        p=transform(TRANS[city].transform,point)
        return self.features[i]['properties'],candidates,p.distance(self.projected[key].boundary)

def competition(lon,lat,address,sites):
    keys=list(sites)
    points=list(sites.values())
    distances=np.asarray(GEOD.inv(np.full(len(points),lon),np.full(len(points),lat),
        np.array([p['longitude'] for p in points]),np.array([p['latitude'] for p in points]))[2])
    focal=identity(address,lon,lat)
    other=np.array([key!=focal for key in keys])
    d=distances[other]
    nearest_index=int(np.argmin(np.where(other,distances,np.inf)))
    count=int(np.count_nonzero(d<=500))
    return {'atm_density_500m':count/(math.pi*0.5**2),'nearest_other_atm':float(d.min()),
        'other_atm_count_500m':count,'other_atm_count_within10m':int(np.count_nonzero(d<=10)),
        'other_atm_count_10_to500m':int(np.count_nonzero((d>10)&(d<=500))),
        'baseline_membership':focal in sites,'nearest_other_baseline_id':points[nearest_index]['baseline_id']}

