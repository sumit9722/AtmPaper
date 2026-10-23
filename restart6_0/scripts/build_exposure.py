"""OSM-ID annual continuity and exact-coordinate sensitivity; adapted from Restart 5."""
import collections,datetime as dt,json,re
from common import *
def month_index(d):return d.year*12+d.month
def source_features(city,slug,dates):
 from shapely import from_wkb
 from shapely.ops import transform
 import pyarrow.parquet as pq
 inverse=Transformer.from_crs({'New York City':32618,'Chicago':32616,'Los Angeles':32611}[city],4326,always_xy=True)
 for date in dates:
  path=RAW/f'osm_v2/{slug}/{date}.parquet'
  if not path.exists():raise RuntimeError(f'Missing historical OSM snapshot: {slug}/{date}')
  side=json.loads(Path(str(path)+'.request.json').read_text())
  if sha(path)!=side['sha256'] or side['params']['time']!=date+'T00:00:00Z':raise RuntimeError('OSM snapshot provenance mismatch')
  timestamp=dt.datetime.fromisoformat(date+'T00:00:00+00:00')
  for index,row in enumerate(pq.read_table(path).to_pylist()):
   if not row['edit_timestamp']<=timestamp<row['valid_to_timestamp']:raise RuntimeError('OSM feature is not valid at requested date')
   tags=dict(row['tags'] or []);osm=f"{row['osm_type']}/{row['osm_id']}"
   geometry=from_wkb(row['geom']) if row['geom'] is not None else None
   point=None;reason=''
   if geometry is None or geometry.is_empty or not geometry.is_valid:reason='empty_or_invalid_geometry'
   else:
    point=geometry if geometry.geom_type=='Point' else transform(inverse.transform,transform(TRANS[city].transform,geometry).centroid)
   yield path,index,{'properties':tags|{'@snapshotTimestamp':date,'@osmId':osm,'@geometryIsCentroid':geometry is not None and geometry.geom_type!='Point','@geometryExclusion':reason},
    'geometry':{'type':'Point','coordinates':[point.x,point.y]} if point is not None else None}

def load_snapshots(polys):
 dates=json.loads((RAW/'osm/snapshot_dates.json').read_text())
 bydate={date:{} for date in dates};exclusions=[];duplicates=[];coverage=[]
 for city,slug in CITIES.items():
  for path,index,feature in source_features(city,slug,dates):
   tags=feature['properties'];date=tags['@snapshotTimestamp'][:10]
   if date not in bydate:raise RuntimeError('Unexpected OSM snapshot date '+date)
   osm=tags['@osmId'];geom=feature.get('geometry')
   base={'snapshot':date,'city':city,'osm_id':osm,'source_file':str(path.relative_to(ROOT)),'source_row_index':index,'address_raw':' '.join(str(tags.get(k,'')) for k in ['addr:housenumber','addr:street']).strip(),'institution':tags.get('operator',tags.get('brand',tags.get('name','')))}
   if not geom or geom['type']!='Point':exclusions.append(base|{'reason':tags.get('@geometryExclusion') or 'missing_or_nonpoint_centroid'});continue
   lon,lat=geom['coordinates'][:2]
   if locate(lon,lat,polys)!=city:exclusions.append(base|{'reason':'outside_study_municipality'});continue
   if not (tags.get('amenity')=='atm' or (tags.get('amenity')=='bank' and tags.get('atm')=='yes')):raise RuntimeError('Unexpected OSM tag filter')
   identity='osm_'+hashlib.sha256(f'{city}|{osm}|{lon!r}|{lat!r}'.encode()).hexdigest()[:16]
   if identity in bydate[date]:duplicates.append(base|{'site_id':identity,'rule':'same_city_osm_id_and_coordinates'});continue
   bydate[date][identity]={'site_id':identity,'city':city,'address_raw':base['address_raw'],
    'address_normalized':norm(base['address_raw']),'continuity_key':osm,'osm_id':osm,
    'longitude':lon,'latitude':lat,'institution':base['institution'],
    'osm_amenity':tags['amenity'],'osm_atm_tag':tags.get('atm',''),
    'osm_geometry_is_centroid':tags['@geometryIsCentroid'],'source_population':'OSM_ATM_or_explicit_bank_ATM',
    'source_file':str(path.relative_to(ROOT))}
 snapshots=[]
 for date,sites in sorted(bydate.items()):
  # Per-date normalized records are derived, not raw source snapshots.
  path=OUT/'snapshots'/f'osm_{date}.csv'
  write(path.relative_to(OUT),sites.values())
  snapshots.append((dt.date.fromisoformat(date),sites,path))
  for city in CITIES:coverage.append({'snapshot_date':date,'month':date[:7],'city':city,
   'unique_sites':sum(s['city']==city for s in sites.values()),'file':str(path.relative_to(ROOT)),'sha256':sha(path)})
 return snapshots,exclusions,duplicates,coverage

