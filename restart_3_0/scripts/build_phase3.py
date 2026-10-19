"""Build housing-context predictors without using outcomes."""
import json,math,collections
import numpy as np
import shapefile
from scipy.stats import spearmanr
from shapely.geometry import Point
import phase3_common as c
ROOT=c.ROOT;OUT=c.OUT;RAW=ROOT/'data/raw/environment_acs2022';SPEC=ROOT/'protocol/phase3_feature_spec.md'
def specs():return json.loads((ROOT/'protocol/environment_variables.json').read_text())['features']
def definitions():
    defs=[dict(raw_feature='background_primary',predictor='log1p_background_primary',transformation='log1p',role='primary')]
    for f in specs():defs.append(dict(raw_feature=f['name'],predictor=('log1p_' if f['transform']=='log1p' else '')+f['name'],transformation=f['transform'],role='primary'))
    defs.append(dict(raw_feature='background_unfiltered',predictor='log1p_background_unfiltered',transformation='log1p',role='sensitivity'))
    return defs

def attributes():
    attrs={};coverage={}
    for path in sorted((RAW/'attributes').glob('county_*.json')):
        if '.request.' in path.name:continue
        table=json.loads(path.read_text());keys=set()
        for values in table[1:]:
            r=dict(zip(table[0],values));key=''.join(r[k] for k in ['state','county','tract','block group']);assert key not in keys;keys.add(key)
            previous=attrs.setdefault(key,{})
            for field,value in r.items():
                if field in previous:assert previous[field]==value
                previous[field]=value
        county=path.name.split('_')[1]
        if county in coverage:assert coverage[county]==keys
        coverage[county]=keys
    assert len(coverage)==7
    return attrs

def layers():
    reader=shapefile.Reader(str(ROOT/'data/raw/temporal_extension/acs2022/tl_2022_36_bg.zip'));features=[]
    for sr in reader.iterShapeRecords():
        p=sr.record.as_dict()
        if p['COUNTYFP'] in ['005','047','061','081','085','029','055']:
            features.append(dict(type='Feature',properties=dict(GEOID=p['GEOID'],ALAND=p['ALAND']),geometry=sr.shape.__geo_interface__))
    path=OUT/'data/acs2022_boundaries.geojson';c.save(path,dict(type='FeatureCollection',features=features))
    attrs=attributes();assert {f['properties']['GEOID'] for f in features}==set(attrs)
    return c.PolygonLayer('acs2022',[path]),attrs

def value(f,ar):
    vals={v:c.number(ar.get(v+'E')) for v in f['components']}
    if any(v is None for v in vals.values()):return None
    if 'denominator' in f:
        den=vals[f['denominator']]
        if not den:return None
        result=sum(vals[v] for v in f['numerator'])/den
        assert 0<=result<=1.000001
        return result
    result=vals[f['components'][0]]
    if 'subtract_from' in f:
        if not 1600<=result<=f['subtract_from']:return None
        result=f['subtract_from']-result
    return result

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
    (OUT/'data').mkdir(parents=True,exist_ok=True);defs=definitions()
    schema=dict(version='restart_3_0',feature_spec_sha256=c.digest(SPEC),primary_predictors=[d['predictor'] for d in defs if d['role']=='primary'],sensitivity_predictors=['log1p_background_unfiltered'],key='row_id',imputation_performed=False,scaling_performed=False,model_fitted=False,confirmatory_modeling_ready=False)
    c.save(OUT/'data/feature_schema.json',schema);c.write(OUT/'data/feature_dictionary.csv',defs)
    acs,attrs=layers();panel=c.read(ROOT/'data/processed/atm_panel_2024_2025_full_year.csv')
    contexts=[];lookups=[];models=[];joins=[]
    for p in panel:
        year=int(p['outcome_year']);city=p['city'];lon=float(p['longitude']);lat=float(p['latitude'])
        a,indices,distance=acs.join(Point(lon,lat),city);ar=attrs[a['GEOID']] if a else {}
        row=dict(row_id=p['row_id'],acs_geoid_2022=a['GEOID'] if a else None,background_primary=c.number(p['background_primary_200_500m']),background_unfiltered=c.number(p['background_unfiltered_200_500m']))
        for f in specs():
            for v in f['components']:
                for suffix in ['E','M','EA','MA']:row[v+suffix]=ar.get(v+suffix)
            row[f['name']]=value(f,ar)
        lookup=dict(row_id=p['row_id'],year=year,city=city,longitude=lon,latitude=lat,acs_join_matches=len(indices),acs_boundary_distance_m=distance,confirmatory_eligible=False)
        joins.append(dict(row_id=p['row_id'],matches=len(indices),status='unique' if len(indices)==1 else 'unmatched' if not indices else 'ambiguous'))
        model={'row_id':p['row_id']}
        for d in defs:
            v=row[d['raw_feature']];model[d['predictor']]=math.log1p(v) if v is not None and d['transformation']=='log1p' else v
        contexts.append(row);lookups.append(lookup);models.append(model)
    c.write(OUT/'data/site_context_raw.csv',contexts);c.write(OUT/'data/site_lookup_and_quality.csv',lookups);c.write(OUT/'qa/spatial_join_audit.csv',joins)
    for kind in ['primary','sensitivity']:
        fields=['row_id']+schema[kind+'_predictors'];rows=[{k:r[k] for k in fields} for r in models]
        c.write(OUT/f'data/features_{kind}.csv',rows,fields)
        for year in [2024,2025]:c.write(OUT/f'data/features_{kind}_{year}.csv',[r for r,l in zip(rows,lookups) if l['year']==year],fields)
    diagnostics(models,lookups,defs)
    paths=[p for p in RAW.rglob('*') if p.is_file()]+[SPEC,ROOT/'protocol/environment_variables.json',ROOT/'data/processed/atm_panel_2024_2025_full_year.csv',ROOT/'data/raw/temporal_extension/acs2022/tl_2022_36_bg.zip']
    paths += [ROOT/'scripts'/name for name in ['build_phase3.py','phase3_common.py','validate_phase3.py','report_phase3.py']]
    c.write(OUT/'qa/input_manifest.csv',[dict(file=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=c.digest(p)) for p in sorted(set(paths))])
    c.save(OUT/'qa/phase3_status.json',dict(build_status='complete',validation_status='pending',site_years=len(models),primary_predictors=9,confirmatory_modeling_ready=False))
    print('Built',len(models),'rows; join statuses',dict(collections.Counter(r['status'] for r in joins)),flush=True)
if __name__=='__main__':main()
