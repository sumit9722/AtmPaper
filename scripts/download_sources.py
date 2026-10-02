"""Download immutable, paginated official source extracts for phases 1 and 2."""
import concurrent.futures
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw'
RAW.mkdir(parents=True, exist_ok=True)

def get(name, url, params=None):
    path = RAW / name
    if path.exists() and path.with_suffix(path.suffix+'.request.json').exists():
        return json.loads(path.read_text())
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=180)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and 'error' in data:
                raise RuntimeError(data['error'])
            break
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(r.content)
    path.with_suffix(path.suffix+'.request.json').write_text(json.dumps({
        'url': r.url, 'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'sha256': hashlib.sha256(r.content).hexdigest(), 'http_status': r.status_code,
        'raw_modified': False}, indent=2))
    return data

def socrata(name, domain, dataset, datefield=None, predicate=None, fields=None):
    url = f'https://{domain}/resource/{dataset}.json'
    where = f"{datefield} >= '2024-01-01T00:00:00' AND {datefield} < '2026-01-01T00:00:00'" if datefield else '1=1'
    if predicate:
        where += ' AND ('+predicate+')'
    count = int(get(f'{name}/count.json', url, {'$select':'count(*)', '$where':where})[0]['count'])
    downloaded = 0
    for offset in range(0, count, 20000):
        params = {'$where':where, '$limit':20000, '$offset':offset, '$order':':id'}
        if fields:
            params['$select'] = fields
        rows = get(f'{name}/page_{offset:07d}.json', url, params)
        downloaded += len(rows)
        print(name, downloaded, '/', count, flush=True)
    assert downloaded == count, (name, downloaded, count)

def boundaries():
    d = get('boundaries/cities.geojson', 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query',
        {'where':"STATE='36' AND PLACE IN ('51000','11000','63000')", 'outFields':'*', 'returnGeometry':'true', 'outSR':4326, 'f':'geojson'})
    assert len(d['features']) == 3
    print('boundaries', [x['properties']['NAME'] for x in d['features']], flush=True)

def rochester():
    url='https://gis.cityofrochester.gov/arcgis/rest/services/RPD/RPD_Part_I_Crime/MapServer/3/query'
    where='OccurredFrom_Date_Year IN (2024,2025)'
    ids = get('rochester/object_ids.json', url, {'where':where, 'returnIdsOnly':'true','f':'json'})['objectIds']
    downloaded=0
    for offset in range(0,len(ids),1000):
        rows=get(f'rochester/page_{offset:07d}.json', url, {'objectIds':','.join(map(str,sorted(ids)[offset:offset+1000])), 'outFields':'*','returnGeometry':'true','outSR':4326,'f':'json'})
        assert not rows.get('exceededTransferLimit')
        downloaded+=len(rows['features'])
        print('rochester',downloaded,'/',len(ids),flush=True)
    assert downloaded == len(ids)

def nyc_monthly():
    """Bound the date range per request to avoid expensive deep-offset timeouts."""
    url='https://data.cityofnewyork.us/resource/qgea-i56i.json'
    fields='cmplnt_num,cmplnt_fr_dt,cmplnt_fr_tm,cmplnt_to_dt,rpt_dt,ky_cd,ofns_desc,pd_cd,pd_desc,crm_atpt_cptd_cd,law_cat_cd,boro_nm,loc_of_occur_desc,prem_typ_desc,juris_desc,latitude,longitude'
    total_where="cmplnt_fr_dt >= '2024-01-01T00:00:00' AND cmplnt_fr_dt < '2026-01-01T00:00:00' AND ofns_desc IN ('ROBBERY','BURGLARY','GRAND LARCENY','PETIT LARCENY')"
    expected=int(get('nyc/count.json',url,{'$select':'count(*)','$where':total_where})[0]['count'])
    # Preserve the first incomplete offset attempt separately, never combine it with the monthly extract.
    for p in (RAW/'nyc').glob('page_[0-9]*'):
        dest=RAW/'nyc/initial_offset_attempt'/p.name
        dest.parent.mkdir(exist_ok=True)
        if not dest.exists():p.rename(dest)
    def month(year,month):
        start=f'{year}-{month:02d}-01T00:00:00'
        end=f'{year+1}-01-01T00:00:00' if month==12 else f'{year}-{month+1:02d}-01T00:00:00'
        where=f"cmplnt_fr_dt >= '{start}' AND cmplnt_fr_dt < '{end}' AND ofns_desc IN ('ROBBERY','BURGLARY','GRAND LARCENY','PETIT LARCENY')"
        count=int(get(f'nyc/count_{year}_{month:02d}.json',url,{'$select':'count(*)','$where':where})[0]['count'])
        assert count<50000,'Use additional pagination for a month with >=50000 records'
        rows=get(f'nyc/page_month_{year}_{month:02d}.json',url,{'$where':where,'$limit':count+1,'$select':fields})
        assert len(rows)==count,(year,month,len(rows),count)
        print('nyc',year,month,len(rows),flush=True)
        return len(rows)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(month,y,m) for y in [2024,2025] for m in range(1,13)]
        total=sum(f.result() for f in concurrent.futures.as_completed(futures))
    assert total==expected,(total,expected)

def main():
    jobs = [
        (boundaries, ()),
        (socrata, ('dfs','data.ny.gov','ndex-ad5r')),
        (nyc_monthly, ()),
        (socrata, ('buffalo','data.buffalony.gov','d6g9-xbgu','incident_datetime')),
        (rochester, ())]
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(fn,*args):fn.__name__+str(args[:1]) for fn,args in jobs}
        for future in concurrent.futures.as_completed(futures):
            try:future.result()
            except Exception as exc:errors.append((futures[future],str(exc)))
    if errors:raise RuntimeError(errors)

if __name__ == '__main__':main()
