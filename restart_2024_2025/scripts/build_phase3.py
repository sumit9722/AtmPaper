"""Build frozen common predictors for both restart panels; no model fitting."""
import collections, math, json, re
from pathlib import Path
import numpy as np
import shapefile
from scipy.stats import spearmanr
from shapely.geometry import Point,shape
from shapely.ops import transform
import phase3_common as c
ROOT=c.ROOT; OUT=c.OUT; RAW=c.RAW
ACS=ROOT/'data/raw/temporal_extension/acs2022'
SPEC=ROOT/'protocol/phase3_feature_spec.md'

def definitions():
    result=[]
    for name,method,unit,source,role,vintage in c.DEFS:
        if name=='background_report_date_cutoff':name='background_unfiltered'
        source={'acs2023':'acs2022','dfs2024':'prior_december_dfs','police_2024':'prior_year_police'}.get(source,source)
        unit=unit.replace('2023 USD','2022 USD')
        formula=c.SOURCE_FIELDS.get(name,'background_unfiltered_200_500m')
        if name=='background_primary':formula='background_primary_200_500m (phase 2 report cutoff applied)'
        if name=='nearest_other_atm':formula='minimum WGS84 distance to other prior-December DFS identity'
        if name=='population_density':formula='B01003_001E / ALAND * 1000000'
        result.append({'raw_feature':name,'predictor':('log1p_'+name if method=='log1p' else name),'transformation':method,'unit':unit,'source':source,'formula':formula,'role':role,'missing_policy':'retain null; future training-fold imputation only'})
    return result

def baseline(year):
    path=ROOT/('data/raw/temporal_extension/atm_history/dfs_2023-12-15_v258.csv' if year==2024 else 'data/raw/atm_history/dfs_2024-12-15_v270.csv')
    sites={}; exclusions=[]
    for i,raw in enumerate(c.read(path)):
        r={re.sub(r'[^a-z0-9]+','_',k.lower()).strip('_'):v for k,v in raw.items()}
        coords=re.findall(r'-?\d+(?:\.\d+)?',r.get('georeference',''))
        if len(coords)!=2:exclusions.append({'source_row':i,'reason':'unparsed_coordinates'});continue
        lon,lat=map(float,coords)
        if not (-80<lon<-71 and 40<lat<46):exclusions.append({'source_row':i,'reason':'outside_broad_NY_bounds'});continue
        key=c.identity(r['street_address'],lon,lat)
        sites.setdefault(key,{'baseline_id':c.hashlib.sha256('|'.join(key).encode()).hexdigest()[:16],'address':r['street_address'],'longitude':lon,'latitude':lat,'snapshot_date':f'{year-1}-12-15'})
    c.write(OUT/f'data/atm_baseline_{year}.csv',sites.values())
    c.write(OUT/f'qa/baseline_exclusions_{year}.csv',exclusions,['source_row','reason'])
    return sites

def layers():
    reader=shapefile.Reader(str(ACS/'tl_2022_36_bg.zip'));features=[]
    for sr in reader.iterShapeRecords():
        p=sr.record.as_dict()
        if p['COUNTYFP'] in ['005','047','061','081','085','029','055']:
            features.append({'type':'Feature','properties':{'GEOID':p['GEOID'],'ALAND':p['ALAND']},'geometry':sr.shape.__geo_interface__})
    path=OUT/'data/acs2022_boundaries.geojson';path.write_text(json.dumps({'type':'FeatureCollection','features':features}))
    attrs={}
    for path in sorted((ACS/'attributes').glob('county_*.json')):
        if '.request.' in path.name:continue
        table=json.loads(path.read_text())
        for values in table[1:]:
            r=dict(zip(table[0],values));key=''.join(r[k] for k in ['state','county','tract','block group'])
            assert key not in attrs;attrs[key]=r
    assert {f['properties']['GEOID'] for f in features}==set(attrs),'ACS geography/attribute mismatch'
    return c.PolygonLayer('acs2022',[OUT/'data/acs2022_boundaries.geojson']),c.PolygonLayer('sld2021'),attrs

