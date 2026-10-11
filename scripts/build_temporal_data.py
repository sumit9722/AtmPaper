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
from build_phase3 import identity,competition,number,SLD_FIELDS
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw/temporal_extension';OUT=ROOT/'results/temporal_data'
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

def full2024():
 paths=sorted(list((RAW/'atm_history').glob('dfs_*.csv'))+[ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv',ROOT/'data/raw/atm_history/dfs_2025-01-15_v271.csv'],key=lambda p:p.name)
 assert len(paths)==14
 snapshots=[];inventory={};exclusions=[];intervals=collections.defaultdict(list);coverage=[]
 for p in paths:
  date=dt.date.fromisoformat(p.name[4:14]);sites,_,ex=snapshot(p);inventory.update(sites);exclusions.extend(ex)
  snapshots.append((date,set(sites)));coverage.append({'date':date.isoformat(),'city_sites':len(sites),'source_file':str(p.relative_to(ROOT))})
 for (a,sa),(b,sb) in zip(snapshots,snapshots[1:]):
  assert 0<(b-a).days<=62
  start=max(a,dt.date(2024,1,1));end=min(b,dt.date(2025,1,1))
  if start<end:
   for id in sa&sb:intervals[id].append((start,end))
 full=[];periods=[];sitecoverage=[]
 for id,site in inventory.items():
  days=sum((b-a).days for a,b in intervals[id])
  sitecoverage.append(site|{'supported_days_2024':days})
  for a,b in intervals[id]:periods.append({'site_id':id,'start_inclusive':str(a),'end_exclusive':str(b),'days':(b-a).days})
  if days==366:full.append(site|{'year':2024,'supported_days':366})
 write('qa/exposure_2024_intervals.csv',periods);write('qa/exposure_2024_inventory.csv',sitecoverage)
 write('qa/snapshot_2024_coverage.csv',coverage);write('qa/snapshot_coordinate_exclusions.csv',exclusions)
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
  if eligible:linked.append(base|{'year':2024,'supported_days':366})
 write('qa/continuity_links_2024.csv',audits)
 assert not full,'Reconsider amendment: exact identity unexpectedly yields full-year sites'
 return sorted(linked,key=lambda r:r['site_id'])

def crime2023():
 out=[];exclusions=[];duplicates=[];codebook=collections.Counter()
 for city,slug in SLUG.items():
  records={}
  for p in sorted((RAW/'crime2023'/slug).glob('page_*.json')):
   if '.request.' in p.name:continue
   raw=json.loads(p.read_text());rows=raw.get('features',[]) if isinstance(raw,dict) else raw
   for i,item in enumerate(rows):
    a=item.get('attributes',item)
    if slug=='nyc':
     id=a.get('cmplnt_num');date=a.get('cmplnt_fr_dt','');report=a.get('rpt_dt','');off=a.get('ofns_desc','');lon=number_signed(a.get('longitude'));lat=number_signed(a.get('latitude'))
    elif slug=='buffalo':
     id=a.get('case_number');date=a.get('incident_datetime','');report=a.get('created_at','');off=a.get('incident_type_primary','');lon=number_signed(a.get('longitude'));lat=number_signed(a.get('latitude'))
    else:
     def epoch(ms):return dt.datetime.fromtimestamp(ms/1000,dt.timezone.utc).astimezone(ZoneInfo('America/New_York')).isoformat() if ms is not None else ''
     id=a.get('Case_Number');date=epoch(a.get('OccurredFrom_Timestamp'));report=epoch(a.get('Reported_Timestamp'));off=a.get('Statute_Text','')
     geo=item.get('geometry') or {};lon=number_signed(geo.get('x'));lat=number_signed(geo.get('y'))
    category=off.strip().lower();primary=category in ['robbery','burglary'];codebook[(city,off,primary)]+=1
    if not primary:continue
    r={'city':city,'event_id':slug+':'+str(id),'event_date':date[:10],'report_datetime':report,'category':category,'longitude':lon,'latitude':lat,'source_file':str(p.relative_to(ROOT)),'source_row':i}
    reason='missing_id' if not id else 'invalid_date' if not date.startswith('2023-') else 'missing_coordinates' if lon is None or lat is None else 'outside_city' if locate(lon,lat)!=city else ''
    if reason:exclusions.append(r|{'reason':reason});continue
    if r['event_id'] in records:
     old=records[r['event_id']];priority=lambda x:({'robbery':2,'burglary':1}[x['category']],x['event_date'])
     keep,drop=(r,old) if priority(r)>priority(old) else (old,r);records[r['event_id']]=keep;duplicates.append(drop)
    else:records[r['event_id']]=r
  out+=list(records.values())
 write('data/crime_primary_2023.csv',out);write('qa/crime2023_exclusions.csv',exclusions)
 write('qa/crime2023_duplicates.csv',duplicates,['city','event_id','event_date','report_datetime','category','longitude','latitude','source_file','source_row'])
 write('qa/crime2023_codebook.csv',[{'city':c,'native_offense':o,'primary':p,'source_rows':n,'independent_review':'PENDING'} for (c,o,p),n in codebook.items()])
 return out

def number_signed(v):
 try:n=float(v);return n if math.isfinite(n) else None
 except (TypeError,ValueError):return None

def crime2024():
 out=[]
 with (ROOT/'data/processed/crime_events_2024_2025.csv').open() as f:
  for r in csv.DictReader(f):
   if r['event_date'].startswith('2024-') and r['primary_included']=='1':out.append({'city':r['city'],'event_id':r['event_id'],'event_date':r['event_date'],'report_datetime':r['report_datetime'],'category':r['common_category'],'longitude':float(r['longitude']),'latitude':float(r['latitude'])})
 return out

class Layer:
 def __init__(self,paths,idfield):
  self.features=[];self.idfield=idfield
  for p in paths:self.features+=json.loads(p.read_text())['features']
  self.geom=[];self.repairs=[]
  for f in self.features:
   g=shape(f['geometry'])
   if not g.is_valid:
    fixed=make_valid(g);relative=abs(fixed.area-g.area)/max(g.area,1e-20)
    assert relative<1e-6 and fixed.geom_type in ['Polygon','MultiPolygon']
    self.repairs.append({'layer':idfield,'geoid':f['properties'][idfield],'relative_area_change':relative});g=fixed
   self.geom.append(g)
  self.tree=STRtree(self.geom)
 def get(self,point):
  hits=self.tree.query(point,predicate='covered_by')
  return (self.features[int(hits[0])]['properties'] if len(hits)==1 else None),len(hits)

def main():
 freeze=json.loads((OUT/'qa/protocol_freeze.json').read_text());assert sha(ROOT/freeze['specification'])==freeze['sha256']
 sites=full2024()
 panel25={r['site_id']:r for r in read(ROOT/'data/processed/atm_panel_2025_full_year.csv')}
 for r in panel25.values():sites.append({k:r[k] for k in ['site_id','city','longitude','latitude','address_raw']}|{'year':2025,'supported_days':365})
 events={2023:crime2023(),2024:crime2024()}
 indexed={}
 for year,rows in events.items():
  for city in CITIES:
   rs=[r for r in rows if r['city']==city]
   xy=np.array([TRANS[city].transform(r['longitude'],r['latitude']) for r in rs])
   indexed[(year,city)]=(rs,cKDTree(xy))
 baselines={}
 for year,p in [(2024,RAW/'atm_history/dfs_2023-12-15_v258.csv'),(2025,ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv')]:
  _,baselines[year],ex=snapshot(p);write(f'data/atm_baseline_{year-1}12.csv',baselines[year].values())
 # The archived TIGERweb service disagrees with the ACS identifiers. Use the
 # official same-year TIGER/Line archive, retaining both originals for audit.
 import shapefile
 reader=shapefile.Reader(str(RAW/'acs2022/tl_2022_36_bg.zip'))
 polygons=[]
 for sr in reader.iterShapeRecords():
  r=sr.record.as_dict()
  if r['COUNTYFP'] in ['005','047','061','081','085','029','055']:
   polygons.append({'type':'Feature','properties':{'GEOID':r['GEOID'],'AREALAND':r['ALAND']},'geometry':sr.shape.__geo_interface__})
 polygon_path=OUT/'data/acs2022_boundaries.geojson'
 polygon_path.write_text(json.dumps({'type':'FeatureCollection','features':polygons}))
 layer=Layer([polygon_path],'GEOID')
 sld=Layer(sorted((ROOT/'data/raw/phase3/sld2021').glob('county_*.geojson')),'GEOID20')
 acs={}
 for path in sorted((RAW/'acs2022/attributes').glob('county_*.json')):
  if '.request.' in path.name:continue
  table=json.loads(path.read_text())
  for values in table[1:]:
   r=dict(zip(table[0],values));acs[''.join(r[k] for k in ['state','county','tract','block group'])]=r
 names=json.loads((ROOT/'results/phase3/data/feature_schema.json').read_text())['primary_predictors']
 contexts=[];features=[];labels=[];join_audit=[];outcome_links=[]
 for site in sites:
  year=int(site['year']);city=site['city'];lon=float(site['longitude']);lat=float(site['latitude']);rid=f"{site['site_id']}:{year}"
  row={'row_id':rid,'site_id':site['site_id'],'year':year,'city':city,'longitude':lon,'latitude':lat,'supported_days':site['supported_days'],'confirmatory_eligible':False,'prediction_cutoff':f'{year}-01-01'}
  point=Point(lon,lat);ag,ac=layer.get(point);sg,sc=sld.get(point);a=acs.get(ag['GEOID']) if ag else None
  assert not ag or a
  raw={'row_id':rid,'acs_geoid_2022':ag['GEOID'] if ag else None,'sld_geoid_2019':sg['GEOID20'] if sg else None,
       'population':number(a['B01003_001E']) if a else None,'land_m2':number(ag['AREALAND']) if ag else None}
  raw['population_density']=raw['population']*1e6/raw['land_m2'] if raw['population'] is not None and raw['land_m2'] else None
  raw['median_household_income']=number(a['B19013_001E']) if a else None
  labor=number(a['B23025_003E']) if a else None;unemployed=number(a['B23025_005E']) if a else None
  raw['unemployment_rate']=unemployed/labor if labor and unemployed is not None else None
  for field in ['B01003_001','B19013_001','B23025_003','B23025_005']:
   for suffix in ['E','M','EA','MA']:raw[field+suffix]=a[field+suffix] if a else None
  for name,field in SLD_FIELDS.items():raw[name]=number(sg.get(field)) if sg else None
  raw.update(competition(lon,lat,site['address_raw'],baselines[year]))
  rs,tree=indexed[(year-1,city)];indices=tree.query_ball_point(TRANS[city].transform(lon,lat),502)
  bg=bg_all=0;missing=late=0
  for j in indices:
   e=rs[j];distance=G.inv(lon,lat,e['longitude'],e['latitude'])[2]
   if 200<distance<=500:
    bg_all+=1
    if e['report_datetime'] and e['report_datetime'][:10]<f'{year}-01-01':bg+=1
    elif not e['report_datetime']:missing+=1
    else:late+=1
  raw.update(background_primary=bg,background_unfiltered=bg_all,background_unknown_report=missing,background_late_report=late)
  if year==2024:
   counts={r:0 for r in [25,50,100]};unfiltered=0
   rs,tree=indexed[(2024,city)]
   for j in tree.query_ball_point(TRANS[city].transform(lon,lat),101):
    e=rs[j];distance=G.inv(lon,lat,e['longitude'],e['latitude'])[2]
    if distance<=100:
     known=bool(e['report_datetime'] and e['report_datetime'][:10]<'2025-01-01')
     if distance<=50:unfiltered+=1
     for radius in counts:
      if distance<=radius and known:counts[radius]+=1
     outcome_links.append({'row_id':rid,'event_id':e['event_id'],'event_date':e['event_date'],'report_datetime':e['report_datetime'],'distance_m':distance,'known_by_2025':known})
   row.update(y=int(counts[50]>0),primary_count_50m=counts[50],unfiltered_primary_count_50m=unfiltered,label_cutoff='2025-01-01',label_vintage='report_date_filtered_latest_extract_proxy')
  else:
   p=panel25[site['site_id']];row.update(y=int(p['primary_any_50m']),primary_count_50m=int(p['primary_count_50m']),unfiltered_primary_count_50m=int(p['primary_count_50m']),label_cutoff='retrospective_complete_year',label_vintage='phase2_2025_latest_extract')
  model={'row_id':rid}
  for name in names:
   field=name.removeprefix('log1p_');v=raw[field];model[name]=math.log1p(v) if name.startswith('log1p_') and v is not None else v
  join_audit.append({'row_id':rid,'acs_matches':ac,'sld_matches':sc,'baseline_member':raw['baseline_membership']})
  assert raw['baseline_membership'],'Full-year site absent from prior December snapshot'
  contexts.append(raw);features.append(model);labels.append(row)
 write('data/context_raw.csv',contexts);write('data/features.csv',features);write('data/cohort.csv',labels)
 write('qa/spatial_joins.csv',join_audit);write('qa/geometry_repairs.csv',layer.repairs+sld.repairs,['layer','geoid','relative_area_change'])
 write('data/outcome_links_2024.csv',outcome_links)
 summary=[]
 for year in [2024,2025]:
  for city in CITIES:
   rs=[r for r in labels if r['year']==year and r['city']==city]
   summary.append({'year':year,'city':city,'full_year_sites':len(rs),'positive_50m':sum(r['y'] for r in rs)})
 write('qa/city_year_summary.csv',summary)
 sources=[p for p in RAW.rglob('*') if p.is_file()]
 sources += list((ROOT/'data/raw/atm_history').glob('dfs_*.csv'))
 sources += list((ROOT/'data/raw/phase3/sld2021').glob('county_*.geojson'))
 sources += [ROOT/'data/raw/boundaries/cities.geojson',ROOT/'data/processed/crime_events_2024_2025.csv',ROOT/'data/processed/atm_panel_2025_full_year.csv',ROOT/'results/phase3/data/feature_schema.json',ROOT/'scripts/build_temporal_data.py',ROOT/'protocol/phase45_temporal_extension_v2.md',ROOT/'protocol/phase45_boundary_correction.md',ROOT/'protocol/phase45_continuity_amendment.md']
 write('qa/input_manifest.csv',[{'file':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(set(sources))])
 print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
