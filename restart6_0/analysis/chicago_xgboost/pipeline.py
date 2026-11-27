"""Auditable Chicago-only retrospective XGBoost analysis; see analysis_plan.md."""
from __future__ import annotations
import argparse
import hashlib
import html
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
import warnings

PROJECT = Path(__file__).resolve().parents[3]
ROOT = PROJECT / 'restart6_0'
HERE = Path(__file__).resolve().parent
DEFAULT_OUT = ROOT / 'results/chicago_xgboost'
os.environ.setdefault('MPLCONFIGDIR', str(PROJECT / '.mplconfig-chicago'))
os.environ.setdefault('XDG_CACHE_HOME', str(PROJECT / '.mplconfig-chicago'))
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cdist
from pyproj import Transformer
import xgboost as xgb
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (average_precision_score, roc_auc_score, brier_score_loss,
    log_loss, confusion_matrix, matthews_corrcoef, roc_curve, precision_recall_curve)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CRIME = ['background_unfiltered', 'prior_crime_25m_unfiltered',
         'prior_crime_50m_unfiltered', 'prior_crime_100m_unfiltered',
         'prior_robbery_50m_unfiltered', 'prior_burglary_50m_unfiltered',
         'prior_recent_crime_50m_unfiltered']
UNAVAILABLE = ['background_primary', 'prior_crime_25m', 'prior_crime_50m',
               'prior_crime_100m', 'prior_robbery_50m', 'prior_burglary_50m', 'prior_recent_crime_50m']
GRID = [dict(max_depth=d, n_estimators=n, min_child_weight=w, reg_lambda=r)
        for d, n, w, r in [(2,80,5,5),(2,180,10,10),(3,80,5,10),(3,180,10,20),
                            (2,300,10,20),(3,300,15,30),(4,120,10,20),(4,240,20,30)]]
ASSOCIATION_TARGETS = ['primary_any_50m','primary_count_50m','robbery_count_50m',
                       'burglary_count_50m','primary_any_25m','primary_any_100m']

def digest(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def dump(p, obj):
    def clean(x):
        if isinstance(x, dict): return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x, (list,tuple)): return [clean(v) for v in x]
        if isinstance(x, np.ndarray): return clean(x.tolist())
        if isinstance(x, np.generic): return clean(x.item())
        if isinstance(x, float) and not np.isfinite(x): return None
        if isinstance(x, Path): return str(x)
        return x
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(clean(obj), indent=2, allow_nan=False)+'\n')

def csv(p, records):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    frame = records if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    frame.to_csv(p, index=False)

def sources():
    return [ROOT/'data/processed/atm_panel_full_year_2024_2025.csv',
        ROOT/'results/phase3/data/site_context_raw.csv',
        ROOT/'results/phase3_environment_expanded/environment_full_year_2024_2025.csv',
        ROOT/'results/phase3_environment_expanded/environment_dictionary.csv',
        ROOT/'results/phase3_environment_expanded/schema.json']

def verify_sources():
    expected = {}
    for manifest, base in [(ROOT/'reports/artifact_manifest.csv', ROOT),
        (ROOT/'results/phase3/qa/output_manifest.csv', PROJECT),
        (ROOT/'results/phase3_environment_expanded/output_manifest.csv', PROJECT)]:
        for r in pd.read_csv(manifest).to_dict('records'):
            expected[(base/r['file']).resolve()] = r['sha256']
    rows=[]
    for p in sources():
        got=digest(p); assert got == expected[p.resolve()], f'Frozen input changed: {p}'
        rows.append({'file':str(p.relative_to(PROJECT)), 'bytes':p.stat().st_size, 'sha256':got})
    return rows

def load_data(city='Chicago'):
    schema=json.loads(sources()[4].read_text()); env=schema['exploratory_predictors']
    e=pd.read_csv(sources()[2], dtype={'acs_geoid_2022':str,'sld_geoid_2019':str})
    p=pd.read_csv(sources()[0]); c=pd.read_csv(sources()[1])
    for frame in (e,p,c): assert frame.row_id.is_unique
    e=e[e.city.eq(city)].copy()
    cols=['row_id','site_id','city','outcome_year','longitude','latitude',
          'acs_geoid_2022','sld_geoid_2019']+env
    outcomes=[f'primary_{k}_{r}m' for r in (25,50,100) for k in ('any','count')]
    pcols=outcomes+['robbery_count_50m','burglary_count_50m',
                   'osm_geometry_is_centroid','boundary_buffer_clear_500m']
    d=e[cols].merge(c[['row_id']+CRIME+UNAVAILABLE], on='row_id',validate='one_to_one')
    d=d.merge(p[['row_id']+pcols], on='row_id',validate='one_to_one')
    assert len(d)==len(e) and set(d.outcome_year)=={2024,2025}
    if city=='Chicago':
        assert len(d)==925 and d[UNAVAILABLE].isna().all().all()
    assert not np.isinf(d[env+CRIME].to_numpy(dtype=float)).any()
    for r in (25,50,100): assert (d[f'primary_any_{r}m']==(d[f'primary_count_{r}m']>0)).all()
    epsg={'Chicago':32616,'New York City':32618,'Los Angeles':32611}[city]
    x,y=Transformer.from_crs(4326,epsg,always_xy=True).transform(d.longitude,d.latitude)
    d['x_m']=x; d['y_m']=y
    d['spatial_block']=blocks(d,2000)
    d=d.sort_values(['outcome_year','row_id']).reset_index(drop=True)
    dictionary=pd.read_csv(sources()[3]).set_index('column').to_dict('index')
    descriptions=['Prior-year crime in >200–500 m ring','Prior-year crime within 25 m',
        'Prior-year crime within 50 m','Prior-year crime within 100 m',
        'Prior-year robbery within 50 m','Prior-year burglary within 50 m',
        'Prior-year July–December crime within 50 m']
    for f,desc in zip(CRIME,descriptions):
        dictionary[f]={'description':desc+' (retrospective; report date unavailable)',
            'source':'prior-year occurrence records, latest extract', 'units':'incidents',
            'spatial_support':'site radius/ring','available_at':'historical reporting availability unknown'}
    return d,env,dictionary

def blocks(d,size):
    return (np.floor(d.x_m/size).astype(int).astype(str)+'_'+
            np.floor(d.y_m/size).astype(int).astype(str)).to_numpy()

def training_columns(frame, candidates):
    """Learn exclusions from this training subset only, never evaluation rows."""
    kept=[]; reasons={}
    for f in candidates:
        if frame[f].notna().sum()==0: reasons[f]='all_missing_in_training'
        elif frame[f].nunique(dropna=True)<=1: reasons[f]='constant_observed_values_in_training'
        else:
            dup=next((k for k in kept if frame[f].equals(frame[k])),None)
            if dup: reasons[f]='exact_training_duplicate_of:'+dup
            else: kept.append(f)
    return kept,reasons

def spatial_folds(train, y, seed=17):
    splitter=StratifiedGroupKFold(n_splits=4,shuffle=True,random_state=seed)
    xy=train[['x_m','y_m']].to_numpy(); groups=train.spatial_block.to_numpy()
    result=[]; audit=[]
    for fold,(a,b) in enumerate(splitter.split(xy,y,groups)):
        near=cdist(xy[a],xy[b]).min(axis=1)<1000
        shared=np.zeros(len(a),dtype=bool)
        for field in ['acs_geoid_2022','sld_geoid_2019']:
            shared |= train.iloc[a][field].isin(train.iloc[b][field].dropna()).to_numpy()
        retained=a[~(near|shared)]
        assert len(np.unique(y[retained]))==2 and len(np.unique(y[b]))==2
        assert not set(groups[retained]) & set(groups[b])
        minimum=float(cdist(xy[retained],xy[b]).min()); assert minimum>=1000
        result.append((retained,b))
        audit.append({'fold':fold,'training_before_purge':len(a),'training_after_purge':len(retained),
            'validation_rows':len(b),'purged_rows':len(a)-len(retained),
            'minimum_train_validation_distance_m':minimum,'train_positive':int(y[retained].sum()),
            'validation_positive':int(y[b].sum())})
    return result,audit

