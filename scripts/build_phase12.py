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
    for f in sorted((ROOT/'data/raw'/city).glob('page_*.json')):
        if '.request.' in f.name:continue
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

def build_sites():
    records=[];sites={};excluded=[]
    for raw,path,row in readpages('dfs'):
        coords=raw.get('georeference',{}).get('coordinates',[None,None])
        lon,lat=map(number,coords);city=locate(lon,lat)
        r={'source_record_index':row,'source_file':path,'institution_raw':raw.get('name_of_institution',''),
           'address_raw':raw.get('street_address',''),'postal_city_raw':raw.get('city',''),'county_raw':raw.get('county',''),
           'zip_raw':raw.get('zip_code',''),'address_normalized':norm(raw.get('street_address','')),
           'latitude':lat,'longitude':lon,'city':city,'snapshot_date':'2026-09-15',
           'active_from':'','active_to':'','active_days':'','exposure_status':'current_snapshot_only'}
        if not city:
            r['exclusion_reason']='missing_or_invalid_coordinates' if lon is None or lat is None else 'outside_three_city_polygons'
            excluded.append(r);continue
        # Exact duplicate addresses/points are the same physical site, regardless of bank name.
        key=f'{city}|{r["address_normalized"]}|{lon:.7f}|{lat:.7f}'
        site_id='dfs_'+sid(key);r['site_id']=site_id
        if site_id not in sites:
            x,y=TRANS[city].transform(lon,lat)
            sites[site_id]={**r,'easting_m':x,'northing_m':y,'analysis_crs':f'EPSG:{CITIES[city][1]}','source_record_count':0}
        sites[site_id]['source_record_count']+=1
        records.append(r)
    sites=list(sites.values())
    for city in CITIES:
        subset=[s for s in sites if s['city']==city]
        xy=np.array([[s['easting_m'],s['northing_m']] for s in subset])
        parents=list(range(len(subset)))
        def root(i):
            while parents[i]!=i:
                parents[i]=parents[parents[i]];i=parents[i]
            return i
        for a,b in cKDTree(xy).query_pairs(10.1):
            sa,sb=subset[a],subset[b]
            if GEOD.inv(sa['longitude'],sa['latitude'],sb['longitude'],sb['latitude'])[2]<=10:
                parents[root(b)]=root(a)
        groups=collections.defaultdict(list)
        for i in range(len(subset)):groups[root(i)].append(i)
        for indices in groups.values():
            cluster='cluster_'+sid('|'.join(sorted(subset[i]['site_id'] for i in indices)))
            for i in indices:
                subset[i]['site_cluster_id']=cluster;subset[i]['cluster_site_count']=len(indices)
                subset[i]['facility_review_required']=len(indices)>1
        STATS[city]['dfs_source_records']=sum(s['source_record_count'] for s in subset)
        STATS[city]['dfs_sites']=len(subset)
        STATS[city]['site_clusters']=len(groups)
    byid={s['site_id']:s for s in sites}
    for r in records:r['site_cluster_id']=byid[r['site_id']]['site_cluster_id']
    write('atm_records_three_cities.csv',records)
    write('atm_sites_three_cities.csv',sites)
    write('atm_records_excluded.csv',excluded)
    features=[{'type':'Feature','geometry':{'type':'Point','coordinates':[s['longitude'],s['latitude']]},'properties':s} for s in sites]
    (OUT/'atm_sites_three_cities.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
    return sites

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
               'available_before_2025_by_report_date':bool(report and report[:10]<'2025-01-01')}
            exclusion=''
            try:
                year=dt.date.fromisoformat(date[:10]).year
                if year not in [2024,2025]:exclusion='outside_2024_2025'
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
        for year in [2024,2025]:
            for month in range(1,13):quality.append({'city':city,'month':f'{year}-{month:02d}','unique_valid_events':months[f'{year}-{month:02d}']})
    write('crime_events_2024_2025.csv',events)
    write('crime_records_excluded.csv',excluded)
    write('crime_duplicate_rows.csv',duplicates,['city','event_id','native_row_id','event_datetime_local','event_date','report_datetime','native_offense','native_code','native_description','common_category','primary_included','broad_included','attempt_status','latitude','longitude','address_raw','source_file','source_row_index','coordinate_precision_flag','available_before_2025_by_report_date','duplicate_rule','coordinate_conflict'])
    write('crime_codebook.csv',codebook.values())
    write('crime_monthly_coverage.csv',quality)
    return events

