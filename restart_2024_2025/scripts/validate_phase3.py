"""Independent output/source and sampled spatial checks for restart phase 3."""
import csv,json,hashlib,math,re
from pathlib import Path
import numpy as np
import shapefile
from pyproj import Geod
from shapely.geometry import shape,Point
from shapely import make_valid
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/phase3'
def read(p):
    with p.open(newline='') as f:return list(csv.DictReader(f))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def num(v):
    try:n=float(v);return n if math.isfinite(n) and n>=0 else None
    except (ValueError,TypeError):return None
def same(a,b):
    if a in ['',None] or b in ['',None]:return a in ['',None] and b in ['',None]
    return math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-9)
def main():
    checks=[]
    def check(ok,label):
        assert ok,label;checks.append(label)
    schema=json.loads((OUT/'data/feature_schema.json').read_text());defs=read(OUT/'data/feature_dictionary.csv')
    check(schema['feature_spec_sha256']==sha(ROOT/'protocol/phase3_feature_spec.md'),'Frozen feature specification matches schema')
    for r in read(OUT/'qa/input_manifest.csv'):assert sha(ROOT/r['file'])==r['sha256'],r['file']
    check(True,'All input checksums match')
    verified=0
    for folder in [ROOT/'data/raw/phase3',ROOT/'data/raw/temporal_extension/acs2022']:
        for p in folder.rglob('*.request.json'):
            m=json.loads(p.read_text());base=Path(str(p).replace('.request.json',''))
            if not base.exists():base=base.with_suffix('.json')
            if base.exists() and 'sha256' in m:assert sha(base)==m['sha256'];verified+=1
    check(verified>0,'Archived acquisition hashes verified')
    panel={r['row_id']:r for r in read(ROOT/'data/processed/atm_panel_2024_2025_full_year.csv')}
    lookup={r['row_id']:r for r in read(OUT/'data/site_lookup_and_quality.csv')};context={r['row_id']:r for r in read(OUT/'data/site_context_raw.csv')}
    check(set(panel)==set(lookup)==set(context),'All phase 2 site-year rows retained')
    matrices={}
    for kind,count in [('primary',14),('sensitivity',3)]:
        rows=read(OUT/f'data/features_{kind}.csv');names=schema[kind+'_predictors']
        check(len(names)==count and list(rows[0])==['row_id']+names,'Predictor allowlist and count: '+kind)
        check(len(rows)==len(panel) and {r['row_id'] for r in rows}==set(panel),'Unique complete predictor keys: '+kind)
        matrices[kind]={r['row_id']:r for r in rows}
        for year in ['2024','2025']:
            subset=read(OUT/f'data/features_{kind}_{year}.csv')
            check(subset==[r for r in rows if panel[r['row_id']]['outcome_year']==year],f'{kind} {year} annual export matches combined matrix')
    for rid,r in context.items():
        p=panel[rid];l=lookup[rid]
        assert l['prediction_cutoff']==p['outcome_year']+'-01-01' and l['confirmatory_eligible']=='False' and l['baseline_membership']=='True'
        assert same(r['background_primary'],p['background_primary_200_500m']) and same(r['background_unfiltered'],p['background_unfiltered_200_500m'])
        assert same(r['population'],num(r['B01003_001E']))
        land=num(r['acs_land_area_m2']);pop=num(r['B01003_001E'])
        assert same(r['population_density'],pop*1e6/land if pop is not None and land else None)
        assert same(r['median_household_income'],num(r['B19013_001E']))
        labor=num(r['B23025_003E']);unemployed=num(r['B23025_005E'])
        assert same(r['unemployment_rate'],unemployed/labor if labor and unemployed is not None else None)
        assert same(r['atm_density_500m'],int(r['other_atm_count_500m'])/(math.pi*.5**2))
        for d in defs:
            v=num(r[d['raw_feature']]);assert r[d['raw_feature']]=='' or v is not None
            if d['raw_feature'] in ['employment_mix','unemployment_rate']:assert v is None or v<=1.000001
            expected=math.log1p(v) if v is not None and d['transformation']=='log1p' else v
            assert same(matrices[d['role']][rid][d['predictor']],expected)
    check(True,'Every formula, transformation, range, year cutoff and background matches phase 2')
    # Independent source lookup, geometry/attribute coverage and polygon construction.
    acsroot=ROOT/'data/raw/temporal_extension/acs2022';attrs={}
    for p in (acsroot/'attributes').glob('county_*.json'):
        if '.request.' in p.name:continue
        table=json.loads(p.read_text())
        for values in table[1:]:
            r=dict(zip(table[0],values));attrs[''.join(r[k] for k in ['state','county','tract','block group'])]=r
    ag={};areas={}
    for sr in shapefile.Reader(str(acsroot/'tl_2022_36_bg.zip')).iterShapeRecords():
        p=sr.record.as_dict()
        if p['GEOID'] in attrs:ag[p['GEOID']]=make_valid(shape(sr.shape.__geo_interface__));areas[p['GEOID']]=p['ALAND']
    check(set(ag)==set(attrs),'Official TIGER/Line geometry and ACS attribute identifiers agree')
    sg={};sattrs={}
    for p in (ROOT/'data/raw/phase3/sld2021').glob('county_*.geojson'):
        fs=json.loads(p.read_text())['features'];assert len(fs)==json.loads(p.with_name(p.stem+'_count.json').read_text())['count']
        for f in fs:sattrs[f['properties']['GEOID20']]=f['properties'];sg[f['properties']['GEOID20']]=make_valid(shape(f['geometry']))
    check(True,'EPA county geometry totals agree with archived API counts')
    mapping={'employment_density':'D1C','retail_employment_density':'D1C5_RET','employment_mix':'D2B_E5MIXA','road_network_density':'D3A','auto_road_density':'D3AAO','intersection_density':'D3B','transit_service_density':'D4D','auto_job_accessibility':'D5AR','transit_centroid_distance':'D4A','transit_job_accessibility':'D5BR'}
    for r in context.values():
        if r['acs_geoid_2022']:
            a=attrs[r['acs_geoid_2022']];assert same(r['acs_land_area_m2'],areas[r['acs_geoid_2022']])
            for key in [k for k in r if k.startswith('B')]:assert r[key]==('' if a[key] is None else str(a[key]))
        for name,field in mapping.items():
            value=sattrs[r['sld_geoid_2019']].get(field) if r['sld_geoid_2019'] else None
            assert same(r[name],num(value))
            assert r['sld_raw_'+field]==('' if value is None else str(value))
    check(True,'Every ACS uncertainty/annotation field and EPA source value preserved')
    samples=[]
    for year in ['2024','2025']:
        for city in sorted({p['city'] for p in panel.values()}):
            rows=sorted([p for p in panel.values() if p['city']==city and p['outcome_year']==year],key=lambda r:r['row_id'])
            samples.extend(rows[::max(1,len(rows)//5)][:5])
    joins={(r['row_id'],r['layer']):r for r in read(OUT/'qa/spatial_join_audit.csv')}
    for p in samples:
        pt=Point(float(p['longitude']),float(p['latitude']))
        for name,geoms,key in [('acs2022',ag,'acs_geoid_2022'),('sld2021',sg,'sld_geoid_2019')]:
            hits=sorted(k for k,g in geoms.items() if g.covers(pt));audit=joins[(p['row_id'],name)]
            assert len(hits)==int(audit['matches']) and set(hits)==set(filter(None,audit['candidate_geoids'].split('|')))
            assert context[p['row_id']][key]==(hits[0] if len(hits)==1 else '')
    check(True,'Independent brute-force polygon joins pass for five sites per city/year')
    geod=Geod(ellps='WGS84')
    norm=lambda s:re.sub(r'[^A-Z0-9]+',' ',s.upper()).strip()
    for year in ['2024','2025']:
        baseline=read(OUT/f'data/atm_baseline_{year}.csv')
        rawpath=ROOT/('data/raw/temporal_extension/atm_history/dfs_2023-12-15_v258.csv' if year=='2024' else 'data/raw/atm_history/dfs_2024-12-15_v270.csv')
        expected={}
        for raw in read(rawpath):
            r={re.sub(r'[^a-z0-9]+','_',k.lower()).strip('_'):v for k,v in raw.items()};coords=re.findall(r'-?\d+(?:\.\d+)?',r.get('georeference',''))
            if len(coords)==2:
                lon,lat=map(float,coords)
                if -80<lon<-71 and 40<lat<46:expected.setdefault((norm(r['street_address']),f'{lon:.7f}',f'{lat:.7f}'),(lon,lat))
        actual={(norm(r['address']),f"{float(r['longitude']):.7f}",f"{float(r['latitude']):.7f}") for r in baseline}
        assert actual==set(expected) and len(actual)==len(baseline)
        for r in baseline:
            key=(norm(r['address']),f"{float(r['longitude']):.7f}",f"{float(r['latitude']):.7f}")
            assert (float(r['longitude']),float(r['latitude']))==expected[key]
        assert all(r['snapshot_date']==str(int(year)-1)+'-12-15' for r in baseline)
        for p in [p for p in samples if p['outcome_year']==year]:
            key=(norm(p['address_raw']),f"{float(p['longitude']):.7f}",f"{float(p['latitude']):.7f}")
            distances=[geod.inv(float(p['longitude']),float(p['latitude']),float(lon),float(lat))[2] for identity,(lon,lat) in expected.items() if identity!=key]
            r=context[p['row_id']]
            assert sum(d<=500 for d in distances)==int(r['other_atm_count_500m']) and same(min(distances),r['nearest_other_atm'])
            assert sum(d<=10 for d in distances)==int(r['other_atm_count_within10m'])
    check(True,'Both statewide baseline inventories and sampled independent WGS84 competition calculations pass')
    check(not schema['imputation_performed'] and not schema['scaling_performed'] and not schema['model_fitted'] and not schema['confirmatory_modeling_ready'],'No learned preprocessing or model fitting; independent research gates preserved')
    result={'status':'PASS','site_years':len(panel),'primary_predictors':14,'sensitivity_predictors':3,'request_hashes_checked':verified,'spatial_sample_rows':len(samples),'checks':checks}
    (OUT/'qa/validation.json').write_text(json.dumps(result,indent=2)+'\n')
    status=json.loads((OUT/'qa/phase3_status.json').read_text());status['validation_status']='PASS';(OUT/'qa/phase3_status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
