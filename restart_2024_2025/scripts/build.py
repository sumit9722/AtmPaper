"""Offline 2024 phase 1/2 build from copied official archives."""
import datetime as dt
import collections
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import crime_inputs as crime
import exposure_inputs as exposure
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/processed'
def write(name, rows, fields=None):
    rows=list(rows); path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    spec=ROOT/'protocol/study_spec.md'
    (ROOT/'reports/protocol_freeze.json').write_text(json.dumps({'specification':'protocol/study_spec.md','sha256':digest(spec),'status':'retrospective_working_specification'},indent=2))
    sites=exposure.full_year(2024)+exposure.full_year(2025)
    events=crime.build_crimes()
    primary=[e for e in events if e['primary_included']]
    write('crime_primary_2023_2025.csv',primary)
    links=[];panels=[];facilities=[]
    for outcome_year in [2024,2025]:
        for city in crime.CITIES:
            ss=[s for s in sites if s['city']==city and s['year']==outcome_year]
            xy=np.array([crime.TRANS[city].transform(s['longitude'],s['latitude']) for s in ss])
            tree=cKDTree(xy); counts={s['site_id']:collections.Counter() for s in ss}
            for a,b in tree.query_pairs(10.1):
                x,y=ss[a],ss[b]; d=crime.GEOD.inv(x['longitude'],x['latitude'],y['longitude'],y['latitude'])[2]
                if d<=10:facilities.append({'city':city,'outcome_year':outcome_year,'site_a':x['site_id'],'site_b':y['site_id'],'distance_m':d,'reviewer_decision':'PENDING'})
            for e in primary:
                if e['city']!=city:continue
                year=int(e['event_date'][:4]); matches=[]
                if year not in [outcome_year-1,outcome_year]:continue
                for j in tree.query_ball_point([e['easting_m'],e['northing_m']],502):
                    s=ss[j];d=crime.GEOD.inv(e['longitude'],e['latitude'],s['longitude'],s['latitude'])[2]
                    if (year==outcome_year and d<=100) or (year==outcome_year-1 and 200<d<=500):matches.append((d,s))
                matches.sort(key=lambda pair:(pair[0],pair[1]['site_id']))
                for rank,(d,s) in enumerate(matches):
                    known=bool(e['report_datetime'] and e['report_datetime'][:10]<f'{year+1}-01-01')
                    r={'city':city,'site_id':s['site_id'],'outcome_year':outcome_year,'event_id':e['event_id'],'event_date':e['event_date'],'report_datetime':e['report_datetime'],'category':e['common_category'],'distance_m':d,'role':'outcome' if year==outcome_year else 'background','reported_by_year_end':known,'nearest_cohort_site':rank==0,'event_longitude':e['longitude'],'event_latitude':e['latitude'],'site_longitude':s['longitude'],'site_latitude':s['latitude']}
                    c=counts[s['site_id']]
                    for radius in [25,50,100]:
                        r[f'matches_{radius}m']=sum(md<=radius for md,_ in matches) if year==outcome_year else 0
                        if year==outcome_year and d<=radius:
                            c[f'primary_count_{radius}m']+=1
                            c[f'{e["common_category"]}_count_{radius}m']+=1
                            c[f'primary_reported_count_{radius}m']+=int(known)
                            c[f'primary_nearest_count_{radius}m']+=int(rank==0)
                    if year==outcome_year-1:
                        c['background_unfiltered_200_500m']+=1
                        c['background_primary_200_500m']+=int(known)
                        c['background_missing_report']+=int(not e['report_datetime'])
                        c['background_late_report']+=int(bool(e['report_datetime']) and not known)
                    links.append(r)
            for s in ss:
                c=counts[s['site_id']];p=s|{'row_id':s['site_id']+':'+str(outcome_year),'outcome_year':outcome_year,'background_year':outcome_year-1,'exposure_rule':'unique_address_all_14_snapshots_max_50m_drift','confirmatory_eligible':False,'actual_active_days':'','actual_opening_date':'','actual_closing_date':'','coordinate_precision_flag':'rounded_block_address' if city=='Buffalo' else 'public_geocode_unverified'}
                for radius in [25,50,100]:
                    for prefix in ['primary','robbery','burglary','primary_reported','primary_nearest']:p[f'{prefix}_count_{radius}m']=c[f'{prefix}_count_{radius}m']
                    p[f'primary_any_{radius}m']=int(c[f'primary_count_{radius}m']>0)
                for key in ['background_unfiltered_200_500m','background_primary_200_500m','background_missing_report','background_late_report']:p[key]=c[key]
                panels.append(p)
    write('atm_panel_2024_2025_full_year.csv',panels);write('event_atm_links.csv',links)
    write('qa/facility_review.csv',facilities,['city','outcome_year','site_a','site_b','distance_m','reviewer_decision'])
    strata=collections.defaultdict(list)
    for r in links:
        band=next((str(n) for n in [25,50,100,500] if r['distance_m']<=n))
        strata[(r['outcome_year'],r['city'],r['role'],r['category'],band,r['matches_50m']>1)].append(r)
    audit=[]
    for key,rows in sorted(strata.items()):
        for r in sorted(rows,key=lambda r:hashlib.sha256((r['site_id']+r['event_id']).encode()).hexdigest())[:5]:audit.append(r|{'stratum':str(key),'reviewer_decision':'PENDING','reviewer':'','notes':''})
    write('qa/manual_linkage_audit.csv',audit)
    for year in [2024,2025]:write(f'atm_panel_{year}_full_year.csv',[p for p in panels if p['outcome_year']==year])
    summary=[{'year':year,'city':city,'full_year_sites':sum(p['city']==city and p['outcome_year']==year for p in panels),'positive_50m':sum(p['primary_any_50m'] for p in panels if p['city']==city and p['outcome_year']==year)} for year in [2024,2025] for city in crime.CITIES]
    write('city_summary.csv',summary)
    manifest=[];sources=[]
    for p in sorted((ROOT/'data/raw').rglob('*')):
        if not p.is_file():continue
        manifest.append({'file':str(p.relative_to(ROOT)),'sha256':digest(p),'bytes':p.stat().st_size})
        if p.name.endswith('.request.json'):
            m=json.loads(p.read_text());sources.append({'sidecar':str(p.relative_to(ROOT)),'url':m.get('url',''),'params':json.dumps(m.get('params',{}),sort_keys=True),'retrieved_utc':m.get('retrieved_utc',m.get('retrieved_at_utc','unknown'))})
    write('source_manifest.csv',manifest);write('source_register.csv',sources)
    write('data_dictionary.csv',[{'column':k,'description':('Unique outcome-year robbery/burglary cases within radius, latest archive' if k.startswith('primary_count') else 'Outcome-year binary nearby-crime indicator' if k.startswith('primary_any') else 'Report-date-filtered prior-year cases in >200–500 m annulus' if k=='background_primary_200_500m' else 'Unknown actual operation; intentionally blank' if k.startswith('actual_') else k.replace('_',' ')),'example':str(panels[0][k])} for k in panels[0]])
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
