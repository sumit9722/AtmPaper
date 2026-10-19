"""Independent reconstruction of membership, selection, metrics and model replay."""
from common import *
import argparse, collections, joblib, time
from uncertainty import many_ap, weighted_many

def check_solver():
    rng=np.random.default_rng(41);X=rng.normal(size=(300,8));X[rng.random(X.shape)<.05]=np.nan
    X[:,4]=1.;X[:,5]=np.nan
    y=(rng.random(300)<expit(np.nan_to_num(X[:,0])+.5*np.nan_to_num(X[:,1]))).astype(int)
    p=batched_candidates(X[:240],y[:240],X[240:]);errors=[]
    for j in range(8):
        cols=[0] if j==0 else [0,j];e=old.estimator('M1',{'C':1.})
        e.fit(X[:240,cols],y[:240]);errors.append(float(np.max(abs(p[:,j]-e.predict_proba(X[240:,cols])[:,1]))))
    assert max(errors)<1e-6
    yy=rng.integers(0,2,100);pp=np.round(rng.random((5,3,100)),1)
    expected=np.array([[average_precision_score(yy,z) for z in row] for row in pp])
    assert np.max(abs(many_ap(yy,pp)-expected))<1e-12
    w=rng.integers(0,4,(7,100));expect=np.array([average_precision_score(yy,pp[0,0],sample_weight=v) for v in w])
    assert np.max(abs(weighted_many(yy,pp[0,0],w)-expect))<1e-12
    save(ROOT/'reports/solver_validation.json',{'status':'PASS','max_probability_error':max(errors),
         'missing_constant_empty_columns':True,'AP_ties_and_weights':'match sklearn'})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',type=int,choices=[4,5],required=True)
    parser.add_argument('--wait-for-inference',action='store_true',help='Validate fitted models while independent uncertainty computation finishes.')
    args=parser.parse_args()
    phase=args.phase;out=ROOT/f'results/phase{phase}'
    with threadpool_limits(limits=1):check_solver()
    for r in read(ROOT/'reports/input_manifest.csv'):assert sha(PROJECT/r['file'])==r['sha256'],r['file']
    # Verify every inherited raw archive against its original stored digest.
    sources=read(PREVIOUS/'data/processed/source_manifest.csv')
    for r in sources:assert sha(PREVIOUS/r['file'])==r['sha256'],r['file']
    X,y,meta,names,distance=load();ids=[r['site_id'] for r in meta];ix={rid:i for i,rid in enumerate(ids)}
    years=np.array([r['year'] for r in meta]);cities=np.array([r['city'] for r in meta]);folds=np.array([r['spatial_fold'] for r in meta])
    idx24=np.flatnonzero(years==2024);idx25=np.flatnonzero(years==2025)
    plans=json.loads((out/'qa/plan_freeze.json').read_text())['plans']
    for plan in plans:
        if phase==4:
            if plan['scheme']=='forward_spatial':
                test=idx25[folds[idx25]==int(plan['fold'])];candidate=idx24
            else:
                test=idx25[cities[idx25]==plan['fold']];candidate=idx24[cities[idx24]!=plan['fold']]
            train=purge(candidate,test,distance)
        else:
            city=plan['city'];test=idx25[(cities[idx25]==city)&(folds[idx25]==int(plan['fold']))]
            local=purge(idx24[cities[idx24]==city],test,distance)
            if plan['source']=='pooled':source=idx24[cities[idx24]!=city]
            else:source=idx24[cities[idx24]==plan['source']]
            source=purge(source,test,distance)
            condition=plan['condition']
            if condition=='local_full':train=local
            elif condition=='source_only':train=source
            else:
                sample=np.random.default_rng(plan['seed']).permutation(local)[:math.ceil(plan['fraction']*len(local))]
                train=np.sort(sample if condition=='target_only' else np.concatenate([sample,source]))
        assert np.array_equal(test,plan['test']) and np.array_equal(train,plan['train'])
        assert np.all(years[train]==2024) and np.all(years[test]==2025)
        assert distance[np.ix_(train,test)].min()>=1500
    fitrows=read(out/'qa/model_fits.csv');fitmap={r['fit_id']:r for r in fitrows}
    members=collections.defaultdict(list)
    for r in gzread(out/'qa/training_members.csv.gz'):members[r['fit_id']].append(ix[r['row_id']])
    evals=read(out/'qa/evaluations.csv');assert len(evals)==len(plans)*3
    for r in evals:
        p=plans[int(r['plan_id'])];assert members[r['fit_id']]==p['train']
        assert r['model']==fitmap[r['fit_id']]['model']
    selection_outer={}
    for r in fitrows:
        train=members[r['fit_id']];sid=r['selection_id']
        assert old.idhash(train,ids)==r['train_id_hash']
        if sid in selection_outer:assert selection_outer[sid]==train
        else:selection_outer[sid]=train
    scoregroups=collections.defaultdict(list)
    for r in read(out/'data/selection_scores.csv'):scoregroups[r['selection_id']].append(r)
    winner={}
    for sid,rs in scoregroups.items():
        means=sorted([r for r in rs if not r['reason'].startswith('inner_fold')],key=lambda r:int(r['candidate']))
        assert len(means)==len(names)
        best=0
        if int(means[0]['valid_folds'])>=2:
            for j,r in enumerate(means):
                foldvalues=[float(q['mean_inner_ap']) for q in rs if q['candidate']==r['candidate'] and q['reason'].startswith('inner_fold')]
                assert len(foldvalues)==int(r['valid_folds'])
                assert abs(np.mean(foldvalues)-float(r['mean_inner_ap']))<1e-12
                if float(r['mean_inner_ap'])>float(means[best]['mean_inner_ap'])+1e-12:best=j
        assert [int(r['candidate']) for r in means if r['selected']=='True']==[best]
        winner[sid]=best
    inner=collections.defaultdict(lambda:collections.defaultdict(list))
    # Streaming prevents millions of repeated membership dictionaries from accumulating.
    with gzip.open(out/'qa/inner_members.csv.gz','rt',newline='') as f:
        for r in csv.DictReader(f):inner[(r['selection_id'],int(r['fold']))][r['role']].append(ix[r['row_id']])
    for (sid,fold),roles in inner.items():
        outer=np.array(selection_outer[sid]);val=outer[(folds[outer]%3)==fold]
        fit=purge(outer[(folds[outer]%3)!=fold],val,distance)
        assert roles['validation']==val.tolist() and roles['train']==fit.tolist()
    # Independent sklearn reconstruction for all Phase 4 selections and 12 spread Phase 5 selections.
    selectionids=sorted(selection_outer)
    selectedchecks=selectionids if phase==4 else [selectionids[i] for i in np.unique(np.linspace(0,len(selectionids)-1,12).astype(int))]
    checks=0
    with threadpool_limits(limits=1):
        for sid in selectedchecks:
            for (ss,f),roles in inner.items():
                if ss!=sid:continue
                train,val=np.array(roles['train'],dtype=int),np.array(roles['validation'],dtype=int)
                if len(train)<10 or len(set(y[train]))<2 or len(set(y[val]))<2:continue
                scores={int(r['candidate']):float(r['mean_inner_ap']) for r in scoregroups[sid] if r['reason']==f'inner_fold_{f}'}
                for j in range(len(names)):
                    cols=[0] if j==0 else [0,j];e=old.estimator('M1',{'C':1.})
                    e.fit(X[np.ix_(train,cols)],y[train]);ap=average_precision_score(y[val],e.predict_proba(X[np.ix_(val,cols)])[:,1])
                    assert abs(ap-scores[j])<1e-7,(sid,f,j,ap,scores[j]);checks+=1
    del inner
    preds=gzread(out/'data/predictions.csv.gz');predgroups=collections.defaultdict(list)
    for r in preds:
        i=ix[r['site_id']];assert int(r['y'])==y[i] and years[i]==2025
        assert r['city']==meta[i]['city'] and r['block_id']==meta[i]['block_id']
        predgroups[r['fit_id']].append(r)
    maxerror=0.
    with threadpool_limits(limits=1):
        for n,r in enumerate(fitrows):
            artifact=out/r['artifact'];assert sha(artifact)==r['sha256'];bundle=joblib.load(artifact)
            train=members[r['fit_id']];assert bundle['train_ids']==[ids[i] for i in train]
            selected=winner[r['selection_id']]
            expected=[0] if r['model']=='M0' or selected==0 else [0,selected]
            assert bundle['columns']==expected
            assert bundle['predictors']==[names[j] for j in expected]
            if bundle['kind']=='pipeline':
                z=X[np.ix_(train,expected)]
                with warnings.catch_warnings():warnings.simplefilter('ignore',RuntimeWarning);med=np.nanmedian(z,axis=0)
                med=np.nan_to_num(med,nan=0.)
                assert np.allclose(bundle['pipeline'].named_steps['imputer'].statistics_,med)
                if r['model']!='M2':
                    complete=np.where(np.isnan(z),med,z);scaler=bundle['pipeline'].named_steps['scaler']
                    assert np.allclose(scaler.mean_,complete.mean(axis=0))
                    scale=complete.std(axis=0);scale[scale==0]=1
                    assert np.allclose(scaler.scale_,scale)
            else:assert len(set(y[train]))==1 and bundle['probability']==y[train].mean()
            rs=predgroups[r['fit_id']];rows=[ix[q['site_id']] for q in rs]
            actual=predict(bundle,X[rows]);stored=np.array([float(q['p_raw']) for q in rs])
            err=float(np.max(abs(actual-stored)));maxerror=max(maxerror,err);assert err<1e-12
            if n%1000==0:print('Replayed models',n+1,'/',len(fitrows),flush=True)
    byeval=collections.defaultdict(list)
    for r in preds:byeval[(int(r['plan_id']),r['model'])].append(r)
    assert len(byeval)==len(plans)*3
    for (pid,model),rs in byeval.items():
        assert sorted(ix[r['site_id']] for r in rs)==plans[pid]['test']
        assert len({r['fit_id'] for r in rs})==1
    metricrows=read(out/'data/metrics.csv');metricgroups=collections.defaultdict(list)
    if phase==5:
        fields=['city','condition','source','fraction','seed','model']
        for r in preds:metricgroups[tuple(r[k] for k in fields)].append(r)
    else:
        fields=['scheme','city','model']
        for r in preds:
            metricgroups[(r['scheme'],r['city'],r['model'])].append(r)
            metricgroups[(r['scheme'],'ALL',r['model'])].append(r)
    for r in metricrows:
        rs=metricgroups[tuple(r[k] for k in fields)];ri=[q['site_id'] for q in rs]
        assert len(set(ri))==len(ri)
        expectedn=sum(m['year']==2025 and (r['city']=='ALL' or m['city']==r['city']) for m in meta)
        assert len(ri)==expectedn
        expected=old.metrics(np.array([int(q['y']) for q in rs]),np.array([float(q['p_raw']) for q in rs]),ri)
        for k,v in expected.items():
            if v is None:assert r[k]==''
            else:assert abs(float(r[k])-v)<1e-12
    # The unchanged baseline independently reproduces the preserved 3.0 metrics.
    earlier=read(PREVIOUS/f'results/phase{phase}/data/metrics.csv')
    if phase==4:earlier=[r for r in earlier if r['variant']=='primary_50m' and r['probabilities']=='raw']
    oldlookup={tuple(r[k] for k in fields):r for r in earlier if r['model']=='M0'}
    for r in metricrows:
        if r['model']=='M0':
            previousrow=oldlookup[tuple(r[k] for k in fields)]
            for k in ['average_precision','brier_score']:
                assert abs(float(r[k])-float(previousrow[k]))<1e-12
    if phase==5:
        lookup={tuple(r[k] for k in fields):r for r in metricrows}
        required=[out/'data'/name for name in ['benefit_uncertainty.csv','randomization_replicates.csv.gz','bootstrap_replicates.csv.gz']]
        if args.wait_for_inference:
            while not all(p.exists() for p in required):
                print('Model, membership, selection and metric checks passed; awaiting completed inference files.',flush=True)
                time.sleep(60)
        benefits=read(out/'data/transfer_benefits.csv');summary=read(out/'data/benefit_uncertainty.csv')
        for r in benefits:
            a=lookup[(r['city'],'source_plus_target',r['source'],r['fraction'],r['seed'],r['model'])]
            b=lookup[(r['city'],'target_only','target',r['fraction'],r['seed'],r['model'])]
            assert abs(float(a['average_precision'])-float(b['average_precision'])-float(r['transfer_benefit']))<1e-12
        for r in summary:
            values=[float(q['transfer_benefit']) for q in benefits if all(q[k]==r[k] for k in ['city','source','fraction','model'])]
            assert len(values)==20 and abs(np.mean(values)-float(r['ap_difference']))<1e-12
        nulls=collections.defaultdict(list)
        for r in gzread(out/'data/randomization_replicates.csv.gz'):
            nulls[tuple(r[k] for k in ['city','source','fraction','model'])].append(float(r['null_difference']))
        for r in summary:
            values=np.array(nulls[tuple(r[k] for k in ['city','source','fraction','model'])]);assert len(values)==9999
            pv=(1+np.sum(np.abs(values)>=abs(float(r['ap_difference']))-1e-12))/10000
            assert abs(pv-float(r['randomization_p']))<1e-12
        ordered=sorted(summary,key=lambda r:float(r['randomization_p']));last=0.
        for rank,r in enumerate(ordered):
            val=min(1.,max(last,(54-rank)*float(r['randomization_p'])));last=val
            assert abs(val-float(r['holm_p']))<1e-12
            supported=float(r['ap_difference'])>=.01 and float(r['ci_low'])>0 and val<.05
            assert (r['supported_exploratory_benefit']=='True')==supported
    else:summary=read(out/'data/paired_comparisons.csv')
    bs=collections.defaultdict(list)
    for r in gzread(out/'data/bootstrap_replicates.csv.gz'):
        key=tuple(r[k] for k in (['scheme','city','comparison'] if phase==4 else ['city','source','fraction','model']))
        if r['difference']!='':bs[key].append(float(r['difference']))
    for r in summary:
        key=tuple(r[k] for k in (['scheme','city','comparison'] if phase==4 else ['city','source','fraction','model']))
        lo,hi=np.quantile(bs[key],[.025,.975]);assert abs(lo-float(r['ci_low']))<1e-12 and abs(hi-float(r['ci_high']))<1e-12
    result={'status':'PASS','phase':phase,'plans':len(plans),'model_evaluations':len(evals),
        'models_replayed':len(fitrows),'prediction_rows':len(preds),'max_replay_probability_error':maxerror,
        'selection_score_sklearn_refits':checks,'all_inner_memberships_checked':True,
        'matched_memberships_and_metrics':'PASS','inherited_raw_checksums_verified':len(sources),
        'conditional_inference_tables':'PASS','confirmatory_complete':False}
    save(out/'qa/validation.json',result)
    status=json.loads((out/'qa/status.json').read_text());status['validation']='PASS';save(out/'qa/status.json',status)
    globalstatus=json.loads((ROOT/'reports/phase_status.json').read_text());globalstatus[f'phase_{phase}']='complete: validated PASS'
    save(ROOT/'reports/phase_status.json',globalstatus)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
