"""Build frozen Phase 3 features without model fitting or target-based choices."""
import collections
import gzip
import csv
import json
import math
import numpy as np
import pyarrow.parquet as pq
import shapefile
from scipy.spatial import cKDTree
from shapely import from_wkb, make_valid, segmentize
from shapely.geometry import Point, shape, box
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import Transformer
from phase3_common import *

class Layer:
    def __init__(self,name,features):
        self.name=name;self.features=features;self.geometries=[];self.repairs=[];self.projected={};self.invalid=[]
        for f in features:
            g=shape(f['geometry'])
            if not g.is_valid:
                fixed=make_valid(g);change=abs(fixed.area-g.area)/max(g.area,1e-20)
                if fixed.geom_type not in ('Polygon','MultiPolygon') or change>=1e-6:
                    self.invalid.append((len(self.geometries),g.envelope))
                    self.repairs.append({'layer':name,'geoid':f['properties'].get('GEOID',f['properties'].get('GEOID20')),
                                         'relative_area_change':change,'repair':'NOT_REPAIRED; bounding-envelope missingness'})
                    self.geometries.append(Point().buffer(0));continue
                self.repairs.append({'layer':name,'geoid':f['properties'].get('GEOID',f['properties'].get('GEOID20')),
                                     'relative_area_change':change,'repair':'make_valid'})
                g=fixed
            assert g.is_valid and not g.is_empty
            self.geometries.append(g)
        self.tree=STRtree(self.geometries)
    def join(self,point,city):
        if self.invalid_at(point):return None,[],None
        ids=sorted(int(i) for i in self.tree.query(point,predicate='covered_by'))
        if len(ids)!=1:return None,ids,None
        i=ids[0];key=(i,city)
        if key not in self.projected:self.projected[key]=transform(TRANS[city].transform,self.geometries[i])
        distance=transform(TRANS[city].transform,point).distance(self.projected[key].boundary)
        return self.features[i]['properties'],ids,distance
    def invalid_at(self,point):
        return [self.features[i]['properties'].get('GEOID',self.features[i]['properties'].get('GEOID20')) for i,g in self.invalid if g.covers(point)]

def load_acs():
    features=[]
    for state,counties in COUNTIES.items():
        with shapefile.Reader(str(geometry_path(state))) as reader:
            for sr in reader.iterShapeRecords():
                p=sr.record.as_dict()
                if p['COUNTYFP'] in counties:
                    features.append({'type':'Feature','properties':{'GEOID':p['GEOID'],'ALAND':p['ALAND']},'geometry':sr.shape.__geo_interface__})
    geoids={f['properties']['GEOID'] for f in features}
    assert len(geoids)==len(features)
    attrs={g:{} for g in geoids};coverage=[]
    variables=sorted({v for f in definitions() for v in f.get('components',[])})
    for table in sorted({v.split('_')[0] for v in variables}):
        needed=[v for v in variables if v.startswith(table+'_')];seen=set()
        with bulk_path(table).open(newline='',encoding='utf-8-sig') as stream:
            for row in csv.DictReader(stream,delimiter='|'):
                geoid=row['GEO_ID']
                if not geoid.startswith('1500000US') or geoid[9:] not in attrs:continue
                g=geoid[9:];assert g not in seen;seen.add(g)
                for variable in needed:
                    tableid,index=variable.split('_')
                    for kind in ('E','M'):
                        raw=row[f'{tableid}_{kind}{index}']
                        attrs[g][variable+kind]=raw if raw else None
                        attrs[g][variable+kind+'A']=ANNOTATIONS.get(raw)
        assert seen==geoids,(table,len(seen),len(geoids))
        coverage.append({'table':table,'block_groups':len(seen),'status':'PASS'})
        print('ACS table',table,'reconciled',len(seen),'block groups',flush=True)
    write(OUT/'data/acs_components.csv',[{'geoid':g,**attrs[g]} for g in sorted(attrs)])
    write(OUT/'qa/acs_import_coverage.csv',coverage)
    return Layer('acs2022',features),attrs

