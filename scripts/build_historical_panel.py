"""Build 2025 exposure from 14 archived monthly DFS snapshots.

Only intervals bracketed by two observations of the exact site are counted.
This estimates coverage, not actual machine operating days.
"""
import collections
import csv
import datetime as dt
import json
import re
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from build_phase12 import ROOT,OUT,CITIES,TRANS,GEOD,locate,norm,sid,write

START=dt.date(2025,1,1)
END=dt.date(2026,1,1)

def main():
    snapshots=[];sites={};members=[];excluded=[]
    files=sorted((ROOT/'data/raw/atm_history').glob('dfs_*_v*.csv'))
    assert len(files)==14, f'Need 14 snapshots; found {len(files)}'
    for path in files:
        date=dt.date.fromisoformat(path.name[4:14]);present=set();raw_count=0
        with path.open(encoding='utf-8-sig',newline='') as f:
            for index,raw in enumerate(csv.DictReader(f)):
                raw_count+=1
                a={re.sub(r'[^a-z0-9]+','_',k.lower()).strip('_'):v for k,v in raw.items()}
                coords=re.findall(r'-?\d+(?:\.\d+)?',a.get('georeference',''))
                if len(coords)!=2:
                    excluded.append({'source_file':str(path.relative_to(ROOT)),'row_index':index,'reason':'missing_or_unparsed_coordinates','raw_row':json.dumps(raw)});continue
                lon,lat=map(float,coords);city=locate(lon,lat)
                if not city:continue
                key=f'{city}|{norm(a.get("street_address",""))}|{lon:.7f}|{lat:.7f}'
                site_id='dfs_'+sid(key);present.add(site_id)
                if site_id not in sites:
                    x,y=TRANS[city].transform(lon,lat)
                    sites[site_id]={'site_id':site_id,'city':city,'latitude':lat,'longitude':lon,'easting_m':x,'northing_m':y,
                       'address_raw':a.get('street_address',''),'institution_raw':a.get('name_of_institution',''),
                       'postal_city_raw':a.get('city',''),'first_observed_snapshot':date.isoformat(),'last_observed_snapshot':date.isoformat(),
                       'site_cluster_id':'','snapshot_dates':set(),'intervals':[]}
                sites[site_id]['last_observed_snapshot']=date.isoformat();sites[site_id]['snapshot_dates'].add(date.isoformat())
                members.append({'site_id':site_id,'city':city,'snapshot_date':date.isoformat(),'latitude':lat,'longitude':lon,
                    'institution_raw':a.get('name_of_institution',''),'address_raw':a.get('street_address',''),
                    'source_file':str(path.relative_to(ROOT)),'source_row_index':index})
        snapshots.append((date,present))
        assert raw_count>4000,(path,raw_count)
    for (left,ls),(right,rs) in zip(snapshots,snapshots[1:]):
        assert 0<(right-left).days<=62,(left,right)
        start,end=max(left,START),min(right,END)
        if end<=start:continue
        for site_id in ls & rs:sites[site_id]['intervals'].append((start,end))
    active=[s for s in sites.values() if s['intervals']]
    exposure=[];intervalrows=[]
    for s in active:
        days=sum((b-a).days for a,b in s['intervals'])
        s['supported_days_2025']=days
        for a,b in s['intervals']:intervalrows.append({'site_id':s['site_id'],'city':s['city'],'interval_start_inclusive':a.isoformat(),'interval_end_exclusive':b.isoformat(),'supported_days':(b-a).days,'assumption':'continuous_activity_between_consecutive_positive_snapshots'})
    # Cluster without silently merging distinct addresses. Facility review remains a gate.
    for city in CITIES:
        ss=[s for s in active if s['city']==city];parents=list(range(len(ss)))
        def root(i):
            while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
            return i
        for a,b in cKDTree([[s['easting_m'],s['northing_m']] for s in ss]).query_pairs(10.1):
            if GEOD.inv(ss[a]['longitude'],ss[a]['latitude'],ss[b]['longitude'],ss[b]['latitude'])[2]<=10:parents[root(b)]=root(a)
        groups=collections.defaultdict(list)
        for i in range(len(ss)):groups[root(i)].append(i)
        for group in groups.values():
            cluster='cluster_'+sid('|'.join(sorted(ss[i]['site_id'] for i in group)))
            for i in group:ss[i]['site_cluster_id']=cluster;ss[i]['cluster_site_count']=len(group)
    for s in active:
        exposure.append({k:v for k,v in s.items() if k not in ['snapshot_dates','intervals']}|{
            'snapshots_observed':len(s['snapshot_dates']),'continuous_full_year_assumed':s['supported_days_2025']==365,
            'actual_opening_date':'','actual_closing_date':'','actual_active_days':'',
            'exposure_assumption':'presence_in_adjacent_monthly_snapshots_implies_activity_between_them'})
    write('atm_historical_snapshot_membership.csv',members)
    write('atm_historical_snapshot_exclusions.csv',excluded)
    write('atm_exposure_intervals_2025.csv',intervalrows)
    write('atm_historical_sites_2025.csv',exposure)
    # Preserve all historical identities, including single-snapshot sites excluded from intervals.
    write('atm_historical_site_inventory.csv',[{k:v for k,v in s.items() if k not in ['snapshot_dates','intervals']}|{
        'snapshots_observed':len(s['snapshot_dates']),'interval_supported':bool(s['intervals'])} for s in sites.values()])
    events=list(csv.DictReader((OUT/'crime_events_2024_2025.csv').open()))
    links=[];panel=[];summary=[];audit=[]
    for city in CITIES:
        ss=[s for s in active if s['city']==city]
        tree=cKDTree([[s['easting_m'],s['northing_m']] for s in ss]);counts={s['site_id']:collections.Counter() for s in ss}
        for e in events:
            if e['city']!=city or e['broad_included']!='1':continue
            date=dt.date.fromisoformat(e['event_date']);is_target=date.year==2025
            matches=[]
            for j in tree.query_ball_point([float(e['easting_m']),float(e['northing_m'])],502):
                s=ss[j]
                if is_target and not any(a<=date<b for a,b in s['intervals']):continue
                distance=GEOD.inv(float(e['longitude']),float(e['latitude']),s['longitude'],s['latitude'])[2]
                if distance<=500:matches.append((distance,s))
            matches.sort(key=lambda x:(x[0],x[1]['site_id']))
            mult={r:sum(d<=r for d,s in matches) for r in [25,50,100]}
            for rank,(distance,s) in enumerate(matches):
                target=is_target and distance<=100
                bg=not is_target and 200<distance<=500
                if not(target or bg):continue
                primary=e['primary_included']=='1';c=counts[s['site_id']]
                r={'city':city,'site_id':s['site_id'],'site_cluster_id':s['site_cluster_id'],'event_id':e['event_id'],
                    'event_date':e['event_date'],'native_offense':e['native_offense'],'common_category':e['common_category'],
                    'primary_included':primary,'event_latitude':e['latitude'],'event_longitude':e['longitude'],
                    'atm_latitude':s['latitude'],'atm_longitude':s['longitude'],'distance_m':round(distance,4),
                    'link_role':'outcome_2025_exposure_supported' if target else 'background_2024',
                    'within_25m':distance<=25,'within_50m':distance<=50,'within_100m':distance<=100,
                    'matches_25m':mult[25],'matches_50m':mult[50],'matches_100m':mult[100],'nearest_eligible_site':rank==0}
                links.append(r)
                if target:
                    for radius in [25,50,100]:
                        if distance<=radius:
                            c[f'broad_count_{radius}m']+=1
                            if primary:
                                c[f'primary_count_{radius}m']+=1;c[f'{e["common_category"]}_count_{radius}m']+=1
                                if rank==0:c[f'primary_nearest_count_{radius}m']+=1
                else:
                    c['background_broad_2024_200_500m']+=1
                    if primary:
                        c['background_primary_2024_200_500m']+=1
                        if e['available_before_2025_by_report_date']=='True':c['background_primary_reported_before_2025']+=1
        for s in ss:
            p={k:s[k] for k in ['city','site_id','site_cluster_id','latitude','longitude','address_raw','institution_raw','supported_days_2025','cluster_site_count','first_observed_snapshot','last_observed_snapshot']}
            p.update(outcome_year=2025,background_year=2024,full_year_exposure_supported=s['supported_days_2025']==365,
                exposure_fraction=s['supported_days_2025']/365,exposure_assumption='continuous_between_adjacent_positive_snapshots',
                analysis_status='historical_snapshot_supported; independent_QA_pending',confirmatory_eligible=False,
                actual_active_days='',actual_opening_date='',actual_closing_date='')
            c=counts[s['site_id']]
            for radius in [25,50,100]:
                for prefix in ['primary','broad','robbery','burglary','primary_nearest']:p[f'{prefix}_count_{radius}m']=c[f'{prefix}_count_{radius}m']
                p[f'primary_any_{radius}m']=int(c[f'primary_count_{radius}m']>0)
            for key in ['background_broad_2024_200_500m','background_primary_2024_200_500m','background_primary_reported_before_2025']:p[key]=c[key]
            p['coordinate_precision_flag']='rounded_block_address' if city=='Buffalo' else 'public_geocode_unverified'
            p['background_vintage_status']='latest_extract_not_historical_as_of_database'
            panel.append(p)
        cc=[p for p in panel if p['city']==city];full=[p for p in cc if p['full_year_exposure_supported']]
        summary.append({'city':city,'historical_sites_with_supported_intervals':len(cc),'full_year_sites':len(full),
            'partial_year_sites':len(cc)-len(full),'full_year_positive_50m':sum(p['primary_any_50m'] for p in full),
            'full_year_primary_site_event_links_50m':sum(p['primary_count_50m'] for p in full)})
        strata=collections.defaultdict(list)
        for r in links:
            if r['city']!=city:continue
            band='0_25' if r['distance_m']<=25 else '25_50' if r['distance_m']<=50 else '50_100' if r['distance_m']<=100 else '200_500'
            strata[(band,r['primary_included'],r['matches_50m']>1)].append(r)
        for k,rs in strata.items():
            for r in sorted(rs,key=lambda r:sid(r['event_id']+r['site_id']))[:5]:audit.append(r|{'audit_stratum':str(k),'reviewer_decision':'PENDING','reviewer':'','notes':''})
    write('atm_panel_2025_historical.csv',panel)
    write('atm_panel_2025_full_year.csv',[p for p in panel if p['full_year_exposure_supported']])
    write('event_atm_links_historical.csv',links)
    write('manual_linkage_audit_historical.csv',audit)
    write('historical_city_summary.csv',summary)
    assert all(0<p['supported_days_2025']<=365 for p in panel)
    assert all(p['primary_count_25m']<=p['primary_count_50m']<=p['primary_count_100m'] for p in panel)
    assert all(p['primary_nearest_count_50m']<=p['primary_count_50m'] for p in panel)
    print(json.dumps(summary,indent=2));print('Historical panel invariants passed.')

if __name__=='__main__':main()