def diagnostics(rows,lookup,defs):
    byid={r['row_id']:r for r in lookup};stats=[];corr=[]
    for year in [2024,2025,'ALL']:
        for city in c.CITIES+['ALL']:
            group=[r for r in rows if (year=='ALL' or byid[r['row_id']]['year']==year) and (city=='ALL' or byid[r['row_id']]['city']==city)]
            for d in defs:
                name=d['predictor'];values=np.array([r[name] for r in group if r[name] is not None]);missing=len(group)-len(values)
                q=np.quantile(values,[0,.25,.5,.75,1]).tolist() if len(values) else [None]*5
                stats.append({'year':year,'city':city,'feature':name,'rows':len(group),'missing':missing,'missing_fraction':missing/len(group),'min':q[0],'q25':q[1],'median':q[2],'q75':q[3],'max':q[4],'high_missingness_gt20pct':missing>.2*len(group),'zero_variance':len(set(values))<=1})
            names=[d['predictor'] for d in defs if d['role']=='primary']
            for i,a in enumerate(names):
                for b in names[i+1:]:
                    pairs=np.array([[r[a],r[b]] for r in group if r[a] is not None and r[b] is not None]);rho=None
                    if len(pairs)>=3 and np.ptp(pairs[:,0])>0 and np.ptp(pairs[:,1])>0:rho=float(spearmanr(pairs[:,0],pairs[:,1]).statistic)
                    corr.append({'year':year,'city':city,'feature_a':a,'feature_b':b,'pairwise_n':len(pairs),'spearman_rho':rho,'abs_rho_ge_0_90':rho is not None and abs(rho)>=.9})
    c.write(OUT/'qa/feature_distributions.csv',stats);c.write(OUT/'qa/feature_correlations.csv',corr)

