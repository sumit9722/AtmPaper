"""Recover indexed 2023 ATM archives; refuse silently substituted versions."""
import datetime as dt,hashlib,json,time
from pathlib import Path
import requests
from common import ROOT,RAW,savejson,sha
from acquire import get

def main():
 index=json.loads((RAW/'atm_history/history_index_inherited.json').read_text());base='https://data.ny.gov/api/archival'
 entries=[r['value'] for r in index['resource'] if '2023-01-01'<=r['value']['created_at'][:10]<'2023-12-01']
 results=[]
 for e in sorted(entries,key=lambda r:r['created_at']):
  version=e.get('version',e.get('archive',{}).get('data_version'));date=e['created_at'][:10];p=RAW/f'atm_history/dfs_{date}_v{version}.csv';side=Path(str(p)+'.request.json');params={'id':'ndex-ad5r','version':version,'method':'status'}
  if p.exists() and side.exists():assert sha(p)==json.loads(side.read_text())['sha256'];continue
  status=get(f'atm_history/status_{version}_initial.json',base,params)
  if status.get('value',{}).get('version',version)!=version:raise RuntimeError(f'Requested {version}, server substituted {status}')
  if status['type']!='done':
   # This requests a downloadable public archive, not a change to source data.
   r=requests.put(base,params={**params,'method':'createArchive'},timeout=(20,90));r.raise_for_status();q=RAW/f'atm_history/prepare_{version}.json';q.write_bytes(r.content);savejson(Path(str(q)+'.request.json'),{'url':r.url,'method':'PUT_create_public_export','retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':sha(q)})
   for attempt in range(24):
    time.sleep(3);r=requests.get(base,params=params,timeout=(20,90));r.raise_for_status();status=r.json()
    q=RAW/f'atm_history/status_{version}_{attempt:02d}.json';q.write_bytes(r.content);savejson(Path(str(q)+'.request.json'),{'url':r.url,'method':'GET','retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':sha(q)})
    if status['type']=='done':break
    if status['type'] in ['error','failed']:raise RuntimeError(status)
   else:raise RuntimeError(f'Archive {version} still preparing; rerun after source finishes')
  if status.get('value',{}).get('version',version)!=version:raise RuntimeError(f'Wrong returned version: {status}')
  r=requests.get(base+'.csv',params={**params,'method':'export'},timeout=(20,180));r.raise_for_status();assert b'institution' in r.content[:1000].lower()
  p.write_bytes(r.content);savejson(side,{'url':r.url,'method':'GET','retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':sha(p),'snapshot_date':date,'requested_version':version,'verified_status':status,'raw_modified':False})
  print('ATM',date,version,len(r.content),'bytes',flush=True)
 print('Indexed 2023 recovery complete',len(entries),flush=True)
 captures=json.loads((RAW/'discovery/wayback_dfs_csv.json').read_text())
 for record in captures[1:]:
  item=dict(zip(captures[0],record));stamp=item['timestamp'];p=RAW/f'atm_supplemental/wayback_{stamp}.csv';side=Path(str(p)+'.request.json')
  if p.exists() and side.exists():assert sha(p)==json.loads(side.read_text())['sha256'];continue
  url=f"https://web.archive.org/web/{stamp}id_/{item['original']}"
  try:
   r=requests.get(url,timeout=(20,180));r.raise_for_status();assert b'institution' in r.content[:2000].lower(), 'Not an ATM CSV'
   p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.content)
   savejson(side,{'url':url,'resolved_url':r.url,'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':sha(p),'archive_capture_timestamp':stamp,'capture_is_not_verified_DFS_publication_date':True,'use':'isolated_supplemental_observation_not_continuous_exposure'})
   print('Supplemental capture',stamp,len(r.content),flush=True)
  except (requests.RequestException,AssertionError) as e:
   savejson(ROOT/f'reports/wayback_{stamp}_failure.json',{'url':url,'error':str(e),'status':'not_recovered'});print('Supplemental capture unavailable',stamp,str(e),flush=True)
if __name__=='__main__':main()