def merge(intervals):
 result=[]
 for a,b in sorted(intervals):
  if result and a<=result[-1][1]:result[-1]=(result[-1][0],max(result[-1][1],b))
  else:result.append((a,b))
 return result

def main():
 freeze();polys=polygons();snapshots,exclusions,duplicates,coverage=load_snapshots(polys)
 assert len({d for d,_,_ in snapshots})==len(snapshots)
 write('qa/atm_snapshot_coverage.csv',coverage);write('qa/atm_snapshot_exclusions.csv',exclusions,['snapshot','city','osm_id','source_file','source_row_index','address_raw','institution','reason']);write('qa/atm_snapshot_duplicate_rows.csv',duplicates,['snapshot','city','osm_id','source_file','source_row_index','address_raw','institution','site_id','rule'])
 available={str(d)[:7]:(d,s,p) for d,s,p in snapshots};assert len(available)==len(snapshots),'Ambiguous multiple monthly snapshots require explicit selection'
 required=[f'{y}-{m:02d}' for y in range(2022,2027) for m in range(1,13) if '2022-12'<=f'{y}-{m:02d}'<='2026-01']
 write('qa/required_atm_months.csv',[{'month':m,'available':m in available,'snapshot_date':str(available[m][0]) if m in available else '', 'file':str(available[m][2].relative_to(ROOT)) if m in available else '', 'status':'observed_snapshot' if m in available else 'MISSING_no_exposure_inferred'} for m in required])
 cohorts=[];partial_address=[];interval_rows=[];inventory_rows=[];continuity=[];eligibility=[];year_availability=[]
 for year in YEARS:
  start=dt.date(year,1,1);end=dt.date(year+1,1,1);year_days=(end-start).days;window=[f'{year-1}-12']+[f'{year}-{m:02d}' for m in range(1,13)]+[f'{year+1}-01']
  chosen=[available[m] for m in window if m in available];complete=len(chosen)==14 and all(0<(b[0]-a[0]).days<=62 for a,b in zip(chosen,chosen[1:]));groups=[];inventory={};intervals=collections.defaultdict(list)
  for d,sites,p in chosen:
   inventory.update(sites);g=collections.defaultdict(list)
   for s in sites.values():g[(s['city'],s['continuity_key'])].append(s)
   groups.append(g)
  for (a,sa,pa),(b,sb,pb) in zip(chosen,chosen[1:]):
   if month_index(b)-month_index(a)!=1 or not 0<(b-a).days<=62:continue
   lo=max(a,start);hi=min(b,end)
   if lo<hi:
    for id in sa.keys()&sb.keys():intervals[id].append((lo,hi))
  for id,s in sorted(inventory.items()):
   spans=merge(intervals[id]);days=sum((b-a).days for a,b in spans)
   inventory_rows.append(s|{'outcome_year':year,'supported_days':days,'calendar_days':year_days,'exact_full_year':days==year_days,'status':'supported_partial_or_full' if days else 'no_supported_interval'})
   for a,b in spans:interval_rows.append({'site_id':id,'city':s['city'],'outcome_year':year,'start_inclusive':str(a),'end_exclusive':str(b),'supported_days':(b-a).days})
  if chosen:
   initial=groups[0]
   for key,initial_sites in sorted(initial.items()):
    matches=[g.get(key,[]) for g in groups];unique=all(len(m)==1 for m in matches);base=initial_sites[0];distances=[GEOD.inv(base['longitude'],base['latitude'],m[0]['longitude'],m[0]['latitude'])[2] for m in matches] if unique else []
    maxdrift=max(distances) if distances else None
    reason='missing_required_months' if not complete else 'missing_or_ambiguous_osm_id' if not unique else 'coordinate_drift_over_50m' if maxdrift>50 else 'eligible'
    eligibility.append({'outcome_year':year,'city':key[0],'osm_id':key[1],'site_id':base['site_id'],'observed_months':len(chosen),'required_months':14,'unique_all_observed':unique,'max_coordinate_drift_m':maxdrift,'reason':reason,'eligible_10m':bool(complete and unique and maxdrift<=10),'eligible_25m':bool(complete and unique and maxdrift<=25),'eligible_50m':reason=='eligible'})
    if unique:
     for (date,_,p),m,distance in zip(chosen,matches,distances):continuity.append({'outcome_year':year,'city':base['city'],'site_id':base['site_id'],'snapshot_date':str(date),'snapshot_file':str(p.relative_to(ROOT)),'matched_site_id':m[0]['site_id'],'baseline_longitude':base['longitude'],'baseline_latitude':base['latitude'],'matched_longitude':m[0]['longitude'],'matched_latitude':m[0]['latitude'],'distance_from_baseline_m':distance,'eligible':reason=='eligible'})
    if reason=='eligible':cohorts.append(base|{'outcome_year':year,'supported_days':year_days,'calendar_days':year_days,'max_coordinate_drift_m':maxdrift,'strict_exact_identity_full_year':sum((b-a).days for a,b in merge(intervals[base['site_id']]))==year_days})
    if year==2023 and len(chosen)==12 and str(chosen[0][0])=='2023-02-22' and unique and maxdrift<=50:
     partial_address.append(base|{'outcome_year':year,'supported_days':(end-chosen[0][0]).days,'calendar_days':year_days,'max_coordinate_drift_m':maxdrift,'strict_exact_identity_full_year':False,'supported_start':'2023-02-22','supported_end_exclusive':'2024-01-01'})
  for c in CITIES:
   elig=[r for r in eligibility if r['outcome_year']==year and r['city']==c];inv=[r for r in inventory_rows if r['outcome_year']==year and r['city']==c]
   year_availability.append({'city':c,'outcome_year':year,'required_snapshots':14,'available_snapshots':len(chosen),'complete_monthly_window':complete,'inventory_identities':len(inv),'any_exact_supported_identities':sum(r['supported_days']>0 for r in inv),'exact_full_year_sites':sum(r['exact_full_year'] for r in inv),'full_year_sites':sum(r['eligible_50m'] for r in elig) if complete else '', 'drift_10m_full_year_sites':sum(r['eligible_10m'] for r in elig) if complete else '', 'drift_25m_full_year_sites':sum(r['eligible_25m'] for r in elig) if complete else '', 'baseline_osm_candidates':len(elig),'missing_ambiguous_candidates':sum(r['reason']=='missing_or_ambiguous_osm_id' for r in elig),'drift_excluded_candidates':sum(r['reason']=='coordinate_drift_over_50m' for r in elig),'status':'supported_exploratory_cohort' if complete else 'MISSING_full_year_exposure','crime_available':True,'confirmatory_eligible':False})
 write('atm_sites_full_year.csv',cohorts);write('qa/exact_exposure_intervals.csv',interval_rows,['site_id','city','outcome_year','start_inclusive','end_exclusive','supported_days']);write('qa/exact_exposure_inventory.csv',inventory_rows);write('qa/continuity_links.csv',continuity);write('qa/continuity_eligibility.csv',eligibility);write('city_year_availability.csv',year_availability)
 write('atm_sites_partial_2023.csv',partial_address)
 print('Exposure:',len(cohorts),'full site-years;',len(interval_rows),'exact supported intervals;',len(snapshots),'snapshots',flush=True)
if __name__=='__main__':main()