def estimator(params,seed,threads):
    return xgb.XGBClassifier(**params, learning_rate=.04, subsample=.85,colsample_bytree=.85,
        reg_alpha=.1, objective='binary:logistic',eval_metric='logloss', tree_method='hist',
        random_state=seed,n_jobs=threads,verbosity=0)

def metric_values(y,p,threshold=.5):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=float); hard=p>=threshold
    tn,fp,fn,tp=confusion_matrix(y,hard,labels=[0,1]).ravel()
    div=lambda a,b: float(a/b) if b else float('nan')
    k=max(1,math.ceil(len(y)*.1)); top=np.argsort(-p,kind='stable')[:k]
    # Fractional allocation at the boundary avoids row-order effects for tied scores.
    cut=np.sort(p)[-k]; above=p>cut; tied=p==cut
    top_positive=float(y[above].sum())+(k-int(above.sum()))*float(y[tied].mean())
    two=len(np.unique(y))==2
    return {'n':len(y),'positive':int(y.sum()),'prevalence':float(y.mean()),
        'average_precision':float(average_precision_score(y,p)) if y.sum() else float('nan'),
        'roc_auc':float(roc_auc_score(y,p)) if two else float('nan'),
        'brier':float(brier_score_loss(y,p)), 'log_loss':float(log_loss(y,np.clip(p,1e-9,1-1e-9),labels=[0,1])),
        'accuracy':div(tp+tn,len(y)),'balanced_accuracy':(div(tp,tp+fn)+div(tn,tn+fp))/2,
        'precision':div(tp,tp+fp),'recall':div(tp,tp+fn),'specificity':div(tn,tn+fp),
        'negative_predictive_value':div(tn,tn+fn),'f1':div(2*tp,2*tp+fp+fn),
        'mcc':float(matthews_corrcoef(y,hard)) if two else float('nan'),
        'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp),
        'top10_precision':top_positive/k,'top10_recall':div(top_positive,y.sum()),
        'top10_lift':div(top_positive/k,y.mean()),'threshold':float(threshold)}

def cluster_weights(groups,n_boot,seed):
    _,inv=np.unique(np.asarray(groups),return_inverse=True); g=inv.max()+1
    rng=np.random.default_rng(seed)
    counts=rng.multinomial(g,np.full(g,1/g),size=n_boot)
    return counts[:,inv].astype(float)

def weighted_rank(v,w):
    """Midranks of expanded bootstrap samples, represented by multiplicity weights."""
    order=np.argsort(v,kind='stable'); vals=v[order]; sw=w[:,order]
    starts=np.r_[0,np.flatnonzero(vals[1:]!=vals[:-1])+1]
    totals=np.add.reduceat(sw,starts,axis=1); end=np.cumsum(totals,axis=1)
    mid=end-totals/2+.5
    ranks=np.repeat(mid,np.diff(np.r_[starts,len(v)]),axis=1)
    out=np.empty_like(w); out[:,order]=ranks
    return out

def weighted_corr(a,b,w):
    with np.errstate(divide='ignore',invalid='ignore'):
        mass=w.sum(axis=1);am=(w*a).sum(axis=1)/mass;bm=(w*b).sum(axis=1)/mass
        ac=a-am[:,None];bc=b-bm[:,None]
        denom=np.sqrt((w*ac*ac).sum(axis=1)*(w*bc*bc).sum(axis=1))
        r=(w*ac*bc).sum(axis=1)/denom
        r[(mass<3)|(denom==0)]=np.nan
    return r

def spearman_boot(x,y,weights):
    mask=np.isfinite(x)&np.isfinite(y)
    if mask.sum()<3 or len(np.unique(x[mask]))<2: return np.full(len(weights),np.nan)
    w=weights[:,mask];a=x[mask];b=y[mask]
    return weighted_corr(weighted_rank(a,w),weighted_rank(b,w),w)

def interval(values):
    good=np.asarray(values,dtype=float);good=good[np.isfinite(good)]
    if not len(good): return np.nan,np.nan,0
    lo,hi=np.quantile(good,[.025,.975]);return float(lo),float(hi),len(good)

def bh(values):
    p=np.asarray(values,dtype=float);out=np.full(len(p),np.nan);ids=np.flatnonzero(np.isfinite(p))
    order=ids[np.argsort(p[ids])]; m=len(order)
    if m:out[order]=np.minimum(1,np.minimum.accumulate((p[order]*m/np.arange(1,m+1))[::-1])[::-1])
    return out

def cluster_rank_p(x,y,g):
    mask=np.isfinite(x)&np.isfinite(y); x=x[mask];y=y[mask];g=np.asarray(g)[mask]
    if len(x)<4 or len(np.unique(x))<2 or len(np.unique(y))<2:return np.nan
    a=stats.rankdata(x);b=stats.rankdata(y);a-=a.mean();b-=b.mean();sxx=np.dot(a,a)
    beta=np.dot(a,b)/sxx;res=b-beta*a
    _,idx=np.unique(g,return_inverse=True);G=idx.max()+1
    if G<3:return np.nan
    score=np.bincount(idx,weights=a*res)
    variance=G/(G-1)*(len(x)-1)/(len(x)-2)*np.dot(score,score)/sxx**2
    if variance<=0:return np.nan
    return float(2*stats.t.sf(abs(beta)/math.sqrt(variance),df=G-1))

