"""One-command offline restart 6 rebuild, or resumable acquisition with --acquire."""
import argparse
import datetime as dt
import json
import subprocess
import sys
import time
from common import *

def freeze_sources():
    paths=sorted(p for p in RAW.rglob('*') if p.is_file() and not p.name.endswith('.partial'))
    manifest=OUT/'source_manifest.csv'
    if manifest.exists():
        saved={r['file']:r for r in read(manifest)}
        assert set(saved)=={str(p.relative_to(ROOT)) for p in paths}, 'Raw source file set changed; review before a new release'
        for name,r in saved.items():
            assert sha(ROOT/name)==r['sha256'], name
        return
    for p in paths:
        side=Path(str(p)+'.request.json')
        if side.exists():
            assert sha(p)==json.loads(side.read_text())['sha256'], p
    for r in read(OUT/'inherited_sources.csv'):
        assert sha(ROOT/r['target_file'])==r['target_sha256']
    assert len(list((RAW/'osm_v2').rglob('*.parquet')))==108, 'Incomplete OSM acquisition; need 36 snapshots for each of three cities'
    write('source_manifest.csv',[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquire',action='store_true')
    parser.add_argument('--key-stdin',action='store_true',help='Use a hidden API key prompt during acquisition')
    args=parser.parse_args()
    def run(script, *arguments):
        print('Running',script,flush=True)
        subprocess.run([sys.executable,str(ROOT/'scripts'/script),*arguments],cwd=PROJECT,check=True)
    if args.acquire:
        if not (OUT/'inherited_sources.csv').exists():
            run('prepare_inputs.py')
        run('acquire.py','--stage','all',*(['--key-stdin'] if args.key_stdin else []))
    freeze()
    status={'release':'restart6_0','cities':list(CITIES),'phase_1':'REBUILDING','phase_2':'REBUILDING',
            'scientific_review':'PENDING','confirmatory_eligible':False,'models_fitted':False}
    savejson(REPORTS/'phase_status.json',status)
    started=time.monotonic();steps=[]
    try:
        freeze_sources()
        begin=time.monotonic()
        command=[sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v']
        regression=subprocess.run(command,cwd=PROJECT,capture_output=True,text=True)
        (REPORTS/'regression_tests.log').write_text(regression.stdout+regression.stderr)
        savejson(REPORTS/'regression_tests.json',{
            'status':'PASS' if regression.returncode==0 else 'FAIL',
            'command':'.venv/bin/python -m unittest discover -s restart6_0/tests -v',
            'exit_code':regression.returncode,
            'fixture_policy':'Synthetic data created in a temporary directory only; never included in research panels',
            'test_sha256':sha(ROOT/'tests/test_pipeline.py')})
        regression.check_returncode()
        steps.append({'script':'tests/test_pipeline.py','status':'PASS','elapsed_seconds':round(time.monotonic()-begin,3)})
        for script in ('build_exposure.py','build_crime.py','build_panel.py','build_monthly.py','validate.py','report.py'):
            begin=time.monotonic();run(script)
            steps.append({'script':script,'status':'PASS','elapsed_seconds':round(time.monotonic()-begin,3)})
        run('large_artifacts.py','split')
        savejson(REPORTS/'acquisition.json',{'status':'PASS','basis':'Frozen cache reconciled by validate.py',
            'osm_city_date_snapshots':108,'crime_new_source_year_partitions':12,
            'nyc_inputs':'Inherited and checksum verified',
            'earlier_attempt_logs':'acquisition_all.json and source_probes.json preserve historical failures; acquisition.json is the final validated status'})
        status.update(phase_1='COMPUTATION_COMPLETE',phase_2='COMPUTATION_COMPLETE',validation='PASS')
        savejson(REPORTS/'phase_status.json',status)
        savejson(REPORTS/'execution.json',{'status':'PASS','steps':steps,'elapsed_seconds':round(time.monotonic()-started,3),
            'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'network_used':args.acquire,'models_fitted':False})
        rows=[]
        for p in sorted(ROOT.rglob('*')):
            if not p.is_file() or 'raw' in p.relative_to(ROOT).parts or '__pycache__' in p.parts or p.name=='artifact_manifest.csv':
                continue
            if p.name=='apikey.txt' or p.name=='.env' or p.name.startswith('.env.'):
                continue
            if p.name in ('crime_primary_2022_2025.csv','event_atm_links.csv'):
                continue
            rows.append({'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)})
        with (REPORTS/'artifact_manifest.csv').open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['file','bytes','sha256']);writer.writeheader();writer.writerows(rows)
        print('Restart 6 offline build and validation PASS',flush=True)
    except Exception as exc:
        status.update(phase_1='INCOMPLETE',phase_2='BUILD_FAILED',error=str(exc),completed_steps=steps)
        savejson(REPORTS/'phase_status.json',status)
        raise

if __name__=='__main__':
    main()
