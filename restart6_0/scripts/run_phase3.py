"""Reproduce Restart 6 Phase 3 offline; optionally acquire missing public inputs."""
import argparse
import datetime as dt
import subprocess
import sys
import time
from phase3_common import *

def input_paths():
    paths=[p for p in RAW.rglob('*') if p.is_file() and not p.name.endswith('.partial')]
    for table in sorted({v.split('_')[0] for f in definitions() for v in f.get('components',[])}):
        p=bulk_path(table);paths.extend([p,Path(str(p)+'.source.json')])
    for state in COUNTIES:
        p=geometry_path(state);paths.extend([p,Path(str(p)+'.request.json')])
    for p in sld_paths():paths.extend([p,Path(str(p)+'.request.json')])
    for slug in CITIES.values():
        for year in (2023,2024):
            p=ROOT/f'data/raw/osm_v2/{slug}/{year}-12-15.parquet';paths.extend([p,Path(str(p)+'.request.json')])
    paths.extend(ROOT/p for p in ['data/processed/atm_panel_full_year_2024_2025.csv','data/processed/atm_panel_partial_2023.csv',
        'data/processed/crime_primary_2022_2025.csv','reports/validation.json','reports/artifact_manifest.csv',
        'data/processed/source_manifest.csv','large_artifacts.json','protocol/phase3_feature_spec.md','protocol/phase3_variables.json'])
    paths.append(ROOT/'protocol/phase3_geometry_policy.md')
    return paths

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--acquire',action='store_true');args=parser.parse_args()
    started=time.monotonic();steps=[];freeze();verify_phase12()
    def run(name,*arguments):
        begin=time.monotonic();print('Running',name,flush=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/name),*arguments],cwd=PROJECT,check=True)
        steps.append({'script':name,'status':'PASS','elapsed_seconds':round(time.monotonic()-begin,3)})
    status={'phase_3':'BUILDING','phase_1_2':'unchanged; independently verified','models_fitted':False,
        'scientific_review':'PENDING','confirmatory_modeling_ready':False}
    savejson(OUT/'qa/phase3_status.json',status)
    try:
        if args.acquire:run('acquire_phase3.py')
        manifest=OUT/'qa/input_manifest.csv';expected=fingerprint(input_paths())
        if manifest.exists():
            prior=manifest_check(manifest)
            assert {r['file']:r['sha256'] for r in prior}=={r['file']:r['sha256'] for r in expected},'Phase 3 frozen inputs changed'
        else:write(manifest,expected)
        test=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'phase3/tests'),'-v'],cwd=PROJECT,capture_output=True,text=True)
        (OUT/'qa/regression_tests.log').write_text(test.stdout+test.stderr);test.check_returncode()
        steps.append({'script':'phase3/tests','status':'PASS'})
        for name in ('build_phase3.py','validate_phase3.py','report_phase3.py'):run(name)
        status.update(phase_3='COMPUTATION_COMPLETE',validation='PASS')
        savejson(OUT/'qa/phase3_status.json',status)
        savejson(OUT/'qa/execution.json',{'status':'PASS','steps':steps,'elapsed_seconds':round(time.monotonic()-started,3),
            'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'network_used_in_this_run':args.acquire})
        outputs=[p for p in OUT.rglob('*') if p.is_file() and p.name!='output_manifest.csv']
        outputs+=[ROOT/'scripts'/name for name in ('phase3_common.py','acquire_phase3.py','build_phase3.py','validate_phase3.py','report_phase3.py','run_phase3.py')]
        outputs+=list((ROOT/'phase3/tests').glob('*.py'))
        outputs.append(ROOT/'phase3/requirements.txt')
        write(OUT/'qa/output_manifest.csv',fingerprint(outputs));manifest_check(OUT/'qa/output_manifest.csv')
        print('Restart 6 Phase 3 PASS',flush=True)
    except Exception as exc:
        savejson(OUT/'qa/phase3_status.json',{**status,'phase_3':'INCOMPLETE','error':str(exc),'completed_steps':steps})
        raise

if __name__=='__main__':main()
