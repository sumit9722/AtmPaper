"""Offline, outcome-blind construction of common 2025 environmental predictors."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import numpy as np
from pyproj import Geod, Transformer
from scipy.stats import spearmanr
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree
from shapely import make_valid
from shapely.validation import explain_validity

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/phase3'
OUT=ROOT/'results/phase3'
PROC=ROOT/'data/processed'
GEOD=Geod(ellps='WGS84')
CITIES=['New York City','Buffalo','Rochester']
TRANS={c:Transformer.from_crs(4326,32618 if c=='New York City' else 32617,always_xy=True) for c in CITIES}
CUTOFF='2025-01-01'
# Dictionary fixed before extraction; order also defines the locked predictor order.
DEFS=[
 ('background_primary','log1p','count','police_2024','primary','2024 incidents'),
 ('population_density','log1p','residents/km2 land','acs2023','primary','2019-2023'),
 ('median_household_income','log1p','2023 USD','acs2023','primary','2019-2023'),
 ('unemployment_rate','identity','fraction','acs2023','primary','2019-2023'),
 ('employment_density','log1p','jobs/unprotected acre','sld2021','primary','2017 LEHD / 2019 geography'),
 ('retail_employment_density','log1p','retail jobs/unprotected acre','sld2021','primary','2017 LEHD / 2019 geography'),
 ('employment_mix','identity','entropy 0-1','sld2021','primary','2017 LEHD / 2019 geography'),
 ('road_network_density','log1p','facility miles/mi2 land','sld2021','primary','2018 HERE / 2019 geography'),
 ('auto_road_density','log1p','auto-oriented facility miles/mi2 land','sld2021','primary','2018 HERE / 2019 geography'),
 ('intersection_density','log1p','weighted intersections/mi2','sld2021','primary','2018 HERE / 2019 geography'),
 ('transit_service_density','log1p','departures/hour/mi2','sld2021','primary','2020 GTFS / 2019 geography'),
 ('auto_job_accessibility','log1p','time-weighted jobs','sld2021','primary','2020 travel times / 2017 LEHD'),
 ('atm_density_500m','log1p','other sites/km2 circle','dfs2024','primary','2024-12-15 snapshot'),
 ('nearest_other_atm','log1p','metres WGS84','dfs2024','primary','2024-12-15 snapshot'),
 ('transit_centroid_distance','log1p','metres from CBG centroid','sld2021','sensitivity','2020 GTFS / 2019 geography'),
 ('transit_job_accessibility','log1p','time-weighted jobs','sld2021','sensitivity','2020 transit / 2017 LEHD'),
 ('background_report_date_cutoff','log1p','count','police_2024','sensitivity','2024 incidents with report cutoff'),
]
SLD_FIELDS={'employment_density':'D1C','retail_employment_density':'D1C5_RET','employment_mix':'D2B_E5MIXA',
 'road_network_density':'D3A','auto_road_density':'D3AAO','intersection_density':'D3B','transit_service_density':'D4D',
 'auto_job_accessibility':'D5AR','transit_centroid_distance':'D4A','transit_job_accessibility':'D5BR'}
SOURCE_FIELDS={**SLD_FIELDS,'background_primary':'background_primary_2024_200_500m',
 'population_density':'B01003_001E / AREALAND * 1000000','median_household_income':'B19013_001E',
 'unemployment_rate':'B23025_005E / B23025_003E','atm_density_500m':'other_site_count_500m / (pi * 0.5**2)',
 'nearest_other_atm':'min WGS84 distance to other Dec 2024 DFS identities',
 'background_report_date_cutoff':'background_primary_reported_before_2025'}
AVAILABLE={'acs2023':'2024-12-12','sld2021':'2021-12-31','dfs2024':'2024-12-15','police_2024':None}

def read(path):
    with path.open(newline='',encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
def write(path,rows,fields=None):
    rows=list(rows)
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def norm(s):return re.sub(r'[^A-Z0-9]+',' ',s.upper()).strip()
def identity(address,lon,lat):return (norm(address),f'{float(lon):.7f}',f'{float(lat):.7f}')
def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n>=0 else None
    except (TypeError,ValueError):return None

def feature_dictionary():
    rows=[]
    for name,method,unit,source,role,vintage in DEFS:
        rows.append({'raw_feature':name,'predictor':('log1p_'+name) if method=='log1p' else name,
            'transformation':method,'raw_unit':unit,'source':source,'source_field_or_formula':SOURCE_FIELDS[name],
            'source_vintage':vintage,'available_by':AVAILABLE[source],
            'availability_qualification':'conservative year-end bound for 2021 release' if source=='sld2021' else
                'event-year lag only; exact as-of database unavailable' if source=='police_2024' else 'published snapshot/release date',
            'prediction_cutoff':CUTOFF,'role':role,'missing_policy':'retain null; imputation only within future training folds'})
    return rows

def freeze():
    rows=feature_dictionary()
    schema={'version':'1.0','prediction_cutoff':CUTOFF,'primary_predictors':[r['predictor'] for r in rows if r['role']=='primary'],
        'sensitivity_predictors':[r['predictor'] for r in rows if r['role']=='sensitivity'],
        'feature_spec_sha256':digest(ROOT/'protocol/phase3_feature_spec_v1.0.md'),
        'no_labels_in_predictors':True,'imputation_performed':False,'scaling_performed':False,'model_fitted':False,
        'confirmatory_modeling_ready':False}
    path=OUT/'data/feature_schema.json'
    if path.exists():
        assert json.loads(path.read_text())==schema,'Frozen schema changed; create a versioned amendment'
    else:save(path,schema)
    write(OUT/'data/feature_dictionary.csv',rows)
    return schema

class PolygonLayer:
    def __init__(self,name):
        self.features=[]
        for path in sorted((RAW/name).glob('county_*.geojson')):
            self.features.extend(json.loads(path.read_text())['features'])
        assert self.features, name
        self.polygons=[shape(f['geometry']) for f in self.features]
        repairs=[]
        for i,p in enumerate(self.polygons):
            if not p.is_valid:
                fixed=make_valid(p)
                change=abs(fixed.area-p.area)/max(p.area,1e-20)
                assert fixed.geom_type in ['Polygon','MultiPolygon'] and change<1e-6, 'Material geometry repair requires review'
                repairs.append({'layer':name,'geoid':self.features[i]['properties'].get('GEOID',self.features[i]['properties'].get('GEOID20')),
                    'issue':explain_validity(p),'repair':'GEOS make_valid; raw geometry preserved',
                    'relative_area_change':change})
                self.polygons[i]=fixed
        write(OUT/f'qa/geometry_repairs_{name}.csv',repairs,['layer','geoid','issue','repair','relative_area_change'])
        assert all(p.is_valid and not p.is_empty for p in self.polygons),f'Invalid {name} geometry; review before joining'
        self.tree=STRtree(self.polygons)
        self.projected={}
    def join(self,point,city):
        candidates=sorted(int(i) for i in self.tree.query(point,predicate='covered_by'))
        if len(candidates)!=1:return None,candidates,None
        i=candidates[0]
        key=(i,city)
        if key not in self.projected:self.projected[key]=transform(TRANS[city].transform,self.polygons[i])
        p=transform(TRANS[city].transform,point)
        return self.features[i]['properties'],candidates,p.distance(self.projected[key].boundary)

def baseline_sites():
    sites={};excluded=[]
    source=ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv'
    for i,r in enumerate(read(source)):
        coords=re.findall(r'-?\d+(?:\.\d+)?',r.get('georeference',''))
        if len(coords)!=2:
            excluded.append({'source_row':i,'reason':'unparsed_coordinates'});continue
        lon,lat=map(float,coords)
        if not (-80<lon<-71 and 40<lat<46):
            excluded.append({'source_row':i,'reason':'outside_broad_NY_coordinate_bounds'});continue
        key=identity(r['street_address'],lon,lat)
        sites.setdefault(key,{'baseline_id':hashlib.sha256('|'.join(key).encode()).hexdigest()[:16],
            'address':r['street_address'],'longitude':lon,'latitude':lat,'snapshot_date':'2024-12-15','source_row':i})
    write(OUT/'data/atm_baseline_dec2024.csv',sites.values())
    write(OUT/'qa/atm_baseline_exclusions.csv',excluded,['source_row','reason'])
    return sites

def competition(lon,lat,address,sites):
    keys=list(sites)
    points=list(sites.values())
    distances=np.asarray(GEOD.inv(np.full(len(points),lon),np.full(len(points),lat),
        np.array([p['longitude'] for p in points]),np.array([p['latitude'] for p in points]))[2])
    focal=identity(address,lon,lat)
    other=np.array([key!=focal for key in keys])
    d=distances[other]
    nearest_index=int(np.argmin(np.where(other,distances,np.inf)))
    count=int(np.count_nonzero(d<=500))
    return {'atm_density_500m':count/(math.pi*0.5**2),'nearest_other_atm':float(d.min()),
        'other_atm_count_500m':count,'other_atm_count_within10m':int(np.count_nonzero(d<=10)),
        'other_atm_count_10_to500m':int(np.count_nonzero((d>10)&(d<=500))),
        'baseline_membership':focal in sites,'nearest_other_baseline_id':points[nearest_index]['baseline_id']}

def diagnostics(context,primary,lookup,schema):
    byid={r['site_id']:r for r in lookup}
    fields=schema['primary_predictors']+schema['sensitivity_predictors']
    stats=[];ranges=[];corr=[]
    for cohort in ['all_historical','full_year']:
        selected=[r for r in primary if cohort=='all_historical' or byid[r['site_id']]['full_year_exposure_supported']=='True']
        for city in CITIES+['ALL']:
            group=[r for r in selected if city=='ALL' or byid[r['site_id']]['city']==city]
            for name in fields:
                values=np.array([r[name] for r in group if r[name] is not None],dtype=float)
                missing=len(group)-len(values)
                quant=np.quantile(values,[0,.25,.5,.75,1]).tolist() if len(values) else [None]*5
                stats.append({'cohort':cohort,'city':city,'feature':name,'rows':len(group),'nonmissing':len(values),
                    'missing':missing,'missing_fraction':missing/len(group) if group else None,
                    'min':quant[0],'q25':quant[1],'median':quant[2],'q75':quant[3],'max':quant[4],
                    'unique_nonmissing':len(set(values)),'high_missingness_gt20pct':missing>0.2*len(group),
                    'zero_variance':len(set(values))<=1})
            if cohort=='full_year':
                for ia,a in enumerate(schema['primary_predictors']):
                    for b in schema['primary_predictors'][ia+1:]:
                        pairs=np.array([[r[a],r[b]] for r in group if r[a] is not None and r[b] is not None])
                        rho=None
                        if len(pairs)>=3 and np.ptp(pairs[:,0])>0 and np.ptp(pairs[:,1])>0:
                            rho=float(spearmanr(pairs[:,0],pairs[:,1]).statistic)
                        corr.append({'city':city,'feature_a':a,'feature_b':b,'pairwise_n':len(pairs),
                            'spearman_rho':rho,'abs_rho_ge_0_90':rho is not None and abs(rho)>=.9})
    for r in context:
        for name,*_ in DEFS:
            v=r[name]
            if v is not None and (v<0 or not math.isfinite(v) or (name in ['unemployment_rate','employment_mix'] and v>1.000001)):
                ranges.append({'site_id':r['site_id'],'feature':name,'value':v,'issue':'invalid range'})
    write(OUT/'qa/feature_distributions.csv',stats)
    write(OUT/'qa/feature_correlations.csv',corr)
    write(OUT/'qa/range_violations.csv',ranges,['site_id','feature','value','issue'])
    assert not ranges,'Out-of-range features; inspect QA'
    return stats,corr

def manifest():
    paths=set()
    for folder in [RAW,ROOT/'data/raw/census/acs2023_5year']:
        paths.update(p for p in folder.rglob('*') if p.is_file())
    paths.update(PROC/name for name in ['atm_panel_2025_historical.csv','atm_panel_2025_full_year.csv','census/block_group_context.csv'])
    paths.update([ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv',ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv.request.json',ROOT/'data/raw/boundaries/cities.geojson'])
    paths.update([ROOT/'protocol/phase3_feature_spec_v1.0.md',ROOT/'scripts/build_phase3.py',ROOT/'scripts/download_phase3.py'])
    paths.update([ROOT/'scripts/validate_phase3.py',ROOT/'scripts/report_phase3.py'])
    write(OUT/'qa/input_manifest.csv',[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(paths)])

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-only',action='store_true');args=parser.parse_args()
    schema=freeze()
    if args.freeze_only:
        print('Frozen candidate dictionary and predictor schema before extraction.');return
    # Only identifiers, exposure QA and 2024 baseline fields are consumed from phase 2.
    panel=read(PROC/'atm_panel_2025_historical.csv')
    acs={r['geoid']:r for r in read(PROC/'census/block_group_context.csv')}
    layers={name:PolygonLayer(name) for name in ['acs2023','sld2021']}
    baseline=baseline_sites()
    city_polys={}
    for f in json.loads((ROOT/'data/raw/boundaries/cities.geojson').read_text())['features']:
        city='New York City' if f['properties']['BASENAME']=='New York' else f['properties']['BASENAME']
        city_polys[city]=transform(TRANS[city].transform,shape(f['geometry']))
    context=[];lookup=[];transformed=[];assignments=[]
    for p in panel:
        city=p['city'];lon=float(p['longitude']);lat=float(p['latitude']);point=Point(lon,lat)
        a,ai,ad=layers['acs2023'].join(point,city)
        s,si,sd=layers['sld2021'].join(point,city)
        ar=acs.get(a['GEOID']) if a else None
        assert a is None or ar is not None, 'ACS geometry has no attribute row'
        row={'site_id':p['site_id'],'city':city,'acs_geoid_2023':a['GEOID'] if a else None,
             'sld_geoid_2019':s.get('GEOID20') if s else None,'sld_geoid10_source':s.get('GEOID10') if s else None,
             'acs_land_area_m2':number(a['AREALAND']) if a else None,
             'background_primary':number(p['background_primary_2024_200_500m']),
             'background_report_date_cutoff':number(p['background_primary_reported_before_2025'])}
        pop=number(ar['population']) if ar else None
        row['population']=pop
        row['population_density']=pop*1e6/row['acs_land_area_m2'] if pop is not None and row['acs_land_area_m2'] else None
        for field in ['median_household_income','unemployment_rate','civilian_labor_force','unemployed']:
            row[field]=number(ar[field]) if ar else None
        for field in ['population','median_household_income','civilian_labor_force','unemployed']:
            row[field+'_moe90']=number(ar[field+'_moe90']) if ar else None
            row[field+'_annotation']=ar[field+'_annotation'] if ar else None
            row[field+'_moe_annotation']=ar[field+'_moe_annotation'] if ar else None
        row['income_topcoded']=bool(ar and '+' in ar['median_household_income_annotation'])
        row['income_bottomcoded']=bool(ar and ar['median_household_income_annotation'].endswith('-') and ar['median_household_income_annotation']!='-')
        for name,field in SLD_FIELDS.items():
            row['sld_raw_'+field]=s.get(field) if s else None
            row[name]=number(s.get(field)) if s else None
        comp=competition(lon,lat,p['address_raw'],baseline)
        row.update(comp)
        context.append(row)
        projected=transform(TRANS[city].transform,point)
        edge=projected.distance(city_polys[city].boundary)
        lookup.append({'site_id':p['site_id'],'city':city,'longitude':lon,'latitude':lat,'site_cluster_id':p['site_cluster_id'],
            'full_year_exposure_supported':p['full_year_exposure_supported'],'supported_days_2025':p['supported_days_2025'],
            'confirmatory_eligible':p['confirmatory_eligible'],'prediction_cutoff':CUTOFF,
            'acs_join_matches':len(ai),'sld_join_matches':len(si),'acs_boundary_distance_m':ad,'sld_boundary_distance_m':sd,
            'acs_within10m_boundary':ad is not None and ad<=10,'sld_within10m_boundary':sd is not None and sd<=10,
            'city_boundary_distance_m':edge,'background_annulus_crosses_city_boundary':edge<=500,
            'coordinate_precision_flag':p['coordinate_precision_flag'],'baseline_membership':comp['baseline_membership'],
            'other_atm_within10m':comp['other_atm_count_within10m']>0,
            'strict_asof_police_data_available':False,'phase2_independent_review':'PENDING'})
        for name,indices in [('acs2023',ai),('sld2021',si)]:
            assignments.append({'site_id':p['site_id'],'layer':name,'matches':len(indices),
                'status':'unique' if len(indices)==1 else 'unmatched' if not indices else 'ambiguous',
                'candidate_geoids':'|'.join(str(layers[name].features[i]['properties'].get('GEOID',layers[name].features[i]['properties'].get('GEOID20'))) for i in indices)})
        model={'site_id':p['site_id']}
        for f in feature_dictionary():
            v=row[f['raw_feature']]
            model[f['predictor']]=math.log1p(v) if v is not None and f['transformation']=='log1p' else v
        transformed.append(model)
    full_ids={p['site_id'] for p in panel if p['full_year_exposure_supported']=='True'}
    assert len(full_ids)==len(read(PROC/'atm_panel_2025_full_year.csv'))
    write(OUT/'data/site_context_raw.csv',context)
    write(OUT/'data/site_lookup_and_quality.csv',lookup)
    write(OUT/'qa/spatial_join_audit.csv',assignments)
    for cohort in ['all_historical','full_year']:
        rows=[r for r in transformed if cohort=='all_historical' or r['site_id'] in full_ids]
        for kind in ['primary','sensitivity']:
            fields=['site_id']+schema[kind+'_predictors']
            write(OUT/f'data/features_{kind}_{cohort}.csv',[{k:r[k] for k in fields} for r in rows],fields)
    stats,corr=diagnostics(context,transformed,lookup,schema)
    cities=[]
    for city in CITIES:
        rs=[r for r in lookup if r['city']==city]
        cities.append({'city':city,'historical_sites':len(rs),
            'full_year_sites':sum(r['full_year_exposure_supported']=='True' for r in rs),
            'acs_unique_join':sum(r['acs_join_matches']==1 for r in rs),'sld_unique_join':sum(r['sld_join_matches']==1 for r in rs),
            'present_in_dec2024_snapshot':sum(r['baseline_membership'] for r in rs),
            'near_city_edge_500m':sum(r['background_annulus_crosses_city_boundary'] for r in rs),
            'acs_near_boundary_10m':sum(r['acs_within10m_boundary'] for r in rs),
            'sld_near_boundary_10m':sum(r['sld_within10m_boundary'] for r in rs)})
    write(OUT/'qa/city_summary.csv',cities)
    manifest()
    status={'phase':3,'build_status':'complete','validation_status':'pending independent computational validation',
        'research_acceptance':'pending phase 2 review and feature-schema ratification','confirmatory_modeling_ready':False,
        'historical_rows':len(context),'full_year_rows':len(full_ids),'primary_predictors':len(schema['primary_predictors']),
        'sensitivity_predictors':len(schema['sensitivity_predictors']),'baseline_statewide_sites':len(baseline),
        'acs_polygons':len(layers['acs2023'].features),'sld_polygons':len(layers['sld2021'].features),
        'range_violations':0,'unmatched_or_ambiguous_joins':sum(r['matches']!=1 for r in assignments),
        'model_fitted':False,'census_api_key_used':False,'city_summary':cities}
    save(OUT/'qa/phase3_status.json',status)
    print(json.dumps(status,indent=2))

if __name__=='__main__':main()
