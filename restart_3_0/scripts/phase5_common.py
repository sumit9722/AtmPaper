"""Phase 5 data loading and metrics; reuse frozen phase 4 cohort only."""
import collections,csv,gzip,hashlib,json,math
from pathlib import Path
import numpy as np
from pyproj import Geod
from threadpoolctl import threadpool_limits
import phase4_common as old
import run_phase4 as phase4
ROOT=old.ROOT;P4=old.OUT;P5=ROOT/'results/phase5';CITIES=old.CITIES;MODELS=old.MODELS;SEED=old.SEED
read=old.read;write=old.write;save=old.save;sha=old.sha

def load():
 assert json.loads((P4/'qa/validation.json').read_text())['status']=='PASS'
 for r in read(P4/'qa/output_manifest.csv'):assert sha(P4/r['file'])==r['sha256'],r['file']
 X,meta,names=phase4.inputs();frozen={r['site_id']:r for r in read(P4/'data/modeling_cohort.csv')}
 assert set(frozen)=={r['site_id'] for r in meta}
 for r in meta:
  q=frozen[r['site_id']]
  assert q['city']==r['city'] and int(q['y_primary_50m'])==r['y_primary_50m']
  r.update(year=int(r['outcome_year']),y=int(r['y_primary_50m']),spatial_fold=int(q['spatial_fold']),block_id=q['block_id'])
 lon=np.array([float(r['longitude']) for r in meta]);lat=np.array([float(r['latitude']) for r in meta]);g=Geod(ellps='WGS84')
 d=np.array([g.inv(np.full(len(meta),lon[i]),np.full(len(meta),lat[i]),lon,lat)[2] for i in range(len(meta))])
 return X,np.array([r['y'] for r in meta]),meta,names,d

def purge(candidates,test,d):
 return candidates[d[np.ix_(candidates,test)].min(axis=1)>=1500] if len(candidates) else candidates

def metrics_table(predictions,group_fields):
 groups=collections.defaultdict(list)
 for r in predictions:groups[tuple(r[k] for k in group_fields)].append(r)
 results=[]
 for key,rs in groups.items():
  ids=[r['site_id'] for r in rs];assert len(ids)==len(set(ids))
  y=np.array([int(r['y']) for r in rs]);p=np.array([float(r['p_raw']) for r in rs])
  results.append(dict(zip(group_fields,key))|{'probabilities':'raw'}|old.metrics(y,p,ids))
 return results

def freeze_splits(names):
 hashes={str(p.relative_to(P5)):sha(p) for p in names};path=P5/'qa/split_freeze.json'
 if path.exists():assert json.loads(path.read_text())==hashes,'Frozen phase 5 split changed'
 else:save(path,hashes)

def gzip_rows(path,rows,fields=None):
 rows=list(rows);fields=fields or list(dict.fromkeys(k for r in rows for k in r))
 with gzip.open(path,'wt',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def gzread(path):
 with gzip.open(path,'rt',newline='') as f:return list(csv.DictReader(f))
