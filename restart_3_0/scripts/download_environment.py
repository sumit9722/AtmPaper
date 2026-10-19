"""Acquire fixed-vintage housing context; never save credentials or credential URLs."""
import argparse,datetime as dt,getpass,hashlib,json,os,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw/environment_acs2022';BASE='https://api.census.gov/data/2022/acs/acs5'
GROUPS=['B25002','B25003','B25024','B25014','B25044','B25064','B25035','B25038']
COUNTIES=['005','047','061','081','085','029','055']
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['metadata','data'],required=True);parser.add_argument('--public',action='store_true');args=parser.parse_args()
 RAW.mkdir(parents=True,exist_ok=True);key=None
 if args.stage=='data' and not args.public:
  key=os.environ.get('CENSUS_API_KEY') or getpass.getpass('Census API key (hidden; not saved): ')
  if not key.strip():raise RuntimeError('Missing Census credential')
 calls=0
 def get(name,endpoint,params):
  nonlocal calls
  p=RAW/name;side=p.with_suffix('.request.json')
  if p.exists() and side.exists():
   assert hashlib.sha256(p.read_bytes()).hexdigest()==json.loads(side.read_text())['sha256'];return json.loads(p.read_text())
  if calls>=80:raise RuntimeError('Request cap reached; stop and inspect')
  if calls:time.sleep(2)
  calls+=1;query=dict(params)
  if key:query['key']=key
  try:r=requests.get(endpoint,params=query,timeout=(20,120),allow_redirects=False)
  except requests.RequestException:raise RuntimeError('Network request failed; endpoint/response suppressed to protect credentials') from None
  if r.status_code in [301,302,303,307,308] and not key:
   from urllib.parse import urlsplit
   dest=urlsplit(r.headers.get('Location',''));print('Public endpoint redirect:',dest.hostname,dest.path,flush=True)
  if r.status_code!=200:raise RuntimeError(f'HTTP {r.status_code}; response suppressed')
  try:data=r.json()
  except ValueError:raise RuntimeError('Non-JSON response; response suppressed') from None
  if key and key.encode() in r.content:raise RuntimeError('Credential found in response; refusing persistence')
  if args.stage=='metadata':assert isinstance(data,dict) and 'variables' in data
  else:assert isinstance(data,list) and len(data)>1 and 'block group' in data[0]
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.content)
  side.write_text(json.dumps({'endpoint':endpoint,'params':params,'authenticated':bool(key),'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':hashlib.sha256(r.content).hexdigest()},indent=2)+'\n')
  print('Saved',name,flush=True);return data
 if args.stage=='metadata':
  for group in GROUPS:get('metadata/'+group+'.json',BASE+'/groups/'+group+'.json',{})
 else:
  spec=json.loads((ROOT/'protocol/environment_variables.json').read_text());variables=sorted({v+suffix for f in spec['features'] for v in f['components'] for suffix in ['E','M','EA','MA']})
  for county in COUNTIES:
   for k,start in enumerate(range(0,len(variables),48)):
    get(f'attributes/county_{county}_chunk{k}.json',BASE,{'get':','.join(['NAME']+variables[start:start+48]),'for':'block group:*','in':f'state:36 county:{county} tract:*'})
 print('Requests this run:',calls,flush=True)
if __name__=='__main__':
 try:main()
 except (RuntimeError,AssertionError) as e:raise SystemExit(str(e) or 'Source validation failed') from None
