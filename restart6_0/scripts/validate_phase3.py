"""Independent source, formula, spatial and temporal audits for Phase 3."""
import collections
import csv
import gzip
import json
import math
import random
import numpy as np
import shapefile
from shapely.geometry import Point, shape
from shapely import make_valid
from scipy.stats import spearmanr
from phase3_common import *

def same(a,b):
    if a in (None,''):assert b in (None,''),(a,b)
    else:assert b not in (None,'') and math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-9),(a,b)

def main():
    freeze();verify_phase12();manifest_check(OUT/'qa/input_manifest.csv');checks={}
    checks['frozen_inputs_and_phase12_integrity']='PASS'
    panels=panel();pby={p['row_id']:p for p in panels};assert len(pby)==4018
    raw={r['row_id']:r for r in read(OUT/'data/site_context_raw.csv')}
    lookup={r['row_id']:r for r in read(OUT/'data/site_lookup_and_quality.csv')}
    assert set(raw)==set(lookup)==set(pby)
    defs=definitions();schema=json.loads((OUT/'data/feature_schema.json').read_text())
    models={k:{} for k in pby}
    for role in ('primary','sensitivity'):
        fields=['row_id']+[f['predictor'] for f in defs if f['role']==role]
        for suffix,years in [('full_year_2024_2025',('2024','2025')),('2024',('2024',)),('2025',('2025',)),('partial_2023',('2023',))]:
            path=OUT/f'data/features_{role}_{suffix}.csv'
            with path.open() as stream:
                reader=csv.DictReader(stream);assert reader.fieldnames==fields;rows=list(reader)
            expected={p['row_id'] for p in panels if p['outcome_year'] in years}
            assert {r['row_id'] for r in rows}==expected and len(rows)==len(expected)
            for r in rows:
                for field in fields[1:]:
                    if field in models[r['row_id']]:same(models[r['row_id']][field],r[field])
                    models[r['row_id']][field]=r[field]
    assert len(schema['primary_predictors'])==28 and len(schema['sensitivity_predictors'])==9
    assert not schema['models_fitted'] and not schema['imputation_performed'] and not schema['scaling_performed']
    checks['cohort_preservation_and_predictor_allowlist']='PASS'
    # Independently parse public source cells and verify every imported component.
    imported={r['geoid']:r for r in read(OUT/'data/acs_components.csv')}
    variables=sorted({v for f in defs for v in f.get('components',[])})
    source_cells=0
    for table in sorted({v.split('_')[0] for v in variables}):
        needed=[v for v in variables if v.startswith(table+'_')];seen=set()
        with bulk_path(table).open(newline='',encoding='utf-8-sig') as stream:
            reader=csv.reader(stream,delimiter='|');header=next(reader);pos={v:i for i,v in enumerate(header)}
            for values in reader:
                identifier=values[pos['GEO_ID']]
                if not identifier.startswith('1500000US') or identifier[9:] not in imported:continue
                geoid=identifier[9:];assert geoid not in seen;seen.add(geoid)
                for variable in needed:
                    tableid,index=variable.split('_')
                    for kind in ('E','M'):
                        original=values[pos[f'{tableid}_{kind}{index}']]
                        assert imported[geoid][variable+kind]==original
                        assert imported[geoid][variable+kind+'A']==(ANNOTATIONS.get(original) or '')
                        source_cells+=1
        assert seen==set(imported)
    checks['all_acs_estimates_margins_and_jam_annotations']='PASS'
    # Independently assemble polygon sources; scalar covers scans do not use a spatial index.
    acs_polys=[];acs_area={};unsafe={'acs2022':[],'sld2021':[]}
    for state,counties in COUNTIES.items():
        with shapefile.Reader(str(geometry_path(state))) as reader:
            for sr in reader.iterShapeRecords():
                p=sr.record.as_dict()
                if p['COUNTYFP'] not in counties:continue
                geometry=shape(sr.shape.__geo_interface__)
                if not geometry.is_valid:
                    fixed=make_valid(geometry);change=abs(fixed.area-geometry.area)/max(geometry.area,1e-20)
                    if fixed.geom_type not in ('Polygon','MultiPolygon') or change>=1e-6:
                        unsafe['acs2022'].append((p['GEOID'],geometry.envelope));geometry=Point().buffer(0)
                    else:geometry=fixed
                acs_polys.append((p['GEOID'],geometry));acs_area[p['GEOID']]=p['ALAND']
    assert set(acs_area)==set(imported)
    sld_attrs={};sld_polys=[]
    for path in sld_paths():
        for f in json.loads(path.read_text())['features']:
            p=f['properties'];geoid=p['GEOID20'];assert geoid not in sld_attrs
            sld_attrs[geoid]=p;geometry=shape(f['geometry'])
            if not geometry.is_valid:
                fixed=make_valid(geometry);change=abs(fixed.area-geometry.area)/max(geometry.area,1e-20)
                if fixed.geom_type not in ('Polygon','MultiPolygon') or change>=1e-6:
                    unsafe['sld2021'].append((geoid,geometry.envelope));geometry=Point().buffer(0)
                else:geometry=fixed
            sld_polys.append((geoid,geometry))
    for state in ('17','06'):
        for county in COUNTIES[state]:
            prefix=f'{state}_{county}';ids=[]
            for path in sorted((RAW/'sld2021').glob(prefix+'_*.geojson')):
                ids.extend(f['properties']['OBJECTID'] for f in json.loads(path.read_text())['features'])
            before=json.loads((RAW/f'sld2021/{prefix}_count_before.json').read_text())['count']
            after=json.loads((RAW/f'sld2021/{prefix}_count_after.json').read_text())['count']
            assert len(ids)==len(set(ids))==before==after
    checks['sld_pagination_identity_and_counts']='PASS'
    selected=[]
    for city in CITIES:
        for year in ('2023','2024','2025'):
            group=sorted(p['row_id'] for p in panels if p['city']==city and p['outcome_year']==year)
            selected+=random.Random(603).sample(group,min(4,len(group)))
    for rowid in selected:
        p=pby[rowid];point=Point(float(p['longitude']),float(p['latitude']))
        for name,layer,key in [('acs2022',acs_polys,'acs_geoid_2022'),('sld2021',sld_polys,'sld_geoid_2019')]:
            unavailable=(name=='acs2022' and p['outcome_year']=='2023') or any(g.covers(point) for _,g in unsafe[name])
            matches=[] if unavailable else [g for g,polygon in layer if polygon.covers(point)]
            assert raw[rowid][key]==(str(matches[0]) if len(matches)==1 else '')
            assert int(lookup[rowid]['acs_matches' if name=='acs2022' else 'sld_matches'])==len(matches)
    checks['independent_scalar_polygon_membership']='PASS'
    for rowid,p in pby.items():
        point=Point(float(p['longitude']),float(p['latitude']))
        for name,key,flag in [('acs2022','acs_geoid_2022','acs_invalid_source_geoids'),('sld2021','sld_geoid_2019','sld_invalid_source_geoids')]:
            expected=[] if name=='acs2022' and p['outcome_year']=='2023' else [str(geoid) for geoid,g in unsafe[name] if g.covers(point)]
            assert lookup[rowid][flag]=='|'.join(expected)
            if expected:assert raw[rowid][key]==''
    checks['invalid_source_geometry_conservative_missingness']='PASS'
    # Check all formulas against imported sources; do not call the builder's formula helper.
    for rowid,r in raw.items():
        p=pby[rowid];year=int(p['outcome_year']);a=imported.get(r['acs_geoid_2022'],{});s=sld_attrs.get(r['sld_geoid_2019'],{})
        for variable in variables:
            for suffix in ('E','M','EA','MA'):assert r[variable+suffix]==a.get(variable+suffix,'')
        for f in defs:
            if f['source']=='ACS2022':
                values=[number(a.get(v+'E')) for v in f['components']];expected=None
                if all(v is not None for v in values):
                    mapping=dict(zip(f['components'],values))
                    if 'denominator' in f:
                        denominator=mapping[f['denominator']]
                        if denominator>0:expected=sum(mapping[v] for v in f['numerator'])/denominator
                    elif 'area_denominator' in f:
                        area=acs_area[r['acs_geoid_2022']];expected=values[0]*1e6/area if area>0 else None
                    elif 'subtract_from' in f:
                        expected=2022-values[0] if 1600<=values[0]<=2022 else None
                    else:expected=values[0]
                if year==2023:assert r[f['name']]==''
                else:assert f['available_at']<lookup[rowid]['prediction_cutoff']
                same(expected,r[f['name']])
            elif f['source']=='EPA_SLD2021':
                same(number(s.get(f['field'])),r[f['name']]);assert f['available_at']<lookup[rowid]['prediction_cutoff']
            value=number(r[f['name']]);transformed=math.log1p(value) if value is not None and f['transform']=='log1p' else value
            same(transformed,models[rowid][f['predictor']])
        same(number(p['background_primary_200_500m']),r['background_primary'])
        same(number(p['background_unfiltered_200_500m']),r['background_unfiltered'])
    checks['all_feature_formulas_transforms_and_vintage_cutoffs']='PASS'
    events=read(ROOT/'data/processed/crime_primary_2022_2025.csv');byid={e['event_id']:e for e in events}
    grouped=collections.defaultdict(list)
    for e in events:grouped[(e['city'],e['event_year'])].append(e)
    counts=collections.defaultdict(lambda:np.zeros((2,6),dtype=int));seen=set();nlinks=0
    with gzip.open(OUT/'data/prior_event_links.csv.gz','rt',newline='') as stream:
        for link in csv.DictReader(stream):
            p=pby[link['row_id']];e=byid[link['event_id']];key=(p['row_id'],e['event_id'])
            assert key not in seen;seen.add(key)
            assert e['city']==p['city'] and int(e['event_year'])==int(p['outcome_year'])-1
            d=GEOD.inv(float(p['longitude']),float(p['latitude']),float(e['longitude']),float(e['latitude']))[2]
            same(d,link['distance_m']);assert d<=100
            known=e['report_date_usable']=='True' and e['report_date']<p['outcome_year']+'-01-01'
            assert (link['report_available_by_cutoff']=='True')==known
            increment=np.array([d<=25,d<=50,True,d<=50 and e['category']=='robbery',d<=50 and e['category']=='burglary',d<=50 and e['event_date'][5:7]>='07'],dtype=int)
            counts[p['row_id']][0]+=increment
            if known:counts[p['row_id']][1]+=increment
            nlinks+=1
    for rowid,p in pby.items():
        for index,name in enumerate(LAGS):
            same(counts[rowid][0,index],raw[rowid][name+'_unfiltered'])
            same(None if p['city']=='Chicago' else counts[rowid][1,index],raw[rowid][name])
    for rowid in selected:
        p=pby[rowid];es=grouped[(p['city'],str(int(p['outcome_year'])-1))]
        distances=GEOD.inv(np.full(len(es),float(p['longitude'])),np.full(len(es),float(p['latitude'])),
            np.array([float(e['longitude']) for e in es]),np.array([float(e['latitude']) for e in es]))[2]
        direct={(rowid,e['event_id']) for e,d in zip(es,distances) if d<=100}
        assert direct=={key for key in seen if key[0]==rowid}
    checks['prior_event_link_replay_and_bruteforce_omissions']='PASS'
    # Reconstruct ATM counts from prior-December raw inventories, including outside-city objects.
    from build_phase3 import osm_inventory
    inventories={(city,year):osm_inventory(city,year) for city in CITIES for year in (2024,2025)}
    neighbor_links=collections.defaultdict(list)
    for link in read(OUT/'data/atm_neighbor_links.csv'):neighbor_links[link['row_id']].append(link)
    for rowid,p in pby.items():
        year=int(p['outcome_year']);q=lookup[rowid]
        if year==2023:
            assert raw[rowid]['atm_density_500m']==raw[rowid]['nearest_other_atm']==''
            assert not neighbor_links[rowid];continue
        objects,boundary=inventories[(p['city'],year)]
        distances={oid:GEOD.inv(float(p['longitude']),float(p['latitude']),lo,la)[2] for oid,(lo,la) in objects.items() if oid!=p['osm_id']}
        nearest=min(distances.values());count=sum(d<=500 for d in distances.values())
        same(count,q['atm_neighbor_count_500m']);same(sum(d<=10 for d in distances.values()),q['atm_colocated_other_objects_10m'])
        assert q['atm_snapshot_date']==f'{year-1}-12-15'
        point=Point(*TRANS[p['city']].transform(float(p['longitude']),float(p['latitude'])))
        margin=point.distance(boundary.boundary)/1.01 if boundary.covers(point) else 0
        same(margin,q['atm_query_margin_m'])
        assert (q['atm_density_coverage']=='True')==(margin>500)
        assert (q['atm_nearest_coverage']=='True')==(nearest<margin)
        same(count/(math.pi*.25) if margin>500 else None,raw[rowid]['atm_density_500m'])
        same(nearest if nearest<margin else None,raw[rowid]['nearest_other_atm'])
        expected={oid for oid,d in distances.items() if d<=500 or d==nearest}
        actual=neighbor_links[rowid];assert len(actual)==len(expected) and {l['neighbor_osm_id'] for l in actual}==expected
        for l in actual:same(distances[l['neighbor_osm_id']],l['distance_m'])
    checks['all_historical_atm_neighbors_and_query_coverage']='PASS'
    for r in read(OUT/'data/outcomes.csv'):
        for field,value in r.items():assert value==pby[r['row_id']][field]
    checks['labels_separate_and_unchanged']='PASS'
    savejson(OUT/'qa/validation.json',{'status':'PASS','checks':checks,'primary_site_years':2731,'partial_supplement_rows':1287,
        'primary_predictors':28,'sensitivity_predictors':9,'acs_source_cells_verified':source_cells,'prior_event_links':nlinks,
        'bruteforce_sampled_site_years':len(selected),'atm_rows_reconstructed':2731,'scientific_review':'PENDING','confirmatory_modeling_ready':False})
    print('Phase 3 validation PASS:',len(checks),'groups;',nlinks,'prior-event links',flush=True)

if __name__=='__main__':main()
