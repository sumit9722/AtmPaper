"""Verify phase 4 split isolation, fitted preprocessing, predictions and evaluation."""
import collections
import json
import math
from pathlib import Path
import warnings
import joblib
import numpy as np
from pyproj import Geod
from sklearn.metrics import average_precision_score
from run_phase4 import ROOT,OUT,read,save,sha,inputs,metrics,calibrate,VARIANTS,MODELS,CANDIDATES

checks=[]
def check(condition,message):
    if not condition:raise AssertionError(message)
    checks.append(message)
def close(a,b):
    if a in ('',None) or b is None:return a in ('',None) and b is None
    return math.isclose(float(a),float(b),rel_tol=1e-7,abs_tol=1e-8)
def keyed(rows,fields):
    out=collections.defaultdict(list)
    for r in rows:out[tuple(r[k] for k in fields)].append(r)
    return out

X,meta,names=inputs();ids=[r['site_id'] for r in meta];index={sid:i for i,sid in enumerate(ids)}
cohort=read(OUT/'data/modeling_cohort.csv');lookup={r['site_id']:r for r in cohort}
check(set(lookup)==set(ids) and len(cohort)==len(ids),'Model cohort exactly matches phase 3 full-year sites')
check(all(r['confirmatory_eligible']=='False' for r in cohort),'Research-review ineligibility remains explicit')
freeze=json.loads((OUT/'qa/split_freeze.json').read_text())
check(all(sha(OUT/'data'/p)==h for p,h in freeze['sha256'].items()),'All split and cohort hashes match their pre-fitting freeze')
outer=keyed(read(OUT/'data/outer_split_membership.csv'),['variant','scheme','fold'])
inner=keyed(read(OUT/'data/inner_split_membership.csv'),['variant','scheme','fold','inner_fold'])
outer_sets={};inner_sets={}
geod=Geod(ellps='WGS84')
lon=np.array([float(r['longitude']) for r in meta]);lat=np.array([float(r['latitude']) for r in meta])
# Recompute the WGS84 distance matrix independently of the split-builder storage.
distance=np.array([geod.inv(np.full(len(ids),lon[i]),np.full(len(ids),lat[i]),lon,lat)[2] for i in range(len(ids))])
for key,rows in outer.items():
    roles={role:{r['site_id'] for r in rows if r['role']==role} for role in ['train','test','purged']}
    outer_sets[key]=roles
    assert all(not(roles[a]&roles[b]) for a,b in [('train','test'),('train','purged'),('test','purged')])
    eligible={r['site_id'] for r in meta if key[0]!='exclude_buffalo' or r['city']!='Buffalo'}
    assert set.union(*roles.values())==eligible
    tr=[index[s] for s in roles['train']];te=[index[s] for s in roles['test']]
    assert distance[np.ix_(tr,te)].min()>=1500-1e-6
    if roles['purged']:
        removed=[index[s] for s in roles['purged']]
        assert np.all(distance[np.ix_(removed,te)].min(axis=1)<1500)
    if key[1]=='leave_city_out':
        target={lookup[s]['city'] for s in roles['test']};assert len(target)==1
        assert not target&{lookup[s]['city'] for s in roles['train']}
    else:
        k=key[2].split('_')[-1];assert all(lookup[s]['spatial_fold']==k for s in roles['test'])
for key,rows in inner.items():
    roles={role:{r['site_id'] for r in rows if r['role']==role} for role in ['train','validation','purged']}
    inner_sets[key]=roles
    assert all(not(roles[a]&roles[b]) for a,b in [('train','validation'),('train','purged'),('validation','purged')])
    assert set.union(*roles.values())==outer_sets[key[:3]]['train']
    tr=[index[s] for s in roles['train']];va=[index[s] for s in roles['validation']]
    if tr:assert distance[np.ix_(tr,va)].min()>=1500-1e-6
check(True,'Every outer and inner split is disjoint, excludes test leakage, and satisfies 1,500 m center separation')
check(True,'Every leave-one-city-out model excludes all labels from its held-out city')
for variant in VARIANTS:
    expected={r['site_id'] for r in meta if variant!='exclude_buffalo' or r['city']!='Buffalo'}
    for scheme in ['spatial','leave_city_out']:
        tested=[sid for key,roles in outer_sets.items() if key[:2]==(variant,scheme) for sid in roles['test']]
        assert len(tested)==len(expected) and set(tested)==expected
