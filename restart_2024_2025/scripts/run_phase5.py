"""Prespecified earlier-label transfer ladder, with matched controls and 20 seeds."""
import datetime as dt, warnings
from phase5_common import *
import joblib, importlib.metadata, argparse
PARAMS={'M0':{},'M1':{'C':1},'M2':{'max_depth':2,'reg_lambda':10}}
SEEDS=list(range(20261001,20261021))
GROUP=['city','condition','source','fraction','seed','model']
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
 for sub in ['data','qa','figures','models','docs']:(P5/sub).mkdir(parents=True,exist_ok=True)
 spec=ROOT/'protocol/phase5_transfer_spec.md';freeze={'specification':str(spec.relative_to(ROOT)),'sha256':sha(spec)};path=P5/'qa/protocol_freeze.json'
 if path.exists():assert json.loads(path.read_text())==freeze,'Frozen phase 5 specification changed'
 else:save(path,freeze)
 (P5/'qa/validation.json').unlink(missing_ok=True);(P5/'qa/output_manifest.csv').unlink(missing_ok=True)
 save(P5/'qa/status.json',{'computation':'running','validation':'pending','confirmatory_complete':False})
 started=dt.datetime.now(dt.timezone.utc).isoformat()
 X,y,meta,names,d=load();P5.mkdir(parents=True,exist_ok=True)
 for sub in ['data','qa','figures']:(P5/sub).mkdir(exist_ok=True)
 ids=[r['site_id'] for r in meta];years=np.array([r['year'] for r in meta]);cities=np.array([r['city'] for r in meta]);folds=np.array([r['spatial_fold'] for r in meta]);idx24=np.flatnonzero(years==2024);idx25=np.flatnonzero(years==2025)
 plans=[];splits=[];samples=[]
 for city in CITIES:
  for fold in range(5):
   test=np.flatnonzero((years==2025)&(cities==city)&(folds==fold));pool=purge(np.flatnonzero((years==2024)&(cities==city)),test,d)
   sources={c:purge(np.flatnonzero((years==2024)&(cities==c)),test,d) for c in CITIES if c!=city};sources['pooled']=np.sort(np.concatenate(list(sources.values())))
   for role,ix in [('test',test),('local_pool',pool)]+[(c,v) for c,v in sources.items()]:
    splits.extend({'city':city,'fold':fold,'role':role,'row_id':ids[i],'year':int(years[i])} for i in ix)
   def add(condition,source,fraction,seed,train):plans.append({'city':city,'fold':fold,'condition':condition,'source':source,'fraction':fraction,'seed':seed,'train':np.sort(train),'test':test})
   add('local_full','target',1.,0,pool)
   for source,ix in sources.items():add('source_only',source,0.,0,ix)
   for seed in SEEDS:
    order=np.random.default_rng(seed).permutation(pool)
    for fraction in [.1,.25]:
     selected=order[:math.ceil(fraction*len(pool))];samples.extend({'city':city,'fold':fold,'seed':seed,'fraction':fraction,'pool_n':len(pool),'sample_n':len(selected),'row_id':ids[i]} for i in selected)
     add('target_only','target',fraction,seed,selected)
     for source,ix in sources.items():add('source_plus_target',source,fraction,seed,np.concatenate([ix,selected]))
 write(P5/'data/splits.csv',splits);write(P5/'data/target_samples.csv',samples);freeze_splits([P5/'data/splits.csv',P5/'data/target_samples.csv'])
 write(P5/'data/modeling_cohort.csv',meta)
 save(P5/'qa/experiment_registry.json',{'training_year':2024,'test_year':2025,'seeds':SEEDS,'parameters':PARAMS,'purge_m':1500,'fractions':[.1,.25],'primary_predictors':names,'planned_evaluations':len(plans)*len(MODELS),'phase4_primary_gate_passed':False})
 paths=[spec,ROOT/'scripts/run_phase5.py',ROOT/'scripts/phase5_common.py',ROOT/'scripts/run_phase4.py',ROOT/'scripts/phase4_common.py',ROOT/'requirements-phase5.txt',P4/'qa/output_manifest.csv',P4/'data/modeling_cohort.csv',ROOT/'results/phase3/qa/output_manifest.csv',ROOT/'data/processed/atm_panel_2024_2025_full_year.csv']
 write(P5/'qa/input_manifest.csv',[{'file':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in paths])
 if args.prepare_only:print('Prepared',len(plans),'plans /',len(plans)*len(MODELS),'model evaluations.',flush=True);return
 cache={};fitrows=[];members=[];preprocess=[];warn=[];pred=[];evals=[]
 with threadpool_limits(limits=1):
  for n,plan in enumerate(plans):
   train=plan['train'];test=plan['test'];tag={k:plan[k] for k in ['city','fold','condition','source','fraction','seed']}
   for model in MODELS:
    key=(model,tuple(train));cols=[0] if model=='M0' else list(range(len(names)))
    if not len(train):evals.append(tag|{'model':model,'status':'unsupported_empty_pool'});continue
    if key not in cache:
     fitid=f'fit_{len(cache):05d}';fallback=len(set(y[train]))<2
     if fallback:
      prob=np.full(len(meta),float(y[train].mean()));bundle={'kind':'constant','probability':float(y[train].mean()),'predictors':[names[c] for c in cols]}
     else:
      estimator=old.estimator(model,PARAMS[model])
      with warnings.catch_warnings(record=True) as caught:
       warnings.simplefilter('always');estimator.fit(X[np.ix_(train,cols)],y[train])
      warn.extend({'fit_id':fitid,'warning':str(w.message)} for w in caught)
      prob=np.full(len(meta),np.nan);prob[idx25]=estimator.predict_proba(X[np.ix_(idx25,cols)])[:,1]
      imp=estimator.named_steps['imputer'];scaler=estimator.named_steps.get('scaler')
      preprocess.extend({'fit_id':fitid,'feature':names[c],'median':float(imp.statistics_[j]),'mean':float(scaler.mean_[j]) if scaler is not None else None,'scale':float(scaler.scale_[j]) if scaler is not None else None,'all_missing_in_training':bool(np.isnan(X[train,c]).all())} for j,c in enumerate(cols))
      bundle={'kind':'pipeline','pipeline':estimator,'predictors':[names[c] for c in cols]}
     artifact=P5/'models'/f'{fitid}.joblib';joblib.dump(bundle,artifact,compress=3)
     cache[key]=(fitid,prob)
     fitrows.append({'fit_id':fitid,'model':model,'params':json.dumps(PARAMS[model],sort_keys=True),'train_n':len(train),'positive_n':int(y[train].sum()),'single_class_fallback':fallback,'training_year':2024,'train_id_hash':old.idhash(train,ids),'model_artifact':str(artifact.relative_to(P5)),'model_sha256':sha(artifact)})
     members.extend({'fit_id':fitid,'row_id':ids[i]} for i in train)
    fitid,prob=cache[key];evals.append(tag|{'model':model,'fit_id':fitid,'status':'complete','train_n':len(train),'test_n':len(test),'min_distance_m':float(d[np.ix_(train,test)].min())})
    pred.extend(tag|{'model':model,'fit_id':fitid,'site_id':ids[i],'y':int(y[i]),'p_raw':float(prob[i]),'block_id':meta[i]['block_id']} for i in test)
   if n%164==163:print('Phase 5 plans',n+1,'/',len(plans),'unique fits',len(cache),flush=True)
 gzip_rows(P5/'data/predictions.csv.gz',pred);gzip_rows(P5/'qa/training_members.csv.gz',members)
 write(P5/'qa/model_fits.csv',fitrows);write(P5/'qa/preprocessing.csv',preprocess);write(P5/'qa/evaluations.csv',evals);write(P5/'qa/warnings.csv',warn,['fit_id','warning'])
 metrics=metrics_table(pred,GROUP);write(P5/'data/metrics.csv',metrics)
 lookup={tuple(r[k] for k in GROUP):r for r in metrics};gaps=[];benefits=[]
 for r in metrics:
  if r['condition']=='source_only':
   local=lookup[(r['city'],'local_full','target',1.,0,r['model'])]
   gaps.append({k:r[k] for k in ['city','source','model']}|{'local_ap':local['average_precision'],'source_ap':r['average_precision'],'transfer_gap':local['average_precision']-r['average_precision']})
  if r['condition']=='source_plus_target':
   control=lookup[(r['city'],'target_only','target',r['fraction'],r['seed'],r['model'])];zero=lookup[(r['city'],'source_only',r['source'],0.,0,r['model'])]
   benefits.append({k:r[k] for k in ['city','source','fraction','seed','model']}|{'augmented_ap':r['average_precision'],'target_only_ap':control['average_precision'],'transfer_benefit':r['average_precision']-control['average_precision'],'improvement_over_zero_shot':r['average_precision']-zero['average_precision']})
 write(P5/'data/transfer_gaps.csv',gaps);write(P5/'data/transfer_benefits.csv',benefits)
 grouped=collections.defaultdict(list)
 for r in benefits:grouped[tuple(r[k] for k in ['city','source','fraction','model'])].append(r['transfer_benefit'])
 summary=[dict(zip(['city','source','fraction','model'],k))|{'seeds':len(v),'mean_benefit':float(np.mean(v)),'sd':float(np.std(v,ddof=1)),'seed_p025':float(np.quantile(v,.025)),'seed_p975':float(np.quantile(v,.975)),'negative_seeds':sum(x<0 for x in v),'positive_seeds':sum(x>0 for x in v)} for k,v in grouped.items()]
 write(P5/'data/benefit_summary.csv',summary)
 extra=[]
 for city in CITIES:
  target=idx25[cities[idx25]==city]
  for source in [c for c in CITIES if c!=city]+['pooled']:
   ix=idx24[cities[idx24]!=city] if source=='pooled' else idx24[cities[idx24]==source]
   for j,name in enumerate(names):
    values=X[ix,j];values=values[np.isfinite(values)];tv=X[target,j];known=np.isfinite(tv)
    extra.append({'city':city,'source':source,'feature':name,'source_observed':len(values),'target_observed':int(known.sum()),'target_missing':int((~known).sum()),'source_min':float(values.min()) if len(values) else None,'source_max':float(values.max()) if len(values) else None,'target_outside_range':int(((tv[known]<values.min())|(tv[known]>values.max())).sum()) if len(values) else None})
 write(P5/'data/extrapolation.csv',extra)
 save(P5/'qa/run_environment.json',{'started_utc':started,'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'python':old.os.sys.version,'packages':{n:importlib.metadata.version(n) for n in ['numpy','scipy','scikit-learn','xgboost-cpu','joblib','matplotlib','pyproj']},'cpu_threads_per_model':1})
 save(P5/'qa/status.json',{'computation':'complete','validation':'pending','training_year':2024,'test_year':2025,'seeds':SEEDS,'plans':len(plans),'model_evaluations':len(evals),'unique_fits':len(fitrows),'prediction_rows':len(pred),'unsupported':sum(r['status']!='complete' for r in evals),'single_class_fits':sum(r['single_class_fallback'] for r in fitrows),'confirmatory_complete':False,'independent_human_review_completed':False,'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
 print('Phase 5 complete',len(fitrows),'unique fits',len(pred),'predictions',flush=True)
if __name__=='__main__':main()