def build_osm(sites):
    rows=[]
    for i,expected in enumerate(CITIES,1):
        d=json.loads((ROOT/f'export ({i}).json').read_text())
        for a in d['elements']:
            lon,lat=a.get('lon'),a.get('lat');city=locate(lon,lat);tags=a.get('tags',{})
            subset=[s for s in sites if s['city']==city]
            distances=[GEOD.inv(lon,lat,s['longitude'],s['latitude'])[2] for s in subset]
            nearest=int(np.argmin(distances)) if distances else None
            rows.append({'osm_id':a['id'],'osm_type':a['type'],'expected_city':expected,'polygon_city':city,
                'latitude':lat,'longitude':lon,'amenity':tags.get('amenity',''),'atm_tag':tags.get('atm',''),'name':tags.get('name',''),
                'operator':tags.get('operator',''),'snapshot_timestamp':d['osm3s']['timestamp_osm_base'],
                'nearest_dfs_site_id':subset[nearest]['site_id'] if nearest is not None else '',
                'nearest_dfs_distance_m':round(distances[nearest],3) if nearest is not None else '',
                'primary_population_included':False,'ownership_verified':False,'source_file':f'export ({i}).json'})
    write('osm_atm_candidates.csv',rows)

def link_panel(sites,events):
    links=[];panel=[];audits=[]
    for city in CITIES:
        ss=[s for s in sites if s['city']==city]
        ee=[e for e in events if e['city']==city and e['broad_included']]
        tree=cKDTree([[s['easting_m'],s['northing_m']] for s in ss])
        counts={s['site_id']:collections.Counter() for s in ss}
        for e in ee:
            candidates=tree.query_ball_point([e['easting_m'],e['northing_m']],502)
            matches=[]
            for j in candidates:
                s=ss[j];dist=GEOD.inv(e['longitude'],e['latitude'],s['longitude'],s['latitude'])[2]
                if dist<=500:matches.append((dist,s))
            matches.sort(key=lambda x:(x[0],x[1]['site_id']))
            mult={r:sum(d<=r for d,s in matches) for r in [25,50,100]}
            for rank,(distance,s) in enumerate(matches):
                target=e['event_date'].startswith('2025') and distance<=100
                bg=e['event_date'].startswith('2024') and 200<distance<=500
                if not target and not bg:continue
                row={'city':city,'event_id':e['event_id'],'site_id':s['site_id'],'site_cluster_id':s['site_cluster_id'],
                    'event_date':e['event_date'],'native_offense':e['native_offense'],'common_category':e['common_category'],
                    'primary_included':e['primary_included'],'broad_included':e['broad_included'],
                    'event_latitude':e['latitude'],'event_longitude':e['longitude'],'atm_latitude':s['latitude'],'atm_longitude':s['longitude'],
                    'distance_m':round(distance,4),'link_role':'outcome_2025' if target else 'background_2024',
                    'within_25m':distance<=25,'within_50m':distance<=50,'within_100m':distance<=100,
                    'matches_25m':mult[25],'matches_50m':mult[50],'matches_100m':mult[100],
                    'nearest_site':rank==0,'background_reported_before_2025':bg and e['available_before_2025_by_report_date']}
                links.append(row);c=counts[s['site_id']]
                if target:
                    for radius in [25,50,100]:
                        if distance<=radius:
                            c[f'broad_count_{radius}m']+=1
                            if e['primary_included']:
                                c[f'primary_count_{radius}m']+=1
                                c[f'{e["common_category"]}_count_{radius}m']+=1
                                if rank==0:c[f'primary_nearest_count_{radius}m']+=1
                if bg:
                    c['background_broad_2024_200_500m']+=1
                    if e['primary_included']:
                        c['background_primary_2024_200_500m']+=1
                        if e['available_before_2025_by_report_date']:c['background_primary_reported_before_2025']+=1
            if mult[50]>1 and e['event_date'].startswith('2025') and e['primary_included']:STATS[city]['primary_events_multiple_sites_50m']+=1
        for s in ss:
            c=counts[s['site_id']]
            p={k:s[k] for k in ['city','site_id','site_cluster_id','latitude','longitude','address_raw','institution_raw','snapshot_date','cluster_site_count']}
            p.update(outcome_year=2025,background_year=2024,exposure_status='unknown_historical_activity',active_from='',active_to='',active_days='',
                     analysis_status='exploratory_current_snapshot_backcast',confirmatory_eligible=False,
                     coordinate_precision_flag='rounded_block_address' if city=='Buffalo' else 'public_geocode_unverified')
            for radius in [25,50,100]:
                for prefix in ['primary','broad','robbery','burglary','primary_nearest']:p[f'{prefix}_count_{radius}m']=c[f'{prefix}_count_{radius}m']
                p[f'primary_any_{radius}m']=int(c[f'primary_count_{radius}m']>0)
            for field in ['background_broad_2024_200_500m','background_primary_2024_200_500m','background_primary_reported_before_2025']:p[field]=c[field]
            p['background_vintage_status']='latest_extract; report-date cutoff does not recover historical database vintage'
            panel.append(p)
        STATS[city]['sites_positive_50m']=sum(p['primary_any_50m'] for p in panel if p['city']==city)
        STATS[city]['primary_site_event_links_50m']=sum(p['primary_count_50m'] for p in panel if p['city']==city)
        # Deterministic stratification includes outcome radii, financial/broad categories and backgrounds.
        strata=collections.defaultdict(list)
        for l in links:
            if l['city']!=city:continue
            band='0_25' if l['distance_m']<=25 else '25_50' if l['distance_m']<=50 else '50_100' if l['distance_m']<=100 else '200_500'
            strata[(band,l['primary_included'],l['matches_50m']>1)].append(l)
        for key,ls in strata.items():
            for l in sorted(ls,key=lambda x:sid(x['event_id']+x['site_id']))[:5]:
                audits.append({**l,'audit_stratum':str(key),'reviewer_decision':'PENDING','reviewer':'','review_notes':''})
    write('event_atm_links.csv',links)
    write('atm_panel_2025_EXPLORATORY.csv',panel)
    write('manual_linkage_audit.csv',audits)
    cohort=[{'city':s['city'],'site_id':s['site_id'],'latitude':s['latitude'],'longitude':s['longitude'],
             'snapshot_date':s['snapshot_date'],'planned_followup_start':'2026-10-01','planned_followup_end':'2027-09-30',
             'activity_during_followup':'requires_monthly_verification','outcome_count':'','outcome_any':'','status':'future_outcomes_not_observed'} for s in sites]
    write('prospective_cohort_PENDING.csv',cohort)
    return panel