check(True,'Each eligible site is tested exactly once per variant and evaluation scheme')
fits=read(OUT/'qa/model_fit_audit.csv')
predictions=read(OUT/'data/predictions.csv')
pred_groups=keyed(predictions,['variant','scheme','fold','model'])
preprocess=keyed(read(OUT/'qa/fitted_preprocessing.csv'),['variant','scheme','fold','model'])
search=keyed(read(OUT/'data/inner_search_scores.csv'),['variant','scheme','fold','model'])
calib=keyed(read(OUT/'qa/calibration_training_oof.csv'),['variant','scheme','fold','model'])
for fit in fits:
    key=tuple(fit[k] for k in ['variant','scheme','fold','model']);variant,scheme,fold,model=key
    artifact=OUT/fit['model_artifact'];assert sha(artifact)==fit['model_sha256']
    bundle=joblib.load(artifact);pipe=bundle['pipeline']
    rows=pred_groups[key];assert {r['site_id'] for r in rows}==outer_sets[key[:3]]['test']
    tr=np.array(sorted(index[s] for s in outer_sets[key[:3]]['train']))
    test=np.array([index[r['site_id']] for r in rows])
    x=X.copy()
    if variant=='report_cutoff_background':x[:,0]=[r['log1p_background_report_date_cutoff'] for r in meta]
    columns=[0] if model=='M0' else list(range(x.shape[1]));x=x[:,columns]
    assert bundle['predictors']==[names[j] for j in columns]
    median=[]
    for j in range(x.shape[1]):
        values=x[tr,j];values=values[np.isfinite(values)]
        median.append(float(np.median(values)) if len(values) else 0.)
    np.testing.assert_allclose(pipe.named_steps['imputer'].statistics_,median,rtol=1e-10,atol=1e-10)
    recorded={r['feature']:r for r in preprocess[key]}
    for j,c in enumerate(columns):assert close(recorded[names[c]]['training_median'],median[j])
    if model!='M2':
        imputed=np.where(np.isnan(x[tr]),np.array(median),x[tr])
        expected_scale=imputed.std(axis=0);expected_scale[expected_scale==0]=1
        np.testing.assert_allclose(pipe.named_steps['scaler'].mean_,imputed.mean(axis=0),rtol=1e-8,atol=1e-8)
        np.testing.assert_allclose(pipe.named_steps['scaler'].scale_,expected_scale,rtol=1e-8,atol=1e-8)
    raw=pipe.predict_proba(x[test])[:,1];adjusted=calibrate(raw,bundle['sigmoid'])
    for j,r in enumerate(rows):
        assert int(r['y'])==int(meta[test[j]]['y_'+variant])
        assert close(r['p_raw'],raw[j]) and close(r['p_sigmoid'],adjusted[j])
        assert 0<=float(r['p_raw'])<=1 and 0<=float(r['p_sigmoid'])<=1
    scores={}
    for candidate in range(len(CANDIDATES[model])):
        sr=[r for r in search[key] if int(r['candidate_index'])==candidate]
        fold_scores=[float(r['average_precision']) for r in sr if r['inner_fold']!='MEAN']
        mean=next(r for r in sr if r['inner_fold']=='MEAN')
        assert close(mean['average_precision'],float(np.mean(fold_scores)) if fold_scores else None)
        if fold_scores:scores[candidate]=float(np.mean(fold_scores))
    best=max(scores,key=lambda k:(scores[k],-k)) if scores else 0
    assert int(fit['candidate_index'])==best
    for r in calib[key]:
        assert r['site_id'] in outer_sets[key[:3]]['train']
        assert r['site_id'] not in outer_sets[key[:3]]['test']
check(True,'All fitted medians/scalers reconcile to outer training rows only')
check(True,'Every saved model reproduces its held-out probabilities and uses only the feature allowlist')
check(True,'Selected hyperparameters maximize inner validation AP; calibrators see outer-training OOF rows only')
for row in read(OUT/'data/metrics.csv'):
    selected=[r for r in predictions if r['variant']==row['variant'] and r['scheme']==row['scheme'] and r['model']==row['model'] and (row['city']=='ALL' or r['city']==row['city'])]
    y=np.array([int(r['y']) for r in selected]);p=np.array([float(r['p_'+row['probabilities']]) for r in selected])
    result=metrics(y,p,[r['site_id'] for r in selected])
    assert all(close(row[k],v) for k,v in result.items()),row
check(True,'All AP, ROC-AUC, Brier, calibration and top-decile metrics reconcile to saved predictions')
rep_groups=keyed(read(OUT/'data/paired_bootstrap_replicates.csv'),['scheme','city'])
for row in read(OUT/'data/paired_ap_comparisons.csv'):
    samples=rep_groups[(row['scheme'],row['city'])]
    assert len(samples)==2000
    model=row['comparison'].split('-')[0];column='delta_'+model+'_M0'
    values=np.array([float(r[column]) for r in samples if r[column]!=''])
    for r in samples:
        if r[column]!='':assert close(r[column],float(r['ap_'+model])-float(r['ap_M0']))
    low,high=np.quantile(values,[.025,.975]);assert close(row['ci_low'],low) and close(row['ci_high'],high)
    assert int(row['valid_replicates'])==len(values) and row['confirmatory_go']=='False'
    expected_gate=float(row['ap_difference'])>=.01 and low>0
    assert (row['exploratory_numerical_gate']=='True')==expected_gate
check(True,'All paired intervals use 2,000 spatial-block draws and reconcile to bootstrap replicates')
for row in read(OUT/'qa/input_manifest.csv'):assert sha(ROOT/row['file'])==row['sha256'],row['file']
check(True,'Input/specification/implementation checksums remain unchanged')
status=json.loads((OUT/'qa/phase4_status.json').read_text())
check(status['full_blueprint_phase4_complete'] is False and status['confirmatory_modeling_ready'] is False,
      'Unavailable forward-time validation and pending research gates cannot be reported as completed')
status['validation_status']='PASS';save(OUT/'qa/phase4_status.json',status)
report={'status':'PASS','checks':checks,'model_artifacts_verified':len(fits),'prediction_rows_verified':len(predictions),
        'human_review_completed':False,'forward_temporal_validation_completed':False}
save(OUT/'qa/validation.json',report)
print(json.dumps(report,indent=2))
