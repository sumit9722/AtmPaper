"""Independent file-based acceptance checks; no imports from builder modules.

Reconstructs exposure from source rows, all geodesic link distances/counts,
source partition counts/IDs, and sampled brute-force omission checks.
"""
import collections,csv,datetime as dt,hashlib,json,math,re
import numpy as np
from shapely.geometry import Point
from shapely.ops import transform
from common import *
import sys
sys.path.insert(0,str(PROJECT/'scripts'))
from large_artifacts import restore

def main():
 restore(['restart5_0/data/processed/event_atm_links.csv'])
 checks=[]
 def check(ok,name,detail=None):
  if not ok:raise AssertionError(name)
  checks.append({'check':name,'status':'PASS','detail':detail})
 freeze();check(True,'Active specification matches its pre-build freeze')
 manifest=read(OUT/'source_manifest.csv');sidecars=0
 for r in manifest:assert sha(ROOT/r['file'])==r['sha256'],r['file']
 for p in RAW.rglob('*.request.json'):
  m=json.loads(p.read_text());original=Path(str(p).removesuffix('.request.json'))
  assert original.exists() and sha(original)==m['sha256'],p;sidecars+=1
 check(True,'Every raw manifest and request hash matches preserved bytes',{'files':len(manifest),'sidecars':sidecars})
 acquisitions=[]
 for city,slug in CITIES.items():
  for year in range(2015,2026):
   folder=RAW/f'crime/{slug}/{year}';seen=set();count=0
   for p in sorted(folder.glob('page_*.json')):
    if '.request.' in p.name:continue
    obj=json.loads(p.read_text());rr=obj['features'] if isinstance(obj,dict) else obj
    ids=[r['attributes']['OBJECTID'] if slug=='rochester' else r['source_row_id'] for r in rr]
    assert len(ids)==len(set(ids)) and not seen.intersection(ids),(p,'duplicate source row');seen.update(ids);count+=len(ids)
   if slug=='rochester':
    before=json.loads((folder/'object_ids_before.json').read_text())['objectIds'];after=json.loads((folder/'object_ids_after.json').read_text())['objectIds'];assert len(before)==len(set(before)) and set(before)==set(after)==seen
   else:
    before=int(json.loads((folder/'count_before.json').read_text())[0]['count']);after=int(json.loads((folder/'count_after.json').read_text())[0]['count']);assert before==after==count
   acquisitions.append({'city':city,'year':year,'source_rows':count,'active':year>=2022})
 check(len(acquisitions)==33,'All 33 acquired source partitions reconcile, including 12 active partitions')
 for year in range(2022,2026):
  folder=RAW/f'crime/nyc/{year}/late_current';seen=set();total=0
  for p in sorted(folder.glob('page_*.json')):
   if '.request.' in p.name:continue
   rows=json.loads(p.read_text());ids=[r['source_row_id'] for r in rows];assert len(ids)==len(set(ids)) and not seen.intersection(ids);seen.update(ids);total+=len(ids)
  before=int(json.loads((folder/'count_before.json').read_text())[0]['count']);after=int(json.loads((folder/'count_after.json').read_text())[0]['count']);assert before==after==total
  acquisitions.append({'city':'New York City','year':year,'source_rows':total,'active':True,'source':'late_current'})
 check(True,'NYC current-year feed late-occurrence supplements reconcile')
 events=read(OUT/'crime_events_2022_2025.csv');primary=read(OUT/'crime_primary_2022_2025.csv');excluded=read(OUT/'qa/crime_exclusions.csv');duplicates=read(OUT/'qa/crime_duplicates.csv');eb={e['event_id']:e for e in primary}
 check(len(events)==len({r['event_id'] for r in events}),'Global city-case uniqueness after harmonization')
 check(sum(a['source_rows'] for a in acquisitions if a['active'])==len(events)+len(excluded)+len(duplicates),'Every active raw row accounted for as retained, excluded, or duplicate')
 check(len(eb)==len(primary) and set(eb)=={r['event_id'] for r in events if r['primary_included']=='True'},'Primary extract is exactly the robbery/burglary subset')
 source_refs=[(r['source_file'],r['source_row_index']) for r in events+excluded+duplicates]
 check(len(source_refs)==len(set(source_refs)),'Retained, excluded and duplicate source references form a disjoint partition')
 del source_refs
 polys=polygons()
 for e in events:
  assert 2022<=int(e['event_year'])<=2025 and dt.date.fromisoformat(e['event_date']).year==int(e['event_year'])
  assert polys[e['city']].covers(Point(float(e['longitude']),float(e['latitude'])))
  try:report=dt.date.fromisoformat(e['report_date']);valid=report>=dt.date.fromisoformat(e['event_date'])
  except ValueError:valid=False
  assert valid==(e['report_date_usable']=='True')
 check(True,'Retained event dates, geometry and report chronology valid')
 monthly=read(OUT/'crime_monthly_coverage.csv');months=collections.Counter((r['city'],r['event_date'][:7],r['primary_included']=='True') for r in events)
 check(len(monthly)==144 and len({(r['city'],r['month']) for r in monthly})==144,'Complete 144-row city/month active crime grid')
 for r in monthly:
  assert int(r['primary_cases'])==months[(r['city'],r['month'],True)]
  assert int(r['unique_valid_cases'])==sum(months[(r['city'],r['month'],k)] for k in [False,True])
 # Independently parse official snapshots, grouping exact published locations.
 snaps={};date_by_month={}
 for p in sorted((RAW/'atm_history').glob('dfs_*.csv')):
  date=dt.date.fromisoformat(p.name[4:14]);sites={};group=collections.defaultdict(list)
  for raw in read(p):
   row={re.sub(r'[^a-z0-9]+','_',k.lower()).strip('_'):v for k,v in raw.items()};address=norm(row.get('street_address',''));coord=re.findall(r'-?\d+(?:\.\d+)?',row.get('georeference',''))
   if len(coord)!=2 or not address:continue
   lon,lat=map(float,coord);city=locate(lon,lat,polys)
   if not city:continue
   id=sid(city,address,lon,lat);sites[id]=(city,address,lon,lat)
  for id,s in sites.items():group[(s[0],s[1])].append((id,s))
  snaps[date]=(sites,group);date_by_month[str(date)[:7]]=date
 dates=sorted(snaps)
 check(len(dates)==36 and str(dates[0])=='2023-02-22' and str(dates[-1])=='2026-01-15','Recovered continuous snapshot series spans February 2023–January 2026')
 check(all((b.year*12+b.month)-(a.year*12+a.month)==1 and 0<(b-a).days<=62 for a,b in zip(dates,dates[1:])),'Every adjacent snapshot advances one month with <=62-day gap')
 full=read(OUT/'atm_panel_full_year_2024_2025.csv');early=read(OUT/'atm_panel_partial_2023.csv');partial=read(OUT/'atm_panel_exact_supported_2023_2025.csv');panel=full+early+partial;pb={p['row_id']:p for p in panel}
 check(len(panel)==len(pb)>0,'Panel row IDs unique across distinct exposure cohorts')
 expectedfull=set();expectedearly=set();expectedspans=collections.defaultdict(set)
 for year in YEARS:
  start=dt.date(year,1,1);end=dt.date(year+1,1,1);months=[f'{year-1}-12']+[f'{year}-{m:02d}' for m in range(1,13)]+[f'{year+1}-01'];chosen=[date_by_month[m] for m in months if m in date_by_month]
  if len(chosen)==14 or (year==2023 and len(chosen)==12):
   for key,initial in snaps[chosen[0]][1].items():
    match=[snaps[d][1].get(key,[]) for d in chosen]
    if any(len(m)!=1 for m in match):continue
    id,base=initial[0];ds=[GEOD.inv(base[2],base[3],m[0][1][2],m[0][1][3])[2] for m in match]
    if max(ds)<=50:
     (expectedfull if len(chosen)==14 else expectedearly).add((id,year))
  for a,b in zip(chosen,chosen[1:]):
   if (b.year*12+b.month)-(a.year*12+a.month)!=1 or (b-a).days>62:continue
   lo=max(a,start);hi=min(b,end)
   if lo>=hi:continue
   for id in snaps[a][0].keys()&snaps[b][0].keys():expectedspans[(id,year)].update((lo+dt.timedelta(days=k)).isoformat() for k in range((hi-lo).days))
 check(expectedfull=={(p['site_id'],int(p['outcome_year'])) for p in full},'All and only raw-snapshot eligible full-year sites included')
 check(expectedearly=={(p['site_id'],int(p['outcome_year'])) for p in early},'All and only twelve-snapshot partial 2023 address-continuity sites included')
 check({(p['site_id'],int(p['outcome_year'])) for p in partial}==set(expectedspans),'All and only exact identities with supported days included')
 spans=collections.defaultdict(set)
 for r in read(OUT/'qa/exact_exposure_intervals.csv'):
  a=dt.date.fromisoformat(r['start_inclusive']);b=dt.date.fromisoformat(r['end_exclusive']);assert (b-a).days==int(r['supported_days'])
  ss={(a+dt.timedelta(days=k)).isoformat() for k in range((b-a).days)};key=(r['site_id'],int(r['outcome_year']));assert not spans[key].intersection(ss);spans[key].update(ss)
 check(dict(spans)==dict(expectedspans),'Every supported exposure day independently reconstructed; no overlap or gap filling')
 for p in panel:
  y=int(p['outcome_year']);days=(dt.date(y+1,1,1)-dt.date(y,1,1)).days
  assert int(p['calendar_days'])==days and int(p['background_year'])==y-1 and p['confirmatory_eligible']=='False'
  assert all(p[k]=='' for k in ['actual_active_days','actual_opening_date','actual_closing_date'])
  assert int(p['supported_days'])==(days if p['cohort']=='address_continuity_full_year' else 313 if p['cohort']=='address_continuity_partial_2023' else len(spans[(p['site_id'],y)]))
  if p['cohort']=='address_continuity_partial_2023':assert p['supported_start']=='2023-02-22' and p['supported_end_exclusive']=='2024-01-01' and p['full_year_supported']=='False'
  assert 0<=float(p['annulus_fraction_inside_city'])<=1.00000001
 check(True,'Exposure duration, leap years, baseline years, null operation dates and scientific gates consistent')
 availability=read(OUT/'city_year_availability.csv')
 check(len(availability)==9 and all(r['full_year_sites']=='' for r in availability if r['outcome_year']=='2023'),'Nine-cell availability grid keeps unsupported 2023 full-year counts null')
 counts=collections.defaultdict(collections.Counter);nlinks=0;previous=None;group=[]
 def check_group(group):
  if not group:return
  ordered=sorted(group,key=lambda r:(float(r['distance_m']),r['site_id']))
  assert len(ordered)==len({r['site_id'] for r in ordered})
  for rank,r in enumerate(ordered):
   assert (r['nearest_eligible_site']=='True')==(rank==0)
   for radius in [25,50,100]:assert int(r[f'matches_{radius}m'])==(sum(float(t['distance_m'])<=radius for t in ordered) if r['role']=='outcome' else 0)
 with (OUT/'event_atm_links.csv').open() as f:
  for r in csv.DictReader(f):
   nlinks+=1;p=pb[r['row_id']];e=eb[r['event_id']];y=int(p['outcome_year']);distance=float(r['distance_m']);isout=r['role']=='outcome'
   assert r['city']==p['city']==e['city'] and r['cohort']==p['cohort'] and r['site_id']==p['site_id'] and r['outcome_year']==p['outcome_year']
   assert r['event_date']==e['event_date'] and r['report_date']==e['report_date'] and r['report_date_usable']==e['report_date_usable'] and r['category']==e['category']
   for k in ['longitude','latitude']:assert float(r['event_'+k])==float(e[k]) and float(r['site_'+k])==float(p[k])
   d=GEOD.inv(float(p['longitude']),float(p['latitude']),float(e['longitude']),float(e['latitude']))[2];assert abs(d-distance)<1e-7
   assert int(e['event_year'])==(y if isout else y-1)
   assert 0<=d<=100 if isout else 200<d<=500
   if isout and p['cohort']=='exact_identity_supported':assert e['event_date'] in spans[(p['site_id'],y)]
   if isout and p['cohort']=='address_continuity_partial_2023':assert p['supported_start']<=e['event_date']<p['supported_end_exclusive']
   cutoff=f'{y+1 if isout else y}-01-01';known=e['report_date_usable']=='True' and e['report_date']<cutoff
   assert known==(r['report_available_by_cutoff']=='True');c=counts[r['row_id']]
   if isout:
    for radius in [25,50,100]:
     if d<=radius:
      c[f'primary_count_{radius}m']+=1;c[f'{e["category"]}_count_{radius}m']+=1;c[f'primary_reported_count_{radius}m']+=known;c[f'primary_nearest_count_{radius}m']+=r['nearest_eligible_site']=='True';c[f'multiple_match_count_{radius}m']+=int(r[f'matches_{radius}m'])>1
   else:
    c['background_unfiltered_200_500m']+=1;c['background_primary_200_500m']+=known;c['background_missing_invalid_report']+=e['report_date_usable']!='True';c['background_late_report']+=e['report_date_usable']=='True' and not known
   key=(r['cohort'],r['city'],r['outcome_year'],r['event_id'],r['role'])
   if key!=previous:check_group(group);group=[];previous=key
   group.append(r)
 check_group(group)
 for p in panel:
  c=counts[p['row_id']]
  for k,v in p.items():
   if ('_count_' in k and not k.startswith('rounding_')) or k in ['background_unfiltered_200_500m','background_primary_200_500m','background_missing_invalid_report','background_late_report']:assert int(v)==c[k],(p['row_id'],k,v,c[k])
  for radius in [25,50,100]:
   assert int(p[f'primary_any_{radius}m'])==int(int(p[f'primary_count_{radius}m'])>0)
   assert int(p[f'primary_count_{radius}m'])==int(p[f'robbery_count_{radius}m'])+int(p[f'burglary_count_{radius}m'])
   if p['city']=='Buffalo':assert int(p[f'rounding_scenario_lower_count_{radius}m'])<=int(p[f'primary_count_{radius}m'])<=int(p[f'rounding_scenario_upper_count_{radius}m'])
  assert int(p['background_unfiltered_200_500m'])==sum(int(p[k]) for k in ['background_primary_200_500m','background_missing_invalid_report','background_late_report'])
  assert (p['background_has_unknown_availability']=='True')==(int(p['background_missing_invalid_report'])>0)
  if int(p['background_unfiltered_200_500m']):assert abs(float(p['background_report_date_coverage'])-(1-int(p['background_missing_invalid_report'])/int(p['background_unfiltered_200_500m'])))<1e-12
  else:assert p['background_report_date_coverage']==''
  assert int(p['primary_count_25m'])<=int(p['primary_count_50m'])<=int(p['primary_count_100m'])
 check(True,'Every link distance, temporal eligibility, multiplicity, nearest flag and panel count reconciles',{'links':nlinks})
 # Direct geodesics against all city-year events bypass the candidate index entirely.
 eventgroups=collections.defaultdict(list)
 for e in primary:eventgroups[(e['city'],int(e['event_year']))].append(e)
 sampled=0
 for cohort in sorted({p['cohort'] for p in panel}):
  for y in YEARS:
   for city in CITIES:
    pp=sorted([p for p in panel if p['cohort']==cohort and int(p['outcome_year'])==y and p['city']==city],key=lambda p:hashlib.sha256(p['row_id'].encode()).hexdigest())
    sample=pp[:12]
    zeros=[p for p in pp if p['primary_count_50m']=='0'];sample += [p for p in zeros[:2] if p not in sample]
    for p in sample:
     sampled+=1
     for ey in [y-1,y]:
      es=eventgroups[(city,ey)];lon=np.array([float(e['longitude']) for e in es]);lat=np.array([float(e['latitude']) for e in es]);ds=GEOD.inv(np.full(len(es),float(p['longitude'])),np.full(len(es),float(p['latitude'])),lon,lat)[2]
      if ey==y:
       active=np.array([cohort=='address_continuity_full_year' or (p['supported_start']<=e['event_date']<p['supported_end_exclusive'] if cohort=='address_continuity_partial_2023' else e['event_date'] in spans[(p['site_id'],y)]) for e in es])
       for radius in [25,50,100]:assert int(p[f'primary_count_{radius}m'])==int(np.sum((ds<=radius)&active)),p['row_id']
       if city=='Buffalo':
        uncertainty=GEOD.inv(lon,lat,lon+.0005,lat+.0005)[2]
        for radius in [25,50,100]:
         assert int(p[f'rounding_scenario_lower_count_{radius}m'])==int(np.sum((ds+uncertainty<=radius)&active))
         assert int(p[f'rounding_scenario_upper_count_{radius}m'])==int(np.sum((np.maximum(0,ds-uncertainty)<=radius)&active))
      else:
       annulus=(ds>200)&(ds<=500);known=np.array([e['report_date_usable']=='True' and e['report_date']<f'{y}-01-01' for e in es]);assert int(p['background_unfiltered_200_500m'])==int(np.sum(annulus));assert int(p['background_primary_200_500m'])==int(np.sum(annulus&known))
     xy=TRANS[city].transform(float(p['longitude']),float(p['latitude']));point=Point(*xy);poly=transform(TRANS[city].transform,polys[city]);annulus=point.buffer(500,quad_segs=64).difference(point.buffer(200,quad_segs=64));assert abs(annulus.intersection(poly).area/annulus.area-float(p['annulus_fraction_inside_city']))<1e-10
 check(True,'Brute-force direct geodesics detect omitted links; boundary and rounding sensitivities replay',{'sampled_site_years':sampled,'includes_observed_zero_sites':True})
 for name in ['qa/manual_linkage_audit.csv','qa/facility_review.csv','crime_codebook.csv']:check(all(r['reviewer_decision']=='PENDING' for r in read(OUT/name)),'No fabricated human approval: '+name)
 result={'status':'PASS','scope':'user_revised_maximum_recovered_continuous_snapshot_period','full_years':[2024,2025],'partial_years':[2023,2024,2025],'snapshot_start':str(dates[0]),'snapshot_end':str(dates[-1]),'snapshots':len(dates),'full_year_site_years':len(full),'partial_2023_continuity_site_years':len(early),'exact_supported_site_years':len(partial),'primary_events':len(primary),'all_unique_events':len(events),'excluded_rows':len(excluded),'duplicate_rows':len(duplicates),'link_rows':nlinks,'checks':checks,'scientific_acceptance':'PENDING independent construct, facility, exposure, linkage and coordinate review','confirmatory_eligible':False}
 savejson(REPORTS/'validation.json',result);print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2),flush=True)
if __name__=='__main__':main()
