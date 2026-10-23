"""Restart 6.0 shared paths; adapted from Restart 5.0."""
import csv,datetime as dt,hashlib,json,math,re
from pathlib import Path
from pyproj import Geod,Transformer
from shapely.geometry import Point,shape
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;RAW=ROOT/'data/raw';OUT=ROOT/'data/processed';REPORTS=ROOT/'reports'
CITIES={'New York City':'nyc','Chicago':'chicago','Los Angeles':'la'};YEARS=range(2023,2026);GEOD=Geod(ellps='WGS84')
TRANS={c:Transformer.from_crs(4326,{'New York City':32618,'Chicago':32616,'Los Angeles':32611}[c],always_xy=True) for c in CITIES}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):
 with Path(p).open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(name,rows,fields=None):
 rows=list(rows);p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 if not fields:raise ValueError(f'Empty output requires a schema: {name}')
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def savejson(path,data):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def norm(s):return re.sub(r'[^A-Z0-9]+',' ',str(s).upper()).strip()
def number(x):
 try:
  v=float(x);return v if math.isfinite(v) else None
 except (ValueError,TypeError):return None
def sid(city,address,lon,lat):return 'dfs_'+hashlib.sha256(f'{city}|{norm(address)}|{lon!r}|{lat!r}'.encode()).hexdigest()[:16]
def polygons():
 return {('New York City' if f['properties']['BASENAME']=='New York' else f['properties']['BASENAME']):shape(f['geometry']) for f in json.loads((RAW/'boundaries/cities.geojson').read_text())['features']}
def locate(lon,lat,polys):
 if lon is None or lat is None or not (-180<=lon<=180 and -90<=lat<=90):return ''
 return next((c for c,p in polys.items() if p.covers(Point(lon,lat))),'')
def freeze():
 p=ROOT/'protocol/study_spec.md';target=REPORTS/'protocol_freeze.json'
 if target.exists():assert json.loads(target.read_text())['sha256']==sha(p),'Protocol changed after freeze; record an amendment first'
 else:savejson(target,{'file':'protocol/study_spec.md','sha256':sha(p),'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'retrospective_working_specification','independent_approval':'PENDING'})
 amendments={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'protocol').glob('*amendment.md'))}
 amendment_file=REPORTS/'amendment_freeze.json'
 if amendment_file.exists():assert json.loads(amendment_file.read_text())['files']==amendments,'Frozen amendment changed'
 else:savejson(amendment_file,{'files':amendments,'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
