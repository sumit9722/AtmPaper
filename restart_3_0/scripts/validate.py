"""Independent file-based reconciliation of the restart outputs."""
import collections,csv,hashlib,json,math
import numpy as np
from pathlib import Path
from pyproj import Geod
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/processed'
def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checks=[]
    def check(ok,name):
        if not ok:raise AssertionError(name)
        checks.append(name)
    freeze=json.loads((ROOT/'reports/protocol_freeze.json').read_text())
    check(sha(ROOT/freeze['specification'])==freeze['sha256'],'Working specification matches build freeze')
    for r in read(OUT/'source_manifest.csv'):check(sha(ROOT/r['file'])==r['sha256'],'Manifest: '+r['file'])
    sidecars=0
    for p in (ROOT/'data/raw').rglob('*.request.json'):
        m=json.loads(p.read_text());original=Path(str(p).removesuffix('.request.json'))
        if original.exists() and 'sha256' in m:
            assert sha(original)==m['sha256'],p; sidecars+=1
    check(sidecars>0,'Archived request hashes verified')
    acquisitions=[]
    for folder in [ROOT/'data/raw',ROOT/'data/raw/temporal_extension/crime2023']:
        for city in ['nyc','buffalo','rochester']:
            base=folder/city;pages=sorted(p for p in base.glob('page_*.json') if '.request.' not in p.name)
            rows=[]
            for p in pages:
                obj=json.loads(p.read_text()); rr=obj['features'] if isinstance(obj,dict) else obj;rows+=rr
                if 'page_month_' in p.name:
                    count=json.loads((base/p.name.replace('page_month_','count_')).read_text())
                    assert len(rr)==int(count[0]['count'])
            if city=='rochester':
                ids=json.loads((base/'object_ids.json').read_text())['objectIds']
                actual=[r['attributes']['OBJECTID'] for r in rows]
                assert len(actual)==len(set(actual)) and set(actual)==set(ids)
            elif not any('page_month_' in p.name for p in pages):
                assert len(rows)==int(json.loads((base/'count.json').read_text())[0]['count'])
            assert rows
            acquisitions.append({'source':str(base.relative_to(ROOT)),'downloaded_rows':len(rows)})
    check(True,'All six city/period extracts match archived API counts or exact object IDs')
    panel=read(OUT/'atm_panel_2024_2025_full_year.csv'); byid={(p['site_id'],p['outcome_year']):p for p in panel}
    check(len(panel)==len(byid)>0,'Unique nonempty site cohort')
    check(all(p['supported_days']==('366' if p['outcome_year']=='2024' else '365') and p['outcome_year'] in ['2024','2025'] and int(p['background_year'])==int(p['outcome_year'])-1 and p['confirmatory_eligible']=='False' for p in panel),'2024 leap-year exposure, prior-year baseline and research gate')
    for year in ['2024','2025']:
        continuity=collections.defaultdict(list)
        for r in read(OUT/f'exposure_{year}/qa/continuity_links.csv'):continuity[r['site_id']].append(r)
        check(all(len(continuity[s])==14 and all(r['eligible']=='True' and float(r['distance_from_baseline_m'])<=50 for r in continuity[s]) for s,y in byid if y==year),f'{year}: every cohort site has 14 eligible continuity observations')
    check(not read(OUT/'exposure_2024/qa/exact_identity_full_year.csv'),'Strict 2024 exact-identity full-year cohort explicitly empty')
    events=read(OUT/'crime_primary_2023_2025.csv'); eb={e['event_id']:e for e in events}
    check(len(eb)==len(events) and {e['event_date'][:4] for e in events}=={'2023','2024','2025'},'Crime identifiers unique; only 2023/2024/2025 primary events')
    grouped_links=collections.defaultdict(list)
    counts=collections.defaultdict(collections.Counter); seen=set(); g=Geod(ellps='WGS84'); nlinks=0
    with (OUT/'event_atm_links.csv').open() as f:
        for r in csv.DictReader(f):
            nlinks+=1;s=(r['site_id'],r['outcome_year']);e=eb[r['event_id']];p=byid[s];d=float(r['distance_m']);key=(s,r['event_id'])
            assert key not in seen;seen.add(key)
            assert e['event_date']==r['event_date'] and e['city']==p['city']==r['city']
            actual=g.inv(float(e['longitude']),float(e['latitude']),float(p['longitude']),float(p['latitude']))[2]
            assert abs(actual-d)<1e-6
            known=bool(e['report_datetime'] and e['report_datetime'][:10]<str(int(e['event_date'][:4])+1)+'-01-01')
            assert (r['reported_by_year_end']=='True')==known
            grouped_links[(r['outcome_year'],r['event_id'])].append((d,s[0],r['nearest_cohort_site'],[int(r[f'matches_{n}m']) for n in [25,50,100]],r['role']))
            c=counts[s]
            if r['role']=='outcome':
                assert e['event_date'].startswith(r['outcome_year']+'-') and 0<=d<=100
                for radius in [25,50,100]:
                    if d<=radius:
                        c[f'primary_count_{radius}m']+=1;c[f'{r["category"]}_count_{radius}m']+=1
                        c[f'primary_reported_count_{radius}m']+=known;c[f'primary_nearest_count_{radius}m']+=r['nearest_cohort_site']=='True'
            else:
                assert int(e['event_date'][:4])==int(r['outcome_year'])-1 and 200<d<=500
                c['background_unfiltered_200_500m']+=1;c['background_primary_200_500m']+=known
                c['background_missing_report']+=not e['report_datetime'];c['background_late_report']+=bool(e['report_datetime']) and not known
    for p in panel:
        c=counts[(p['site_id'],p['outcome_year'])]
        for k,v in p.items():
            if '_count_' in k or k.startswith('background_') and k!='background_year':assert int(v)==c[k],(p['site_id'],k,v,c[k])
        assert int(p['primary_count_25m'])<=int(p['primary_count_50m'])<=int(p['primary_count_100m'])
        for radius in [25,50,100]:assert int(p[f'primary_any_{radius}m'])==int(int(p[f'primary_count_{radius}m'])>0)
    for rows in grouped_links.values():
        ordered=sorted(rows,key=lambda r:(r[0],r[1]))
        for i,r in enumerate(ordered):
            assert (r[2]=='True')==(i==0)
            if r[4]=='outcome':assert r[3]==[sum(t[0]<=n for t in rows) for n in [25,50,100]]
    check(True,'Multiplicity and nearest-site flags independently reconciled within each outcome year')
    # Brute-force geodesic lookup checks for omitted candidate links, including zero-count sites.
    for year in ['2024','2025']:
        for city in sorted({p['city'] for p in panel}):
            subset=sorted([p for p in panel if p['city']==city and p['outcome_year']==year],key=lambda p:p['site_id'])
            sampled=subset[::max(1,len(subset)//10)][:10]
            for event_year in [str(int(year)-1),year]:
                es=[e for e in events if e['city']==city and e['event_date'][:4]==event_year]
                lons=np.array([float(e['longitude']) for e in es]);lats=np.array([float(e['latitude']) for e in es])
                for p in sampled:
                    ds=g.inv(np.full(len(es),float(p['longitude'])),np.full(len(es),float(p['latitude'])),lons,lats)[2]
                    if event_year==year:
                        for radius in [25,50,100]:assert int(p[f'primary_count_{radius}m'])==int(np.sum(ds<=radius))
                    else:assert int(p['background_unfiltered_200_500m'])==int(np.sum((ds>200)&(ds<=500)))
    check(True,'Brute-force geodesic counts for up to ten sites per city/year confirm candidate-search completeness')
    check(True,'Every link distance independently recomputed; all panel counts reconcile exactly')
    check(all(r['reviewer_decision']=='PENDING' for r in read(OUT/'qa/manual_linkage_audit.csv')),'Human review has not been fabricated')
    result={'status':'PASS','full_year_site_years':len(panel),'unique_sites':len({p['site_id'] for p in panel}),'link_rows':nlinks,'primary_events':len(events),'request_hashes_checked':sidecars,'acquisitions':acquisitions,'checks':checks,'scientific_acceptance':'PENDING independent review'}
    (ROOT/'reports/validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))
if __name__=='__main__':main()
