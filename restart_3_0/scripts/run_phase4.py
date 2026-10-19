"""Frozen 2024-to-2025 nested, spatially separated model comparisons."""
import argparse,collections,datetime as dt,importlib.metadata,json
import numpy as np
from pyproj import Geod
from threadpoolctl import threadpool_limits
from phase4_common import *
SPEC=ROOT/'protocol/phase4_analysis_spec.md'

def inputs():
    freeze=json.loads((OUT/'qa/protocol_freeze.json').read_text());assert sha(SPEC)==freeze['sha256']
    assert json.loads((P3/'qa/validation.json').read_text())['status']=='PASS'
    for r in read(P3/'qa/output_manifest.csv'):assert sha(P3/r['file'])==r['sha256'],r['file']
    panel=sorted(read(ROOT/'data/processed/atm_panel_2024_2025_full_year.csv'),key=lambda r:r['row_id'])
    features={r['row_id']:r for r in read(P3/'data/features_primary.csv')}
    sensitivity={r['row_id']:r for r in read(P3/'data/features_sensitivity.csv')}
    names=json.loads((P3/'data/feature_schema.json').read_text())['primary_predictors']
    assert names[0]=='log1p_background_primary' and len(names)==9
    nearest=collections.Counter()
    with (ROOT/'data/processed/event_atm_links.csv').open() as f:
        for r in csv.DictReader(f):
            if r['role']=='outcome' and r['outcome_year']=='2024' and r['reported_by_year_end']=='True' and r['nearest_cohort_site']=='True' and float(r['distance_m'])<=50:nearest[r['site_id']+':2024']+=1
    X=[];meta=[]
    for p in panel:
        rid=p['row_id'];year=int(p['outcome_year']);r={'site_id':rid,'physical_site_id':p['site_id'],'outcome_year':year,'city':p['city'],'longitude':p['longitude'],'latitude':p['latitude'],'confirmatory_eligible':False,'label_vintage':'report_filtered_before_2025' if year==2024 else 'latest_archive_2025_occurrences','unfiltered_primary_label':int(p['primary_any_50m'])}
        for variant,(field,_,_) in VARIANTS.items():
            radius=25 if variant=='radius_25m' else 100 if variant=='radius_100m' else 50
            count=nearest[rid] if variant=='nearest_only_50m' and year==2024 else int(p['primary_nearest_count_50m']) if variant=='nearest_only_50m' else int(p[f'primary_reported_count_{radius}m']) if year==2024 else int(p[f'primary_count_{radius}m'])
            r['y_'+variant]=int(count>0)
        r['log1p_background_unfiltered']=safe(sensitivity[rid]['log1p_background_unfiltered'])
        X.append([safe(features[rid][n]) for n in names]);meta.append(r)
    return np.array(X),meta,names

