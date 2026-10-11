"""Shared temporal split and evaluation utilities; no fitting on import."""
import collections,csv,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from pyproj import Geod
from threadpoolctl import threadpool_limits
import run_phase4 as old
ROOT=old.ROOT;DATA=ROOT/'results/temporal_data';P4=ROOT/'results/phase4/temporal_v2';P5=ROOT/'results/phase5';CITIES=old.CITIES;MODELS=old.MODELS;SEED=old.SEED
read=old.read;write=old.write;save=old.save;sha=old.sha

def load():
 rows=read(DATA/'data/cohort.csv');rows.sort(key=lambda r:(int(r['year']),r['row_id']))
 raw={r['row_id']:r for r in read(DATA/'data/features.csv')}
 names=json.loads((ROOT/'results/phase3/data/feature_schema.json').read_text())['primary_predictors']
 X=np.array([[float(raw[r['row_id']][n]) if raw[r['row_id']][n] else np.nan for n in names] for r in rows]);y=np.array([int(r['y']) for r in rows])
 metadata=[]
 for r in rows:
  metadata.append(r|{'physical_site_id':r['site_id'],'site_id':r['row_id'],'year':int(r['year'])})
 indices24=np.array([i for i,r in enumerate(metadata) if r['year']==2024]);indices25=np.array([i for i,r in enumerate(metadata) if r['year']==2025])
 previous={r['site_id']:r for r in read(ROOT/'results/phase4/data/modeling_cohort.csv')}
 with threadpool_limits(limits=1):fold24,block24,xy24,_=old.partitions([metadata[i] for i in indices24])
 for j,i in enumerate(indices24):metadata[i].update(spatial_fold=int(fold24[j]),block_id=block24[j])
 for i in indices25:
  r=previous[metadata[i]['physical_site_id']];metadata[i].update(spatial_fold=int(r['spatial_fold']),block_id=r['block_id'])
 lon=np.array([float(r['longitude']) for r in metadata]);lat=np.array([float(r['latitude']) for r in metadata]);g=Geod(ellps='WGS84')
 distances=np.array([g.inv(np.full(len(rows),lon[i]),np.full(len(rows),lat[i]),lon,lat)[2] for i in range(len(rows))])
 return X,y,metadata,names,distances

def purge(candidates,test,distances):
 return candidates[distances[np.ix_(candidates,test)].min(axis=1)>=1500] if len(candidates) else candidates

def metrics_table(predictions,group_fields,probabilities=['raw']):
 groups=collections.defaultdict(list)
 for r in predictions:groups[tuple(r[k] for k in group_fields)].append(r)
 results=[]
 for key,rs in groups.items():
  ids=[r['site_id'] for r in rs];assert len(ids)==len(set(ids))
  y=np.array([int(r['y']) for r in rs])
  for prob in probabilities:
   p=np.array([float(r['p_'+prob]) for r in rs]);results.append(dict(zip(group_fields,key))|{'probabilities':prob}|old.metrics(y,p,ids))
 return results

def p4_bootstrap(predictions):
 comparisons=[];replicates=[]
 for city in ['ALL']+CITIES:
  rows=[r for r in predictions if city=='ALL' or r['city']==city]
  bymodel={m:sorted([r for r in rows if r['model']==m],key=lambda r:r['site_id']) for m in MODELS}
  base=bymodel['M0'];ids=[r['site_id'] for r in base];y=np.array([r['y'] for r in base],dtype=float)
  probs={m:np.array([r['p_raw'] for r in rs]) for m,rs in bymodel.items()}
  functions={m:old.weighted_ap_setup(y,p) for m,p in probs.items()}
  blocks=sorted({r['block_id'] for r in base});index={b:i for i,b in enumerate(blocks)};rblock=np.array([index[r['block_id']] for r in base])
  cityblocks={c:np.array([index[b] for b in blocks if b.startswith(c+':')]) for c in sorted({r['city'] for r in base})}
  rng=np.random.default_rng(SEED);samples={m:[] for m in ['M1','M2']}
  for rep in range(2000):
   w=np.zeros(len(blocks))
   for group in cityblocks.values():w+=np.bincount(rng.choice(group,len(group),replace=True),minlength=len(blocks))
   weights=w[rblock];aps={m:functions[m](weights) for m in MODELS}
   row={'city':city,'replicate':rep,'sample_sites':int(weights.sum()),'sample_positive':int(weights@y)}
   for m in MODELS:row['ap_'+m]=float(aps[m]) if np.isfinite(aps[m]) else None
   for m in ['M1','M2']:
    delta=aps[m]-aps['M0'];row['delta_'+m]=float(delta) if np.isfinite(delta) else None
    if np.isfinite(delta):samples[m].append(float(delta))
   replicates.append(row)
  for m in ['M1','M2']:
   delta=functions[m](np.ones(len(y)))-functions['M0'](np.ones(len(y)));low,high=np.quantile(samples[m],[.025,.975])
   comparisons.append({'city':city,'comparison':m+'-M0','ap_difference':delta,'ci_low':float(low),'ci_high':float(high),'blocks':len(blocks),'valid_replicates':len(samples[m]),'replicates':2000,'numerical_gate':bool(delta>=.01 and low>0),'confirmatory_go':False})
 return comparisons,replicates

def freeze_splits(folder,names):
 hashes={str(p.relative_to(folder)):sha(p) for p in names};path=folder/'qa/split_freeze.json'
 if path.exists():assert json.loads(path.read_text())==hashes,'Frozen temporal split changed'
 else:save(path,hashes)

def gzip_rows(path,rows,fields=None):
 rows=list(rows);fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 with gzip.open(path,'wt',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
