"""Shared I/O and polygon join utilities for housing context."""
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