def prepare(meta):
    folds=np.zeros(len(meta),dtype=int)
    with threadpool_limits(limits=1):
        for year in [2024,2025]:
            idx=[i for i,r in enumerate(meta) if r['outcome_year']==year]
            f,b,xy,_=partitions([meta[i] for i in idx])
            for j,i in enumerate(idx):
                folds[i]=f[j];meta[i].update(spatial_fold=int(f[j]),block_id=b[j],easting_m=float(xy[j,0]),northing_m=float(xy[j,1]))
    lon=np.array([float(r['longitude']) for r in meta]);lat=np.array([float(r['latitude']) for r in meta]);g=Geod(ellps='WGS84')
    distance=np.array([g.inv(np.full(len(meta),lon[i]),np.full(len(meta),lat[i]),lon,lat)[2] for i in range(len(meta))])
    city=np.array([r['city'] for r in meta]);year=np.array([r['outcome_year'] for r in meta]);idx=np.arange(len(meta))
    plans={};outer=[];inner=[];audit=[]
    def purge(candidates,test):return candidates[distance[np.ix_(candidates,test)].min(axis=1)>=PURGE_M] if len(candidates) else candidates
    for variant,(_,_,exclude) in VARIANTS.items():
        eligible=idx[city!='Buffalo'] if exclude else idx;tr24=eligible[year[eligible]==2024];te25=eligible[year[eligible]==2025]
        definitions=[('forward_spatial',f'fold_{k}',te25[folds[te25]==k],tr24) for k in range(5)]
        definitions += [('forward_leave_city_out',c.lower().replace(' ','_'),te25[city[te25]==c],tr24[city[tr24]!=c]) for c in CITIES if not(exclude and c=='Buffalo')]
        plans[variant]=[]
        for scheme,name,test,candidates in definitions:
            train=purge(candidates,test);removed=np.setdiff1d(candidates,train);assert len(train) and len(test)
            tag={'variant':variant,'scheme':scheme,'fold':name};plan=tag|{'train':train,'test':test,'inner':[]}
            for role,rows in [('train',train),('test',test),('purged',removed)]:
                for i in rows:outer.append(tag|{'role':role,'site_id':meta[i]['site_id']})
            audit.append(tag|{'inner_fold':'OUTER','n_train':len(train),'n_test':len(test),'n_purged':len(removed),'minimum_train_test_distance_m':float(distance[np.ix_(train,test)].min())})
            for k in sorted(set(folds[train])):
                val=train[folds[train]==k];cand=train[folds[train]!=k];fit=purge(cand,val);removed=np.setdiff1d(cand,fit)
                plan['inner'].append((int(k),fit,val))
                for role,rows in [('train',fit),('validation',val),('purged',removed)]:
                    for i in rows:inner.append(tag|{'inner_fold':int(k),'role':role,'site_id':meta[i]['site_id']})
                audit.append(tag|{'inner_fold':int(k),'n_train':len(fit),'n_test':len(val),'n_purged':len(removed),'minimum_train_test_distance_m':float(distance[np.ix_(fit,val)].min()) if len(fit) else None})
            plans[variant].append(plan)
    write(OUT/'data/modeling_cohort.csv',meta);write(OUT/'data/outer_split_membership.csv',outer);write(OUT/'data/inner_split_membership.csv',inner);write(OUT/'qa/split_separation.csv',audit)
    hashes={p:sha(OUT/'data'/p) for p in ['modeling_cohort.csv','outer_split_membership.csv','inner_split_membership.csv']}
    path=OUT/'qa/split_freeze.json'
    if path.exists():assert json.loads(path.read_text())['sha256']==hashes
    else:save(path,{'frozen_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':hashes})
    return plans

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
    for folder in ['data','qa','models','docs','figures']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    freeze={'specification':str(SPEC.relative_to(ROOT)),'sha256':sha(SPEC)};path=OUT/'qa/protocol_freeze.json'
    if path.exists():assert json.loads(path.read_text())==freeze,'Protocol changed after freeze'
    else:save(path,freeze)
    (OUT/'qa/validation.json').unlink(missing_ok=True);(OUT/'qa/output_manifest.csv').unlink(missing_ok=True)
    save(OUT/'qa/phase4_status.json',{'computational_status':'running','validation_status':'pending','confirmatory_modeling_ready':False})
    X,meta,names=inputs();plans=prepare(meta)
    save(OUT/'qa/experiment_registry.json',{'seed':SEED,'purge_m':PURGE_M,'block_size_m':2000,'training_year':2024,'test_year':2025,'candidates':CANDIDATES,'variants':VARIANTS,'primary_predictors':names,'analysis_status':'RETROSPECTIVE_2024_TO_2025','phase5_performed':False})
    files=[SPEC,ROOT/'requirements-phase4.txt',ROOT/'requirements.txt',ROOT/'data/processed/atm_panel_2024_2025_full_year.csv',ROOT/'data/processed/event_atm_links.csv',P3/'qa/output_manifest.csv']
    files += [ROOT/'scripts'/n for n in ['run_phase4.py','phase4_common.py']]
    write(OUT/'qa/input_manifest.csv',[{'file':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in files])
    if args.prepare_only:print('Prepared',sum(map(len,plans.values())),'outer evaluations.');return
    store=[[] for _ in range(6)];started=dt.datetime.now(dt.timezone.utc).isoformat()
    with threadpool_limits(limits=1):
        for variant,ps in plans.items():
            x=X.copy();y=np.array([r['y_'+variant] for r in meta])
            if variant=='unfiltered_background':x[:,0]=[r['log1p_background_unfiltered'] for r in meta]
            for plan in ps:
                for dest,rows in zip(store,fit_plan(plan,x,y,names,meta)):dest.extend(rows)
                print(variant,plan['scheme'],plan['fold'],'train',len(plan['train']),'test',len(plan['test']),flush=True)
    predictions,search,prep,fits,warnings_log,calib=store
    for name,rows in [('data/predictions.csv',predictions),('data/inner_search_scores.csv',search),('qa/fitted_preprocessing.csv',prep),('qa/model_fit_audit.csv',fits),('qa/calibration_training_oof.csv',calib)]:write(OUT/name,rows)
    write(OUT/'qa/fit_warnings.csv',warnings_log,['variant','scheme','fold','model','stage','warning'])
    evaluate(predictions);bootstrap(predictions)
    save(OUT/'qa/run_environment.json',{'python':os.sys.version,'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','xgboost-cpu','joblib','matplotlib','pyproj']},'started_utc':started,'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'cpu_threads_per_model':1})
    save(OUT/'qa/phase4_status.json',{'computational_status':'complete','validation_status':'pending','forward_temporal_validation_completed':True,'training_year':2024,'test_year':2025,'train_cohort_rows':sum(r['outcome_year']==2024 for r in meta),'test_cohort_rows':sum(r['outcome_year']==2025 for r in meta),'outer_evaluations':sum(map(len,plans.values())),'fitted_outer_models':len(fits),'prediction_rows':len(predictions),'confirmatory_modeling_ready':False,'full_blueprint_phase4_complete':False,'research_acceptance':'PENDING independent review; retrospective previously inspected outcomes','phase5_performed':False})
    print('All phase 4 experiments complete.',flush=True)
if __name__=='__main__':main()
