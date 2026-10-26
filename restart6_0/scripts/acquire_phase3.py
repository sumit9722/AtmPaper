"""Resumable public Phase 3 downloads; no API credential is required."""
import argparse
import datetime as dt
import json
import time
import requests
from phase3_common import *

SLD='https://geodata.epa.gov/arcgis/rest/services/OA/SmartLocationDatabase/MapServer/1'
FIELDS='OBJECTID,GEOID20,STATEFP,COUNTYFP,D1C,D1C5_RET,D2B_E5MIXA,D3A,D3AAO,D3B,D4A,D4D,D5AR,D5BR'
BASE='https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/5YRData/'

def get(path,url,params=None,binary=False,source_side=False):
    side=Path(str(path)+('.source.json' if source_side else '.request.json'))
    params=params or {}
    if path.exists() and side.exists():
        meta=json.loads(side.read_text());verified(path,side)
        assert meta['url']==url and meta['params']==params
        return path.read_bytes() if binary else json.loads(path.read_text())
    print('Downloading',path.relative_to(ROOT),flush=True)
    for attempt in range(3):
        response=requests.get(url,params=params,timeout=(20,180))
        if response.status_code in (502,503,504) and attempt<2:
            time.sleep(3*(attempt+1));continue
        response.raise_for_status();break
    if binary:
        assert 'text/html' not in response.headers.get('Content-Type',''),path
        data=response.content
    else:
        data=response.json()
        assert not isinstance(data,dict) or 'error' not in data,(path,data)
        if isinstance(data,dict) and data.get('exceededTransferLimit'):
            # ArcGIS signals that more rows remain on a successful full page.
            # Count/ID reconciliation below verifies the complete paginated set.
            assert 'resultOffset' in params and len(data.get('features',[]))==params['resultRecordCount'],path
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=Path(str(path)+'.partial');tmp.write_bytes(response.content);tmp.replace(path)
    savejson(side,{'url':url,'params':params,'method':'GET','retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
                   'sha256':sha(path),'bytes':path.stat().st_size,'authenticated':False})
    time.sleep(.5)
    return data

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['all','census','sld'],default='all');args=parser.parse_args()
    freeze();verify_phase12()
    if args.stage in ('all','census'):
        for state in ('17','06'):
            name=f'tl_2022_{state}_bg.zip';get(RAW/'tiger2022'/name,'https://www2.census.gov/geo/tiger/TIGER2022/BG/'+name,binary=True)
        for table in sorted({v.split('_')[0] for f in definitions() for v in f.get('components',[])}):
            name=f'acsdt5y2022-{table.lower()}.dat'
            old=PROJECT/'restart_3_0/data/raw/environment_acs2022/bulk'/name
            if old.exists():bulk_path(table)
            else:get(RAW/'acs_bulk'/name,BASE+name,binary=True,source_side=True)
    if args.stage in ('all','sld'):
        get(RAW/'sld2021_layer.json',SLD,{'f':'json'})
        for state in ('17','06'):
            for county in COUNTIES[state]:
                where=f"STATEFP='{state}' AND COUNTYFP='{county}'";prefix=f'{state}_{county}'
                query={'where':where,'returnCountOnly':'true','f':'json'}
                before=get(RAW/f'sld2021/{prefix}_count_before.json',SLD+'/query',query)['count']
                seen=set()
                for offset in range(0,before,1000):
                    data=get(RAW/f'sld2021/{prefix}_{offset:05d}.geojson',SLD+'/query',
                        {'where':where,'outFields':FIELDS,'returnGeometry':'true','outSR':4326,'f':'geojson',
                         'orderByFields':'OBJECTID','resultRecordCount':min(1000,before-offset),'resultOffset':offset})
                    ids=[f['properties']['OBJECTID'] for f in data['features']]
                    assert len(ids)==min(1000,before-offset) and len(ids)==len(set(ids)) and not seen.intersection(ids)
                    seen.update(ids)
                after=get(RAW/f'sld2021/{prefix}_count_after.json',SLD+'/query',query)['count']
                assert before==after==len(seen)
                print('SLD reconciled',prefix,before,flush=True)
    savejson(OUT/f'qa/acquisition_{args.stage}.json',{'status':'PASS','stage':args.stage,'credentials_used':False,
        'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat()})

if __name__=='__main__':main()
