"""Cached, sequential public GIS downloads. No Census API credential is used."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/phase3'
ACS = 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer/10'
SLD = 'https://geodata.epa.gov/arcgis/rest/services/OA/SmartLocationDatabase/MapServer/1'
COUNTIES = ['005', '047', '061', '081', '085', '029', '055']
GUIDE = 'https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf'

class Downloader:
    def __init__(self):
        self.calls = 0
    def get(self, name, url, params=None, binary=False):
        path = RAW / name
        sidecar = Path(str(path) + '.request.json')
        if path.exists() and sidecar.exists():
            content = path.read_bytes()
            meta = json.loads(sidecar.read_text())
            assert meta['sha256'] == hashlib.sha256(content).hexdigest(), name
            assert meta['url'] == url and meta['params'] == (params or {}), name
            return content if binary else json.loads(content)
        if self.calls >= 50:
            raise RuntimeError('Request cap reached; stop and investigate.')
        if self.calls:
            time.sleep(2)
        self.calls += 1
        try:
            r = requests.get(url, params=params, timeout=(20, 180))
            r.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f'Network error for {name}: {type(exc).__name__}; no retry.') from None
        if binary:
            data = r.content
        else:
            data = r.json()
            if 'error' in data:
                raise RuntimeError(f'{name}: {data["error"]}')
            if data.get('exceededTransferLimit'):
                raise RuntimeError(f'{name}: truncated response; not cached')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        sidecar.write_text(json.dumps({'url':url, 'params':params or {}, 'resolved_url':r.url,
            'retrieved_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'sha256':hashlib.sha256(r.content).hexdigest(), 'bytes':len(r.content)}, indent=2)+'\n')
        print(f'Saved {name}: {len(r.content):,} bytes', flush=True)
        return data

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['metadata','data'], default='metadata')
    args=parser.parse_args()
    d=Downloader()
    for name, url in [('acs2023_layer.json', ACS), ('sld2021_layer.json', SLD)]:
        d.get(name,url,{'f':'json'})
    d.get('sld2021_user_guide.pdf',GUIDE,binary=True)
    if args.stage == 'metadata':
        return
    sldmeta=json.loads((RAW/'sld2021_layer.json').read_text())
    lookup={f['name'].lower():f['name'] for f in sldmeta['fields']}
    desired=['objectid','geoid20','geoid10','statefp','countyfp','d1c','d1c5_ret','d2b_e5mixa','d3a','d3aao','d3b','d4a','d4c','d4d','d5ar','d5br']
    # Select only fields present; key and metrics are checked below.
    fields=[lookup[x] for x in desired if x in lookup]
    assert all(x in lookup for x in ['d1c','d3a','d3aao','d3b','d4a','d4c','d5ar','d5br','statefp','countyfp'])
    for county in COUNTIES:
        for source, layer, where, selected in [
            ('acs2023',ACS,f"STATE='36' AND COUNTY='{county}'",'OBJECTID,GEOID,STATE,COUNTY,AREALAND,AREAWATER'),
            ('sld2021',SLD,f"{lookup['statefp']}='36' AND {lookup['countyfp']}='{county}'",','.join(fields))]:
            count=d.get(f'{source}/county_{county}_count.json',layer+'/query',{'where':where,'returnCountOnly':'true','f':'json'})['count']
            features=d.get(f'{source}/county_{county}.geojson',layer+'/query',{'where':where,'outFields':selected,
                'returnGeometry':'true','outSR':4326,'f':'geojson','orderByFields':'OBJECTID','resultRecordCount':5000})['features']
            assert len(features)==count, (source,county,len(features),count)
    print(f'Done; {d.calls} new sequential requests.',flush=True)

if __name__=='__main__':
    try:
        main()
    except (RuntimeError,AssertionError) as exc:
        raise SystemExit(str(exc)) from None
