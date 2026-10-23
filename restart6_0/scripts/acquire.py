"""Cached downloads for restart 6; historical OSM v2 requires a HeiGIT key.

Run once with network access. Rebuilds use the verified local cache.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from common import RAW, REPORTS, PROJECT, savejson, sha

SOURCES = {
    'chicago': ('data.cityofchicago.org', 'ijzp-q8t2', 'date',
                "primary_type in ('ROBBERY','BURGLARY')",
                'id,case_number,date,block,iucr,primary_type,description,location_description,updated_on,latitude,longitude'),
    'la_legacy': ('data.lacity.org', '2nrs-mtv8', 'date_occ',
                  "crm_cd in ('210','220','310','320')",
                  'dr_no,date_rptd,date_occ,time_occ,crm_cd,crm_cd_desc,premis_cd,premis_desc,location,lat,lon'),
    'la_nibrs': ('data.lacity.org', 'k7nn-b2ep', 'date_occ',
                 "nibr_code in ('120','220')",
                 'caseno,uniquenibrno,date_rptd,date_occ,time_occ,nibr_code,nibr_description,premis_cd,premis_desc,hndrdth_loc_chk,hndrdth_lat,hndrdth_lon'),
}

def get(name, url, params=None):
    path = RAW / name
    side = Path(str(path) + '.request.json')
    params = params or {}
    if path.exists() and side.exists():
        meta = json.loads(side.read_text())
        if sha(path) != meta['sha256'] or meta['url'] != url or meta['params'] != params:
            raise RuntimeError(f'Cache/provenance mismatch: {path}')
        return json.loads(path.read_text())
    for attempt in range(3):
        response = requests.get(url, params=params, timeout=(20, 240))
        if response.status_code in (429, 502, 503, 504) and attempt < 2:
            time.sleep(2 ** attempt)
            continue
        if not response.ok:
            savejson(REPORTS/'last_acquisition_error.json', {'source': name, 'http_status': response.status_code,
                'response': response.text[:2000], 'url': url, 'params': params})
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and ('error' in data or data.get('exceededTransferLimit')):
            raise RuntimeError(f'Incomplete/error response: {name}: {str(data)[:300]}')
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(path) + '.partial')
        tmp.write_bytes(response.content)
        tmp.replace(path)
        savejson(side, {'url': url, 'params': params, 'method': 'GET',
                        'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                        'http_status': response.status_code, 'sha256': sha(path), 'raw_modified': False})
        return data
    raise RuntimeError(name)

def crime(slug):
    host, dataset, datefield, condition, fields = SOURCES[slug]
    get(f'metadata/{slug}.json', f'https://{host}/api/views/{dataset}.json')
    url = f'https://{host}/resource/{dataset}.json'
    results = []
    for year in range(2022, 2026):
        where = f"{datefield}>='{year}-01-01T00:00:00' AND {datefield}<'{year+1}-01-01T00:00:00' AND ({condition})"
        folder = f'crime/{slug}/{year}'
        query = {'$select': 'count(*)', '$where': where}
        before = int(get(folder+'/count_before.json', url, query)[0]['count'])
        seen = set()
        for offset in range(0, before, 10000):
            rows = get(folder+f'/page_{offset:07d}.json', url, {
                '$select': ':id as source_row_id,'+fields, '$where': where,
                '$order': ':id', '$limit': 10000, '$offset': offset})
            ids = [r['source_row_id'] for r in rows]
            if len(rows) != min(10000, before-offset) or len(ids) != len(set(ids)) or seen.intersection(ids):
                raise RuntimeError(f'Pagination mismatch: {slug}/{year}/{offset}')
            seen.update(ids)
        after = int(get(folder+'/count_after.json', url, query)[0]['count'])
        if before != after or before != len(seen):
            raise RuntimeError(f'Source changed during download: {slug}/{year}')
        results.append({'source': slug, 'year': year, 'rows': before, 'unique_source_rows': len(seen),
                        'count_after': after, 'status': 'PASS'})
        print(slug, year, before, 'reconciled', flush=True)
    return results

def boundaries():
    data = get('boundaries/cities.geojson',
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query',
        {'where': "GEOID IN ('3651000','1714000','0644000')", 'outFields': '*',
         'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'})
    if {f['properties']['GEOID'] for f in data['features']} != {'3651000','1714000','0644000'}:
        raise RuntimeError('Expected exactly NYC, Chicago and Los Angeles polygons')
    return [{'source': 'boundaries', 'status': 'PASS', 'cities': 3}]

def osm():
    from shapely.geometry import shape
    meta = get('metadata/ohsome.json', 'https://api.ohsome.org/v1/metadata')
    if meta['extractRegion']['temporalExtent']['toTimestamp'] < '2026-01-15':
        raise RuntimeError('OSM history does not reach final required snapshot')
    # Match the already recovered Restart 5 dates exactly; no invented observations.
    dates = [p.name[4:14] for p in sorted((PROJECT/'restart5_0/data/raw/atm_history').glob('dfs_*.csv'))]
    assert len(dates) == 36 and dates[0] == '2023-02-22' and dates[-1] == '2026-01-15'
    polygons = json.loads((RAW/'boundaries/cities.geojson').read_text())
    slugs = {'New York': 'nyc', 'Chicago': 'chicago', 'Los Angeles': 'la'}
    results = []
    for feature in polygons['features']:
        slug = slugs[feature['properties']['BASENAME']]
        bounds = ','.join(str(v) for v in shape(feature['geometry']).bounds)
        for year in range(2023, 2027):
            selected = [d+'T00:00:00Z' for d in dates if d.startswith(str(year))]
            if not selected:
                continue
            data = get(f'osm/{slug}/{year}.geojson', 'https://api.ohsome.org/v1/elements/centroid',
                {'bboxes': bounds, 'time': ','.join(selected),
                 'filter': 'amenity=atm or (amenity=bank and atm=yes)',
                 'properties': 'tags,metadata', 'clipGeometry': 'false'})
            if data.get('type') != 'FeatureCollection':
                raise RuntimeError(f'Unexpected OSM response: {slug}/{year}')
            results.append({'source': 'osm_'+slug, 'year': year, 'snapshots_requested': len(selected),
                            'features': len(data['features']), 'status': 'PASS'})
            print('OSM', slug, year, len(data['features']), flush=True)
    savejson(RAW/'osm/snapshot_dates.json', dates)
    return results

def osm_v2():
    """Single-snapshot Parquet extraction; keep authentication solely in headers."""
    from shapely.geometry import shape
    import pyarrow.parquet as pq
    from io import BytesIO
    dates = json.loads((RAW/'inherited/snapshot_dates.json').read_text())
    features = json.loads((RAW/'boundaries/cities.geojson').read_text())['features']
    slugs = {'New York':'nyc','Chicago':'chicago','Los Angeles':'la'}
    url = 'https://api.heigit.org/ohsome-api/v2/extraction/features.parquet'
    key = os.environ.get('OHSOME_API_KEY', '').strip()
    results = []
    for feature in features:
        slug = slugs[feature['properties']['BASENAME']]
        bounds = ','.join(str(v) for v in shape(feature['geometry']).bounds)
        for date in dates:
            path = RAW/f'osm_v2/{slug}/{date}.parquet'
            side = Path(str(path)+'.request.json')
            params = {'aoi':bounds,'time':date+'T00:00:00Z',
                      'filter':'amenity=atm or (amenity=bank and atm=yes)','clip':'false'}
            if path.exists() and side.exists():
                meta = json.loads(side.read_text())
                if sha(path)!=meta['sha256'] or meta['params']!=params or meta['url']!=url:
                    raise RuntimeError(f'OSM cache mismatch: {slug}/{date}')
                count = pq.read_metadata(path).num_rows
            else:
                if not key:
                    raise RuntimeError('OHSOME_API_KEY is required for uncached historical ATM downloads. Configure it in the invoking environment; never put it in source or command arguments.')
                try:
                    response = requests.get(url,params=params,headers={'Authorization':key,
                        'User-Agent':'atmSop2-restart6/1.0 (academic ATM geography study)'},timeout=(20,260))
                except requests.RequestException:
                    raise RuntimeError(f'OSM v2 network failure at {slug}/{date}; cached files preserved') from None
                if response.status_code != 200:
                    # Never persist headers, response bodies, or credential-bearing exceptions.
                    savejson(REPORTS/'osm_v2_error.json',{'city':slug,'date':date,'http_status':response.status_code})
                    raise RuntimeError(f'OSM v2 HTTP {response.status_code} at {slug}/{date}; check account quota/key; cached files preserved')
                data = pq.read_table(BytesIO(response.content))
                required={'osm_type','osm_id','tags','geom','edit_timestamp','valid_to_timestamp'}
                if not required <= set(data.column_names):
                    raise RuntimeError('OSM v2 extraction schema mismatch')
                path.parent.mkdir(parents=True,exist_ok=True)
                tmp=Path(str(path)+'.partial');tmp.write_bytes(response.content);tmp.replace(path)
                count=data.num_rows
                savejson(side,{'url':url,'params':params,'method':'GET','http_status':200,
                    'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'sha256':sha(path),
                    'raw_modified':False,'authentication':'Authorization header; value not retained'})
                # Basic plan: at most 15 requests in every sliding 60-second window.
                time.sleep(4.2)
            results.append({'source':'osm_v2_'+slug,'date':date,'features':count,'status':'PASS'})
            print('OSM v2',slug,date,count,flush=True)
    savejson(RAW/'osm/snapshot_dates.json',dates)
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['all', 'crime', 'boundaries', 'osm', 'osm-v1', 'probe'], default='all')
    parser.add_argument('--key-stdin', action='store_true', help='Read the API key from stdin without echoing or saving it')
    args = parser.parse_args()
    if args.key_stdin:
        import getpass
        os.environ['OHSOME_API_KEY'] = (getpass.getpass('HeiGIT key (hidden): ') if sys.stdin.isatty() else sys.stdin.readline()).strip()
    if args.stage == 'probe':
        probes = [
            ('GET', 'https://api.ohsome.org/v1/elements/geometry', {'bboxes':'-87.64,41.87,-87.62,41.89','time':'2024-01-15','filter':'amenity=atm','properties':'tags,metadata'}),
            ('POST', 'https://api.ohsome.org/v1/elements/centroid', {'bboxes':'-87.64,41.87,-87.62,41.89','time':'2024-01-15','filter':'amenity=atm','properties':'tags,metadata'}),
            ('GET', 'https://api.ohsome.org/v1/elements/count', {'bboxes':'-87.64,41.87,-87.62,41.89','time':'2024-01-15','filter':'amenity=atm'}),
            ('GET', 'https://overpass-api.de/api/interpreter', {'data':'[out:json][timeout:60][date:"2024-01-15T00:00:00Z"];nwr[amenity=atm](41.87,-87.64,41.89,-87.62);out geom;'}),
            ('GET', 'https://overpass.kumi.systems/api/interpreter', {'data':'[out:json][timeout:60][date:"2024-01-15T00:00:00Z"];nwr[amenity=atm](41.87,-87.64,41.89,-87.62);out geom;'})]
        results=[]
        for method,url,params in probes:
            try:
                response=requests.request(method,url,params=params if method=='GET' else None,data=params if method=='POST' else None,timeout=(20,90))
                result={'method':method,'url':url,'status':response.status_code,'body':response.text[:1500]}
            except requests.RequestException as exc:
                result={'method':method,'url':url,'error':str(exc)}
            results.append(result)
            print(result,flush=True)
        savejson(REPORTS/'source_probes.json',results)
        return
    results, errors = [], []
    if args.stage in ('all', 'boundaries'):
        results += boundaries()
    if args.stage in ('all', 'crime'):
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs = {pool.submit(crime, slug): slug for slug in SOURCES}
            for future in as_completed(jobs):
                try:
                    results += future.result()
                except Exception as exc:
                    errors.append({'source': jobs[future], 'error': str(exc)})
    if args.stage in ('all', 'osm', 'osm-v1'):
        try:
            results += osm() if args.stage=='osm-v1' else osm_v2()
        except Exception as exc:
            errors.append({'source': 'osm', 'error': str(exc)})
    savejson(REPORTS/f'acquisition_{args.stage}.json', {'status': 'PASS' if not errors else 'INCOMPLETE',
        'partitions': results, 'errors': errors, 'credentials_used': args.stage in ('all','osm') and bool(os.environ.get('OHSOME_API_KEY'))})
    if errors:
        raise RuntimeError(errors)

if __name__ == '__main__':
    main()
