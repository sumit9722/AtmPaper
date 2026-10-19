"""Normalize all raw city/year partitions with retained exclusions and conflicts."""
import collections,datetime as dt,json
from zoneinfo import ZoneInfo
from common import *

def epoch(value):
 if value is None:return ''
 try:return dt.datetime.fromtimestamp(float(value)/1000,dt.timezone.utc).astimezone(ZoneInfo('America/New_York')).isoformat()
 except (ValueError,TypeError,OverflowError,OSError):return ''
def date_valid(value):
 try:return dt.date.fromisoformat(str(value)[:10])
 except ValueError:return None

def main():
 freeze();polys=polygons();events=[];excluded=[];duplicates=[];codebook={};raw_counts=collections.Counter();precision=collections.Counter()
 for city,slug in CITIES.items():
  grouped={}
  for year in range(2022,2026):
   for path in sorted((RAW/f'crime/{slug}/{year}').rglob('page_*.json')):
    if '.request.' in path.name:continue
    obj=json.loads(path.read_text());rows=obj['features'] if isinstance(obj,dict) else obj
    for index,raw in enumerate(rows):
     raw_counts[(city,year)]+=1;a=raw.get('attributes',raw)
     if slug=='nyc':
      case=a.get('cmplnt_num');occ=a.get('cmplnt_fr_dt','');report=a.get('rpt_dt','');offense=a.get('ofns_desc','');desc=a.get('pd_desc','');code=a.get('pd_cd','');lon=number(a.get('longitude'));lat=number(a.get('latitude'));attempt=a.get('crm_atpt_cptd_cd','');address='';native=a.get('source_row_id');proxy=False
      if a.get('cmplnt_fr_tm') and occ:occ=occ[:10]+'T'+a['cmplnt_fr_tm']
     elif slug=='buffalo':
      case=a.get('case_number');occ=a.get('incident_datetime','');report=a.get('created_at','');offense=a.get('incident_type_primary','');desc=a.get('incident_description','');code=offense;lon=number(a.get('longitude'));lat=number(a.get('latitude'));attempt='not_published';address=a.get('address_1','');native=a.get('source_row_id');proxy=True
     else:
      case=a.get('Case_Number');occ=epoch(a.get('OccurredFrom_Timestamp'));report=epoch(a.get('Reported_Timestamp'));offense=a.get('Statute_Text','');desc=(a.get('Statute_Description') or '').strip();code=str(a.get('Statute_Section') or '').strip();geom=raw.get('geometry') or {};lon=number(geom.get('x'));lat=number(geom.get('y'));attempt=a.get('Statute_Attempted','');address=a.get('Address_StreetFull','');native=a.get('OBJECTID');proxy=False
     offense=offense or '';desc=desc or '';category=offense.strip().lower() if offense.strip().upper() in ['ROBBERY','BURGLARY'] else 'other';primary=category!='other'
     ck=(city,str(code),offense,desc)
     if ck not in codebook:codebook[ck]={'city':city,'native_code':code,'native_offense':offense,'native_description':desc,'category':category,'primary_included':primary,'source_rows':0,'reviewer_decision':'PENDING'}
     codebook[ck]['source_rows']+=1
     od=date_valid(occ);rd=date_valid(report);chronology=bool(od and rd and rd<od);report_valid=bool(rd and not chronology)
     r={'city':city,'event_id':f'{slug}:{case}' if case else '', 'native_case_id':str(case or ''),'native_row_id':str(native),'occurrence_datetime_local':occ,'event_date':str(od) if od else '', 'event_year':od.year if od else '', 'report_datetime':report,'report_date':str(rd) if rd else '', 'report_date_usable':report_valid,'report_before_occurrence':chronology,'report_time_is_ingestion_proxy':proxy,'category':category,'primary_included':primary,'native_offense':offense,'native_code':code,'native_description':desc,'attempt_status':attempt,'longitude':lon,'latitude':lat,'address_raw':address,'source_file':str(path.relative_to(ROOT)),'source_row_index':index,'source_partition_year':year,'coordinate_precision_flag':'rounded_block_address' if slug=='buffalo' else 'public_geocode_unverified'}
     reasons=[]
     if not case:reasons.append('missing_case_id')
     if not od:reasons.append('invalid_occurrence_date')
     elif od.year!=year:reasons.append('occurrence_year_disagrees_with_source_partition')
     if lon is None or lat is None:reasons.append('missing_invalid_coordinates')
     elif locate(lon,lat,polys)!=city:reasons.append('outside_city_polygon')
     if reasons:excluded.append(r|{'exclusion_reasons':'|'.join(reasons)});continue
     key=r['event_id']
     if key in grouped:
      old=grouped[key]
      priority=lambda x:({'robbery':2,'burglary':1,'other':0}[x['category']],x['occurrence_datetime_local'],x['source_file'],x['source_row_index'])
      keep,drop=(r,old) if priority(r)>priority(old) else (old,r);grouped[key]=keep
      duplicates.append(drop|{'kept_source_file_at_resolution':keep['source_file'],'kept_source_row_at_resolution':keep['source_row_index'],'year_conflict':r['event_year']!=old['event_year'],'coordinate_conflict':(r['longitude'],r['latitude'])!=(old['longitude'],old['latitude']),'category_conflict':r['category']!=old['category'],'report_date_conflict':r['report_date']!=old['report_date'],'rule':'city_case_global; robbery>burglary>other; later_occurrence; source_order','reviewer_decision':'PENDING'})
     else:grouped[key]=r
  for r in grouped.values():
   x,y=TRANS[city].transform(r['longitude'],r['latitude']);r.update(easting_m=x,northing_m=y)
   for dp in [3,4,5]:r[f'coordinates_on_{dp}dp_grid']=all(abs(v-round(v,dp))<1e-8 for v in [r['longitude'],r['latitude']])
   events.append(r)
  print('Normalized',city,len(grouped),flush=True)
 fields=list(events[0]);write('crime_events_2022_2025.csv',events);write('crime_primary_2022_2025.csv',(r for r in events if r['primary_included']),fields)
 write('qa/crime_exclusions.csv',excluded,list(dict.fromkeys(fields+['exclusion_reasons'])))
 # Excluded/duplicate rows precede derived coordinates. Fill missing columns explicitly.
 write('qa/crime_duplicates.csv',duplicates,list(dict.fromkeys(fields+['kept_source_file_at_resolution','kept_source_row_at_resolution','year_conflict','coordinate_conflict','category_conflict','report_date_conflict','rule','reviewer_decision'])))
 write('crime_codebook.csv',codebook.values())
 monthcounts=collections.Counter((r['city'],r['event_date'][:7],r['primary_included']) for r in events)
 write('crime_monthly_coverage.csv',[{'city':c,'month':f'{y}-{m:02d}','unique_valid_cases':sum(monthcounts[(c,f'{y}-{m:02d}',k)] for k in [False,True]),'primary_cases':monthcounts[(c,f'{y}-{m:02d}',True)],'source_scope':'primary_only' if c=='New York City' else 'all_published_categories','zero_is_observed_after_acquisition':True} for c in CITIES for y in range(2022,2026) for m in range(1,13)])
 qa=[]
 for c in CITIES:
  for y in range(2022,2026):
   es=[r for r in events if r['city']==c and r['event_year']==y];primary=[r for r in es if r['primary_included']]
   qa.append({'city':c,'year':y,'source_rows':raw_counts[(c,y)],'unique_valid_cases':len(es),'primary_cases':len(primary),'excluded_source_rows':sum(r['city']==c and r['source_partition_year']==y for r in excluded),'duplicate_source_rows':sum(r['city']==c and r['source_partition_year']==y for r in duplicates),'missing_invalid_report_primary':sum(not r['report_date_usable'] for r in primary),'report_before_occurrence_primary':sum(r['report_before_occurrence'] for r in primary),'reported_after_year_primary':sum(r['report_date_usable'] and r['report_date']>=f'{y+1}-01-01' for r in primary),'primary_coordinates_on_3dp_grid':sum(r['coordinates_on_3dp_grid'] for r in primary),'primary_coordinates_on_4dp_grid':sum(r['coordinates_on_4dp_grid'] for r in primary),'primary_coordinates_on_5dp_grid':sum(r['coordinates_on_5dp_grid'] for r in primary)})
 write('qa/crime_quality_by_city_year.csv',qa)
 print('Crime build complete',len(events),'unique cases',len(excluded),'excluded',len(duplicates),'duplicate rows',flush=True)
if __name__=='__main__':main()
