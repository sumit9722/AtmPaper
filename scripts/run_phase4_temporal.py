"""Run nested 2024->2025 spatially separated model validation."""
import datetime as dt,json
import numpy as np
from threadpoolctl import threadpool_limits
import run_phase4 as old
from temporal_common import *

def main():
 X,y,meta,names,d=load();old.OUT=P4
 train24=np.array([i for i,r in enumerate(meta) if r['year']==2024]);test25=np.array([i for i,r in enumerate(meta) if r['year']==2025]);fold=np.array([r['spatial_fold'] for r in meta])
 plans=[];outer=[];inner=[];audit=[]
 for k in range(5):
  test=test25[fold[test25]==k];train=purge(train24,test,d);removed=np.setdiff1d(train24,train)
  plan={'variant':'temporal_50m','scheme':'forward_spatial','fold':f'fold_{k}','train':train,'test':test,'inner':[]}
  for role,idx in [('train',train),('test',test),('purged',removed)]:
   for i in idx:outer.append({'fold':k,'role':role,'row_id':meta[i]['site_id'],'year':meta[i]['year']})
  audit.append({'fold':k,'inner_fold':'OUTER','train_n':len(train),'test_n':len(test),'min_distance_m':float(d[np.ix_(train,test)].min())})
  for j in sorted(set(fold[train])):
   val=train[fold[train]==j];candidate=train[fold[train]!=j];fit=purge(candidate,val,d);removed_inner=np.setdiff1d(candidate,fit)
   plan['inner'].append((int(j),fit,val))
   for role,idx in [('train',fit),('validation',val),('purged',removed_inner)]:
    for i in idx:inner.append({'fold':k,'inner_fold':j,'role':role,'row_id':meta[i]['site_id'],'year':meta[i]['year']})
   audit.append({'fold':k,'inner_fold':j,'train_n':len(fit),'test_n':len(val),'min_distance_m':float(d[np.ix_(fit,val)].min()) if len(fit) else None})
  plans.append(plan)
 write(P4/'data/outer_splits.csv',outer);write(P4/'data/inner_splits.csv',inner);write(P4/'qa/separation.csv',audit)
 write(P4/'data/cohort_with_groups.csv',meta)
 freeze_splits(P4,[P4/'data/outer_splits.csv',P4/'data/inner_splits.csv'])
 store=[[] for _ in range(6)];started=dt.datetime.now(dt.timezone.utc).isoformat()
 with threadpool_limits(limits=1):
  for plan in plans:
   for dest,rows in zip(store,old.fit_plan(plan,X,y,names,meta)):dest.extend(rows)
   print('Temporal',plan['fold'],'train',len(plan['train']),'test',len(plan['test']),flush=True)
 predictions,search,preprocess,fits,warnings_log,calib=store
 for r in predictions:r['analysis_status']='RETROSPECTIVE_2024_TO_2025'
 for path,rows in [('data/predictions.csv',predictions),('data/inner_search.csv',search),('qa/preprocessing.csv',preprocess),('qa/model_fits.csv',fits),('qa/calibration_training.csv',calib)]:write(P4/path,rows)
 write(P4/'qa/warnings.csv',warnings_log,['variant','scheme','fold','model','stage','warning'])
 metric_rows=metrics_table(predictions,['city','model'],['raw','sigmoid'])
 metric_rows+=metrics_table([r|{'city':'ALL'} for r in predictions],['city','model'],['raw','sigmoid'])
 write(P4/'data/metrics.csv',metric_rows)
 comparisons,reps=p4_bootstrap(predictions);write(P4/'data/paired_ap_comparisons.csv',comparisons);write(P4/'data/bootstrap_replicates.csv',reps)
 save(P4/'qa/status.json',{'temporal_computation':'complete','training_year':2024,'test_year':2025,'train_cohort_rows':len(train24),'test_cohort_rows':len(test25),'models':len(fits),'validation':'pending','independent_human_review_completed':False,'confirmatory_complete':False,'prior_2025_results_already_inspected':True,'started_utc':started,'finished_utc':dt.datetime.now(dt.timezone.utc).isoformat()})
 print('Temporal phase 4 fits finished.',flush=True)
if __name__=='__main__':main()
