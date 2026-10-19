"""Resumable official 2015–2025 acquisition, with raw-byte hashes and reconciliation.

Only crime and metadata GET requests; independent city tasks use three threads.
No private credentials or record modification. Reuse verified files on rerun.
"""
import concurrent.futures,csv,datetime as dt,hashlib,json,time
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1];RAW=ROOT/'data/raw'
NYC_FIELDS=':id as source_row_id,cmplnt_num,cmplnt_fr_dt,cmplnt_fr_tm,cmplnt_to_dt,rpt_dt,ky_cd,ofns_desc,pd_cd,pd_desc,crm_atpt_cptd_cd,law_cat_cd,boro_nm,loc_of_occur_desc,prem_typ_desc,juris_desc,latitude,longitude'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def get(name,url,params):
 p=RAW/name;side=Path(str(p)+'.request.json')
 if p.exists() and side.exists():
  assert sha(p)==json.loads(side.read_text())['sha256'],p
  return json.loads(p.read_text())
 for attempt in range(4):
  try:
   r=requests.get(url,params=params,timeout=(20,180));r.raise_for_status();data=r.json()
   if isinstance(data,dict) and ('error' in data or data.get('exceededTransferLimit')):raise ValueError(str(data)[:500])
   break
  except (requests.RequestException,ValueError):
   if attempt==3:raise
   time.sleep(2**attempt)
 p.parent.mkdir(parents=True,exist_ok=True);tmp=Path(str(p)+'.partial');tmp.write_bytes(r.content);tmp.replace(p)
 side.write_text(json.dumps({'url':url,'params':params,'resolved_url':r.url,'method':'GET','http_status':r.status_code,'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':sha(p),'raw_modified':False},indent=2)+'\n')
 return data

def socrata(slug):
 nyc=slug=='nyc';url='https://'+('data.cityofnewyork.us/resource/qgea-i56i.json' if nyc else 'data.buffalony.gov/resource/d6g9-xbgu.json');field='cmplnt_fr_dt' if nyc else 'incident_datetime'
 result=[]
 metadata=get(f'metadata/{slug}.json',url.split('/resource/')[0]+'/api/views/'+('qgea-i56i' if nyc else 'd6g9-xbgu')+'.json',{})
 buffalo_fields=':id as source_row_id,'+','.join(c['fieldName'] for c in metadata['columns'] if not c['fieldName'].startswith(':'))
 for year in range(2015,2026):
  where=f"{field} >= '{year}-01-01T00:00:00' AND {field} < '{year+1}-01-01T00:00:00'"
  if nyc:where+=" AND ofns_desc IN ('ROBBERY','BURGLARY')"
  folder=f'crime/{slug}/{year}';expected=int(get(folder+'/count_before.json',url,{'$select':'count(*)','$where':where})[0]['count']);seen=set();total=0
  for offset in range(0,expected,10000):
   params={'$where':where,'$limit':10000,'$offset':offset,'$order':':id','$select':NYC_FIELDS if nyc else buffalo_fields}
   rows=get(folder+f'/page_{offset:07d}.json',url,params)
   assert len(rows)==min(10000,expected-offset),(slug,year,len(rows),expected)
   ids=[str(r['source_row_id']) for r in rows];assert len(ids)==len(set(ids)) and not seen.intersection(ids),(slug,year,'source row duplication')
   seen.update(ids);total+=len(rows)
  after=int(get(folder+'/count_after.json',url,{'$select':'count(*)','$where':where})[0]['count']);assert expected==after==total,(slug,year,expected,after,total)
  result.append({'city_slug':slug,'year':year,'api_rows':expected,'downloaded_rows':total,'unique_source_rows':len(seen),'count_after':after,'status':'PASS','scope':'robbery_burglary' if nyc else 'all_published_categories'})
  print(slug,year,total,'reconciled',flush=True)
 return result

