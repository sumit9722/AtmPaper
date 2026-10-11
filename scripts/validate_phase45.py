"""Independent recomputation of temporal splits, sampling, preprocessing and metrics."""
import joblib
from temporal_common import *
def gzread(p):
 with gzip.open(p,'rt',newline='') as f:return list(csv.DictReader(f))
def main():
 X,y,meta,names,d=load();ids=[r['site_id'] for r in meta];ix={id:i for i,id in enumerate(ids)};checks=[]
 def check(name,condition):
  assert condition,name
  checks.append({'check':name,'passed':True});print('PASS',name,flush=True)
 def close(a,b):return np.allclose(a,b,rtol=1e-8,atol=1e-10,equal_nan=True)
 def indices(rs):return np.array([ix[r['row_id']] for r in rs],dtype=int)
 check('unique year-site identities',len(ids)==len(set(ids)))
 check('both years and all cities present',all(any(r['year']==yr and r['city']==c for r in meta) for yr in [2024,2025] for c in CITIES))
 check('full-year leap-year exposure',all(int(r['supported_days'])==(366 if r['year']==2024 else 365) for r in meta))
 links=read(DATA/'qa/continuity_links_2024.csv');groups=collections.defaultdict(list)
 for r in links:
  if r['eligible']=='True':groups[r['site_id']].append(r)
 check('14 unique continuity snapshots and <=50m drift',all(len(rs)==14 and len({r['snapshot'] for r in rs})==14 and max(float(r['distance_from_baseline_m']) for r in rs)<=50 for rs in groups.values()) and set(groups)=={r['physical_site_id'] for r in meta if r['year']==2024})
 panel={r['site_id']:r for r in read(ROOT/'data/processed/atm_panel_2025_full_year.csv')}
 check('2025 labels unchanged',all(int(panel[r['physical_site_id']]['primary_any_50m'])==int(r['y']) for r in meta if r['year']==2025))
 counts=collections.Counter()
 for r in read(DATA/'data/outcome_links_2024.csv'):
  if r['known_by_2025']=='True':
   assert r['report_datetime'] and r['report_datetime'][:10]<'2025-01-01'
   if float(r['distance_m'])<=50:counts[r['row_id']]+=1
 check('2024 labels reconcile to eligible reported crimes',all(counts[r['row_id']]==int(r['primary_count_50m']) and int(r['y'])==int(counts[r['row_id']]>0) for r in meta if r['year']==2024))
 check('input hashes unchanged',all(sha(ROOT/r['file'])==r['sha256'] for r in read(DATA/'qa/input_manifest.csv')))
 frozen=json.loads((DATA/'qa/amendment_freeze.json').read_text())['sha256']
 check('pre-fit amendments and experiment implementation unchanged',all(sha(ROOT/p)==h for p,h in frozen.items()))
 outer=read(P4/'data/outer_splits.csv');inner=read(P4/'data/inner_splits.csv');trainmap={};testmap={}
 for k in range(5):
  train=indices([r for r in outer if r['fold']==str(k) and r['role']=='train']);test=indices([r for r in outer if r['fold']==str(k) and r['role']=='test']);trainmap[k]=train;testmap[k]=test
  assert all(meta[i]['year']==2024 for i in train) and all(meta[i]['year']==2025 for i in test)
  assert d[np.ix_(train,test)].min()>=1500
  for j in range(5):
   fit=indices([r for r in inner if r['fold']==str(k) and r['inner_fold']==str(j) and r['role']=='train']);val=indices([r for r in inner if r['fold']==str(k) and r['inner_fold']==str(j) and r['role']=='validation'])
   assert set(fit)|set(val)<=set(train)
   if len(fit) and len(val):assert d[np.ix_(fit,val)].min()>=1500
 check('phase4 temporal nesting and 1500m separation',True)
 pred4=read(P4/'data/predictions.csv')
 for fit in read(P4/'qa/model_fits.csv'):
  k=int(fit['fold'].split('_')[-1]);tr=trainmap[k];te=testmap[k];a=joblib.load(P4/fit['model_artifact']);cols=[names.index(n) for n in a['predictors']]
  assert sha(P4/fit['model_artifact'])==fit['model_sha256'];assert old.idhash(tr,ids)==fit['train_id_hash']
  med=np.array([np.nanmedian(X[tr,c]) if np.isfinite(X[tr,c]).any() else 0 for c in cols]);assert close(med,a['pipeline'].named_steps['imputer'].statistics_)
  probs=a['pipeline'].predict_proba(X[np.ix_(te,cols)])[:,1];lookup={r['site_id']:r for r in pred4 if r['model']==fit['model'] and r['fold']==fit['fold']}
  assert close(probs,[float(lookup[ids[i]]['p_raw']) for i in te]);assert close(old.calibrate(probs,a['sigmoid']),[float(lookup[ids[i]]['p_sigmoid']) for i in te])
 check('all 15 temporal models reproduce predictions and training medians',True)
 for r in read(P4/'qa/calibration_training.csv'):assert ix[r['site_id']] in trainmap[int(r['fold'].split('_')[-1])]
 check('calibration uses only outer training rows',True)
 metrics4=metrics_table(pred4,['city','model'],['raw','sigmoid'])+metrics_table([r|{'city':'ALL'} for r in pred4],['city','model'],['raw','sigmoid'])
 def compare_metrics(actual,path,keys):
  saved={tuple(r[k] for k in keys):r for r in read(path)}
  assert len(actual)==len(saved)
  for r in actual:
   oldr=saved[tuple(str(r[k]) for k in keys)]
   for name in ['average_precision','roc_auc','brier_score','ece_10bins']:
    if r[name] is not None:assert close(r[name],float(oldr[name]))
 compare_metrics(metrics4,P4/'data/metrics.csv',['city','model','probabilities']);check('phase4 metrics recomputed',True)
 replicates=read(P4/'data/bootstrap_replicates.csv')
 for r in read(P4/'data/paired_ap_comparisons.csv'):
  model=r['comparison'].split('-')[0];vals=[float(x['delta_'+model]) for x in replicates if x['city']==r['city'] and x['delta_'+model]]
  assert len(vals)==int(r['valid_replicates']);assert close(np.quantile(vals,[.025,.975]),[float(r['ci_low']),float(r['ci_high'])])
  assert (r['numerical_gate']=='True')==(float(r['ap_difference'])>=.01 and float(r['ci_low'])>0)
 check('bootstrap intervals and numerical gates reconcile',True)
 splits=read(P5/'data/splits.csv');pool={};tests={};source={}
 for c in CITIES:
  for k in range(5):
   rows=[r for r in splits if r['city']==c and r['fold']==str(k)]
   pool[c,k]=indices([r for r in rows if r['role']=='local_pool']);tests[c,k]=indices([r for r in rows if r['role']=='test'])
   for s in [x for x in CITIES if x!=c]+['pooled']:source[c,k,s]=indices([r for r in rows if r['role']==s])
 samples=collections.defaultdict(set)
 for r in read(P5/'data/target_samples.csv'):samples[r['city'],int(r['fold']),int(r['seed']),float(r['fraction'])].add(ix[r['row_id']])
 for (c,k),p in pool.items():
  for seed in range(20261001,20261021):
   order=np.random.default_rng(seed).permutation(p)
   for fraction in [.1,.25]:assert samples[c,k,seed,fraction]==set(order[:math.ceil(fraction*len(p))])
   assert samples[c,k,seed,.1]<=samples[c,k,seed,.25]
 check('20 deterministic seeds, exact fractions and nested subsets',True)
 members=collections.defaultdict(set)
 for r in gzread(P5/'qa/training_members.csv.gz'):members[r['fit_id']].add(ix[r['row_id']])
 fits5={r['fit_id']:r for r in read(P5/'qa/model_fits.csv')}
 evals=read(P5/'qa/evaluations.csv')
 for r in evals:
  assert r['status']=='complete'
  c=r['city'];k=int(r['fold']);seed=int(r['seed']);fraction=float(r['fraction']);tr=members[r['fit_id']];te=tests[c,k]
  expected=set(pool[c,k]) if r['condition']=='local_full' else set(source[c,k,r['source']]) if r['condition']=='source_only' else samples[c,k,seed,fraction]
  if r['condition']=='source_plus_target':expected=expected|set(source[c,k,r['source']])
  assert tr==expected and all(meta[i]['year']==2024 for i in tr)
  assert d[np.ix_(sorted(tr),te)].min()>=1500
 check('every transfer fit uses exact source/control members and spatial separation',True)
 for id,r in fits5.items():
  tr=np.array(sorted(members[id]));assert int(r['train_n'])==len(tr) and int(r['positive_n'])==int(y[tr].sum())
  assert old.idhash(tr,ids)==r['train_id_hash'];assert (r['single_class_fallback']=='True')==(len(set(y[tr]))==1)
 for r in read(P5/'qa/preprocessing.csv'):
  tr=sorted(members[r['fit_id']]);col=names.index(r['feature']);v=X[tr,col];median=np.nanmedian(v) if np.isfinite(v).any() else 0
  assert close(median,float(r['median']))
  if r['mean']:
   v=np.where(np.isnan(v),median,v);assert close(v.mean(),float(r['mean']));assert close(v.std() if v.std()>1e-14 else 1,float(r['scale']))
 check('transfer preprocessing and constant fallback audit',True)
 pred5=gzread(P5/'data/predictions.csv.gz');GROUP=['city','condition','source','fraction','seed','model']
 check('transfer probabilities finite and bounded',all(0<=float(r['p_raw'])<=1 and int(r['y'])==y[ix[r['site_id']]] for r in pred5))
 vectors=collections.defaultdict(list)
 for r in pred5:vectors[tuple(r[k] for k in GROUP)].append(r)
 expected_city={c:{ids[i] for i,r in enumerate(meta) if r['year']==2025 and r['city']==c} for c in CITIES}
 check('all 1476 prediction vectors cover the identical full target cohorts',len(vectors)==1476 and all({r['site_id'] for r in rs}==expected_city[key[0]] and len(rs)==len(expected_city[key[0]]) for key,rs in vectors.items()))
 for r in pred5:
  fit=fits5[r['fit_id']]
  if fit['single_class_fallback']=='True':assert close(float(r['p_raw']),int(fit['positive_n'])/int(fit['train_n']))
 check('single-class probabilities equal training prevalence',True)
 # Refit baseline and adapted conditions in each city/family, independently
 # from saved parameters/memberships, to check the cached prediction route.
 with threadpool_limits(limits=1):
  for c in CITIES:
   for model in MODELS:
    for condition in ['local_full','source_plus_target']:
     evaluation=next(r for r in evals if r['city']==c and r['model']==model and r['condition']==condition and r['fold']=='0')
     fit=fits5[evaluation['fit_id']];tr=np.array(sorted(members[fit['fit_id']]));te=tests[c,0];cols=[0] if model=='M0' else list(range(len(names)))
     if fit['single_class_fallback']=='True':continue
     estimator=old.estimator(model,json.loads(fit['params']));estimator.fit(X[np.ix_(tr,cols)],y[tr]);p=estimator.predict_proba(X[np.ix_(te,cols)])[:,1]
     selected={r['site_id']:r for r in pred5 if all(r[k]==evaluation[k] for k in ['city','fold','condition','source','fraction','seed','model'])}
     assert close(p,[float(selected[ids[i]]['p_raw']) for i in te])
 check('18 representative transfer models independently refitted',True)
 compare_metrics(metrics_table(pred5,GROUP),P5/'data/metrics.csv',GROUP+['probabilities']);check('all transfer metrics independently recomputed',True)
 mets={tuple(r[k] for k in GROUP):r for r in read(P5/'data/metrics.csv')};benefitgroups=collections.defaultdict(list)
 for r in read(P5/'data/transfer_benefits.csv'):
  a=mets[r['city'],'source_plus_target',r['source'],r['fraction'],r['seed'],r['model']];b=mets[r['city'],'target_only','target',r['fraction'],r['seed'],r['model']]
  delta=float(a['average_precision'])-float(b['average_precision']);assert close(delta,float(r['transfer_benefit']));benefitgroups[r['city'],r['source'],r['fraction'],r['model']].append(delta)
 for r in read(P5/'data/benefit_summary.csv'):
  vals=benefitgroups[r['city'],r['source'],r['fraction'],r['model']];assert len(vals)==20;assert close(np.mean(vals),float(r['mean_benefit']));assert close(np.std(vals,ddof=1),float(r['sd']));assert int(r['negative_seeds'])==sum(v<0 for v in vals)
 check('matched transfer benefits and 20-seed distributions reconcile',True)
 for folder in [P4,P5]:
  frozen=json.loads((folder/'qa/split_freeze.json').read_text());assert all(sha(folder/p)==h for p,h in frozen.items())
  status=json.loads((folder/'qa/status.json').read_text());assert status['confirmatory_complete'] is False and status['independent_human_review_completed'] is False
  status['validation']='passed';save(folder/'qa/status.json',status)
 check('frozen splits and honest research status',True)
 check('new artifacts below 100 MB',all(p.stat().st_size<100_000_000 for folder in [DATA,P4,P5,ROOT/'data/raw/temporal_extension'] for p in folder.rglob('*') if p.is_file()))
 for folder in [DATA,P4,P5]:save(folder/'qa/validation.json',{'passed':True,'checks':checks,'independent_human_review':False})
 print(len(checks),'checks passed',flush=True)
if __name__=='__main__':main()
