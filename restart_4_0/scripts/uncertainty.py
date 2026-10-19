"""Conditional spatial uncertainty, preserving all repeated-seed pairs."""
from common import *
import argparse, collections

def weighted_many(y,p,weights):
    order=np.argsort(-p,kind='stable');ys=y[order]
    ends=np.r_[np.where(np.diff(p[order])!=0)[0],len(p)-1]
    w=np.asarray(weights,dtype=float)[:,order];pos=np.cumsum(w*ys,axis=1)[:,ends];total=np.cumsum(w,axis=1)[:,ends]
    increments=np.diff(np.column_stack([np.zeros(len(w)),pos]),axis=1)
    precision=np.divide(pos,total,out=np.zeros_like(pos),where=total>0)
    return np.divide((increments*precision).sum(axis=1),pos[:,-1],
                     out=np.full(len(w),np.nan),where=pos[:,-1]>0)

def many_ap(y,p):
    """Tie-correct AP on final axis; supports permutation x seed x site arrays."""
    order=np.argsort(-p,axis=-1,kind='stable');ps=np.take_along_axis(p,order,axis=-1)
    yy=np.broadcast_to(y,p.shape);ys=np.take_along_axis(yy,order,axis=-1)
    cp=np.cumsum(ys,axis=-1)
    ends=np.concatenate([np.diff(ps,axis=-1)!=0,np.ones(p.shape[:-1]+(1,),dtype=bool)],axis=-1)
    prior=np.maximum.accumulate(np.where(ends,cp,0),axis=-1)
    prior=np.concatenate([np.zeros(p.shape[:-1]+(1,)),prior[...,:-1]],axis=-1)
    return (np.where(ends,(cp-prior)*cp/np.arange(1,p.shape[-1]+1),0)).sum(axis=-1)/y.sum()

def block_weights(rows,rng,n=2000):
    groups=sorted({r['block_id'] for r in rows});index={g:i for i,g in enumerate(groups)}
    rowgroup=np.array([index[r['block_id']] for r in rows])
    gc={index[r['block_id']]:r['city'] for r in rows}
    mult=np.zeros((n,len(groups)))
    for city in sorted(set(gc.values())):
        ix=np.array([i for i,c in gc.items() if c==city])
        mult[:,ix]=rng.multinomial(len(ix),np.ones(len(ix))/len(ix),size=n)
    return mult[:,rowgroup],rowgroup,len(groups)