def rochester():
 slug='rochester';url='https://gis.cityofrochester.gov/arcgis/rest/services/RPD/RPD_Part_I_Crime/MapServer/3/query';result=[]
 get('metadata/rochester.json',url.removesuffix('/query'),{'f':'json'})
 for year in range(2015,2026):
  where=f'OccurredFrom_Date_Year={year}';folder=f'crime/{slug}/{year}'
  ids=sorted(get(folder+'/object_ids_before.json',url,{'where':where,'returnIdsOnly':'true','f':'json'})['objectIds']);seen=set();total=0
  assert len(ids)==len(set(ids))
  for offset in range(0,len(ids),1000):
   batch=ids[offset:offset+1000];data=get(folder+f'/page_{offset:07d}.json',url,{'objectIds':','.join(map(str,batch)),'outFields':'*','returnGeometry':'true','outSR':4326,'f':'json'})
   rows=data['features'];actual=[r['attributes']['OBJECTID'] for r in rows]
   assert len(actual)==len(set(actual)) and set(actual)==set(batch) and not seen.intersection(actual),(slug,year,offset)
   seen.update(actual);total+=len(rows)
  after=sorted(get(folder+'/object_ids_after.json',url,{'where':where,'returnIdsOnly':'true','f':'json'})['objectIds']);assert ids==after and set(ids)==seen
  result.append({'city_slug':slug,'year':year,'api_rows':len(ids),'downloaded_rows':total,'unique_source_rows':len(seen),'count_after':len(after),'status':'PASS','scope':'all_published_Part_I_categories'})
  print(slug,year,total,'reconciled',flush=True)
 return result

def main():
 results=[];errors=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  jobs={pool.submit(socrata,s):s for s in ['nyc','buffalo']};jobs[pool.submit(rochester)]='rochester'
  for future in concurrent.futures.as_completed(jobs):
   try:results+=future.result()
   except Exception as e:errors.append({'source':jobs[future],'error':str(e)});print('FAILED',jobs[future],repr(e),flush=True)
 late=[]
 try:
  url='https://data.cityofnewyork.us/resource/5uac-w243.json'
  get('metadata/nyc_current.json','https://data.cityofnewyork.us/api/views/5uac-w243.json',{})
  for year in range(2022,2026):
   where=f"cmplnt_fr_dt >= '{year}-01-01T00:00:00' AND cmplnt_fr_dt < '{year+1}-01-01T00:00:00' AND ofns_desc IN ('ROBBERY','BURGLARY')"
   folder=f'crime/nyc/{year}/late_current';expected=int(get(folder+'/count_before.json',url,{'$select':'count(*)','$where':where})[0]['count']);seen=set()
   for offset in range(0,expected,10000):
    rows=get(folder+f'/page_{offset:07d}.json',url,{'$where':where,'$limit':10000,'$offset':offset,'$order':':id','$select':NYC_FIELDS})
    ids=[r['source_row_id'] for r in rows];assert len(ids)==len(set(ids)) and not seen.intersection(ids);seen.update(ids)
   after=int(get(folder+'/count_after.json',url,{'$select':'count(*)','$where':where})[0]['count']);assert expected==after==len(seen)
   late.append({'city_slug':'nyc','year':year,'source':'current_year_late_report_supplement','downloaded_rows':len(seen),'status':'PASS'})
   print('NYC late-report supplement',year,len(seen),flush=True)
 except Exception as e:errors.append({'source':'nyc_current_late_reports','error':str(e)})
 report={'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'status':'PASS' if not errors and len(results)==33 and len(late)==4 else 'INCOMPLETE','partitions':sorted(results,key=lambda x:(x['city_slug'],x['year'])),'late_report_supplements':late,'errors':errors,'limitation':'Counts and IDs checked before/after acquisition; live source revisions within a partition remain possible. Not an as-of historical database.'}
 (ROOT/'reports/acquisition.json').write_text(json.dumps(report,indent=2)+'\n')
 if errors:raise RuntimeError(errors)
if __name__=='__main__':main()