def associations(d,features,dictionary,out,n_boot):
    summary=[];assocs=[];pairrows=[];bins=[];rankboot=[]
    for year,part in d.groupby('outcome_year'):
        part=part.reset_index(drop=True); w=cluster_weights(part.spatial_block,n_boot,1700+int(year))
        primary_boot=[]
        for f in features:
            x=part[f].to_numpy(dtype=float);obs=x[np.isfinite(x)];y=part.primary_any_50m.to_numpy()
            row={'year':year,'parameter':f,**{k:dictionary[f].get(k,'') for k in ('description','source','units','spatial_support')},
                'rows':len(part),'observed':len(obs),'missing':len(part)-len(obs),
                'missing_pct':100*(len(part)-len(obs))/len(part),'unique_observed':len(np.unique(obs)),
                'zeros':int((obs==0).sum()),'status':'available' if len(np.unique(obs))>1 else 'constant' if len(obs) else 'all_missing'}
            if len(obs):
                row.update(mean=float(obs.mean()),std=float(obs.std(ddof=1)) if len(obs)>1 else np.nan,
                    skew=float(stats.skew(obs)) if len(np.unique(obs))>1 else np.nan,
                    excess_kurtosis=float(stats.kurtosis(obs)) if len(np.unique(obs))>1 else np.nan)
                for name,q in [('min',0),('p01',.01),('p05',.05),('p25',.25),('median',.5),('p75',.75),('p95',.95),('p99',.99),('max',1)]:row[name]=float(np.quantile(obs,q))
                row['iqr']=row['p75']-row['p25']
            for cls in (0,1):
                v=x[(y==cls)&np.isfinite(x)];row[f'class{cls}_observed']=len(v)
                row[f'class{cls}_mean']=float(v.mean()) if len(v) else np.nan
                row[f'class{cls}_median']=float(np.median(v)) if len(v) else np.nan
                row[f'class{cls}_std']=float(v.std(ddof=1)) if len(v)>1 else np.nan
                row[f'class{cls}_missing_pct']=100*float(np.isnan(x[y==cls]).mean())
            a=x[(y==1)&np.isfinite(x)];b=x[(y==0)&np.isfinite(x)]
            if len(a)>1 and len(b)>1:
                pooled=np.sqrt(((len(a)-1)*a.var(ddof=1)+(len(b)-1)*b.var(ddof=1))/(len(a)+len(b)-2))
                row['cohens_d_positive_minus_negative']=(a.mean()-b.mean())/pooled if pooled else np.nan
            summary.append(row)
            for target in ASSOCIATION_TARGETS:
                z=part[target].to_numpy(dtype=float);mask=np.isfinite(x)&np.isfinite(z)
                r={'year':year,'parameter':f,'outcome':target,'n_complete':int(mask.sum()),
                   'clusters_complete':part.loc[mask,'spatial_block'].nunique(),'status':row['status']}
                boot=spearman_boot(x,z,w)
                if target=='primary_any_50m':primary_boot.append(boot)
                if row['status']=='available' and len(np.unique(z[mask]))>1:
                    sp=stats.spearmanr(x[mask],z[mask]);pe=stats.pearsonr(x[mask],z[mask]);ke=stats.kendalltau(x[mask],z[mask])
                    lo,hi,valid=interval(boot)
                    r.update(spearman_rho=float(sp.statistic),spearman_p_iid=float(sp.pvalue),
                        pearson_r=float(pe.statistic),pearson_p_iid=float(pe.pvalue),kendall_tau=float(ke.statistic),
                        spearman_ci_low=lo,spearman_ci_high=hi,bootstrap_valid=valid,
                        cluster_rank_p=cluster_rank_p(x,z,part.spatial_block))
                assocs.append(r)
            if len(np.unique(obs))>1:
                # Bin boundaries learned from 2024 only; reused unchanged in 2025.
                tr=d.loc[d.outcome_year.eq(2024),f].dropna()
                edges=np.unique(tr.quantile([0,.25,.5,.75,1]).to_numpy())
                if len(edges)>1:
                    edges[0]=-np.inf;edges[-1]=np.inf
                    cats=pd.cut(part[f],edges,include_lowest=True)
                    for label in cats.cat.categories:
                        m=(cats==label).to_numpy(); yy=y[m];rate=yy.mean() if len(yy) else np.nan
                        means=np.divide(w[:,m]@yy,w[:,m].sum(axis=1),out=np.full(len(w),np.nan),where=w[:,m].sum(axis=1)>0)
                        lo,hi,valid=interval(means)
                        bins.append({'year':year,'parameter':f,'bin':str(label),'n':int(m.sum()),'positive':int(yy.sum()),
                            'event_rate':rate,'rate_ci_low':lo,'rate_ci_high':hi,'bootstrap_valid':valid,'bin_edges_from':2024})
            m=part[f].isna().to_numpy()
            if m.any(): bins.append({'year':year,'parameter':f,'bin':'MISSING','n':int(m.sum()),'positive':int(y[m].sum()),'event_rate':float(y[m].mean()),'bin_edges_from':2024})
        # Uncertainty in the primary correlation ranking, with excluded features unranked.
        arr=np.array(primary_boot).T; rank=stats.rankdata(-np.abs(arr),axis=1,method='average',nan_policy='omit')
        for j,f in enumerate(features):
            lo,hi,valid=interval(rank[:,j]);finite=np.isfinite(rank[:,j])
            rankboot.append({'year':year,'parameter':f,'bootstrap_rank_median':float(np.nanmedian(rank[:,j])) if finite.any() else np.nan,
                'bootstrap_rank_low':lo,'bootstrap_rank_high':hi,'bootstrap_top10_fraction':float(np.mean(rank[finite,j]<=10)) if finite.any() else np.nan})
        corr=part[features].corr(method='spearman',min_periods=10)
        csv(out/f'statistics/parameter_correlation_matrix_{year}.csv',corr.reset_index(names='parameter'))
        for i,f in enumerate(features):
            for j in range(i+1,len(features)):
                pairrows.append({'year':year,'parameter_a':f,'parameter_b':features[j],
                    'spearman_rho':corr.iloc[i,j],'n_complete':int(part[[f,features[j]]].notna().all(axis=1).sum())})
        print(f'Parameter statistics complete: {year}',flush=True)
    s=pd.DataFrame(summary);a=pd.DataFrame(assocs)
    a['cluster_bh_q']=np.nan;a['iid_bh_q']=np.nan
    for _,ids in a.groupby(['year','outcome']).groups.items():
        a.loc[ids,'cluster_bh_q']=bh(a.loc[ids,'cluster_rank_p']);a.loc[ids,'iid_bh_q']=bh(a.loc[ids,'spearman_p_iid'])
    a['absolute_rho']=a.spearman_rho.abs()
    a['correlation_rank']=a.groupby(['year','outcome']).absolute_rho.rank(ascending=False,method='min')
    csv(out/'statistics/distributions_all_parameters.csv',s)
    csv(out/'statistics/associations_all_outcomes.csv',a)
    csv(out/'statistics/parameter_pairs.csv',pd.DataFrame(pairrows).sort_values(['year','spearman_rho']))
    csv(out/'statistics/outcome_rates_by_training_quartile.csv',bins)
    ranks=a[a.outcome.eq('primary_any_50m')].merge(pd.DataFrame(rankboot),on=['year','parameter'])
    ranks=ranks.merge(s[['year','parameter','description','units','missing_pct']],on=['year','parameter'])
    csv(out/'statistics/correlation_rankings.csv',ranks.sort_values(['year','correlation_rank']))
    return s,a,ranks

def tune(train,features,y,folds,threads):
    rows=[]; oofs=[]; exclusions=[]
    fold_features=[]
    for i,(a,b) in enumerate(folds):
        keep,drop=training_columns(train.iloc[a],features); assert keep
        fold_features.append(keep)
        for f in features:exclusions.append({'fold':i,'parameter':f,'included':f in keep,'reason':drop.get(f,'included')})
    for k,params in enumerate(GRID):
        pred=np.full(len(train),np.nan)
        for i,(a,b) in enumerate(folds):
            keep=fold_features[i];model=estimator(params,17,threads)
            model.fit(train.iloc[a][keep],y[a]);p=model.predict_proba(train.iloc[b][keep])[:,1];pred[b]=p
            rows.append({'candidate':k,'fold':i,**params,**metric_values(y[b],p)})
        assert np.isfinite(pred).all();oofs.append(pred)
    table=pd.DataFrame(rows);score=table.groupby('candidate').average_precision.mean()
    best=int(score.idxmax());oof=oofs[best]
    candidates=np.linspace(.05,.95,181)
    f1s=np.array([metric_values(y,oof,t)['f1'] for t in candidates])
    threshold=float(candidates[np.nanargmax(f1s)])
    return GRID[best],threshold,table,pd.DataFrame(exclusions),oof

def calibration(y,p):
    rows=[]
    for i in range(10):
        mask=(p>=i/10)&((p<(i+1)/10) if i<9 else (p<=1))
        rows.append({'bin_left':i/10,'bin_right':(i+1)/10,'n':int(mask.sum()),
            'mean_probability':float(p[mask].mean()) if mask.any() else np.nan,
            'observed_fraction':float(y[mask].mean()) if mask.any() else np.nan})
    return rows

def uncertainty(test,predictions,out,n_boot,seed=801):
    records=[];diffs=[];bootstrap=[]
    for size in (1000,2000,4000):
        w=cluster_weights(blocks(test,size),n_boot,seed+size)
        allvals={}
        for (radius,family),p in predictions.items():
            y=test[f'primary_any_{radius}m'].to_numpy(dtype=int)
            keys=['average_precision','roc_auc','brier','log_loss','accuracy','balanced_accuracy',
                  'precision','recall','specificity','negative_predictive_value','f1','mcc',
                  'top10_precision','top10_recall','top10_lift']
            vals=[]
            for row in w:
                ids=np.repeat(np.arange(len(test)),row.astype(int))
                vals.append(metric_values(y[ids],p[ids]))
            array=pd.DataFrame(vals);allvals[(radius,family)]=array
            point=metric_values(y,p)
            for key in keys:
                lo,hi,n=interval(array[key]);records.append({'radius_m':radius,'model':family,'block_size_m':size,
                    'metric':key,'estimate':point[key],'ci_low':lo,'ci_high':hi,'valid_replicates':n,'replicates_requested':n_boot})
            if size==2000:
                for b,row in enumerate(vals):bootstrap.append({'radius_m':radius,'model':family,'replicate':b,**row})
        for radius in (50,25,100):
            for ref in ('crime_only','environment_only','prevalence_baseline'):
                a=allvals[(radius,'crime_plus_environment')];b=allvals[(radius,ref)]
                for metric in ('average_precision','roc_auc','brier','log_loss'):
                    delta=a[metric]-b[metric];lo,hi,n=interval(delta)
                    point=metric_values(test[f'primary_any_{radius}m'],predictions[(radius,'crime_plus_environment')])[metric]-metric_values(test[f'primary_any_{radius}m'],predictions[(radius,ref)])[metric]
                    diffs.append({'radius_m':radius,'comparison':'crime_plus_environment minus '+ref,'metric':metric,
                        'block_size_m':size,'difference':point,'ci_low':lo,'ci_high':hi,'valid_replicates':n,
                        'better_direction':'negative' if metric in ('brier','log_loss') else 'positive'})
        print(f'Metric bootstrap complete: {size} m blocks',flush=True)
    csv(out/'statistics/model_metric_intervals.csv',records);csv(out/'statistics/paired_model_differences.csv',diffs)
    csv(out/'statistics/model_bootstrap_replicates.csv',bootstrap)
    return pd.DataFrame(records),pd.DataFrame(diffs)