def load_sld():
    features=[]
    for path in sld_paths():features+=json.loads(path.read_text())['features']
    assert len({f['properties']['GEOID20'] for f in features})==len(features)
    return Layer('sld2021',features)

def osm_inventory(city,year):
    date=f'{year-1}-12-15';path=ROOT/f'data/raw/osm_v2/{CITIES[city]}/{date}.parquet'
    if not path.exists():return None
    side=json.loads(Path(str(path)+'.request.json').read_text());assert sha(path)==side['sha256']
    inverse=Transformer.from_crs(TRANS[city].target_crs,4326,always_xy=True)
    objects={}
    for r in pq.read_table(path).to_pylist():
        g=from_wkb(r['geom']) if r['geom'] else None
        if g is None or g.is_empty or not g.is_valid:continue
        point=g if g.geom_type=='Point' else transform(inverse.transform,transform(TRANS[city].transform,g).centroid)
        oid=f"{r['osm_type']}/{r['osm_id']}";assert oid not in objects
        objects[oid]=(point.x,point.y)
    bounds=list(map(float,side['params']['aoi'].split(',')))
    boundary=transform(TRANS[city].transform,segmentize(box(*bounds),.005))
    return objects,boundary

def competition(row,inventory):
    result={'atm_density_500m':None,'nearest_other_atm':None,'atm_neighbor_count_500m':None,
        'atm_colocated_other_objects_10m':None,'atm_query_margin_m':None,'atm_density_coverage':False,
        'atm_nearest_coverage':False,'atm_baseline_focal_present':False,'atm_snapshot_date':None}
    links=[]
    if inventory is None:return result,links
    objects,boundary=inventory;lon=float(row['longitude']);lat=float(row['latitude']);city=row['city']
    point=Point(*TRANS[city].transform(lon,lat))
    margin=point.distance(boundary.boundary)/1.01 if boundary.covers(point) else 0
    ids=sorted(oid for oid in objects if oid!=row['osm_id'])
    distances=np.array([GEOD.inv(lon,lat,*objects[oid])[2] for oid in ids])
    count=int(np.sum(distances<=500));nearest=float(np.min(distances)) if len(distances) else None
    density_ok=margin>500;nearest_ok=nearest is not None and nearest<margin
    result.update(atm_density_500m=count/(math.pi*.5**2) if density_ok else None,
        nearest_other_atm=nearest if nearest_ok else None,atm_neighbor_count_500m=count,
        atm_colocated_other_objects_10m=int(np.sum(distances<=10)),atm_query_margin_m=margin,
        atm_density_coverage=density_ok,atm_nearest_coverage=nearest_ok,
        atm_baseline_focal_present=row['osm_id'] in objects,atm_snapshot_date=f"{int(row['outcome_year'])-1}-12-15")
    for oid,d in zip(ids,distances):
        if d<=500 or d==nearest:
            links.append({'row_id':row['row_id'],'neighbor_osm_id':oid,'distance_m':float(d),
                'neighbor_longitude':objects[oid][0],'neighbor_latitude':objects[oid][1],
                'snapshot_date':result['atm_snapshot_date'],'within_500m':d<=500,'nearest':d==nearest})
    return result,links

