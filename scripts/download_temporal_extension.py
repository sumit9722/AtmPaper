"""Acquire limited cached official inputs for the 2024->2025 extension."""
import argparse,csv,datetime as dt,hashlib,json,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw/temporal_extension'
COUNTIES=['005','047','061','081','085','029','055']
class Download:
 def __init__(self):self.calls=0
 def get(self,name,url,params=None,binary=False,method='GET'):
  p=RAW/name;side=Path(str(p)+'.request.json')
  if p.exists() and side.exists():
   data=p.read_bytes();m=json.loads(side.read_text());assert hashlib.sha256(data).hexdigest()==m['sha256']
   return data if binary else json.loads(data)
  if self.calls>=140:raise RuntimeError('Request cap reached; resume from cache after checking progress')
  if self.calls:time.sleep(2)
  self.calls+=1
  try:
   r=requests.request(method,url,params=params,timeout=(20,180));r.raise_for_status()
  except requests.RequestException as e:raise RuntimeError(f'{name}: {type(e).__name__}; stopped without retry') from None
  data=r.content if binary else r.json()
  if not binary and isinstance(data,dict) and ('error' in data or data.get('exceededTransferLimit')):raise RuntimeError(str(data)[:300])
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(r.content)
  side.write_text(json.dumps({'url':url,'params':params or {},'method':method,'sha256':hashlib.sha256(r.content).hexdigest(),'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat()},indent=2)+'\n')
  print('Saved',name,len(r.content),'bytes',flush=True);return data

def history(d):
 h=json.loads((ROOT/'data/raw/atm_history/history_index.json').read_text())
 entries=[r['value'] for r in h['resource'] if '2023-12-01'<=r['value']['created_at'][:10]<'2024-12-01']
 assert len(entries)==12
 for e in sorted(entries,key=lambda e:e['created_at']):
  date=e['created_at'][:10];v=e['version'];name=f'atm_history/dfs_{date}_v{v}.csv'
  if (RAW/name).exists():continue
  url='https://data.ny.gov/api/archival';params={'id':'ndex-ad5r','version':v,'method':'status'}
  status=d.get(f'atm_history/status_v{v}_initial.json',url,params)
  if status['type']!='done':
   d.get(f'atm_history/prepare_v{v}.json',url,{**params,'method':'createArchive'},method='PUT')
   for attempt in range(15):
    status=d.get(f'atm_history/status_v{v}_{attempt:02d}.json',url,params)
    if status['type']=='done':break
    if status['type'] in ['error','failed']:raise RuntimeError(f'Archive {v} failed')
    time.sleep(5)
   else:raise RuntimeError(f'Archive {v} not ready; stop polling')
  content=d.get(name,url+'.csv',{**params,'method':'export'},binary=True)
  assert b'institution' in content[:1000].lower(),f'Invalid archive {v}'

def crime(d):
 specifications=[('nyc','https://data.cityofnewyork.us/resource/qgea-i56i.json',"cmplnt_fr_dt >= '2023-01-01T00:00:00' AND cmplnt_fr_dt < '2024-01-01T00:00:00' AND ofns_desc IN ('ROBBERY','BURGLARY')",'cmplnt_num,cmplnt_fr_dt,cmplnt_fr_tm,rpt_dt,ofns_desc,pd_cd,pd_desc,crm_atpt_cptd_cd,latitude,longitude'),
 ('buffalo','https://data.buffalony.gov/resource/d6g9-xbgu.json',"incident_datetime >= '2023-01-01T00:00:00' AND incident_datetime < '2024-01-01T00:00:00'",None)]
 for slug,url,where,fields in specifications:
  count=int(d.get(f'crime2023/{slug}/count.json',url,{'$select':'count(*)','$where':where})[0]['count'])
  total=0
  for offset in range(0,count,20000):
   params={'$where':where,'$limit':20000,'$offset':offset,'$order':':id'}
   if fields:params['$select']=fields
   total+=len(d.get(f'crime2023/{slug}/page_{offset:07d}.json',url,params))
  assert total==count
 url='https://gis.cityofrochester.gov/arcgis/rest/services/RPD/RPD_Part_I_Crime/MapServer/3/query'
 ids=d.get('crime2023/rochester/object_ids.json',url,{'where':'OccurredFrom_Date_Year=2023','returnIdsOnly':'true','f':'json'})['objectIds']
 total=0
 for offset in range(0,len(ids),1000):
  data=d.get(f'crime2023/rochester/page_{offset:07d}.json',url,{'objectIds':','.join(map(str,sorted(ids)[offset:offset+1000])),'outFields':'*','returnGeometry':'true','outSR':4326,'f':'json'})
  total+=len(data['features'])
 assert total==len(ids)

def geography(d):
 url='https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2022/MapServer/8'
 d.get('acs2022/layer.json',url,{'f':'json'})
 for c in COUNTIES:
  where=f"STATE='36' AND COUNTY='{c}'"
  count=d.get(f'acs2022/geo_{c}_count.json',url+'/query',{'where':where,'returnCountOnly':'true','f':'json'})['count']
  data=d.get(f'acs2022/geo_{c}.geojson',url+'/query',{'where':where,'outFields':'GEOID,STATE,COUNTY,AREALAND,AREAWATER','returnGeometry':'true','outSR':4326,'f':'geojson','resultRecordCount':5000})
  assert len(data['features'])==count

def acs():
 import download_census as census
 census.RAW=RAW/'acs2022/attributes';census.RAW.mkdir(parents=True,exist_ok=True)
 fetch=census.Fetcher();base='https://api.census.gov/data/2022/acs/acs5'
 for group in ['B01003','B19013','B23025']:fetch.get(group+'.json',base+'/groups/'+group+'.json')
 for c in COUNTIES:
  fetch.get('county_'+c+'.json',base,{'get':','.join(['NAME']+census.VARIABLES),'for':'block group:*','in':f'state:36 county:{c} tract:*'},authenticated=True)
 print('ACS requests this run:',fetch.calls,flush=True)

def tiger(d):
 d.get('acs2022/tl_2022_36_bg.zip','https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_36_bg.zip',binary=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['history','crime','geography','acs','tiger'],required=True);a=p.parse_args()
 if a.stage=='acs':acs()
 else:globals()[a.stage](Download())
if __name__=='__main__':main()
