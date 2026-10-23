"""Build full-year and exact-identity exposure panels with streamed event links."""
import collections,csv,datetime as dt,hashlib,heapq,json,math
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point
from shapely.ops import transform
from common import *
RADII=[25,50,100]
LINK_FIELDS=['cohort','city','site_id','row_id','outcome_year','event_id','event_date','report_date','report_date_usable','category','distance_m','role','report_available_by_cutoff','nearest_eligible_site','matches_25m','matches_50m','matches_100m','site_longitude','site_latitude','event_longitude','event_latitude']

def main():
 freeze();events=read(OUT/'crime_primary_2022_2025.csv');eg=collections.defaultdict(list)
 for e in events:
  for k in ['longitude','latitude','easting_m','northing_m']:e[k]=float(e[k])
  e['report_date_usable']=e['report_date_usable']=='True';eg[(e['city'],int(e['event_year']))].append(e)
 full=read(OUT/'atm_sites_full_year.csv');early=read(OUT/'atm_sites_partial_2023.csv');partial=[r for r in read(OUT/'qa/exact_exposure_inventory.csv') if int(r['supported_days'])>0]
 spans=collections.defaultdict(list)
 for r in read(OUT/'qa/exact_exposure_intervals.csv'):spans[(r['site_id'],int(r['outcome_year']))].append((r['start_inclusive'],r['end_exclusive']))
 polys=polygons();projected={c:transform(TRANS[c].transform,p) for c,p in polys.items()};boundarycache={};audit={};panels=[];facilities=[];nlinks=0
 def geometry(s):
  key=s['site_id']
  if key not in boundarycache:
   c=s['city'];x,y=TRANS[c].transform(s['longitude'],s['latitude']);point=Point(x,y);poly=projected[c];annulus=point.buffer(500,quad_segs=64).difference(point.buffer(200,quad_segs=64));fraction=annulus.intersection(poly).area/annulus.area
   boundarycache[key]={'boundary_distance_projected_m':point.distance(poly.boundary),'annulus_fraction_inside_city':fraction,'boundary_buffer_clear_500m':point.distance(poly.boundary)>502}
  return boundarycache[key]
 linkpath=OUT/'event_atm_links.csv'
 with linkpath.open('w',newline='') as stream:
  writer=csv.DictWriter(stream,fieldnames=LINK_FIELDS);writer.writeheader()
  for cohort,sites in [('osm_continuity_full_year',full),('osm_continuity_partial_2023',early),('exact_identity_supported',partial)]:
   for year in YEARS:
    for city in CITIES:
     ss=[dict(s) for s in sites if s['city']==city and int(s['outcome_year'])==year]
     if not ss:continue
     for s in ss:
      for k in ['longitude','latitude']:s[k]=float(s[k])
      for k in ['outcome_year','supported_days','calendar_days']:s[k]=int(s[k])
     xy=np.array([TRANS[city].transform(s['longitude'],s['latitude']) for s in ss]);tree=cKDTree(xy);counts={s['site_id']:collections.Counter() for s in ss}
     for a,b in sorted(tree.query_pairs(10.1)):
      sa,sb=ss[a],ss[b];distance=GEOD.inv(sa['longitude'],sa['latitude'],sb['longitude'],sb['latitude'])[2]
      if distance<=10:facilities.append({'cohort':cohort,'city':city,'outcome_year':year,'site_a':sa['site_id'],'site_b':sb['site_id'],'distance_m':distance,'reviewer_decision':'PENDING'})
     for eventyear in [year-1,year]:
      isoutcome=eventyear==year;cutoff=f'{year+1 if isoutcome else year}-01-01'
      for e in eg[(city,eventyear)]:
       matches=[];known=e['report_date_usable'] and e['report_date']<cutoff
       for j in tree.query_ball_point([e['easting_m'],e['northing_m']],502):
        s=ss[j]
        if isoutcome and cohort=='exact_identity_supported' and not any(a<=e['event_date']<b for a,b in spans[(s['site_id'],year)]):continue
        if isoutcome and cohort=='osm_continuity_partial_2023' and not s['supported_start']<=e['event_date']<s['supported_end_exclusive']:continue
        distance=GEOD.inv(s['longitude'],s['latitude'],e['longitude'],e['latitude'])[2]
        if (isoutcome and distance<=100) or (not isoutcome and 200<distance<=500):matches.append((distance,s))
       matches.sort(key=lambda pair:(pair[0],pair[1]['site_id']));multiplicity={r:sum(d<=r for d,_ in matches) if isoutcome else 0 for r in RADII}
       for rank,(distance,s) in enumerate(matches):
        c=counts[s['site_id']];rowid=f"{cohort}:{s['site_id']}:{year}"
        link={'cohort':cohort,'city':city,'site_id':s['site_id'],'row_id':rowid,'outcome_year':year,'event_id':e['event_id'],'event_date':e['event_date'],'report_date':e['report_date'],'report_date_usable':e['report_date_usable'],'category':e['category'],'distance_m':distance,'role':'outcome' if isoutcome else 'background','report_available_by_cutoff':known,'nearest_eligible_site':rank==0,**{f'matches_{r}m':multiplicity[r] for r in RADII},'site_longitude':s['longitude'],'site_latitude':s['latitude'],'event_longitude':e['longitude'],'event_latitude':e['latitude']}
        writer.writerow(link);nlinks+=1
        if isoutcome:
         for radius in RADII:
          if distance<=radius:
           c[f'primary_count_{radius}m']+=1;c[f'{e["category"]}_count_{radius}m']+=1;c[f'primary_reported_count_{radius}m']+=int(known);c[f'primary_nearest_count_{radius}m']+=int(rank==0);c[f'multiple_match_count_{radius}m']+=int(multiplicity[radius]>1)
        else:
         c['background_unfiltered_200_500m']+=1;c['background_primary_200_500m']+=int(known);c['background_missing_invalid_report']+=int(not e['report_date_usable']);c['background_late_report']+=int(e['report_date_usable'] and not known)
        band=next(str(r) for r in [25,50,100,500] if distance<=r);stratum=(cohort,year,city,link['role'],e['category'],band,multiplicity[50]>1)
        h=int(hashlib.sha256((rowid+e['event_id']).encode()).hexdigest(),16);bucket=audit.setdefault(stratum,[])
        entry=(-h,rowid+e['event_id'],link)
        if len(bucket)<5:heapq.heappush(bucket,entry)
        elif entry>bucket[0]:heapq.heapreplace(bucket,entry)
     for s in ss:
      c=counts[s['site_id']];p={k:s.get(k,'') for k in ['site_id','city','address_raw','address_normalized','longitude','latitude','institution','outcome_year','supported_days','calendar_days','osm_id','osm_amenity','osm_atm_tag','osm_geometry_is_centroid','source_population']}
      p.update(cohort=cohort,row_id=f"{cohort}:{s['site_id']}:{year}",background_year=year-1,full_year_supported=s['supported_days']==s['calendar_days'],exposure_rule='osm_id_14_months_max_50m_drift' if cohort=='osm_continuity_full_year' else 'exact_identity_adjacent_monthly_snapshots_gap_le_62_days',max_coordinate_drift_m=s.get('max_coordinate_drift_m',''),strict_exact_identity_full_year=s.get('strict_exact_identity_full_year',s.get('exact_full_year','')),confirmatory_eligible=False,actual_active_days='',actual_opening_date='',actual_closing_date='',coordinate_precision_flag='public_block_geocode' if city in ['Chicago','Los Angeles'] else 'public_geocode_unverified',report_time_is_ingestion_proxy=False,**geometry(s))
      p['supported_start']=s['supported_start'] if cohort=='osm_continuity_partial_2023' else f'{year}-01-01' if cohort=='osm_continuity_full_year' else min(a for a,b in spans[(s['site_id'],year)])
      p['supported_end_exclusive']=s['supported_end_exclusive'] if cohort=='osm_continuity_partial_2023' else f'{year+1}-01-01' if cohort=='osm_continuity_full_year' else max(b for a,b in spans[(s['site_id'],year)])
      p['supported_interval_count']=len(spans[(s['site_id'],year)]) if cohort=='exact_identity_supported' else 1
      if cohort=='osm_continuity_partial_2023':p['exposure_rule']='osm_id_12_months_max_50m_drift_313_day_partial_2023'
      for radius in RADII:
       for prefix in ['primary','robbery','burglary','primary_reported','primary_nearest','multiple_match']:p[f'{prefix}_count_{radius}m']=c[f'{prefix}_count_{radius}m']
       p[f'primary_any_{radius}m']=int(c[f'primary_count_{radius}m']>0)
      for key in ['background_unfiltered_200_500m','background_primary_200_500m','background_missing_invalid_report','background_late_report']:p[key]=c[key]
      p['background_report_date_coverage']=1-c['background_missing_invalid_report']/c['background_unfiltered_200_500m'] if c['background_unfiltered_200_500m'] else ''
      p['background_has_unknown_availability']=c['background_missing_invalid_report']>0
      p['background_measurement_status']='unavailable_original_report_dates' if city=='Chicago' else 'incomplete_report_dates' if c['background_missing_invalid_report'] else 'report_filtered_latest_extract'
      if city=='Chicago':
       p['background_primary_200_500m']=''
       for radius in RADII:p[f'primary_reported_count_{radius}m']=''
      p['la_reporting_system_break']=city=='Los Angeles'
      p['exposure_is_mapping_continuity']=True
      panels.append(p)
     print(cohort,city,year,'sites',len(ss),'cumulative links',nlinks,flush=True)
 write('atm_panel_full_year_2024_2025.csv',[p for p in panels if p['cohort']=='osm_continuity_full_year'])
 write('atm_panel_partial_2023.csv',[p for p in panels if p['cohort']=='osm_continuity_partial_2023'])
 write('atm_panel_continuity_2023_2025.csv',[p for p in panels if p['cohort'].startswith('osm_continuity')])
 write('atm_panel_exact_supported_2023_2025.csv',[p for p in panels if p['cohort']=='exact_identity_supported'])
 for year in [2024,2025]:write(f'atm_panel_{year}_full_year.csv',[p for p in panels if p['cohort']=='osm_continuity_full_year' and p['outcome_year']==year])
 write('qa/facility_review.csv',facilities,['cohort','city','outcome_year','site_a','site_b','distance_m','reviewer_decision'])
 auditrows=[]
 for stratum,bucket in sorted(audit.items()):
  for _,_,link in sorted(bucket,reverse=True):auditrows.append(link|{'stratum':str(stratum),'reviewer_decision':'PENDING','reviewer':'','notes':''})
 write('qa/manual_linkage_audit.csv',auditrows)
 summary=[]
 for cohort in ['osm_continuity_full_year','osm_continuity_partial_2023','exact_identity_supported']:
  for year in YEARS:
   if cohort=='osm_continuity_partial_2023' and year!=2023:continue
   for city in CITIES:
    pp=[p for p in panels if p['cohort']==cohort and p['outcome_year']==year and p['city']==city]
    summary.append({'cohort':cohort,'city':city,'outcome_year':year,'site_years':len(pp) if pp else '', 'status':'observed_supported' if pp else 'UNAVAILABLE_full_year_exposure','supported_site_days':sum(p['supported_days'] for p in pp) if pp else '', 'positive_50m':sum(p['primary_any_50m'] for p in pp) if pp else '', 'prevalence_50m':sum(p['primary_any_50m'] for p in pp)/len(pp) if pp else '', 'incident_site_links_50m':sum(p['primary_count_50m'] for p in pp) if pp else '', 'boundary_clear_sites':sum(p['boundary_buffer_clear_500m'] for p in pp) if pp else '', 'strict_exact_full_year_sites':sum(p['strict_exact_identity_full_year'] in [True,'True'] for p in pp) if pp else ''})
 write('city_summary.csv',summary)
 savejson(REPORTS/'build_counts.json',{'panel_rows':len(panels),'link_rows':nlinks,'audit_rows':len(auditrows),'full_year_rows':sum(p['cohort']=='osm_continuity_full_year' for p in panels),'partial_2023_continuity_rows':sum(p['cohort']=='osm_continuity_partial_2023' for p in panels),'exact_supported_rows':sum(p['cohort']=='exact_identity_supported' for p in panels)})
if __name__=='__main__':main()