def paired(rows,A,B,seed=20261001,permutations=False):
    # A and B are seed x site arrays; averages concern AP, not ensemble predictions.
    y=np.array([int(r['y']) for r in rows]);rng=np.random.default_rng(seed)
    point=float(np.mean(many_ap(y,A)-many_ap(y,B)))
    weights,rowgroup,ngroups=block_weights(rows,rng)
    boot=np.zeros(len(weights))
    for a,b in zip(A,B): boot+=weighted_many(y,a,weights)-weighted_many(y,b,weights)
    boot/=len(A);valid=boot[np.isfinite(boot)]
    lo,hi=np.quantile(valid,[.025,.975])
    summary={'ap_difference':point,'ci_low':float(lo),'ci_high':float(hi),
        'spatial_blocks':ngroups,'valid_bootstraps':len(valid),'bootstrap_replicates':2000,
        'uncertainty_scope':'conditional fitted predictions; spatial blocks resampled jointly across seeds'}
    null=[]
    if permutations:
        for start in range(0,9999,25):
            n=min(25,9999-start)
            swap=rng.integers(0,2,size=(n,ngroups),dtype=np.int8)[:,rowgroup].astype(bool)[:,None,:]
            aa=np.where(swap,B[None,:,:],A[None,:,:]);bb=np.where(swap,A[None,:,:],B[None,:,:])
            null.extend(np.mean(many_ap(y,aa)-many_ap(y,bb),axis=1))
        summary.update(randomization_p=float((1+np.sum(np.abs(null)>=abs(point)-1e-12))/10000),permutations=9999)
    return summary,boot,null

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',type=int,choices=[4,5],required=True);args=parser.parse_args()
    phase=args.phase;out=ROOT/f'results/phase{phase}';pred=gzread(out/'data/predictions.csv.gz')
    freeze(out/'qa/inference_amendment_freeze.json',{'sha256':sha(ROOT/'protocol/inference_resolution_amendment.md')})
    summaries=[];replicates=[];randomizations=[]
    if phase==4:
        for scheme in ['forward_spatial','forward_leave_city_out']:
            for city in ['ALL']+CITIES:
                bymodel={m:sorted([r for r in pred if r['scheme']==scheme and r['model']==m and (city=='ALL' or r['city']==city)],key=lambda r:r['site_id']) for m in MODELS}
                base=bymodel['M0'];ids=[r['site_id'] for r in base]
                for model in ['M1','M2']:
                    assert [r['site_id'] for r in bymodel[model]]==ids
                    A=np.array([[float(r['p_raw']) for r in bymodel[model]]]);B=np.array([[float(r['p_raw']) for r in base]])
                    result,boot,_=paired(base,A,B)
                    tag={'scheme':scheme,'city':city,'comparison':model+'-M0'}
                    primary=scheme=='forward_spatial' and city=='ALL' and model=='M1'
                    summaries.append(tag|result|{'primary':primary,'numerical_gate':result['ap_difference']>=.01 and result['ci_low']>0,'confirmatory':False})
                    replicates.extend(tag|{'replicate':i,'difference':float(v) if np.isfinite(v) else ''} for i,v in enumerate(boot))
        write(out/'data/paired_comparisons.csv',summaries)
    else:
        group=['city','condition','source','fraction','seed','model'];groups=collections.defaultdict(list)
        for r in pred:groups[tuple(r[k] for k in group)].append(r)
        for key in groups:groups[key].sort(key=lambda r:r['site_id'])
        count=0
        for city in CITIES:
            for source in [c for c in CITIES if c!=city]+['pooled']:
                for fraction in ['0.1','0.25']:
                    for model in MODELS:
                        aa=[groups[(city,'source_plus_target',source,fraction,str(s),model)] for s in SEEDS]
                        bb=[groups[(city,'target_only','target',fraction,str(s),model)] for s in SEEDS]
                        ids=[r['site_id'] for r in aa[0]]
                        assert all([r['site_id'] for r in rs]==ids for rs in aa+bb)
                        A=np.array([[float(r['p_raw']) for r in rs] for rs in aa]);B=np.array([[float(r['p_raw']) for r in rs] for rs in bb])
                        result,boot,null=paired(aa[0],A,B,permutations=True)
                        y=np.array([int(r['y']) for r in aa[0]])
                        ds=many_ap(y,A)-many_ap(y,B)
                        tag={'city':city,'source':source,'fraction':fraction,'model':model}
                        summaries.append(tag|result|{'seeds':20,'seed_sd':float(np.std(ds,ddof=1)),
                            'seed_p025':float(np.quantile(ds,.025)),'seed_p975':float(np.quantile(ds,.975)),
                            'positive_seeds':int((ds>0).sum()),'negative_seeds':int((ds<0).sum()),'confirmatory':False})
                        replicates.extend(tag|{'replicate':i,'difference':float(v) if np.isfinite(v) else ''} for i,v in enumerate(boot))
                        randomizations.extend(tag|{'permutation':i,'null_difference':float(v)} for i,v in enumerate(null))
                        count+=1;print('Phase 5 uncertainty',count,'/54',city,source,fraction,model,flush=True)
        # Holm family includes all models, source choices, cities and fractions.
        order=sorted(range(len(summaries)),key=lambda i:summaries[i]['randomization_p']);last=0.
        for rank,i in enumerate(order):
            adjusted=min(1.,max(last,(len(order)-rank)*summaries[i]['randomization_p']));last=adjusted
            r=summaries[i];r['holm_p']=adjusted
            r['supported_exploratory_benefit']=r['ap_difference']>=.01 and r['ci_low']>0 and adjusted<.05
        write(out/'data/benefit_uncertainty.csv',summaries)
        gzwrite(out/'data/randomization_replicates.csv.gz',randomizations)
    gzwrite(out/'data/bootstrap_replicates.csv.gz',replicates)
    print('Uncertainty complete.',flush=True)

if __name__=='__main__':main()
