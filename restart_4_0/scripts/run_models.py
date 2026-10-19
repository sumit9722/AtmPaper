"""Run Phase 4 or the full matched Phase 5 ladder with nested feature selection."""
from common import *
import argparse, datetime as dt, joblib, collections, importlib.metadata

def make_plans(phase, meta, distance):
    years=np.array([r['year'] for r in meta]); cities=np.array([r['city'] for r in meta])
    folds=np.array([r['spatial_fold'] for r in meta]); tr=np.flatnonzero(years==2024); te=np.flatnonzero(years==2025)
    plans=[]; samples=[]; pools=[]
    if phase==4:
        definitions=[('forward_spatial', str(f), te[folds[te]==f], tr) for f in range(5)]
        definitions += [('forward_leave_city_out',city,te[cities[te]==city],tr[cities[tr]!=city]) for city in CITIES]
        for scheme,fold,test,pool in definitions:
            plans.append({'scheme':scheme,'fold':fold,'train':purge(pool,test,distance),'test':test})
    else:
        for city in CITIES:
            for fold in range(5):
                test=te[(cities[te]==city)&(folds[te]==fold)]
                pool=purge(tr[cities[tr]==city],test,distance)
                sources={c:purge(tr[cities[tr]==c],test,distance) for c in CITIES if c!=city}
                sources['pooled']=np.sort(np.concatenate(list(sources.values())))
                for role,indices in [('test',test),('local_pool',pool)]+list(sources.items()):
                    pools.extend({'city':city,'fold':fold,'role':role,'row_id':meta[i]['site_id']} for i in indices)
                def add(condition,source,fraction,seed,train):
                    plans.append({'city':city,'fold':fold,'condition':condition,'source':source,
                                  'fraction':fraction,'seed':seed,'train':np.sort(train),'test':test})
                add('local_full','target',1.,0,pool)
                for source,ix in sources.items(): add('source_only',source,0.,0,ix)
                for seed in SEEDS:
                    order=np.random.default_rng(seed).permutation(pool)
                    for fraction in [.1,.25]:
                        selected=order[:math.ceil(fraction*len(pool))]
                        samples.extend({'city':city,'fold':fold,'seed':seed,'fraction':fraction,
                                        'pool_n':len(pool),'row_id':meta[i]['site_id']} for i in selected)
                        add('target_only','target',fraction,seed,selected)
                        for source,ix in sources.items(): add('source_plus_target',source,fraction,seed,np.concatenate([ix,selected]))
    return plans,samples,pools

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',type=int,choices=[4,5],required=True);args=parser.parse_args()
    phase=args.phase; out=ROOT/f'results/phase{phase}'
    for sub in ['data','qa','models','docs','figures']: (out/sub).mkdir(parents=True,exist_ok=True)
    for rel in ['qa/validation.json','data/paired_comparisons.csv','data/benefit_uncertainty.csv',
                'data/randomization_replicates.csv.gz','data/bootstrap_replicates.csv.gz']:
        (out/rel).unlink(missing_ok=True)
    save(out/'qa/status.json',{'computation':'running','validation':'pending'})
    start=dt.datetime.now(dt.timezone.utc).isoformat()
    freeze(out/'qa/protocol_freeze.json',{'sha256':sha(ROOT/'protocol/restart_spec.md')})
    X,y,meta,names,distance=load();ids=[r['site_id'] for r in meta]
    plans,samples,pools=make_plans(phase,meta,distance)
    definitions=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in p.items()} for p in plans]
    freeze(out/'qa/plan_freeze.json',{'metadata_sha256':sha(ROOT/'results/phase3/data/modeling_cohort.csv'),
                                    'plans':definitions})
    save(out/'qa/experiment_registry.json',{'phase':phase,'models':MODELS,'parameters':PARAMS,'features':names,
          'planned_model_evaluations':len(plans)*3,'training_year':2024,'test_year':2025,'seeds':SEEDS,
          'candidate_rule':'background or background plus one variable','selection':'training-only spatial CV',
          'inner_groups':'saved 2024 spatial fold modulo 3','purge_m':1500,'primary_family':'M1'})
    if phase==5:
        write(out/'data/target_samples.csv',samples);write(out/'data/splits.csv',pools)
    models={}; selections={}; selection_scores=[]; members=[]; fitrows=[]; evaluations=[]; predictions=[]; warningrows=[]
    inner_members=[]
    idx25=np.array([i for i,r in enumerate(meta) if r['year']==2025])
    with threadpool_limits(limits=1):
        for pn,plan in enumerate(plans):
            train,test=plan['train'],plan['test'];assert len(train) and len(test)
            assert all(meta[i]['year']==2024 for i in train)
            assert distance[np.ix_(train,test)].min()>=1500
            membership=tuple(train)
            tag={k:v for k,v in plan.items() if k not in ['train','test']}
            if membership not in selections:
                selection_id=f'selection_{len(selections):05d}'
                winner,means,scores,splits=select(X,y,train,meta,distance)
                selections[membership]=(selection_id,winner)
                valid=[s for s in splits if s['valid']]
                for j,name in enumerate(names):
                    selection_scores.append({'selection_id':selection_id,'candidate':j,
                        'added_feature':name if j else 'NONE','mean_inner_ap':float(means[j]) if np.isfinite(means[j]) else '',
                        'valid_folds':len(scores),'selected':j==winner,'reason':'max_validation_ap' if len(scores)>=2 else 'insufficient_valid_folds'})
                    for score,split in zip(scores,valid):
                        selection_scores.append({'selection_id':selection_id,'candidate':j,'added_feature':name if j else 'NONE',
                            'mean_inner_ap':score[j],'valid_folds':len(scores),'selected':False,'reason':f"inner_fold_{split['fold']}"})
                for split in splits:
                    for role in ['train','validation']:
                        inner_members.extend({'selection_id':selection_id,'fold':split['fold'],'role':role,
                                              'valid':split['valid'],'row_id':ids[i]} for i in split[role])
            selection_id,winner=selections[membership]
            for model in MODELS:
                key=(model,membership)
                if key not in models:
                    fitid=f'fit_{len(models):05d}'
                    cols=[0] if model=='M0' or winner==0 else [0,winner]
                    bundle,caught=fit_bundle(model,cols,X,y,train,names)
                    bundle.update(model=model,selection_id=selection_id,train_ids=[ids[i] for i in train])
                    artifact=out/'models'/f'{fitid}.joblib';joblib.dump(bundle,artifact,compress=3)
                    probs=np.full(len(meta),np.nan);probs[idx25]=predict(bundle,X[idx25])
                    models[key]=(fitid,probs)
                    fitrows.append({'fit_id':fitid,'model':model,'selection_id':selection_id,
                        'selected_feature':names[winner] if winner else 'NONE','predictors':json.dumps(bundle['predictors']),
                        'train_n':len(train),'positive_n':int(y[train].sum()),'single_class':bundle['kind']=='constant',
                        'train_id_hash':old.idhash(train,ids),'artifact':str(artifact.relative_to(out)),'sha256':sha(artifact)})
                    members.extend({'fit_id':fitid,'row_id':ids[i]} for i in train)
                    warningrows.extend({'fit_id':fitid,'warning':w} for w in caught)
                fitid,probs=models[key]
                evaluations.append(tag|{'plan_id':pn,'model':model,'fit_id':fitid,'train_n':len(train),
                    'test_n':len(test),'min_distance_m':float(distance[np.ix_(train,test)].min())})
                predictions.extend(tag|{'plan_id':pn,'model':model,'fit_id':fitid,'site_id':ids[i],
                    'city':meta[i]['city'],'block_id':meta[i]['block_id'],'y':int(y[i]),'p_raw':float(probs[i])} for i in test)
            if pn%20==0 or pn==len(plans)-1:
                print(f'Phase {phase}: {pn+1}/{len(plans)} plans; {len(models)} models; {len(selections)} nested selections',flush=True)
    gzwrite(out/'data/predictions.csv.gz',predictions)
    gzwrite(out/'qa/training_members.csv.gz',members)
    gzwrite(out/'qa/inner_members.csv.gz',inner_members)
    write(out/'qa/model_fits.csv',fitrows);write(out/'qa/evaluations.csv',evaluations)
    write(out/'data/selection_scores.csv',selection_scores)
    write(out/'qa/warnings.csv',warningrows,['fit_id','warning'])
    if phase==4:
        metricrows=[]
        for scheme in ['forward_spatial','forward_leave_city_out']:
            for city in ['ALL']+CITIES:
                for model in MODELS:
                    rs=[r for r in predictions if r['scheme']==scheme and r['model']==model and (city=='ALL' or r['city']==city)]
                    yy=np.array([r['y'] for r in rs]);pp=np.array([r['p_raw'] for r in rs]);ri=[r['site_id'] for r in rs]
                    metricrows.append({'scheme':scheme,'city':city,'model':model}|old.metrics(yy,pp,ri))
    else:
        group=['city','condition','source','fraction','seed','model']
        metricrows=previous.metrics_table(predictions,group)
        lookup={tuple(r[k] for k in group):r for r in metricrows};benefits=[];gaps=[]
        for r in metricrows:
            if r['condition']=='source_plus_target':
                control=lookup[(r['city'],'target_only','target',r['fraction'],r['seed'],r['model'])]
                benefits.append({k:r[k] for k in ['city','source','fraction','seed','model']}|
                    {'augmented_ap':r['average_precision'],'target_only_ap':control['average_precision'],
                     'transfer_benefit':r['average_precision']-control['average_precision']})
            if r['condition']=='source_only':
                control=lookup[(r['city'],'local_full','target',1.,0,r['model'])]
                gaps.append({k:r[k] for k in ['city','source','model']}|
                    {'local_ap':control['average_precision'],'source_ap':r['average_precision'],
                     'transfer_gap':control['average_precision']-r['average_precision']})
        write(out/'data/transfer_benefits.csv',benefits);write(out/'data/transfer_gaps.csv',gaps)
    write(out/'data/metrics.csv',metricrows)
    save(out/'qa/status.json',{'computation':'complete','validation':'pending','phase':phase,
        'plans':len(plans),'model_evaluations':len(evaluations),'unique_models':len(models),
        'nested_selections':len(selections),'prediction_rows':len(predictions),
        'single_class_models':sum(r['single_class'] for r in fitrows),'warnings':len(warningrows),'confirmatory_complete':False})
    save(out/'qa/environment.json',{'started_utc':start,'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
         'python':sys.version,'packages':{p:importlib.metadata.version(p) for p in ['numpy','scipy','scikit-learn','xgboost-cpu','joblib']}})
    print(f'Phase {phase} model computation complete.',flush=True)

if __name__=='__main__':main()
