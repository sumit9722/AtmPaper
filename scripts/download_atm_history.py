"""Prepare and download public DFS historical CSV exports; does not edit DFS data."""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'data/raw/atm_history'
BASE='https://data.ny.gov/api/archival'

def fetch(entry):
    date=entry['created_at'][:10]
    version=entry.get('version',entry.get('archive',{}).get('data_version'))
    p=OUT/f'dfs_{date}_v{version}.csv'
    if p.exists():return
    params={'id':'ndex-ad5r','version':version,'method':'status'}
    r=requests.get(BASE,params=params,timeout=90);r.raise_for_status();status=r.json()
    if status['type']!='done':
        r=requests.put(BASE,params={**params,'method':'createArchive'},timeout=90);r.raise_for_status()
        (OUT/f'prepare_v{version}.json').write_text(r.text)
    for _ in range(90):
        r=requests.get(BASE,params=params,timeout=90);r.raise_for_status();status=r.json()
        if status['type']=='done':break
        if status['type'] in ['failed','error']:raise RuntimeError(status)
        time.sleep(5)
    else:raise RuntimeError(f'Archive {version} still preparing')
    r=requests.get(BASE+'.csv',params={**params,'method':'export'},timeout=180);r.raise_for_status()
    if not any(header in r.text[:1000] for header in ['Name of Institution','name_of_institution']):raise RuntimeError(f'Unexpected CSV header: {r.text[:200]}')
    p.write_bytes(r.content)
    p.with_suffix('.csv.request.json').write_text(json.dumps({'url':r.url,'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'sha256':hashlib.sha256(r.content).hexdigest(),'snapshot_date':date,'version':version,'raw_modified':False},indent=2))
    print('Downloaded',p.name,len(r.content),'bytes',flush=True)

def main():
    history=json.loads((OUT/'history_index.json').read_text())
    entries=[r['value'] for r in history['resource'] if '2024-12-01'<=r['value']['created_at'][:10]<'2026-02-01']
    assert len(entries)==14,len(entries)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(fetch,e) for e in entries]
        for f in concurrent.futures.as_completed(futures):f.result()

if __name__=='__main__':main()
