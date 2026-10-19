"""One-command fail-fast offline rebuild of the self-contained 5.0 release."""
import csv,datetime as dt,json,subprocess,sys,time
from common import *
sys.path.insert(0,str(PROJECT/'scripts'))
from large_artifacts import entries, verify_parts
def main():
 freeze()
 for artifact in entries().values():verify_parts(artifact)
 # Verify against the prior manifest before any source registry can be regenerated.
 manifest=OUT/'source_manifest.csv'
 if not manifest.exists():raise RuntimeError('Missing frozen source manifest; restore the archived release before offline rebuilding')
 for r in read(manifest):
  if sha(ROOT/r['file'])!=r['sha256']:raise RuntimeError('Input changed: '+r['file'])
 savejson(REPORTS/'phase_status.json',{'release':'restart5_0','phase_1':{'computational_status':'REBUILDING'},'phase_2':{'computational_status':'REBUILDING'},'confirmatory_eligible':False})
 start=time.monotonic();runs=[]
 try:
  for script in ['build_exposure.py','build_crime.py','build_panel.py','build_monthly.py','make_manifests.py','validate.py','report.py','validate_deliverables.py']:
   step=time.monotonic();print('\nRunning '+script,flush=True)
   subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT.parent,check=True)
   runs.append({'script':script,'status':'PASS','elapsed_seconds':round(time.monotonic()-step,3)})
 except Exception as e:
  savejson(REPORTS/'phase_status.json',{'release':'restart5_0','phase_1':{'computational_status':'REBUILD_FAILED'},'phase_2':{'computational_status':'REBUILD_FAILED'},'error':str(e),'completed_steps':runs,'confirmatory_eligible':False});raise
 savejson(REPORTS/'execution.json',{'status':'PASS','completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,3),'steps':runs,'network_used':False,'models_fitted':False})
 artifacts=[]
 for p in sorted(ROOT.rglob('*')):
  if not p.is_file() or '__pycache__' in p.parts or 'raw' in p.relative_to(ROOT).parts or p==REPORTS/'artifact_manifest.csv' or p==OUT/'event_atm_links.csv':continue
  artifacts.append({'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
 assert sha(OUT/'event_atm_links.csv')==entries()['restart5_0/data/processed/event_atm_links.csv']['sha256']
 with (REPORTS/'artifact_manifest.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['file','bytes','sha256'],lineterminator='\n');w.writeheader();w.writerows(artifacts)
 for r in artifacts:assert sha(ROOT/r['file'])==r['sha256']
 print('Offline rebuild and deliverable verification PASS;',len(artifacts),'derived/code/document artifacts hashed',flush=True)
if __name__=='__main__':main()
