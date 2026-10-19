"""Audit all phase 5 memberships, saved models, metrics and matched controls."""
import joblib
from phase5_common import *
from run_phase5 import PARAMS,SEEDS,GROUP

def main():
 X,y,meta,names,d=load();ids=[r['site_id'] for r in meta];ix={s:i for i,s in enumerate(ids)};checks=[]
 def check(name,ok=True):
  assert ok,name;checks.append(name);print('PASS',name,flush=True)
 def close(a,b):
  if a in ['',None] or b is None:return a in ['',None] and b is None
  return math.isclose(float(a),float(b),rel_tol=1e-7,abs_tol=1e-8)
 def indices(rows):return np.array([ix[r['row_id']] for r in rows],dtype=int)
 freeze=json.loads((P5/'qa/protocol_freeze.json').read_text())
 check('Protocol and input hashes unchanged',sha(ROOT/freeze['specification'])==freeze['sha256'] and all(sha(ROOT/r['file'])==r['sha256'] for r in read(P5/'qa/input_manifest.csv')))
 frozen=json.loads((P5/'qa/split_freeze.json').read_text())
 check('Splits and samples match their before-fitting freeze',all(sha(P5/p)==h for p,h in frozen.items()))
 rows=read(P5/'data/modeling_cohort.csv')
 check('Unique complete phase 4 cohort and primary labels retained',len(rows)==len(meta) and {r['site_id'] for r in rows}==set(ids) and all(int(r['y'])==int(y[ix[r['site_id']]]) for r in rows))
 splitrows=read(P5/'data/splits.csv');pool={};tests={};source={};separation=[]
 for city in CITIES:
  for fold in range(5):
   rows=[r for r in splitrows if r['city']==city and r['fold']==str(fold)]
   test=indices([r for r in rows if r['role']=='test']);local=indices([r for r in rows if r['role']=='local_pool']);tests[city,fold]=test;pool[city,fold]=local
   expected={i for i,r in enumerate(meta) if r['year']==2025 and r['city']==city and r['spatial_fold']==fold}
   assert len(test)==len(set(test)) and set(test)==expected
   for origin in [city]+[c for c in CITIES if c!=city]:
    candidates=np.array([i for i,r in enumerate(meta) if r['year']==2024 and r['city']==origin]);dist=d[np.ix_(candidates,test)].min(axis=1)
    want=candidates[dist>=1500];actual=local if origin==city else indices([r for r in rows if r['role']==origin])
    assert np.array_equal(actual,want)
    if origin!=city:source[city,fold,origin]=actual
    separation.append({'city':city,'fold':fold,'origin':origin,'candidate_n':len(candidates),'retained_n':len(actual),'purged_n':len(candidates)-len(actual),'min_distance_m':float(d[np.ix_(actual,test)].min()) if len(actual) else None})
   pooled=indices([r for r in rows if r['role']=='pooled']);assert np.array_equal(pooled,np.sort(np.concatenate([source[city,fold,c] for c in CITIES if c!=city])))
   source[city,fold,'pooled']=pooled
 write(P5/'qa/verified_pool_separation.csv',separation)
 check('Every local/source pool uses 2024 only, every test uses 2025 only, with correct 1500 m purging')
 samples=collections.defaultdict(set);samplerows=read(P5/'data/target_samples.csv')
 for r in samplerows:
  key=(r['city'],int(r['fold']),int(r['seed']),float(r['fraction']));samples[key].add(ix[r['row_id']])
  assert int(r['pool_n'])==len(pool[key[:2]]) and int(r['sample_n'])==math.ceil(key[3]*len(pool[key[:2]]))
 for (city,fold),local in pool.items():
  assert [ids[i] for i in local]==sorted(ids[i] for i in local)
  for seed in SEEDS:
   order=np.random.default_rng(seed).permutation(local)
   for fraction in [.1,.25]:assert samples[city,fold,seed,fraction]==set(order[:math.ceil(fraction*len(local))])
   assert samples[city,fold,seed,.1]<=samples[city,fold,seed,.25]
 check('All 20-seed target samples are exact deterministic nested 10%/25% subsets')
 members=collections.defaultdict(set)
 with gzip.open(P5/'qa/training_members.csv.gz','rt',newline='') as f:
  for r in csv.DictReader(f):
   i=ix[r['row_id']];assert i not in members[r['fit_id']];members[r['fit_id']].add(i)
 fits={r['fit_id']:r for r in read(P5/'qa/model_fits.csv')};evals=read(P5/'qa/evaluations.csv');evaluations={};test_by_fit=collections.defaultdict(set)
 for r in evals:
  assert r['status']=='complete'
  key=tuple(r[k] for k in ['city','fold','condition','source','fraction','seed','model']);assert key not in evaluations;evaluations[key]=r
  city=r['city'];fold=int(r['fold']);seed=int(r['seed']);fraction=float(r['fraction']);tr=members[r['fit_id']];te=tests[city,fold]
  if r['condition']=='local_full':expected=set(pool[city,fold]);assert r['source']=='target' and seed==0 and fraction==1
  elif r['condition']=='source_only':expected=set(source[city,fold,r['source']]);assert seed==0 and fraction==0
  else:
   expected=samples[city,fold,seed,fraction].copy()
   if r['condition']=='source_plus_target':expected|=set(source[city,fold,r['source']])
   else:assert r['condition']=='target_only' and r['source']=='target'
  assert tr==expected and all(meta[i]['year']==2024 for i in tr)
  assert int(r['train_n'])==len(tr) and int(r['test_n'])==len(te)
  actual=float(d[np.ix_(sorted(tr),te)].min());assert actual>=1500 and close(actual,r['min_distance_m'])
  assert fits[r['fit_id']]['model']==r['model'];test_by_fit[r['fit_id']].update(te)
 check('All 7380 evaluations use exactly matched source/local/control memberships and held-out cohorts',len(evals)==7380)
 signatures=[(r['model'],r['train_id_hash']) for r in fits.values()]
 check('Cached fits share only identical model/membership sets',len(signatures)==len(set(signatures)) and set(fits)==set(members)==set(test_by_fit))
 predictions=gzread(P5/'data/predictions.csv.gz');byfit=collections.defaultdict(list);byeval=collections.defaultdict(list);vectors=collections.defaultdict(list)
 for r in predictions:
  i=ix[r['site_id']];assert meta[i]['year']==2025 and meta[i]['city']==r['city'] and int(r['y'])==y[i] and r['block_id']==meta[i]['block_id']
  assert 0<=float(r['p_raw'])<=1
  key=tuple(r[k] for k in ['city','fold','condition','source','fraction','seed','model']);assert evaluations[key]['fit_id']==r['fit_id']
  byfit[r['fit_id']].append(r);byeval[key].append(r);vectors[tuple(r[k] for k in GROUP)].append(r)
 for key,rows in byeval.items():
  actual=[ix[r['site_id']] for r in rows];assert len(actual)==len(set(actual)) and set(actual)==set(tests[key[0],int(key[1])])
 assert set(byeval)==set(evaluations)
 for key,rows in vectors.items():
  expected={ids[i] for i,r in enumerate(meta) if r['year']==2025 and r['city']==key[0]};actual=[r['site_id'] for r in rows]
  assert len(actual)==len(set(actual)) and set(actual)==expected
 check('All 1476 test vectors cover the identical full target cohorts with no duplicate/omitted predictions',len(vectors)==1476)
 preprocessing=collections.defaultdict(dict)
 for r in read(P5/'qa/preprocessing.csv'):preprocessing[r['fit_id']][r['feature']]=r
 fallback_count=0
 with threadpool_limits(limits=1):
  for n,(fitid,r) in enumerate(fits.items()):
   tr=np.array(sorted(members[fitid]));te=np.array(sorted(test_by_fit[fitid]));cols=[0] if r['model']=='M0' else list(range(len(names)))
   assert int(r['train_n'])==len(tr) and int(r['positive_n'])==int(y[tr].sum()) and old.idhash(tr,ids)==r['train_id_hash']
   assert json.loads(r['params'])==PARAMS[r['model']]
   fallback=len(set(y[tr]))==1;assert (r['single_class_fallback']=='True')==fallback
   artifact=P5/r['model_artifact'];assert sha(artifact)==r['model_sha256'];bundle=joblib.load(artifact)
   assert bundle['predictors']==[names[j] for j in cols]
   if fallback:
    fallback_count+=1;assert bundle['kind']=='constant' and close(bundle['probability'],y[tr].mean()) and fitid not in preprocessing
    pp=np.full(len(te),bundle['probability'])
   else:
    assert bundle['kind']=='pipeline';pipe=bundle['pipeline'];matrix=X[np.ix_(tr,cols)]
    med=np.array([np.nanmedian(matrix[:,j]) if np.isfinite(matrix[:,j]).any() else 0 for j in range(len(cols))])
    np.testing.assert_allclose(pipe.named_steps['imputer'].statistics_,med,rtol=1e-10,atol=1e-10)
    assert set(preprocessing[fitid])=={names[j] for j in cols}
    for j,col in enumerate(cols):
     pr=preprocessing[fitid][names[col]];assert close(pr['median'],med[j]) and (pr['all_missing_in_training']=='True')==bool(np.isnan(matrix[:,j]).all())
    if r['model']!='M2':
     imputed=np.where(np.isnan(matrix),med,matrix);mean=imputed.mean(axis=0);variance=imputed.var(axis=0);scale=np.sqrt(variance)
     # Independent reconstruction of sklearn's float64 constant-feature error bound.
     eps=np.finfo(np.float64).eps;upper_bound=len(tr)*eps*variance+(len(tr)*mean*eps)**2
     scale[variance<=upper_bound]=1
     np.testing.assert_allclose(pipe.named_steps['scaler'].mean_,mean,rtol=1e-8,atol=1e-8);np.testing.assert_allclose(pipe.named_steps['scaler'].scale_,scale,rtol=1e-8,atol=1e-8)
     for j,col in enumerate(cols):assert close(preprocessing[fitid][names[col]]['mean'],mean[j]) and close(preprocessing[fitid][names[col]]['scale'],scale[j])
     assert pipe.named_steps['model'].C==(np.inf if r['model']=='M0' else 1)
    else:
     for key,value in PARAMS['M2'].items():assert pipe.named_steps['model'].get_params()[key]==value
    pp=pipe.predict_proba(X[np.ix_(te,cols)])[:,1]
   probs=dict(zip(te,pp))
   for row in byfit[fitid]:assert close(row['p_raw'],probs[ix[row['site_id']]])
   if (n+1)%1000==0:print('Verified model artifacts',n+1,'/',len(fits),flush=True)
 check('Every unique saved model reproduces every held-out probability; preprocessing is training-only; constants equal training prevalence')
 # Refit fixed representative cases, independent of serialized estimator state.
 with threadpool_limits(limits=1):
  for city in CITIES:
   for model in MODELS:
    for condition in ['local_full','source_plus_target']:
     r=next(r for r in evals if r['city']==city and r['fold']=='0' and r['model']==model and r['condition']==condition)
     fit=fits[r['fit_id']];tr=np.array(sorted(members[r['fit_id']]));te=tests[city,0];cols=[0] if model=='M0' else list(range(len(names)))
     if fit['single_class_fallback']=='True':continue
     estimator=old.estimator(model,PARAMS[model]);estimator.fit(X[np.ix_(tr,cols)],y[tr]);pp=estimator.predict_proba(X[np.ix_(te,cols)])[:,1]
     rows=byeval[tuple(r[k] for k in ['city','fold','condition','source','fraction','seed','model'])];lookup={row['site_id']:float(row['p_raw']) for row in rows}
     np.testing.assert_allclose(pp,[lookup[ids[i]] for i in te],rtol=1e-7,atol=1e-8)
 check('Representative local and augmented models independently refitted for each city/model family')
 metrics={tuple(r[k] for k in GROUP):r for r in read(P5/'data/metrics.csv')}
 assert set(metrics)==set(vectors)
 for key,rows in vectors.items():
  result=old.metrics(np.array([int(r['y']) for r in rows]),np.array([float(r['p_raw']) for r in rows]),[r['site_id'] for r in rows])
  assert all(close(metrics[key][k],v) for k,v in result.items())
 check('All AP, ROC-AUC, Brier, calibration and top-decile metrics reconcile to prediction vectors')
 for r in read(P5/'data/transfer_gaps.csv'):
  local=metrics[r['city'],'local_full','target','1.0','0',r['model']];zero=metrics[r['city'],'source_only',r['source'],'0.0','0',r['model']]
  assert close(r['local_ap'],local['average_precision']) and close(r['source_ap'],zero['average_precision']) and close(r['transfer_gap'],float(local['average_precision'])-float(zero['average_precision']))
 benefitgroups=collections.defaultdict(list)
 for r in read(P5/'data/transfer_benefits.csv'):
  a=metrics[r['city'],'source_plus_target',r['source'],r['fraction'],r['seed'],r['model']];b=metrics[r['city'],'target_only','target',r['fraction'],r['seed'],r['model']];z=metrics[r['city'],'source_only',r['source'],'0.0','0',r['model']]
  delta=float(a['average_precision'])-float(b['average_precision']);assert close(r['transfer_benefit'],delta) and close(r['improvement_over_zero_shot'],float(a['average_precision'])-float(z['average_precision']))
  assert close(r['augmented_ap'],a['average_precision']) and close(r['target_only_ap'],b['average_precision'])
  benefitgroups[r['city'],r['source'],r['fraction'],r['model']].append(delta)
 for r in read(P5/'data/benefit_summary.csv'):
  values=benefitgroups[r['city'],r['source'],r['fraction'],r['model']]
  assert len(values)==int(r['seeds'])==20 and close(r['mean_benefit'],np.mean(values)) and close(r['sd'],np.std(values,ddof=1))
  assert close(r['seed_p025'],np.quantile(values,.025)) and close(r['seed_p975'],np.quantile(values,.975))
  assert int(r['negative_seeds'])==sum(v<0 for v in values) and int(r['positive_seeds'])==sum(v>0 for v in values)
 check('All transfer gaps, exactly matched benefits and complete 20-seed distribution summaries reconcile')
 for r in read(P5/'data/extrapolation.csv'):
  source_rows=[i for i,m in enumerate(meta) if m['year']==2024 and (m['city']!=r['city'] if r['source']=='pooled' else m['city']==r['source'])]
  target=[i for i,m in enumerate(meta) if m['year']==2025 and m['city']==r['city']];col=names.index(r['feature']);sv=X[source_rows,col];sv=sv[np.isfinite(sv)];tv=X[target,col];known=np.isfinite(tv)
  assert int(r['source_observed'])==len(sv) and int(r['target_observed'])==int(known.sum()) and int(r['target_missing'])==int((~known).sum())
  assert close(r['source_min'],float(sv.min()) if len(sv) else None) and close(r['source_max'],float(sv.max()) if len(sv) else None)
  assert close(r['target_outside_range'],int(((tv[known]<sv.min())|(tv[known]>sv.max())).sum()) if len(sv) else None)
 check('Every source-to-target range and missingness diagnostic independently reconciles')
 status=json.loads((P5/'qa/status.json').read_text())
 check('Counts and scientific-review status are accurate',status['unique_fits']==len(fits) and status['model_evaluations']==len(evals) and status['prediction_rows']==len(predictions) and status['single_class_fits']==fallback_count and status['unsupported']==0 and status['confirmatory_complete'] is False and status['independent_human_review_completed'] is False)
 status['validation']='PASS';save(P5/'qa/status.json',status)
 save(P5/'qa/validation.json',{'status':'PASS','checks':checks,'unique_models_verified':len(fits),'model_evaluations_verified':len(evals),'prediction_rows_verified':len(predictions),'single_class_models_verified':fallback_count,'independent_human_review_completed':False})
 print('Phase 5 validation PASS',flush=True)
if __name__=='__main__':main()
