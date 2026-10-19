"""Import official 2022 ACS table-based summary files without an API key.

The public files contain estimates and margins of error. Their numeric jam
values are retained, and the corresponding standard annotations are derived.
"""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import requests
import shapefile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/environment_acs2022'
BULK = RAW / 'bulk'
ATTR = RAW / 'attributes'
BASE = 'https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/5YRData/'
COUNTIES = {'005', '047', '061', '081', '085', '029', '055'}
ANNOTATIONS = {
    '-666666666': '-', '-999999999': 'N', '-888888888': '(X)',
    '-222222222': '**', '-333333333': '***', '-555555555': '*****',
}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def download(table):
    BULK.mkdir(parents=True, exist_ok=True)
    path = BULK / f'acsdt5y2022-{table.lower()}.dat'
    side = BULK / f'{path.name}.source.json'
    url = BASE + path.name
    if path.exists() and side.exists():
        assert sha(path) == json.loads(side.read_text())['sha256']
        return path
    tmp = path.with_suffix('.part')
    response = requests.get(url, stream=True, timeout=(20, 180))
    response.raise_for_status()
    assert response.url == url and response.headers.get('Content-Type', '').split(';')[0] != 'text/html'
    with tmp.open('wb') as stream:
        for chunk in response.iter_content(1024 * 1024):
            stream.write(chunk)
    assert tmp.stat().st_size > 100000
    os.replace(tmp, path)
    side.write_text(json.dumps({
        'source': url, 'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'bytes': path.stat().st_size, 'sha256': sha(path), 'authenticated': False,
    }, indent=2) + '\n')
    print('Downloaded', table, path.stat().st_size, flush=True)
    return path


def main():
    spec = json.loads((ROOT / 'protocol/environment_variables.json').read_text())
    variables = sorted({v for f in spec['features'] for v in f['components']})
    tables = sorted({v.split('_')[0] for v in variables})
    reader = shapefile.Reader(str(ROOT / 'data/raw/temporal_extension/acs2022/tl_2022_36_bg.zip'))
    geoids = {r.record['GEOID'] for r in reader.iterShapeRecords()
              if r.record['COUNTYFP'] in COUNTIES}
    assert geoids and all(len(g) == 12 and g[:2] == '36' and g[2:5] in COUNTIES for g in geoids)
    records = {g: {} for g in geoids}
    coverage = {}
    for table in tables:
        path = download(table)
        needed = [v for v in variables if v.startswith(table + '_')]
        seen = set()
        with path.open(newline='', encoding='utf-8-sig') as stream:
            rows = csv.DictReader(stream, delimiter='|')
            assert all(f'{v.split("_")[0]}_E{v.split("_")[1]}' in rows.fieldnames for v in needed)
            for row in rows:
                geoid = row['GEO_ID']
                if not geoid.startswith('1500000US') or geoid[9:] not in records:
                    continue
                g = geoid[9:]
                assert g not in seen, (table, g)
                seen.add(g)
                for v in needed:
                    prefix, number = v.split('_')
                    for kind, suffix in [('E', 'E'), ('M', 'M')]:
                        raw = row[f'{prefix}_{kind}{number}']
                        records[g][v + suffix] = raw if raw != '' else None
                        records[g][v + suffix + 'A'] = ANNOTATIONS.get(raw)
        coverage[table] = len(seen)
        print('Parsed', table, 'block groups', len(seen), flush=True)
    ATTR.mkdir(parents=True, exist_ok=True)
    fields = ['NAME'] + [v + s for v in variables for s in ['E', 'M', 'EA', 'MA']] + ['state', 'county', 'tract', 'block group']
    for county in sorted(COUNTIES):
        path = ATTR / f'county_{county}_chunk0.json'
        gids = sorted(g for g in geoids if g[2:5] == county)
        data = [fields]
        for g in gids:
            row = {'NAME': None, 'state': g[:2], 'county': g[2:5], 'tract': g[5:11], 'block group': g[11:]}
            row.update(records[g])
            data.append([row.get(k) for k in fields])
        content = (json.dumps(data, separators=(',', ':')) + '\n').encode()
        path.write_bytes(content)
        side = path.with_name(path.name.replace('.json', '.request.json'))
        side.write_text(json.dumps({
            'source_type': 'official_table_based_summary_file',
            'tables': tables, 'county': county, 'authenticated': False,
            'source_files': [str((BULK / f'acsdt5y2022-{t.lower()}.dat').relative_to(ROOT)) for t in tables],
            'sha256': hashlib.sha256(content).hexdigest(), 'rows': len(gids),
            'created_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'annotation_method': 'standard numeric jam-value mapping; other API-only annotations unavailable',
        }, indent=2) + '\n')
    (BULK / 'import_status.json').write_text(json.dumps({
        'tables': tables, 'table_block_group_rows': coverage,
        'boundary_block_groups': len(geoids), 'counties': sorted(COUNTIES),
        'source': BASE, 'note': 'Non-jam API annotations are unavailable from the public summary file.',
    }, indent=2) + '\n')
    print('Imported', len(geoids), 'block groups across', len(COUNTIES), 'counties', flush=True)


if __name__ == '__main__':
    main()
