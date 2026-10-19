"""Independently reconcile the public ACS summary files to imported county JSON."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/environment_acs2022'
ANNOTATIONS = {
    '-666666666': '-', '-999999999': 'N', '-888888888': '(X)',
    '-222222222': '**', '-333333333': '***', '-555555555': '*****',
}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    spec = json.loads((ROOT / 'protocol/environment_variables.json').read_text())
    variables = sorted({v for feature in spec['features'] for v in feature['components']})
    tables = sorted({v.split('_')[0] for v in variables})
    imported = {}
    county_counts = {}
    for county_file in sorted((RAW / 'attributes').glob('county_*.json')):
        if '.request.' in county_file.name:
            continue
        side = county_file.with_name(county_file.name.replace('.json', '.request.json'))
        assert digest(county_file) == json.loads(side.read_text())['sha256']
        table = json.loads(county_file.read_text())
        assert len(table) > 1
        county = county_file.name.split('_')[1]
        county_counts[county] = len(table) - 1
        for values in table[1:]:
            row = dict(zip(table[0], values))
            geoid = ''.join(row[k] for k in ['state', 'county', 'tract', 'block group'])
            assert geoid not in imported and geoid[2:5] == county
            imported[geoid] = row
    assert len(county_counts) == 7 and len(imported) == 8217
    checked = {}
    for table in tables:
        path = RAW / 'bulk' / f'acsdt5y2022-{table.lower()}.dat'
        side = path.with_name(path.name + '.source.json')
        assert digest(path) == json.loads(side.read_text())['sha256']
        components = [v for v in variables if v.startswith(table + '_')]
        found = set()
        with path.open(newline='', encoding='utf-8-sig') as stream:
            rows = csv.DictReader(stream, delimiter='|')
            for source in rows:
                geography = source['GEO_ID']
                if not geography.startswith('1500000US') or geography[9:] not in imported:
                    continue
                geoid = geography[9:]
                assert geoid not in found
                found.add(geoid)
                output = imported[geoid]
                for variable in components:
                    group, number = variable.split('_')
                    for kind in ('E', 'M'):
                        raw = source[f'{group}_{kind}{number}']
                        assert output[variable + kind] == (raw if raw else None), (table, geoid, variable, kind)
                        assert output[variable + kind + 'A'] == ANNOTATIONS.get(raw)
        assert found == set(imported), (table, len(found), len(imported))
        checked[table] = len(found)
    result = {
        'status': 'PASS', 'official_bulk_tables': tables,
        'block_groups_per_table': checked, 'county_rows': county_counts,
        'components': len(variables),
        'check': 'All selected estimates, margins and numeric-jam annotations reconcile to source files',
        'limitation': 'The public summary file omits other API-only annotation qualifiers.',
    }
    path = ROOT / 'reports/environment_bulk_validation.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