def explain(model,train,test,candidates,kept,reasons,out,n_boot,family,threads):
    booster=model.get_booster(); matrix=xgb.DMatrix(test[kept],feature_names=kept)
    contrib=booster.predict(matrix,pred_contribs=True,approx_contribs=False)
    margin=booster.predict(matrix,output_margin=True)
    error=float(np.max(np.abs(contrib.sum(axis=1)-margin)))
    assert error<1e-4, f'TreeSHAP additivity failed: {error}'
    full=np.zeros((len(test),len(candidates)))
    for j,f in enumerate(kept):full[:,candidates.index(f)]=contrib[:,j]
    values=pd.DataFrame(full,columns=candidates);values.insert(0,'row_id',test.row_id.to_numpy())
    values['bias_log_odds']=contrib[:,-1];values['prediction_margin']=margin
    csv(out/f'explanations/{family}_shap_values_2025.csv',values)
    weights=cluster_weights(test.spatial_block,n_boot,1931)
    means=weights@np.abs(full)/weights.sum(axis=1)[:,None]
    ranks=stats.rankdata(-means,axis=1,method='average')
    gain=booster.get_score(importance_type='gain');total_gain=booster.get_score(importance_type='total_gain')
    splits=booster.get_score(importance_type='weight');cover=booster.get_score(importance_type='cover')
    records=[]
    point=np.abs(full).mean(axis=0);total=point.sum()
    for j,f in enumerate(candidates):
        lo,hi,valid=interval(means[:,j]);rl,rh,_=interval(ranks[:,j])
        obs=np.isfinite(test[f].to_numpy(dtype=float));direction=np.nan
        if obs.sum()>2 and test.loc[obs,f].nunique()>1 and np.unique(full[obs,j]).size>1:
            direction=float(stats.spearmanr(test.loc[obs,f],full[obs,j]).statistic)
        records.append({'model':family,'parameter':f,'model_status':reasons.get(f,'included'),
            'mean_abs_shap':point[j],'share_total_abs_shap':point[j]/total if total else 0,
            'mean_signed_shap':full[:,j].mean(),'shap_std':full[:,j].std(ddof=1),
            'shap_p05':np.quantile(full[:,j],.05),'shap_median':np.median(full[:,j]),
            'shap_p95':np.quantile(full[:,j],.95),'shap_positive_fraction':np.mean(full[:,j]>0),
            'shap_ci_low':lo,'shap_ci_high':hi,'bootstrap_valid':valid,
            'shap_rank_low':rl if f in kept else np.nan,'shap_rank_high':rh if f in kept else np.nan,
            'bootstrap_top10_fraction':np.mean(ranks[:,j]<=10) if f in kept else 0,
            'value_vs_shap_spearman':direction,'gain':gain.get(f,0),'total_gain':total_gain.get(f,0),
            'split_count':splits.get(f,0),'cover':cover.get(f,0)})
    result=pd.DataFrame(records)
    result['shap_rank']=result.mean_abs_shap.rank(ascending=False,method='min')
    result.loc[~result.parameter.isin(kept),'shap_rank']=np.nan
    csv(out/f'explanations/{family}_shap_ranking.csv',result.sort_values('shap_rank'))
    # Permutation-repeat variability is explicitly separate from sampling uncertainty.
    y=test.primary_any_50m.to_numpy(dtype=int);baseline=average_precision_score(y,model.predict_proba(test[kept])[:,1])
    rng=np.random.default_rng(541);perms=[];summary=[]
    for f in candidates:
        drops=[]
        if f in kept:
            for repeat in range(20):
                altered=test[kept].copy();altered[f]=altered[f].to_numpy()[rng.permutation(len(test))]
                value=float(baseline-average_precision_score(y,model.predict_proba(altered)[:,1]));drops.append(value)
                perms.append({'parameter':f,'repeat':repeat,'average_precision_drop':value})
        else:drops=[0.]*20
        summary.append({'parameter':f,'permutation_mean_ap_drop':np.mean(drops),'permutation_sd':np.std(drops,ddof=1),
            'permutation_repeat_p025':np.quantile(drops,.025),'permutation_repeat_p975':np.quantile(drops,.975),
            'model_status':reasons.get(f,'included'),'repeats':20})
    ps=pd.DataFrame(summary);ps['permutation_rank']=ps.permutation_mean_ap_drop.rank(ascending=False,method='min')
    ps.loc[~ps.parameter.isin(kept),'permutation_rank']=np.nan
    csv(out/f'explanations/{family}_permutation_ranking.csv',ps.sort_values('permutation_rank'))
    csv(out/f'explanations/{family}_permutation_repeats.csv',perms)
    return result,ps,full,error

