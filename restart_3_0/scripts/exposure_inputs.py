"""Build versioned 2024/2025 context and exposure data without altering prior releases."""
import collections,csv,datetime as dt,hashlib,json,math,re
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from pyproj import Geod,Transformer
from scipy.spatial import cKDTree
from shapely.geometry import shape,Point
from shapely import make_valid
from shapely.strtree import STRtree
def identity(address,lon,lat): return (address.upper(), str(lon), str(lat))
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw/temporal_extension';OUT=ROOT/'data/processed'
CITIES=['New York City','Buffalo','Rochester'];SLUG={'New York City':'nyc','Buffalo':'buffalo','Rochester':'rochester'}
TRANS={c:Transformer.from_crs(4326,32618 if c==CITIES[0] else 32617,always_xy=True) for c in CITIES};G=Geod(ellps='WGS84')
CITY_POLYS={('New York City' if f['properties']['BASENAME']=='New York' else f['properties']['BASENAME']):shape(f['geometry']) for f in json.loads((ROOT/'data/raw/boundaries/cities.geojson').read_text())['features']}
def read(p):
 with p.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write(name,rows,fields=None):
 rows=list(rows);p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def norm(s):return re.sub(r'[^A-Z0-9]+',' ',s.upper()).strip()
def locate(lon,lat):return next((c for c,p in CITY_POLYS.items() if p.covers(Point(lon,lat))),None)
def sid(city,address,lon,lat):return 'dfs_'+hashlib.sha256(f'{city}|{norm(address)}|{lon:.7f}|{lat:.7f}'.encode()).hexdigest()[:16]
def snapshot(path):
 sites={};baseline={};excluded=[]
 for index,r in enumerate(read(path)):
  a={re.sub(r'[^a-z0-9]+','_',k.lower()).strip('_'):v for k,v in r.items()}
  coords=re.findall(r'-?\d+(?:\.\d+)?',a.get('georeference',''))
  if len(coords)!=2:excluded.append({'file':str(path.relative_to(ROOT)),'source_row':index,'reason':'unparsed_coordinates'});continue
  lon,lat=map(float,coords)
  if not(-80<lon<-71 and 40<lat<46):excluded.append({'file':str(path.relative_to(ROOT)),'source_row':index,'reason':'implausible_coordinates'});continue
  address=a.get('street_address','');key=identity(address,lon,lat)
  baseline.setdefault(key,{'baseline_id':hashlib.sha256('|'.join(key).encode()).hexdigest()[:16],'longitude':lon,'latitude':lat,'address':address})
  city=locate(lon,lat)
  if city:
   id=sid(city,address,lon,lat);sites[id]={'site_id':id,'city':city,'longitude':lon,'latitude':lat,'address_raw':address}
 return sites,baseline,excluded

def full_year(year):
 global OUT
 OUT=ROOT/"data/processed"/f"exposure_{year}"
 if year==2024:
  paths=sorted(list((RAW/'atm_history').glob('dfs_*.csv'))+[ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv',ROOT/'data/raw/atm_history/dfs_2025-01-15_v271.csv'],key=lambda p:p.name)
 else:
  paths=sorted((ROOT/'data/raw/atm_history').glob('dfs_*_v*.csv'))
 assert len(paths)==14
 snapshots=[];inventory={};exclusions=[];intervals=collections.defaultdict(list);coverage=[]
 for p in paths:
  date=dt.date.fromisoformat(p.name[4:14]);sites,_,ex=snapshot(p);inventory.update(sites);exclusions.extend(ex)
  snapshots.append((date,set(sites)));coverage.append({'date':date.isoformat(),'city_sites':len(sites),'source_file':str(p.relative_to(ROOT))})
 for (a,sa),(b,sb) in zip(snapshots,snapshots[1:]):
  assert 0<(b-a).days<=62
  start=max(a,dt.date(year,1,1));end=min(b,dt.date(year+1,1,1))
  if start<end:
   for id in sa&sb:intervals[id].append((start,end))
 full=[];periods=[];sitecoverage=[]
 for id,site in inventory.items():
  days=sum((b-a).days for a,b in intervals[id])
  sitecoverage.append(site|{'supported_days':days})
  for a,b in intervals[id]:periods.append({'site_id':id,'start_inclusive':str(a),'end_exclusive':str(b),'days':(b-a).days})
  if days==(dt.date(year+1,1,1)-dt.date(year,1,1)).days:full.append(site|{'year':year,'supported_days':(dt.date(year+1,1,1)-dt.date(year,1,1)).days})
 write('qa/exposure_intervals.csv',periods);write('qa/exposure_inventory.csv',sitecoverage)
 write('qa/snapshot_coverage.csv',coverage);write('qa/snapshot_coordinate_exclusions.csv',exclusions)
 # Deterministic, pre-model continuity amendment: unique address, <=50m drift.
 linked=[];audits=[];bydate=[]
 for p in paths:
  records,_,_=snapshot(p);groups=collections.defaultdict(list)
  for r in records.values():groups[(r['city'],norm(r['address_raw']))].append(r)
  bydate.append(groups)
 for key,initial in bydate[0].items():
  matches=[g.get(key,[]) for g in bydate]
  if any(len(v)!=1 for v in matches):continue
  base=initial[0];distances=[G.inv(base['longitude'],base['latitude'],v[0]['longitude'],v[0]['latitude'])[2] for v in matches]
  eligible=max(distances)<=50
  for p,v,distance in zip(paths,matches,distances):audits.append({'site_id':base['site_id'],'snapshot':p.name,'matched_site_id':v[0]['site_id'],'distance_from_baseline_m':distance,'eligible':eligible})
  if eligible:linked.append(base|{'year':year,'supported_days':(dt.date(year+1,1,1)-dt.date(year,1,1)).days})
 write('qa/continuity_links.csv',audits)
 write('qa/exact_identity_full_year.csv',full,['site_id','city','longitude','latitude','address_raw','year','supported_days'])
 return sorted(linked,key=lambda r:r['site_id'])

