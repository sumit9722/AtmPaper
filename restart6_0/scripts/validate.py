"""Audit sources, reconstruct exposure membership, replay links and brute-force omissions.

No model fitting. Direct distance checks do not use the builder's spatial index.
"""
import collections
import csv
import datetime as dt
import json
import random
import numpy as np
from common import *

def main():
    checks = {}
    for r in read(OUT/'source_manifest.csv'):
        assert sha(ROOT/r['file']) == r['sha256'], r['file']
    checks['frozen_source_hashes'] = 'PASS'
    for slug in ('chicago','la_legacy','la_nibrs'):
        for year in range(2022,2026):
            folder = RAW/f'crime/{slug}/{year}'
            expected = int(json.loads((folder/'count_before.json').read_text())[0]['count'])
            after = int(json.loads((folder/'count_after.json').read_text())[0]['count'])
            ids = []
            for p in sorted(folder.glob('page_*.json')):
                if '.request.' not in p.name:
                    ids += [r['source_row_id'] for r in json.loads(p.read_text())]
            assert len(ids)==len(set(ids))==expected==after, (slug,year)
    for r in read(OUT/'qa/crime_source_conservation.csv'):
        assert int(r['raw_rows'])==sum(int(r[k]) for k in ('retained','excluded','duplicates'))
    checks['source_pagination_and_conservation'] = 'PASS'
    events = read(OUT/'crime_primary_2022_2025.csv')
    assert len({r['event_id'] for r in events}) == len(events)
    assert {r['city'] for r in events} == set(CITIES)
    byid = {r['event_id']:r for r in events}
    city_polygons = polygons()
    grouped = collections.defaultdict(list)
    for e in events:
        assert e['category'] in ('robbery','burglary')
        assert locate(float(e['longitude']),float(e['latitude']),city_polygons)==e['city']
        if e['city']=='Chicago':
            assert not e['report_date'] and e['report_date_usable']=='False'
        grouped[(e['city'],int(e['event_year']))].append(e)
    checks['incident_identity_city_and_report_dates'] = 'PASS'
    # Independently reconstruct membership from normalized snapshots. Raw Parquet and
    # normalization are additionally reconciled below against the actual source rows.
    dates = json.loads((RAW/'osm/snapshot_dates.json').read_text())
    assert dates == json.loads((RAW/'inherited/snapshot_dates.json').read_text())
    assert len(dates)==len(set(dates))==36 and dates==sorted(dates)
    assert dates[0]=='2023-02-22' and dates[-1]=='2026-01-15'
    snapshots = {date:read(OUT/f'snapshots/osm_{date}.csv') for date in dates}
    import pyarrow.parquet as pq
    from shapely import from_wkb
    from shapely.ops import transform
    polys = polygons()
    expected_source_count = 0
    for city,slug in CITIES.items():
        inverse = Transformer.from_crs({'New York City':32618,'Chicago':32616,'Los Angeles':32611}[city],4326,always_xy=True)
        for date in dates:
            expected = {}
            for row in pq.read_table(RAW/f'osm_v2/{slug}/{date}.parquet').to_pylist():
                timestamp=dt.datetime.fromisoformat(date+'T00:00:00+00:00')
                assert row['edit_timestamp']<=timestamp<row['valid_to_timestamp']
                tags=dict(row['tags'] or [])
                assert tags.get('amenity')=='atm' or (tags.get('amenity')=='bank' and tags.get('atm')=='yes')
                geometry=from_wkb(row['geom']) if row['geom'] else None
                if geometry is None or geometry.is_empty or not geometry.is_valid:
                    continue
                point=geometry if geometry.geom_type=='Point' else transform(inverse.transform,transform(TRANS[city].transform,geometry).centroid)
                if polys[city].covers(point):
                    osm_id=f"{row['osm_type']}/{row['osm_id']}"
                    assert osm_id not in expected, (city,date,osm_id)
                    expected[osm_id]=(point.x,point.y)
            observed={s['osm_id']:(float(s['longitude']),float(s['latitude'])) for s in snapshots[date] if s['city']==city}
            assert observed==expected, (city,date)
            expected_source_count += len(expected)
    checks['raw_osm_to_snapshot_reconciliation']='PASS'
    reconstructed={}
    for year in (2023,2024,2025):
        selected=[d for d in dates if f'{year-1}-12'<=d[:7]<=f'{year+1}-01']
        assert len(selected)==(12 if year==2023 else 14)
        for a,b in zip(selected,selected[1:]):
            da,db=dt.date.fromisoformat(a),dt.date.fromisoformat(b)
            assert db.year*12+db.month-(da.year*12+da.month)==1
            assert 0<(db-da).days<=62
        for city in CITIES:
            months=[{r['osm_id']:r for r in snapshots[d] if r['city']==city} for d in selected]
            eligible=set.intersection(*(set(m) for m in months))
            expected=set()
            for osm in eligible:
                base=months[0][osm]
                drift=max(GEOD.inv(float(base['longitude']),float(base['latitude']),float(m[osm]['longitude']),float(m[osm]['latitude']))[2] for m in months)
                if drift<=50:
                    expected.add(osm)
            reconstructed[(city,year)]=expected
    full=read(OUT/'atm_panel_full_year_2024_2025.csv')
    early=read(OUT/'atm_panel_partial_2023.csv')
    exact=read(OUT/'atm_panel_exact_supported_2023_2025.csv')
    for (city,year),expected in reconstructed.items():
        cohort=early if year==2023 else full
        assert {p['osm_id'] for p in cohort if p['city']==city and int(p['outcome_year'])==year}==expected
    for p in early:
        assert p['supported_start']=='2023-02-22' and p['supported_end_exclusive']=='2024-01-01' and p['supported_days']=='313'
    checks['full_year_membership_and_partial_dates']='PASS'
    panels={p['row_id']:p for p in full+early+exact}
    assert len(panels)==len(full)+len(early)+len(exact)
    intervals=collections.defaultdict(list)
    for r in read(OUT/'qa/exact_exposure_intervals.csv'):
        intervals[(r['site_id'],r['outcome_year'])].append((r['start_inclusive'],r['end_exclusive']))
    # Reconstruct exact-coordinate supported days from adjacent raw-derived states.
    expected_days=collections.defaultdict(set)
    states={d:{r['site_id']:r for r in snapshots[d]} for d in dates}
    for a,b in zip(dates,dates[1:]):
        da,db=dt.date.fromisoformat(a),dt.date.fromisoformat(b)
        if db.year*12+db.month-(da.year*12+da.month)!=1 or not 0<(db-da).days<=62:
            continue
        for site in states[a].keys() & states[b].keys():
            day=da
            while day<db:
                if day.year in (2023,2024,2025):
                    expected_days[(site,str(day.year))].add(str(day))
                day+=dt.timedelta(days=1)
    assert set(intervals)==set(expected_days)
    for key,spans in intervals.items():
        observed=set()
        for a,b in spans:
            day,end=dt.date.fromisoformat(a),dt.date.fromisoformat(b)
            assert day<end
            while day<end:
                assert str(day) not in observed, ('overlapping exposure intervals',key)
                observed.add(str(day));day+=dt.timedelta(days=1)
        assert observed==expected_days[key],key
    assert {(p['site_id'],p['outcome_year']) for p in exact}==set(expected_days)
    for p in exact:
        assert int(p['supported_days'])==len(expected_days[(p['site_id'],p['outcome_year'])])
    checks['exact_coordinate_exposure_reconstruction']='PASS'
    totals=collections.defaultdict(collections.Counter)
    assignment_groups={}
    nlinks=0
    with (OUT/'event_atm_links.csv').open() as stream:
        for link in csv.DictReader(stream):
            p=panels[link['row_id']];e=byid[link['event_id']]
            assert e['city']==p['city']==link['city']
            distance=GEOD.inv(float(p['longitude']),float(p['latitude']),float(e['longitude']),float(e['latitude']))[2]
            assert abs(distance-float(link['distance_m']))<1e-5
            c=totals[p['row_id']]
            if link['role']=='outcome':
                assert e['event_year']==p['outcome_year'] and distance<=100
                spans=intervals[(p['site_id'],p['outcome_year'])] if p['cohort']=='exact_identity_supported' else [(p['supported_start'],p['supported_end_exclusive'])]
                assert any(a<=e['event_date']<b for a,b in spans)
                key=(p['cohort'],p['outcome_year'],e['event_id'])
                group=assignment_groups.setdefault(key,[])
                group.append((distance,p['site_id'],link['nearest_eligible_site']=='True',
                              tuple(int(link[f'matches_{r}m']) for r in (25,50,100))))
                for radius in (25,50,100):
                    if distance<=radius:
                        c[f'primary_count_{radius}m']+=1
                        c[f'{e["category"]}_count_{radius}m']+=1
                        c[f'primary_nearest_count_{radius}m']+=link['nearest_eligible_site']=='True'
                        c[f'multiple_match_count_{radius}m']+=int(link[f'matches_{radius}m'])>1
                        c[f'primary_reported_count_{radius}m']+=link['report_available_by_cutoff']=='True'
            else:
                assert link['role']=='background'
                assert int(e['event_year'])==int(p['outcome_year'])-1 and 200<distance<=500
                c['background_unfiltered_200_500m']+=1
                c['background_primary_200_500m']+=link['report_available_by_cutoff']=='True'
            cutoff=f"{int(p['outcome_year'])+(link['role']=='outcome')}-01-01"
            assert (link['report_available_by_cutoff']=='True')==(e['report_date_usable']=='True' and e['report_date']<cutoff)
            nlinks+=1
    for key,matches in assignment_groups.items():
        assert len({m[1] for m in matches})==len(matches),key
        ordered=sorted(matches,key=lambda m:(m[0],m[1]))
        multiplicity=tuple(sum(m[0]<=radius for m in matches) for radius in (25,50,100))
        for index,match in enumerate(ordered):
            assert match[2]==(index==0) and match[3]==multiplicity,key
    checks['nearest_assignment_and_multiplicity']='PASS'
    for p in panels.values():
        c=totals[p['row_id']]
        assert p['confirmatory_eligible']=='False'
        assert 0<=float(p['annulus_fraction_inside_city'])<=1.00000001
        assert int(p['primary_count_25m'])<=int(p['primary_count_50m'])<=int(p['primary_count_100m'])
        if p['city']=='Chicago':
            assert p['background_primary_200_500m']==''
        for field in ['background_unfiltered_200_500m','background_primary_200_500m']+[
            f'{prefix}_count_{radius}m' for radius in (25,50,100) for prefix in
            ('primary','robbery','burglary','primary_nearest','multiple_match','primary_reported')]:
            if p[field]!='':
                assert int(p[field])==c[field],(p['row_id'],field)
    checks['all_link_distances_time_windows_and_count_replay']='PASS'
    # Brute-force against every event, not only emitted matches: detects omitted links.
    tested=0
    for city in CITIES:
        for year in (2023,2024,2025):
            candidates=sorted([p for p in full+early if p['city']==city and int(p['outcome_year'])==year],key=lambda p:p['site_id'])
            chosen=random.Random(608).sample(candidates,min(4,len(candidates)))
            for p in chosen:
                for eventyear in (year-1,year):
                    es=grouped[(city,eventyear)]
                    lon=np.array([float(e['longitude']) for e in es]);lat=np.array([float(e['latitude']) for e in es])
                    distances=GEOD.inv(np.full(len(es),float(p['longitude'])),np.full(len(es),float(p['latitude'])),lon,lat)[2]
                    if eventyear==year:
                        mask=np.array([p['supported_start']<=e['event_date']<p['supported_end_exclusive'] for e in es])
                        for radius in (25,50,100):
                            assert int(np.sum((distances<=radius)&mask))==int(p[f'primary_count_{radius}m'])
                    else:
                        assert int(np.sum((distances>200)&(distances<=500)))==int(p['background_unfiltered_200_500m'])
                tested+=1
    checks['sampled_bruteforce_omission_check']='PASS'
    months=read(OUT/'atm_site_month_panel.csv')
    aggregate=collections.defaultdict(collections.Counter)
    for m in months:
        assert m['annual_row_id'] in panels
        c=aggregate[m['annual_row_id']];c['supported_days']+=int(m['supported_days_in_month'])
        for radius in (25,50,100):
            for prefix in ('primary','robbery','burglary','primary_nearest','primary_reported'):
                field=f'{prefix}_count_{radius}m'
                if m[field]!='':c[field]+=int(m[field])
    for rowid,p in panels.items():
        assert aggregate[rowid]['supported_days']==int(p['supported_days'])
        for field in aggregate[rowid]:
            assert aggregate[rowid][field]==int(p[field]),(rowid,field)
    checks['monthly_to_annual_reconciliation']='PASS'
    savejson(REPORTS/'validation.json',{'status':'PASS','checks':checks,'incident_rows':len(events),
        'osm_snapshot_memberships':expected_source_count,'full_year_rows':len(full),'partial_2023_rows':len(early),
        'exact_supported_rows':len(exact),'link_rows':nlinks,'bruteforce_sites':tested,
        'scientific_review':'PENDING','confirmatory_eligible':False})
    print('Validation PASS:',len(checks),'groups;',nlinks,'links;',tested,'brute-force sites',flush=True)

if __name__=='__main__':
    main()