def lag_features(panels):
    grouped=collections.defaultdict(list)
    for e in read(ROOT/'data/processed/crime_primary_2022_2025.csv'):
        grouped[(e['city'],int(e['event_year']))].append(e)
    results={};audits=[]
    fields=['row_id','event_id','city','event_date','report_date','report_date_usable','category','distance_m','report_available_by_cutoff']
    path=OUT/'data/prior_event_links.csv.gz';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as rawstream:
        with gzip.GzipFile(filename='',fileobj=rawstream,mode='wb',mtime=0) as compressed:
            import io
            with io.TextIOWrapper(compressed,newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
                for city in CITIES:
                    for year in (2023,2024,2025):
                        es=grouped[(city,year-1)];lon=np.array([float(e['longitude']) for e in es]);lat=np.array([float(e['latitude']) for e in es])
                        tree=cKDTree(np.column_stack(TRANS[city].transform(lon,lat)))
                        cutoff=f'{year}-01-01'
                        for p in panels:
                            if p['city']!=city or int(p['outcome_year'])!=year:continue
                            lo,la=float(p['longitude']),float(p['latitude']);counts=np.zeros((2,6),dtype=int);unknown=late=0
                            for j in sorted(tree.query_ball_point(TRANS[city].transform(lo,la),102)):
                                d=GEOD.inv(lo,la,lon[j],lat[j])[2]
                                if d>100:continue
                                e=es[j];usable=e['report_date_usable']=='True';known=usable and e['report_date']<cutoff
                                increments=np.array([d<=25,d<=50,True,d<=50 and e['category']=='robbery',
                                    d<=50 and e['category']=='burglary',d<=50 and e['event_date'][5:7]>='07'],dtype=int)
                                counts[0]+=increments
                                if known:counts[1]+=increments
                                unknown+=not usable;late+=usable and not known
                                writer.writerow({'row_id':p['row_id'],'event_id':e['event_id'],'city':city,'event_date':e['event_date'],
                                    'report_date':e['report_date'],'report_date_usable':e['report_date_usable'],'category':e['category'],
                                    'distance_m':d,'report_available_by_cutoff':known})
                            values={n:int(v) if city!='Chicago' else None for n,v in zip(LAGS,counts[1])}
                            values.update({n+'_unfiltered':int(v) for n,v in zip(LAGS,counts[0])})
                            results[p['row_id']]=values
                            audits.append({'row_id':p['row_id'],'cutoff':cutoff,'prior_year':year-1,'city_events':len(es),
                                'nearby_missing_report_date':unknown,'nearby_late_report':late,
                                'report_filtered_available':city!='Chicago'})
                        print('Prior crime built:',city,year,flush=True)
    write(OUT/'qa/prior_crime_availability.csv',audits)
    return results

def main():
    freeze();verify_phase12();panels=panel();defs=definitions()
    acs,attrs=load_acs();sld=load_sld();lag=lag_features(panels)
    inventories={(city,year):osm_inventory(city,year) for city in CITIES for year in (2023,2024,2025)}
    contexts=[];lookup=[];joins=[];neighbors=[];models=[];outcomes=[]
    variables=sorted({v for f in defs for v in f.get('components',[])})
    for p in panels:
        rowid=p['row_id'];city=p['city'];year=int(p['outcome_year']);cutoff=f'{year}-01-01'
        point=Point(float(p['longitude']),float(p['latitude']))
        a,ai,ad=acs.join(point,city) if year>=2024 else (None,[],None)
        s,si,sd=sld.join(point,city);ar=attrs[a['GEOID']] if a else {}
        context={'row_id':rowid,'acs_geoid_2022':a['GEOID'] if a else None,'sld_geoid_2019':s['GEOID20'] if s else None,
            'acs_land_area_m2':a['ALAND'] if a else None,'background_primary':number(p['background_primary_200_500m']),
            'background_unfiltered':number(p['background_unfiltered_200_500m']),**lag[rowid]}
        for v in variables:
            for suffix in ('E','M','EA','MA'):context[v+suffix]=ar.get(v+suffix)
        for f in defs:
            if f['source']=='ACS2022':context[f['name']]=acs_value(f,ar,a['ALAND'] if a else None)
            if f['source']=='EPA_SLD2021':
                raw=s.get(f['field']) if s else None;context['sld_'+f['field']]=raw;context[f['name']]=number(raw)
        comp,links=competition(p,inventories[(city,year)]);context.update({k:comp[k] for k in ('atm_density_500m','nearest_other_atm')});neighbors+=links
        quality={k:p[k] for k in ('row_id','site_id','city','longitude','latitude','osm_id','cohort','supported_days','annulus_fraction_inside_city','boundary_distance_projected_m')}
        quality.update(outcome_year=year,prediction_cutoff=cutoff,acs_available_at_cutoff=year>=2024,
            acs_matches=len(ai),sld_matches=len(si),acs_boundary_distance_m=ad,sld_boundary_distance_m=sd,
            acs_boundary_within_10m=ad is not None and ad<10,sld_boundary_within_10m=sd is not None and sd<10,
            acs_income_coding_flag=ar.get('B19013_001E') in ('250001','2499'),
            report_filtered_crime_available=city!='Chicago',confirmatory_modeling_ready=False,
            acs_invalid_source_geoids='|'.join(map(str,acs.invalid_at(point))) if year>=2024 else '',
            sld_invalid_source_geoids='|'.join(map(str,sld.invalid_at(point))),
            **{k:v for k,v in comp.items() if k not in ('atm_density_500m','nearest_other_atm')})
        for name,layer,ids in [('acs2022',acs,ai),('sld2021',sld,si)]:
            invalid=layer.invalid_at(point)
            joins.append({'row_id':rowid,'layer':name,'matches':len(ids),
                'status':'not_available_at_cutoff' if name=='acs2022' and year==2023 else 'invalid_source_geometry' if invalid else 'unique' if len(ids)==1 else 'unmatched' if not ids else 'ambiguous',
                'invalid_source_geoids':'|'.join(map(str,invalid)),
                'candidate_geoids':'|'.join(str(layer.features[i]['properties'].get('GEOID',layer.features[i]['properties'].get('GEOID20'))) for i in ids)})
        model={'row_id':rowid}
        for f in defs:
            value=context[f['name']];model[f['predictor']]=math.log1p(value) if value is not None and f['transform']=='log1p' else value
        models.append(model);contexts.append(context);lookup.append(quality)
        outcomes.append({k:p[k] for k in ['row_id']+[f'{prefix}_{radius}m' for radius in (25,50,100) for prefix in ('primary_count','primary_any')]})
    write(OUT/'data/site_context_raw.csv',contexts);write(OUT/'data/site_lookup_and_quality.csv',lookup)
    write(OUT/'data/outcomes.csv',outcomes);write(OUT/'qa/spatial_join_audit.csv',joins)
    write(OUT/'data/atm_neighbor_links.csv',neighbors,['row_id','neighbor_osm_id','distance_m','neighbor_longitude','neighbor_latitude','snapshot_date','within_500m','nearest'])
    write(OUT/'qa/geometry_repairs.csv',acs.repairs+sld.repairs,['layer','geoid','relative_area_change','repair'])
    for role in ('primary','sensitivity'):
        fields=['row_id']+[f['predictor'] for f in defs if f['role']==role]
        for suffix,years in [('full_year_2024_2025',(2024,2025)),('2024',(2024,)),('2025',(2025,)),('partial_2023',(2023,))]:
            write(OUT/f'data/features_{role}_{suffix}.csv',[{k:r[k] for k in fields} for r,l in zip(models,lookup) if l['outcome_year'] in years],fields)
    schema={'version':'restart6_phase3_v1','key':'row_id','primary_predictors':[f['predictor'] for f in defs if f['role']=='primary'],
        'sensitivity_predictors':[f['predictor'] for f in defs if f['role']=='sensitivity'],'primary_site_years':2731,'partial_supplement_rows':1287,
        'labels_file':'outcomes.csv','lookup_file':'site_lookup_and_quality.csv','imputation_performed':False,'scaling_performed':False,
        'models_fitted':False,'confirmatory_modeling_ready':False,'chicago_primary_crime_predictors':'missing; report dates unavailable',
        'partial_2023_acs_and_atm_competition':'missing; sources unavailable before cutoff'}
    savejson(OUT/'data/feature_schema.json',schema)
    write(OUT/'data/feature_dictionary.csv',[{**f,'components':'|'.join(f.get('components',[])),'numerator':'|'.join(f.get('numerator',[])),
        'missing_value_policy':'blank means unavailable; never implicitly zero','formula':json.dumps(f,sort_keys=True)} for f in defs])
    print('Phase 3 built:',len(models),'rows;',len(schema['primary_predictors']),'primary predictors',flush=True)

if __name__=='__main__':main()
