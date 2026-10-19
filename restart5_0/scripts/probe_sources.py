"""Read-only availability probes; preserve responses, including failures."""
import concurrent.futures,datetime,hashlib,json
from pathlib import Path
import requests
OUT=Path(__file__).resolve().parents[1]/'data/raw/discovery';OUT.mkdir(parents=True,exist_ok=True)
JOBS={
 'dfs_history':('https://data.ny.gov/api/publishing/v1/revision/ndex-ad5r/history',{}),
 'dfs_history_public':('https://data.ny.gov/api/publishing/v1/revision/ndex-ad5r/history/public',{}),
 'dfs_revisions':('https://data.ny.gov/api/publishing/v1/revision/ndex-ad5r',{}),
 'dfs_archives':('https://data.ny.gov/api/archival',{'id':'ndex-ad5r','method':'list'}),
 'dfs_version247':('https://data.ny.gov/api/archival',{'id':'ndex-ad5r','version':247,'method':'status'}),
 'dfs_version1':('https://data.ny.gov/api/archival',{'id':'ndex-ad5r','version':1,'method':'status'}),
 'dfs_version200':('https://data.ny.gov/api/archival',{'id':'ndex-ad5r','version':200,'method':'status'}),
 'dfs_revisions_all':('https://data.ny.gov/api/publishing/v1/revision/ndex-ad5r',{'limit':1000,'offset':0}),
 'dfs_history_index':('https://data.ny.gov/api/publishing/v1/revision/ndex-ad5r/history/lookup',{}),
 'wayback_dfs_csv':('https://web.archive.org/cdx/search/cdx',{'url':'data.ny.gov/api/views/ndex-ad5r/rows.csv*','output':'json','filter':'statuscode:200','collapse':'timestamp:6','from':'2015','to':'2023'}),
 'dfs_metadata':('https://data.ny.gov/api/views/ndex-ad5r.json',{}),
 'rochester_metadata':('https://gis.cityofrochester.gov/arcgis/rest/services/RPD/RPD_Part_I_Crime/MapServer/3',{'f':'json'}),
 'buffalo_years':('https://data.buffalony.gov/resource/d6g9-xbgu.json',{'$select':'date_extract_y(incident_datetime) as year, count(*) as n','$group':'year','$order':'year'}),
 'nyc_years':('https://data.cityofnewyork.us/resource/qgea-i56i.json',{'$select':'date_extract_y(cmplnt_fr_dt) as year, count(*) as n','$where':"cmplnt_fr_dt >= '2015-01-01T00:00:00' AND cmplnt_fr_dt < '2026-01-01T00:00:00' AND ofns_desc IN ('ROBBERY','BURGLARY')",'$group':'year','$order':'year'}),
}
def probe(job):
 name,(url,params)=job;p=OUT/(name+'.json')
 if p.exists():return name,json.loads((OUT/(name+'.json.request.json')).read_text()).get('status'),'cached'
 try:
  r=requests.get(url,params=params,timeout=(20,90));p.write_bytes(r.content)
  m={'url':r.url,'status':r.status_code,'retrieved_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(r.content).hexdigest()}
  (OUT/(name+'.json.request.json')).write_text(json.dumps(m,indent=2));return name,r.status_code,r.text[:160]
 except requests.RequestException as e:return name,'error',str(e)[:180]
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for result in pool.map(probe,JOBS.items()):print(result,flush=True)