def save_figure(fig,out,name):
    fig.savefig(out/'figures'/f'{name}.png',dpi=145,bbox_inches='tight')
    fig.savefig(out/'figures'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def figures(train,test,features,env,dictionary,predictions,shap,ranks,out,parameter_plots=True):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    y=test.primary_any_50m.to_numpy(dtype=int)
    fig,axes=plt.subplots(1,3,figsize=(15,4))
    for family in ['crime_only','environment_only','crime_plus_environment','prevalence_baseline']:
        p=predictions[(50,family)];label=family.replace('_',' ')
        fpr,tpr,_=roc_curve(y,p);axes[0].plot(fpr,tpr,label=label)
        prec,rec,_=precision_recall_curve(y,p);axes[1].step(rec,prec,where='post',label=label)
        c=pd.DataFrame(calibration(y,p)).dropna();axes[2].plot(c.mean_probability,c.observed_fraction,'o-',label=label)
    axes[0].plot([0,1],[0,1],'k--',alpha=.3);axes[2].plot([0,1],[0,1],'k--',alpha=.3)
    axes[1].axhline(y.mean(),ls='--',color='grey',alpha=.5)
    for a,title,xlab,ylab in zip(axes,['ROC','Precision–recall','Calibration'],
        ['False-positive rate','Recall','Predicted probability'],['True-positive rate','Precision','Observed event rate']):
        a.set(title=title,xlabel=xlab,ylabel=ylab,xlim=(0,1),ylim=(0,1));a.legend(fontsize=7)
    fig.suptitle('Chicago 2025 evaluation · any nearby robbery/burglary within 50 m')
    fig.tight_layout();save_figure(fig,out,'model_performance_50m')
    r=ranks[ranks.year.eq(2025)].sort_values('correlation_rank').head(20).iloc[::-1]
    fig,ax=plt.subplots(figsize=(10,8));ax.barh(r.parameter,r.spearman_rho,color=np.where(r.spearman_rho>0,'#287b8e','#bf6b45'))
    ax.errorbar(r.spearman_rho,np.arange(len(r)),
        xerr=np.vstack([np.maximum(0,r.spearman_rho-r.spearman_ci_low),np.maximum(0,r.spearman_ci_high-r.spearman_rho)]),fmt='none',color='black',lw=.7)
    ax.set(xlabel='Spearman association with crime indicator; 95% spatial-bootstrap intervals',title='Association ranking · Chicago 2025 · descriptive, not causal')
    fig.tight_layout();save_figure(fig,out,'correlation_top20')
    score=np.abs(shap).mean(axis=0);idx=np.argsort(score)[-20:]
    fig,ax=plt.subplots(figsize=(10,8));ax.barh(np.array(features)[idx],score[idx],color='#287b8e')
    ax.set(xlabel='Mean absolute TreeSHAP contribution (log-odds)',title='Predictive importance · combined model · Chicago 2025')
    fig.tight_layout();save_figure(fig,out,'shap_top20')
    fig,ax=plt.subplots(figsize=(10,8));rng=np.random.default_rng(321)
    for line,j in enumerate(idx):
        val=test[features[j]].to_numpy(dtype=float);valid=np.isfinite(val)
        color=np.full(len(val),.5)
        if valid.sum()>1:color[valid]=stats.rankdata(val[valid])/valid.sum()
        dots=ax.scatter(shap[:,j],line+rng.uniform(-.25,.25,len(test)),c=color,cmap='coolwarm',s=8,alpha=.65,vmin=0,vmax=1)
    ax.set_yticks(np.arange(len(idx)),np.array(features)[idx]);ax.axvline(0,c='grey',lw=.7)
    ax.set(xlabel='SHAP contribution to log-odds (right raises the prediction)',title='SHAP distributions · color shows low-to-high parameter value')
    fig.colorbar(dots,ax=ax,label='Within-parameter value percentile; missing = midpoint')
    fig.tight_layout();save_figure(fig,out,'shap_beeswarm')
    miss=pd.DataFrame({'2024':train[features].isna().mean()*100,'2025':test[features].isna().mean()*100})
    miss=miss[miss.max(axis=1)>0].sort_values('2024')
    fig,ax=plt.subplots(figsize=(10,max(4,len(miss)*.24)));miss.plot.barh(ax=ax)
    ax.set(xlabel='Missing values (%)',title='Missingness by year');fig.tight_layout();save_figure(fig,out,'missingness')
    if not parameter_plots:return
    for j,f in enumerate(features):
        fig,axes=plt.subplots(1,3,figsize=(13,3.3));obs=train[f].dropna()
        for data,label in [(train,'2024'),(test,'2025')]:
            values=data[f].dropna()
            if len(values):axes[0].hist(values,bins=20,alpha=.4,label=label,density=True)
        axes[0].set(title='Distribution (original units)',xlabel=dictionary[f].get('units',''));axes[0].legend(fontsize=8)
        for cls in (0,1):
            v=test.loc[test.primary_any_50m.eq(cls),f].dropna()
            if len(v):axes[1].scatter(np.full(len(v),cls)+np.random.default_rng(j+cls).uniform(-.12,.12,len(v)),v,s=6,alpha=.3)
        axes[1].set(xticks=[0,1],xticklabels=['No nearby crime','Nearby crime'],title='2025 observed values by outcome')
        axes[2].scatter(test[f],shap[:,j],s=8,alpha=.5,color='#287b8e');axes[2].axhline(0,color='grey',lw=.5)
        axes[2].set(title='Combined-model SHAP (2025)',ylabel='Contribution in log-odds',xlabel='Parameter value')
        fig.suptitle(f,fontsize=11);fig.tight_layout()
        fig.savefig(out/'figures/parameters'/f'{f}.png',dpi=110,bbox_inches='tight');plt.close(fig)
    print('Figures complete, including one three-panel figure per parameter',flush=True)

def htable(df):
    return df.to_html(index=False,border=0,na_rep='—',float_format=lambda v:f'{v:,.4f}',escape=True)

def mdtable(df):
    def val(x):
        if isinstance(x,(float,np.floating)):return '—' if not np.isfinite(x) else f'{x:.4f}'
        return str(x).replace('|','/')
    rows=['| '+' | '.join(map(str,df.columns))+' |','| '+' | '.join(['---']*len(df.columns))+' |']
    rows+=['| '+' | '.join(val(x) for x in row)+' |' for row in df.itertuples(index=False,name=None)]
    return '\n'.join(rows)

def report(out,d,features,env,dictionary,distribution,assocs,ranks,importance,permutation,metrics,differences,validation,config):
    main=metrics[(metrics.radius_m==50)&(metrics.threshold_type=='fixed_0.5')&metrics.subset.eq('all')]
    main=main[['model','average_precision','roc_auc','brier','precision','recall','f1','accuracy']]
    delta=differences[(differences.radius_m==50)&(differences.block_size_m==2000)&
        differences.comparison.eq('crime_plus_environment minus crime_only')&differences.metric.eq('average_precision')].iloc[0]
    finding=(f"Adding environmental variables changed 2025 average precision by {delta.difference:+.4f}; "
        f"the 95% spatial-bootstrap interval is [{delta.ci_low:+.4f}, {delta.ci_high:+.4f}]. ")
    finding+=('The interval supports an improvement within this retrospective evaluation.' if delta.ci_low>0 else
        'The interval supports worse performance in this evaluation.' if delta.ci_high<0 else
        'The interval includes zero, so this evaluation does not establish an improvement.')
    top=ranks[ranks.year.eq(2025)].sort_values('correlation_rank')
    top_env=top[top.parameter.isin(env)].head(15)
    topi=importance[importance.parameter.isin(env)].sort_values('shap_rank').head(15)
    topi=topi.merge(pd.DataFrame([{'parameter':f,'description':dictionary[f]['description']} for f in features]),on='parameter')
    warnings_text=("Exploratory retrospective analysis. Chicago has no original report dates: the seven past-crime inputs use occurrence-year records from a later extract. "
        "No outcome-year crime, identifiers, future exposure fields or coordinates enter the models; historical reporting availability still cannot be verified. "
        "The 2025 data did not participate in tuning, exclusions, early stopping or threshold selection. Both years were already examined in earlier study decisions and are not pristine holdouts. "
        "Temporal evaluation permits recurring sites; it does not test unseen cities. OSM is incomplete and may duplicate facilities, and block geocodes limit 25–100 m precision. "
        "Correlations are pairwise associations; SHAP explains model predictions in log-odds; neither proves causation. Correlated variables can share or substitute importance. "
        "Spatial bootstrap intervals condition on the fitted model and chosen grid; adjacent blocks can remain dependent and source uncertainty is not captured. "
        "Missing is not zero. Constant and exact-duplicate candidates remain in the statistical report but are excluded using training data only.")
    summary=f'''# Chicago XGBoost: results and plain-language explanation

## Main finding

{finding}

The target is **any recorded robbery/burglary within 50 metres of an ATM location during the year**. This is not a verified ATM-targeted robbery label. Training uses 443 Chicago site-years from 2024; temporal evaluation uses 482 from 2025. The 25 m and 100 m outcomes are separate sensitivity experiments.

## Model comparison on 2025

{mdtable(main)}

Average precision (AP) measures the quality of ranking crime-positive locations; higher is better. The no-information reference is the positive fraction. ROC AUC measures overall separation. Brier and log loss measure probability errors; lower is better. Precision asks how often a flagged location had nearby crime; recall asks how much nearby crime-positive activity was flagged. Threshold-dependent metrics above use 0.5, not a threshold picked from 2025. Undefined precision is blank when no sites are flagged.

## Strongest environmental associations (2025 descriptive)

{mdtable(top_env[['parameter','description','spearman_rho','spearman_ci_low','spearman_ci_high','cluster_bh_q']])}

Positive rho means larger values tend to occur at sites with nearby crime; negative rho means the opposite. Absolute rho ranks association strength. This is not the effect after controlling for other features. Intervals use block resampling. The q values adjust exploratory cluster-robust tests for multiple comparisons within this year/outcome; they do not certify causation or generalization.

## Environmental parameters most used by the combined model

{mdtable(topi[['parameter','description','mean_abs_shap','shap_ci_low','shap_ci_high','shap_rank']])}

SHAP importance answers how much the fitted model used a parameter to move predictions, not whether changing that parameter changes crime. Mean absolute SHAP is in log-odds, not percentage points. A zero for a training-excluded parameter says nothing about its possible association in other cities.

## What was prepared and tested

- 116 environmental candidates plus seven explicitly retrospective past-crime candidates; every candidate has distributions, missingness, association statistics and an importance record.
- Four spatial folds within 2024; 2 km grid grouping, a 1 km train–validation separation and exclusion of shared Census/EPA areas. Eight prespecified configurations per model family and radius. Tuning maximizes mean fold AP.
- Native XGBoost missing-value handling; no zero filling, no global imputation/scaling and no outcome-guided correlation screening.
- Models: crime-only, environment-only, combined; training-prevalence baseline. Eight grid candidates × four folds × three families × three radii = 288 tuning fits, plus final and seed-stability fits.
- 1,000 block-bootstrap replicates by default; intervals for models, paired differences, correlations and SHAP. 1 km/4 km grid-size sensitivity for performance intervals. Permutation-repeat ranges measure shuffle variability, not sampling confidence.
- Training-only F1 threshold is additionally reported; its selected OOF scores are tuning diagnostics. Recurring/new-site, point-only and boundary-clear evaluations are in the detailed metrics.
- Source hashes, prediction reload equality, SHAP additivity, row identities, feature exclusions and split separation are checked. Exact versions and settings accompany saved models.

## Limits

{warnings_text}

## Files to open

- [Full readable report, searchable parameter-by-parameter](report.html)
- [Every association and outcome](statistics/associations_all_outcomes.csv)
- [Correlation rankings and ranking uncertainty](statistics/correlation_rankings.csv)
- [Every distribution and missingness statistic](statistics/distributions_all_parameters.csv)
- [Predictive importance: SHAP](explanations/crime_plus_environment_shap_ranking.csv)
- [Held-out permutation importance](explanations/crime_plus_environment_permutation_ranking.csv)
- [Model metrics](statistics/model_metrics.csv), [intervals](statistics/model_metric_intervals.csv), [paired differences](statistics/paired_model_differences.csv)
- [Seed stability](explanations/seed_stability.csv), [validation](validation.json), [run configuration](run_config.json)
- [Reproduction and GCP instructions](../../analysis/chicago_xgboost/README.md)

Technical methods: [XGBoost API](https://xgboost.readthedocs.io/en/stable/python/python_api.html), [TreeSHAP contributions](https://xgboost.readthedocs.io/en/stable/prediction.html), [grouped CV](https://scikit-learn.org/stable/modules/cross_validation.html), [permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html).
'''
    (out/'README.md').write_text(summary)
    settings=[]
    for radius in (50,25,100):
        for family in ('crime_only','environment_only','crime_plus_environment'):
            spec=json.loads((out/f'models/{radius}m_{family}.schema.json').read_text())
            modelconf=json.loads((out/f'models/{radius}m_{family}.config.json').read_text())
            settings.append({'radius_m':radius,'model':family,'features_used':len(spec['features']),
                **{k:modelconf.get(k) for k in ('n_estimators','max_depth','min_child_weight','learning_rate','reg_alpha','reg_lambda','subsample','colsample_bytree','random_state','n_jobs')},
                'threshold_from_training_oof':spec['threshold_from_training_oof']})
    settings=pd.DataFrame(settings)
    toc=''.join(f'<option value="{html.escape(f)}">{html.escape(f)}</option>' for f in features)
    parts=[f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chicago ATM study · detailed XGBoost report</title><style>
body{{font:16px/1.6 system-ui,sans-serif;max-width:1320px;margin:35px auto;padding:0 24px;color:#19313b;background:#f8fafb}}
h1,h2,h3{{line-height:1.25}}h1{{font-size:36px}}h2{{margin-top:40px}}p{{max-width:1100px}}
table{{border-collapse:collapse;font-size:12px;white-space:normal;width:100%;background:white}}
td,th{{text-align:left;border-bottom:1px solid #dce3e7;padding:8px;vertical-align:top}}th{{background:#e9f1f4;position:sticky;top:0}}
.scroll{{overflow:auto;max-height:650px;border:1px solid #dce3e7}}.note{{padding:20px;background:#fff1d9;border-left:5px solid #b87a22}}
.finding{{padding:24px;background:#e2f2ee;border-left:5px solid #287b8e;font-size:20px}}
img{{max-width:100%;background:white}}a{{color:#12667e}}details{{background:white;padding:18px;margin:18px 0;border:1px solid #dce3e7;border-radius:8px}}summary{{cursor:pointer;font-weight:700}}input{{padding:12px;width:min(90%,550px);font-size:16px}}.small{{font-size:13px}}.links a{{display:inline-block;margin:5px 15px 5px 0}}code{{background:#e9f1f4;padding:2px 5px}}
</style><h1>Chicago ATM study</h1><p>Detailed retrospective XGBoost analysis · train 2024, evaluate 2025 · primary radius 50 m</p>
<div class="finding">{html.escape(finding)}</div><p class="note">{html.escape(warnings_text)}</p>
<div class="links"><a href="README.md">Summary</a><a href="statistics/correlation_rankings.csv">All correlation ranks</a><a href="explanations/crime_plus_environment_shap_ranking.csv">All SHAP ranks</a><a href="statistics/model_metric_intervals.csv">Metric confidence intervals</a><a href="validation.json">Validation</a></div>
<h2>Model performance</h2>{htable(main)}<p>Higher AP/AUC is better; lower Brier/log loss is better. A probability threshold of 0.5 defines the classification metrics here. Full outputs also include a training-only threshold. The interval on the difference above is paired: the models are compared on the same resampled spatial blocks.</p>
<img src="figures/model_performance_50m.png" alt="ROC precision recall and calibration curves">
<h2>Two different rankings</h2><p><b>Correlation</b> measures one parameter's association with observed crime. <b>SHAP</b> measures that parameter's contribution inside a model using many parameters together. Neither is causal. Strong association does not guarantee additional predictive value when other similar parameters are present.</p>
<img src="figures/correlation_top20.png" alt="Correlation ranking"><img src="figures/shap_top20.png" alt="SHAP ranking"><img src="figures/shap_beeswarm.png" alt="SHAP contribution distributions">
<h2>Environmental associations</h2><div class="scroll">{htable(top_env[['parameter','description','spearman_rho','spearman_ci_low','spearman_ci_high','cluster_bh_q']])}</div>
<h2>Environmental predictive importance</h2><div class="scroll">{htable(topi[['parameter','description','mean_abs_shap','shap_ci_low','shap_ci_high','shap_rank']])}</div>
<h2>Missing data</h2><p>Missing values stay missing and XGBoost learns routing on training data. The seven unavailable original report-filtered crime variables were not filled. Separate retrospective substitutes are named explicitly. Neighborhood values come from fixed older ACS/EPA vintages. Constants and exact duplicates are identified in each training fold.</p><img src="figures/missingness.png" alt="Missingness">
<h2>Training and exact selected settings</h2><p>Four training-year spatial folds, 2 km grid groups, 1 km purge and no shared ACS/EPA areas. Objective: binary logistic. Tree method: histogram on CPU. Each family/radius chooses among the eight prespecified candidates by mean training-fold average precision. The 2025 labels were not used for this selection.</p><div class="scroll">{htable(settings)}</div>
<h2>Complete performance statistics</h2><div class="scroll">{htable(metrics)}</div>
<h2>Paired model comparisons and spatial-grid sensitivity</h2><div class="scroll">{htable(differences)}</div>
<h2>How to read parameter statistics</h2><p>Statistics are separate by year. Spearman rho compares ranks, Pearson r compares numeric values (point-biserial for the binary label), and Kendall tau measures rank agreement. Crime counts and separate robbery/burglary counts are descriptive outcomes. The confidence intervals use spatial clusters. Cluster-rank p values are approximate regression tests on ranks; BH q values adjust within each year/outcome across the parameter family. IID p values ignore spatial dependence and are included only for transparency. Missingness is reported separately for crime-positive and crime-negative locations. A bootstrap rank range shows how unstable a ranking may be.</p>
<p>SHAP values are in log-odds. Their sum plus the base contribution reproduces the model margin. The value–SHAP correlation gives a rough direction, not a universal or causal effect. Permutation AP drop measures the loss of test performance after shuffling one variable; related variables can substitute for each other, and the shuffle can produce unrealistic combinations. Permutation ranges cover repeats, not population uncertainty.</p>
<h2>Every parameter ({len(features)})</h2><input id="search" list="names" placeholder="Search name, source, or description" aria-label="Search parameter"><datalist id="names">{toc}</datalist><p class="small">Open a parameter for its full statistics, association tests, uncertainty, model importance, and plots. All displayed tables are also exported as CSV.</p>''']
    for f in features:
        desc=dictionary[f].get('description',f);ss=distribution[distribution.parameter.eq(f)].drop(columns=['parameter','description','source','units','spatial_support']).set_index('year').T.reset_index(names='statistic')
        aa=assocs[assocs.parameter.eq(f)].drop(columns=['parameter'])
        rr=ranks[ranks.parameter.eq(f)][['year','correlation_rank','bootstrap_rank_median','bootstrap_rank_low','bootstrap_rank_high','bootstrap_top10_fraction']]
        imp=importance[importance.parameter.eq(f)].merge(permutation.drop(columns='model_status'),on='parameter')
        imp=imp.drop(columns=['parameter']).T.reset_index(names='statistic');imp.columns=['statistic','value']
        parts.append(f'<details class="parameter" data-text="{html.escape(f+" "+desc+" "+dictionary[f].get("source",""),quote=True)}"><summary>{html.escape(f)} — {html.escape(desc)}</summary><p>Source: {html.escape(dictionary[f].get("source",""))}. Units: {html.escape(dictionary[f].get("units",""))}. Spatial support: {html.escape(dictionary[f].get("spatial_support",""))}.</p><h3>Distribution and missingness</h3>{htable(ss)}<h3>Associations with every declared outcome</h3><div class="scroll">{htable(aa)}</div><h3>Correlation-rank uncertainty</h3>{htable(rr)}<h3>Combined-model contribution and permutation importance</h3>{htable(imp)}<img loading="lazy" src="figures/parameters/{f}.png" alt="Distributions and SHAP for {html.escape(f)}"></details>')
    parts.append('''<h2>What can be applied to other cities?</h2><p>The saved 2024-trained models and feature schemas can generate predictions for NYC/LA. Matching columns, units and retrospective crime definitions are required. The transfer command exports predictions and feature-distribution drift without evaluating their labels by default. Only a separate target-city evaluation can establish transfer performance; the Chicago ranking is not automatically valid elsewhere. The regional constants excluded in Chicago cannot acquire new learned effects during transfer.</p>
<p>Exact commands and CPU GCP guidance are in <a href="../../analysis/chicago_xgboost/README.md">the reproduction guide</a>. Independent scientific review remains pending.</p>
<script>document.getElementById('search').addEventListener('input',e=>{let q=e.target.value.toLowerCase();document.querySelectorAll('.parameter').forEach(d=>d.hidden=!d.dataset.text.toLowerCase().includes(q));});</script></html>''')
    (out/'report.html').write_text('\n'.join(parts))
    return finding

def run(args):
    started=time.time();out=args.output.resolve()
    if out.exists() and (out/'run_config.json').exists() and not args.overwrite:
        raise RuntimeError('Output already contains an analysis. Choose --output or explicitly use --overwrite.')
    for folder in ('data','models','statistics','explanations','figures/parameters','qa'):(out/folder).mkdir(parents=True,exist_ok=True)
    inputs=verify_sources();csv(out/'qa/input_manifest.csv',inputs)
    source_file_set={str(p):digest(p) for base in [ROOT/'data/processed',ROOT/'results/phase3',ROOT/'results/phase3_environment_expanded',ROOT/'protocol',ROOT/'reports'] for p in base.rglob('*') if p.is_file() and p.stat().st_size<10_000_000}
    d,env,dictionary=load_data();features=env+CRIME
    train=d[d.outcome_year.eq(2024)].reset_index(drop=True);test=d[d.outcome_year.eq(2025)].reset_index(drop=True)
    assert len(train)==443 and len(test)==482 and set(train.row_id).isdisjoint(test.row_id)
    csv(out/'data/chicago_prepared.csv',d)
    csv(out/'data/parameter_dictionary.csv',[{'parameter':f,'family':'past_crime_retrospective' if f in CRIME else 'environment',**dictionary[f]} for f in features])
    csv(out/'data/unavailable_report_filtered_predictors.csv',[{'parameter':f,'missing_2024':int(train[f].isna().sum()),'missing_2025':int(test[f].isna().sum()),'reason':'Chicago original report dates unavailable; not imputed'} for f in UNAVAILABLE])
    versions={pkg:importlib.metadata.version(pkg) for pkg in ['numpy','pandas','scipy','scikit-learn','xgboost','matplotlib','pyproj']}
    config={'source_city':'Chicago','train_year':2024,'test_year':2025,'primary_radius_m':50,'sensitivity_radii_m':[25,100],
        'seed':17,'stability_seeds':[41,73],'bootstrap_replicates':args.bootstrap,'threads':args.threads,
        'grid':GRID,'python':sys.version,'platform':platform.platform(),'versions':versions,
        'candidate_features':features,'past_crime_features':CRIME,'environment_features':env,
        'analysis_plan_sha256':digest(HERE/'analysis_plan.md'),'pipeline_sha256':digest(__file__),
        'historical_report_availability':'UNKNOWN; retrospective unfiltered crime benchmark',
        'scientific_review':'PENDING','confirmatory_eligible':False}
    dump(out/'run_config.json',config)
    families={'crime_only':CRIME,'environment_only':env,'crime_plus_environment':features}
    predictions={};metrics=[];allpred=[];cal=[];exclusions=[];selected={};models={};checks=[];splits=[]
    for radius in (50,25,100):
        y=train[f'primary_any_{radius}m'].to_numpy(dtype=int)
        folds,fa=spatial_folds(train,y);csv(out/f'qa/spatial_folds_{radius}m.csv',fa)
        for i,(a,b) in enumerate(folds):
            for j,rowid in enumerate(train.row_id):splits.append({'radius_m':radius,'fold':i,'row_id':rowid,'role':'train' if j in a else 'validation' if j in b else 'purged'})
        for family,candidates in families.items():
            print(f'Tuning radius={radius} m, family={family}',flush=True)
            params,threshold,tuning,fold_exclusions,oof=tune(train,candidates,y,folds,args.threads)
            csv(out/f'statistics/tuning_{radius}m_{family}.csv',tuning)
            csv(out/f'qa/fold_exclusions_{radius}m_{family}.csv',fold_exclusions)
            csv(out/f'data/oof_{radius}m_{family}.csv',pd.DataFrame({'row_id':train.row_id,'y':y,'probability':oof}))
            kept,reasons=training_columns(train,candidates)
            for f in candidates:exclusions.append({'radius_m':radius,'model':family,'parameter':f,'included':f in kept,'reason':reasons.get(f,'included')})
            specification={'candidate_features':candidates,'features':kept,'excluded':reasons,'parameters':params,
                'threshold_from_training_oof':threshold,'fixed_threshold':.5,'seed':17,'train_year':2024,
                'target':f'primary_any_{radius}m','source_city':'Chicago','past_crime_semantics':'retrospective unfiltered occurrence counts',
                'feature_training_ranges':{f:{'min':float(train[f].min()),'max':float(train[f].max()),'missing_fraction':float(train[f].isna().mean())} for f in kept}}
            selected[(radius,family)]=specification
            # This record is saved before 2025 labels are used for any evaluation.
            dump(out/f'models/{radius}m_{family}.schema.json',specification)
            model=estimator(params,17,args.threads);model.fit(train[kept],y)
            model.save_model(out/f'models/{radius}m_{family}.json')
            dump(out/f'models/{radius}m_{family}.config.json',model.get_params())
            p=model.predict_proba(test[kept])[:,1];predictions[(radius,family)]=p;models[(radius,family)]=model
            restored=xgb.XGBClassifier();restored.load_model(out/f'models/{radius}m_{family}.json')
            assert np.array_equal(p,restored.predict_proba(test[kept])[:,1]);checks.append(f'model_reload_{radius}_{family}')
            assert set(kept).issubset(features) and not set(kept)&set(UNAVAILABLE)
            csv(out/f'statistics/train_vs_test_{radius}m_{family}.csv',[
                {'split':'training_in_sample',**metric_values(y,model.predict_proba(train[kept])[:,1])},
                {'split':'selected_configuration_training_oof_optimistic',**metric_values(y,oof)}])
        predictions[(radius,'prevalence_baseline')]=np.full(len(test),float(y.mean()))
    # All tuning is finished before descriptive 2025 parameter/outcome analysis.
    csv(out/'qa/fold_membership.csv',splits);csv(out/'qa/feature_exclusions.csv',exclusions)
    recurring=test.site_id.isin(train.site_id).to_numpy()
    subsets={'all':np.ones(len(test),bool),'recurring_sites':recurring,'new_sites':~recurring,
        'point_only':~test.osm_geometry_is_centroid.astype(bool).to_numpy(),
        'boundary_clear':test.boundary_buffer_clear_500m.astype(bool).to_numpy()}
    for (radius,family),p in predictions.items():
        y=test[f'primary_any_{radius}m'].to_numpy(dtype=int)
        for threshold_type,t in [('fixed_0.5',.5)]+([('training_oof_f1',selected[(radius,family)]['threshold_from_training_oof'])] if family!='prevalence_baseline' else []):
            for subset,m in subsets.items():
                if m.any():metrics.append({'radius_m':radius,'model':family,'threshold_type':threshold_type,'subset':subset,**metric_values(y[m],p[m],t)})
        for i,rowid in enumerate(test.row_id):allpred.append({'row_id':rowid,'radius_m':radius,'model':family,'y':int(y[i]),'probability':float(p[i]),'prediction_at_0_5':int(p[i]>=.5),'recurring_site':bool(recurring[i])})
        cal.extend({'radius_m':radius,'model':family,**r} for r in calibration(y,p))
    metrics=pd.DataFrame(metrics);csv(out/'statistics/model_metrics.csv',metrics);csv(out/'data/predictions_2025.csv',allpred);csv(out/'statistics/calibration_bins.csv',cal)
    dump(out/'data/cohort_summary.json',{'training_rows':len(train),'evaluation_rows':len(test),
        'unique_sites_both_years':d.site_id.nunique(),'recurring_evaluation_sites':int(recurring.sum()),'new_evaluation_sites':int((~recurring).sum()),
        'training_blocks_2km':train.spatial_block.nunique(),'evaluation_blocks_2km':test.spatial_block.nunique(),
        'train_positive_50m':int(train.primary_any_50m.sum()),'test_positive_50m':int(test.primary_any_50m.sum())})
    print('All models fitted; evaluation predictions frozen. Starting detailed uncertainty/statistics.',flush=True)
    intervals,differences=uncertainty(test,predictions,out,args.bootstrap)
    distribution,assocs,ranks=associations(d,features,dictionary,out,args.bootstrap)
    explanations={};shap_errors={}
    for family,candidates in families.items():
        spec=selected[(50,family)]
        explanations[family]=explain(models[(50,family)],train,test,candidates,spec['features'],spec['excluded'],out,args.bootstrap,family,args.threads)
        shap_errors[family]=explanations[family][3]
        print(f'SHAP and permutation importance complete: {family}',flush=True)
    importance,permutation,shap,_=explanations['crime_plus_environment']
    stability=[];seedmetrics=[]
    for family,candidates in families.items():
        spec=selected[(50,family)];kept=spec['features']
        for seed in (17,41,73):
            model=models[(50,family)] if seed==17 else estimator(spec['parameters'],seed,args.threads)
            if seed!=17:model.fit(train[kept],train.primary_any_50m.to_numpy(dtype=int));model.save_model(out/f'models/50m_{family}_seed{seed}.json')
            p=model.predict_proba(test[kept])[:,1];seedmetrics.append({'model':family,'seed':seed,**metric_values(test.primary_any_50m,p)})
            contrib=model.get_booster().predict(xgb.DMatrix(test[kept],feature_names=kept),pred_contribs=True)[:,:-1]
            means=np.abs(contrib).mean(axis=0);rs=stats.rankdata(-means,method='min')
            for f in candidates:
                j=kept.index(f) if f in kept else None
                stability.append({'model':family,'seed':seed,'parameter':f,'mean_abs_shap':means[j] if j is not None else 0,'rank':rs[j] if j is not None else np.nan})
    csv(out/'explanations/seed_stability.csv',stability);csv(out/'statistics/seed_performance.csv',seedmetrics)
    figures(train,test,features,env,dictionary,predictions,shap,ranks,out)
    assert verify_sources()==inputs
    assert all(digest(p)==sha for p,sha in source_file_set.items()),'Existing release files were modified'
    assert len(distribution)==len(features)*2 and len(assocs)==len(features)*2*len(ASSOCIATION_TARGETS)
    assert len(importance)==len(features) and len(ranks)==len(features)*2
    assert all(np.isfinite(p).all() and ((p>=0)&(p<=1)).all() for p in predictions.values())
    validation={'status':'PASS','models_reloaded_exactly':checks,'shap_max_additivity_errors':shap_errors,
        'all_candidates_reported':len(features),'training_rows':len(train),'evaluation_rows':len(test),
        'source_manifests_verified':True,'existing_small_release_files_unchanged':len(source_file_set),
        'test_data_excluded_from_tuning':True,'fold_purge_distance_m':1000,'shared_geographies_purged':True,
        'historical_reporting_leakage_resolved':False,'scientific_review':'PENDING','confirmatory_eligible':False}
    dump(out/'validation.json',validation)
    finding=report(out,d,features,env,dictionary,distribution,assocs,ranks,importance,permutation,metrics,differences,validation,config)
    dump(out/'status.json',{'status':'COMPLETE','models_fitted':True,'elapsed_seconds':time.time()-started,
        'finding':finding,'scientific_review':'PENDING','confirmatory_eligible':False})
    manifest=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='output_manifest.csv':manifest.append({'file':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':digest(p)})
    csv(out/'output_manifest.csv',manifest)
    print(finding,flush=True);print('Output:',out,flush=True)

def transfer(args):
    """No fitting or tuning; target outcomes used only with explicit --evaluate."""
    source=args.model_dir.resolve();dest=args.output.resolve()
    if dest==source:raise ValueError('Transfer output must differ from training output')
    if dest.exists() and any(dest.iterdir()):raise ValueError('Choose a new empty transfer output directory')
    verify_sources();d,env,_=load_data(args.city);d=d[d.outcome_year.eq(args.year)].reset_index(drop=True)
    dest.mkdir(parents=True,exist_ok=True);preds=[];drift=[];evaluations=[]
    for family in ['crime_only','environment_only','crime_plus_environment']:
        stem=source/'models'/f'{args.radius}m_{family}'
        spec=json.loads(stem.with_suffix('.schema.json').read_text());features=spec['features']
        assert set(features).issubset(d.columns)
        model=xgb.XGBClassifier();model.load_model(stem.with_suffix('.json'))
        p=model.predict_proba(d[features])[:,1]
        for rowid,value in zip(d.row_id,p):preds.append({'row_id':rowid,'city':args.city,'year':args.year,'model':family,'probability':float(value)})
        for f in features:
            limits=spec['feature_training_ranges'][f];v=d[f];obs=v.dropna()
            drift.append({'model':family,'parameter':f,'target_missing_fraction':v.isna().mean(),
                'training_missing_fraction':limits['missing_fraction'],
                'fraction_observed_outside_training_range':float(((obs<limits['min'])|(obs>limits['max'])).mean()) if len(obs) else np.nan,
                'training_min':limits['min'],'training_max':limits['max'],'target_min':v.min(),'target_max':v.max()})
        if args.evaluate:evaluations.append({'model':family,**metric_values(d[f'primary_any_{args.radius}m'],p)})
    csv(dest/'predictions.csv',preds);csv(dest/'feature_drift.csv',drift)
    if args.evaluate:csv(dest/'evaluation.csv',evaluations)
    dump(dest/'status.json',{'city':args.city,'year':args.year,'rows':len(d),'labels_evaluated':args.evaluate,
        'warning':'No target-city tuning; retrospective crime semantics. Distribution drift and source comparability require review.'})
    print('Transfer exports:',dest)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('run');p.add_argument('--output',type=Path,default=DEFAULT_OUT);p.add_argument('--threads',type=int,default=4)
    p.add_argument('--bootstrap',type=int,default=1000);p.add_argument('--overwrite',action='store_true')
    q=sub.add_parser('transfer');q.add_argument('--model-dir',type=Path,default=DEFAULT_OUT)
    q.add_argument('--output',type=Path,required=True);q.add_argument('--city',choices=['New York City','Los Angeles'],required=True)
    q.add_argument('--year',type=int,choices=[2024,2025],default=2025);q.add_argument('--radius',type=int,choices=[25,50,100],default=50);q.add_argument('--evaluate',action='store_true')
    args=parser.parse_args()
    if args.command=='run':
        if args.bootstrap<100:parser.error('At least 100 bootstrap replicates are required; use 1000+ for the report.')
        run(args)
    else:transfer(args)