def main():
    (OUT/'data').mkdir(parents=True,exist_ok=True)
    (OUT/'qa/validation.json').unlink(missing_ok=True)
    (OUT/'qa/output_manifest.csv').unlink(missing_ok=True)
    c.save(OUT/'qa/phase3_status.json',{'phase':3,'build_status':'running','validation_status':'not_validated','confirmatory_modeling_ready':False})
    defs=definitions();schema={'version':'restart_2024_2025_v1','feature_spec_sha256':c.digest(SPEC),'prediction_cutoffs':['2024-01-01','2025-01-01'],'primary_predictors':[d['predictor'] for d in defs if d['role']=='primary'],'sensitivity_predictors':[d['predictor'] for d in defs if d['role']=='sensitivity'],'key':'row_id','imputation_performed':False,'scaling_performed':False,'model_fitted':False,'confirmatory_modeling_ready':False}
    path=OUT/'data/feature_schema.json'
    if path.exists():assert json.loads(path.read_text())==schema,'Frozen specification changed; version amendment required'
    c.save(path,schema);c.write(OUT/'data/feature_dictionary.csv',defs)
    acs,sld,attrs=layers();baselines={y:baseline(y) for y in [2024,2025]}
    polys={('New York City' if f['properties']['BASENAME']=='New York' else f['properties']['BASENAME']):shape(f['geometry']) for f in json.loads((ROOT/'data/raw/boundaries/cities.geojson').read_text())['features']}
    projected_cities={city:transform(c.TRANS[city].transform,poly) for city,poly in polys.items()}
    panel=c.read(ROOT/'data/processed/atm_panel_2024_2025_full_year.csv')
    contexts=[];lookups=[];models=[];joins=[]
    for p in panel:
        year=int(p['outcome_year']);city=p['city'];lon=float(p['longitude']);lat=float(p['latitude']);point=Point(lon,lat)
        a,ai,ad=acs.join(point,city);s,si,sd=sld.join(point,city);ar=attrs[a['GEOID']] if a else None
        row={'row_id':p['row_id'],'acs_geoid_2022':a['GEOID'] if a else None,'sld_geoid_2019':s['GEOID20'] if s else None,'acs_land_area_m2':c.number(a['ALAND']) if a else None,'background_primary':c.number(p['background_primary_200_500m']),'background_unfiltered':c.number(p['background_unfiltered_200_500m'])}
        for field in ['B01003_001','B19013_001','B23025_003','B23025_005']:
            for suffix in ['E','M','EA','MA']:row[field+suffix]=ar[field+suffix] if ar else None
        row['population']=c.number(ar['B01003_001E']) if ar else None
        row['population_density']=row['population']*1e6/row['acs_land_area_m2'] if row['population'] is not None and row['acs_land_area_m2'] else None
        row['median_household_income']=c.number(ar['B19013_001E']) if ar else None
        labor=c.number(ar['B23025_003E']) if ar else None;unemployed=c.number(ar['B23025_005E']) if ar else None
        row['unemployment_rate']=unemployed/labor if labor and unemployed is not None else None
        annotation=(ar.get('B19013_001EA') or '') if ar else ''
        row['income_topcoded']='+' in annotation;row['income_bottomcoded']=annotation.endswith('-') and annotation!='-'
        for name,field in c.SLD_FIELDS.items():row['sld_raw_'+field]=s.get(field) if s else None;row[name]=c.number(s.get(field)) if s else None
        row.update(c.competition(lon,lat,p['address_raw'],baselines[year]));assert row['baseline_membership']
        edge=transform(c.TRANS[city].transform,point).distance(projected_cities[city].boundary)
        lookup={'row_id':p['row_id'],'site_id':p['site_id'],'year':year,'city':city,'longitude':lon,'latitude':lat,'prediction_cutoff':f'{year}-01-01','supported_days':p['supported_days'],'confirmatory_eligible':False,'acs_join_matches':len(ai),'sld_join_matches':len(si),'acs_boundary_distance_m':ad,'sld_boundary_distance_m':sd,'acs_within10m_boundary':ad is not None and ad<=10,'sld_within10m_boundary':sd is not None and sd<=10,'city_boundary_distance_m':edge,'background_annulus_crosses_city_boundary':edge<=500,'baseline_membership':row['baseline_membership'],'other_atm_within10m':row['other_atm_count_within10m']>0,'coordinate_precision_flag':p['coordinate_precision_flag'],'strict_asof_police_data_available':False}
        for name,indices,layer in [('acs2022',ai,acs),('sld2021',si,sld)]:
            joins.append({'row_id':p['row_id'],'layer':name,'matches':len(indices),'status':'unique' if len(indices)==1 else 'unmatched' if not indices else 'ambiguous','candidate_geoids':'|'.join(str(layer.features[i]['properties'].get('GEOID',layer.features[i]['properties'].get('GEOID20'))) for i in indices)})
        model={'row_id':p['row_id']}
        for d in defs:
            v=row[d['raw_feature']]
            assert v is None or math.isfinite(v) and v>=0
            if d['raw_feature'] in ['employment_mix','unemployment_rate']:assert v is None or v<=1.000001
            model[d['predictor']]=math.log1p(v) if v is not None and d['transformation']=='log1p' else v
        contexts.append(row);lookups.append(lookup);models.append(model)
    c.write(OUT/'data/site_context_raw.csv',contexts);c.write(OUT/'data/site_lookup_and_quality.csv',lookups);c.write(OUT/'qa/spatial_join_audit.csv',joins)
    for kind in ['primary','sensitivity']:
        fields=['row_id']+schema[kind+'_predictors'];rows=[{k:r[k] for k in fields} for r in models]
        c.write(OUT/f'data/features_{kind}.csv',rows,fields)
        for year in [2024,2025]:c.write(OUT/f'data/features_{kind}_{year}.csv',[r for r,l in zip(rows,lookups) if l['year']==year],fields)
    diagnostics(models,lookups,defs)
    summary=[]
    for year in [2024,2025]:
        for city in c.CITIES:
            rows=[r for r in lookups if r['year']==year and r['city']==city]
            summary.append({'year':year,'city':city,'rows':len(rows),'acs_unique':sum(r['acs_join_matches']==1 for r in rows),'sld_unique':sum(r['sld_join_matches']==1 for r in rows),'near_city_edge_500m':sum(r['background_annulus_crosses_city_boundary'] for r in rows),'acs_boundary_10m':sum(r['acs_within10m_boundary'] for r in rows),'sld_boundary_10m':sum(r['sld_within10m_boundary'] for r in rows)})
    c.write(OUT/'qa/city_year_summary.csv',summary)
    paths=[p for folder in [RAW,ACS] for p in folder.rglob('*') if p.is_file()]
    paths += [SPEC,ROOT/'data/processed/atm_panel_2024_2025_full_year.csv',ROOT/'data/raw/boundaries/cities.geojson',ROOT/'data/raw/temporal_extension/atm_history/dfs_2023-12-15_v258.csv',ROOT/'data/raw/atm_history/dfs_2024-12-15_v270.csv']
    paths += [ROOT/'scripts'/name for name in ['build_phase3.py','phase3_common.py','validate_phase3.py','report_phase3.py']]
    c.write(OUT/'qa/input_manifest.csv',[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':c.digest(p)} for p in sorted(set(paths))])
    c.save(OUT/'qa/phase3_status.json',{'phase':3,'build_status':'complete','validation_status':'pending','site_years':len(models),'primary_predictors':14,'sensitivity_predictors':3,'confirmatory_modeling_ready':False,'model_fitted':False,'research_acceptance':'PENDING phase 2 independent review and feature approval'})
    print(json.dumps(summary,indent=2),flush=True)
if __name__=='__main__':main()
