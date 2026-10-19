"""Frozen, nested, spatially purged exploratory model comparisons for phase 4."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
os.environ.setdefault('MKL_NUM_THREADS','1')
import argparse
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import warnings
import joblib
import numpy as np
from pyproj import Geod,Transformer
from scipy.optimize import minimize
from scipy.special import expit,logit
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score,roc_auc_score,brier_score_loss
from threadpoolctl import threadpool_limits
from xgboost import XGBClassifier

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/phase4'
P3=ROOT/'results/phase3'
SEED=20261001
PURGE_M=1500.0
CITIES=['New York City','Buffalo','Rochester']
MODELS=['M0','M1','M2']
VARIANTS={
 'primary_50m':('primary_any_50m',False,False),
 'radius_25m':('primary_any_25m',False,False),
 'radius_100m':('primary_any_100m',False,False),
 'nearest_only_50m':('primary_nearest_count_50m',False,False),
 'unfiltered_background':('primary_any_50m',True,False),
 'exclude_buffalo':('primary_any_50m',False,True),
}
CANDIDATES={'M0':[{}],'M1':[{'C':v} for v in [.1,1.,10.]],
 'M2':[{'max_depth':d,'reg_lambda':l} for d,l in [(2,10),(2,1),(3,10),(3,1)]]}

def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def write(path,rows,fields=None):
    rows=list(rows);path.parent.mkdir(parents=True,exist_ok=True)
    fields=fields or list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def idhash(indices,ids):return hashlib.sha256('\n'.join(sorted(ids[i] for i in indices)).encode()).hexdigest()
def safe(v):return float(v) if v!='' else np.nan

def partitions(metadata):
    n=len(metadata);fold=np.zeros(n,dtype=int);blocks=['']*n;xy=np.zeros((n,2))
    for city in CITIES:
        ids=[i for i,r in enumerate(metadata) if r['city']==city]
        t=Transformer.from_crs(4326,32618 if city=='New York City' else 32617,always_xy=True)
        for i in ids:
            xy[i]=t.transform(float(metadata[i]['longitude']),float(metadata[i]['latitude']))
            gx,gy=np.floor(xy[i]/2000).astype(int)
            blocks[i]=f'{city}:{gx}:{gy}'
        unique=sorted({blocks[i] for i in ids})
        centers=[];weights=[]
        for key in unique:
            gx,gy=map(int,key.split(':')[-2:]);centers.append([(gx+.5)*2000,(gy+.5)*2000])
            weights.append(sum(blocks[i]==key for i in ids))
        assert len(unique)>=5
        km=KMeans(n_clusters=5,random_state=SEED,n_init=20).fit(np.array(centers),sample_weight=np.array(weights))
        canonical={old:new for new,old in enumerate(sorted(range(5),key=lambda k:tuple(km.cluster_centers_[k])))}
        assignment={key:canonical[int(label)] for key,label in zip(unique,km.labels_)}
        for i in ids:fold[i]=assignment[blocks[i]]
    geod=Geod(ellps='WGS84')
    lon=np.array([float(r['longitude']) for r in metadata]);lat=np.array([float(r['latitude']) for r in metadata])
    distances=np.zeros((n,n))
    for i in range(n):distances[i]=geod.inv(np.full(n,lon[i]),np.full(n,lat[i]),lon,lat)[2]
    assert np.max(abs(distances-distances.T))<1e-6
    return fold,blocks,xy,distances

def estimator(model,params):
    steps=[('imputer',SimpleImputer(strategy='median',keep_empty_features=True))]
    if model in ['M0','M1']:
        steps += [('scaler',StandardScaler()),('model',LogisticRegression(C=np.inf if model=='M0' else params['C'],
                   solver='lbfgs',max_iter=3000,tol=1e-8))]
    else:
        steps += [('model',XGBClassifier(n_estimators=150,learning_rate=.05,min_child_weight=5,
            subsample=1,colsample_bytree=1,random_state=SEED,n_jobs=1,tree_method='hist',
            objective='binary:logistic',eval_metric='logloss',**params))]
    return Pipeline(steps)

def sigmoid_fit(y,p):
    if len(y)<10 or len(set(y))<2:return {'applied':False,'reason':'insufficient inner OOF data'}
    z=logit(np.clip(p,1e-6,1-1e-6))
    def loss(v):
        linear=v[0]*z+v[1]
        value=np.mean(np.logaddexp(0,linear)-y*linear)+1e-6*v[0]**2
        residual=expit(linear)-y
        return value,np.array([np.mean(residual*z)+2e-6*v[0],np.mean(residual)])
    fit=minimize(loss,[1.,0.],jac=True,method='L-BFGS-B',bounds=[(0,None),(None,None)],options={'maxiter':1000,'ftol':1e-12})
    if not fit.success:return {'applied':False,'reason':str(fit.message)}
    return {'applied':True,'slope':float(fit.x[0]),'intercept':float(fit.x[1]),'n_oof':len(y),'reason':'training-only sigmoid'}
def calibrate(p,params):
    return expit(params['slope']*logit(np.clip(p,1e-6,1-1e-6))+params['intercept']) if params['applied'] else p.copy()

def fit_plan(plan,X,y,names,metadata):
    tr=plan['train'];te=plan['test'];ids=[r['site_id'] for r in metadata]
    tag={k:plan[k] for k in ['variant','scheme','fold']}
    results=[];search=[];preprocessing=[];fits=[];warnings_log=[];calibration_rows=[]
    usable=[]
    for k,fit,val in plan['inner']:
        valid=len(fit)>=10 and len(np.unique(y[fit]))==2 and len(np.unique(y[val]))==2
        if valid:usable.append((k,fit,val))
        else:warnings_log.append(tag|{'model':'ALL','stage':f'inner_{k}','warning':'Skipped inner fold: insufficient training rows or missing outcome class'})
    for model in MODELS:
        columns=[0] if model=='M0' else list(range(X.shape[1]))
        xm=X[:,columns];selected=0;best=-np.inf;best_oof=None
        for candidate_index,params in enumerate(CANDIDATES[model]):
            scores=[];oof=np.full(len(y),np.nan)
            if len(usable)>=2:
                for k,fit,val in usable:
                    e=estimator(model,params)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always');e.fit(xm[fit],y[fit])
                    for w in caught:warnings_log.append(tag|{'model':model,'stage':f'candidate_{candidate_index}_inner_{k}','warning':str(w.message)})
                    pred=e.predict_proba(xm[val])[:,1];oof[val]=pred
                    score=float(average_precision_score(y[val],pred));scores.append(score)
                    search.append(tag|{'model':model,'candidate_index':candidate_index,'params':json.dumps(params,sort_keys=True),
                        'inner_fold':k,'average_precision':score,'train_n':len(fit),'validation_n':len(val),
                        'train_id_hash':idhash(fit,ids),'validation_id_hash':idhash(val,ids)})
            mean=float(np.mean(scores)) if scores else None
            search.append(tag|{'model':model,'candidate_index':candidate_index,'params':json.dumps(params,sort_keys=True),
                'inner_fold':'MEAN','average_precision':mean,'train_n':len(tr),'validation_n':int(np.isfinite(oof).sum()),
                'train_id_hash':idhash(tr,ids),'validation_id_hash':''})
            if mean is not None and mean>best+1e-12:
                best=mean;selected=candidate_index;best_oof=oof
        params=CANDIDATES[model][selected]
        e=estimator(model,params)
        assert len(set(y[tr]))==2,'Outer training cannot fit binary model'
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always');e.fit(xm[tr],y[tr])
        for w in caught:warnings_log.append(tag|{'model':model,'stage':'outer_refit','warning':str(w.message)})
        probabilities=e.predict_proba(xm[te])[:,1]
        valid_idx=np.where(np.isfinite(best_oof))[0] if best_oof is not None else np.array([],dtype=int)
        assert set(valid_idx).issubset(set(tr))
        calibration=sigmoid_fit(y[valid_idx],best_oof[valid_idx]) if len(valid_idx) else {'applied':False,'reason':'fewer than two valid inner folds'}
        for i in valid_idx:calibration_rows.append(tag|{'model':model,'site_id':ids[i],'y':int(y[i]),'p_inner_oof':float(best_oof[i])})
        adjusted=calibrate(probabilities,calibration)
        rel=f"models/{plan['variant']}/{plan['scheme']}_{plan['fold']}_{model}.joblib"
        path=OUT/rel;path.parent.mkdir(parents=True,exist_ok=True)
        joblib.dump({'pipeline':e,'predictors':[names[i] for i in columns],'sigmoid':calibration,'status':'exploratory_fold_model'},path,compress=3)
        model_fit=tag|{'model':model,'candidate_index':selected,'selected_params':json.dumps(params,sort_keys=True),
            'mean_inner_ap':None if best==-np.inf else best,'valid_inner_folds':len(usable),
            'train_n':len(tr),'train_positive':int(y[tr].sum()),'test_n':len(te),
            'train_id_hash':idhash(tr,ids),'test_id_hash':idhash(te,ids),
            'calibration':json.dumps(calibration,sort_keys=True),'model_artifact':rel,'model_sha256':sha(path)}
        fits.append(model_fit)
        for j,column in enumerate(columns):
            preprocessing.append(tag|{'model':model,'feature':names[column],
                'training_median':float(e.named_steps['imputer'].statistics_[j]),
                'all_missing_in_training':bool(np.isnan(xm[tr,j]).all()),
                'scaler_mean':float(e.named_steps['scaler'].mean_[j]) if model!='M2' else None,
                'scaler_scale':float(e.named_steps['scaler'].scale_[j]) if model!='M2' else None})
        for j,i in enumerate(te):
            results.append(tag|{'model':model,'site_id':ids[i],'city':metadata[i]['city'],'block_id':metadata[i]['block_id'],
                'y':int(y[i]),'p_raw':float(probabilities[j]),'p_sigmoid':float(adjusted[j]),'analysis_status':'RETROSPECTIVE_2024_TO_2025'})
    return results,search,preprocessing,fits,warnings_log,calibration_rows

def metrics(y,p,ids):
    n=len(y);pos=int(y.sum());prevalence=pos/n
    order=np.lexsort((np.array(ids),-p));k=math.ceil(n*.1);hits=int(y[order[:k]].sum())
    bins=np.minimum((p*10).astype(int),9)
    ece=sum(np.sum(bins==b)/n*abs(float(p[bins==b].mean())-float(y[bins==b].mean())) for b in range(10) if np.any(bins==b))
    return {'n':n,'positives':pos,'prevalence':prevalence,
        'average_precision':float(average_precision_score(y,p)) if pos else None,
        'roc_auc':float(roc_auc_score(y,p)) if 0<pos<n else None,
        'brier_score':float(brier_score_loss(y,p)), 'ece_10bins':float(ece),
        'calibration_mean_error':float(p.mean()-prevalence),'top_decile_n':k,'top_decile_hits':hits,
        'top_decile_precision':hits/k,'top_decile_recall':hits/pos if pos else None,
        'top_decile_lift':hits/k/prevalence if pos else None}

def evaluate(predictions):
    output=[];calibration=[]
    for variant in VARIANTS:
        for scheme in ['forward_spatial','forward_leave_city_out']:
            for city in ['ALL']+CITIES:
                for model in MODELS:
                    rows=[r for r in predictions if r['variant']==variant and r['scheme']==scheme and r['model']==model and (city=='ALL' or r['city']==city)]
                    if not rows:continue
                    ids=[r['site_id'] for r in rows];assert len(ids)==len(set(ids))
                    y=np.array([r['y'] for r in rows]);tag={'variant':variant,'scheme':scheme,'city':city,'model':model}
                    for kind in ['raw','sigmoid']:
                        p=np.array([r['p_'+kind] for r in rows])
                        output.append(tag|{'probabilities':kind}|metrics(y,p,ids))
                        bins=np.minimum((p*10).astype(int),9)
                        for b in range(10):
                            mask=bins==b;n=int(mask.sum())
                            if not n:continue
                            rate=float(y[mask].mean());z=1.959963984540054
                            center=(rate+z*z/(2*n))/(1+z*z/n)
                            half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
                            calibration.append(tag|{'probabilities':kind,'bin':b,'n':n,'mean_probability':float(p[mask].mean()),
                                'observed_rate':rate,'wilson_low':center-half,'wilson_high':center+half})
    write(OUT/'data/metrics.csv',output)
    write(OUT/'data/calibration_bins.csv',calibration)

def weighted_ap_setup(y,p):
    order=np.argsort(-p,kind='stable');ys=y[order]
    ends=np.r_[np.where(np.diff(p[order])!=0)[0],len(p)-1]
    def ap(weights):
        w=np.asarray(weights,dtype=float)[order];positive=np.cumsum(w*ys)[ends];total=np.cumsum(w)[ends]
        if positive[-1]<=0:return np.nan
        increments=np.diff(np.r_[0,positive]);precision=np.divide(positive,total,out=np.zeros_like(positive),where=total>0)
        return float(np.sum(increments*precision)/positive[-1])
    return ap

def bootstrap(predictions):
    summaries=[];replicates=[]
    for scheme in ['forward_spatial','forward_leave_city_out']:
        for city in ['ALL']+CITIES:
            subset=[r for r in predictions if r['variant']=='primary_50m' and r['scheme']==scheme and (city=='ALL' or r['city']==city)]
            base=sorted([r for r in subset if r['model']=='M0'],key=lambda r:r['site_id'])
            ids=[r['site_id'] for r in base];y=np.array([r['y'] for r in base],dtype=float)
            probabilities={m:np.array([r['p_raw'] for r in sorted([r for r in subset if r['model']==m],key=lambda r:r['site_id'])]) for m in MODELS}
            funcs={m:weighted_ap_setup(y,p) for m,p in probabilities.items()}
            groups=sorted({r['block_id'] for r in base});index={g:i for i,g in enumerate(groups)}
            row_group=np.array([index[r['block_id']] for r in base]);group_city={index[r['block_id']]:r['city'] for r in base}
            strata=[np.array([i for i,c in group_city.items() if c==name],dtype=int) for name in sorted(set(group_city.values()))]
            rng=np.random.default_rng(SEED);values={m:[] for m in ['M1','M2']}
            for b in range(2000):
                multiplicity=np.zeros(len(groups))
                for group_indices in strata:
                    draws=rng.choice(group_indices,size=len(group_indices),replace=True)
                    multiplicity+=np.bincount(draws,minlength=len(groups))
                weights=multiplicity[row_group];aps={m:funcs[m](weights) for m in MODELS}
                row={'scheme':scheme,'city':city,'replicate':b,'resampled_sites':int(weights.sum()),'resampled_positive':int(np.dot(weights,y))}
                for m in MODELS:row['ap_'+m]=float(aps[m]) if np.isfinite(aps[m]) else None
                for m in ['M1','M2']:
                    delta=aps[m]-aps['M0'];row['delta_'+m+'_M0']=float(delta) if np.isfinite(delta) else None
                    if np.isfinite(delta):values[m].append(float(delta))
                replicates.append(row)
            for m in ['M1','M2']:
                v=np.array(values[m]);point=funcs[m](np.ones(len(y)))-funcs['M0'](np.ones(len(y)))
                low,high=np.quantile(v,[.025,.975]) if len(v) else [None,None]
                summaries.append({'scheme':scheme,'city':city,'comparison':m+'-M0','n':len(y),'spatial_blocks':len(groups),
                    'ap_difference':point,'ci_low':float(low) if low is not None else None,'ci_high':float(high) if high is not None else None,
                    'bootstrap_replicates':2000,'valid_replicates':len(v),'exploratory_numerical_gate':bool(point>=.01 and low is not None and low>0),
                    'confirmatory_go':False,'uncertainty_scope':'conditional on fitted OOF predictions; no model refits'})
    write(OUT/'data/paired_bootstrap_replicates.csv',replicates)
    write(OUT/'data/paired_ap_comparisons.csv',summaries)