def manifest():
    rows=[]
    paths=[p for folder in ['dfs','nyc','buffalo','rochester','boundaries','metadata','atm_history'] for p in (ROOT/'data/raw'/folder).rglob('*')]+[ROOT/'query.json',ROOT/'sorted_data.csv']+[ROOT/f'export ({i}).json' for i in [1,2,3]]
    for p in sorted(paths):
        if not p.is_file() or '.request.' in p.name:continue
        data=p.read_bytes();side=p.with_suffix(p.suffix+'.request.json')
        request=json.loads(side.read_text()) if side.exists() else {}
        count='';minimum='';maximum='';missing=''
        try:
            j=json.loads(data)
            if isinstance(j,list):count=len(j)
            elif 'features' in j:count=len(j['features'])
            elif 'elements' in j:count=len(j['elements'])
        except (ValueError,UnicodeDecodeError):pass
        rows.append({'file':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'row_count':count,
            'retrieved_utc':request.get('retrieved_utc','not_recorded_for_supplied_or_initial_metadata_file'),
            'url_and_exact_query':request.get('url','see_source_register'),'raw_modified':False,
            'source_coordinate_crs':'EPSG:4326 for downloaded point/polygon geometries',
            'available_before_2025':'not_verified; current extracts are retrospective revisions'})
    write('source_manifest.csv',rows)

def main():
    sites=build_sites();build_osm(sites);events=build_crimes();panel=link_panel(sites,events);manifest()
    write('city_summary.csv',[{'city':city,**dict(stats)} for city,stats in STATS.items()])
    (ROOT/'reports/qa_summary.json').write_text(json.dumps(STATS,indent=2))
    print(json.dumps(STATS,indent=2))
    assert len(panel)==len(sites)
    assert len({e['event_id'] for e in events})==len(events)
    assert all(p['primary_count_25m']<=p['primary_count_50m']<=p['primary_count_100m'] for p in panel)
    assert all(not p['confirmatory_eligible'] and p['active_days']=='' for p in panel)
    assert all(p['primary_nearest_count_50m']<=p['primary_count_50m'] for p in panel)
    print('Panel invariants passed.')

if __name__=='__main__':main()
