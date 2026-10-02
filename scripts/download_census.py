"""Fetch the study's ex-ante ACS context; never persist or print API credentials."""
import csv
import datetime as dt
import getpass
import hashlib
import json
import os
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/census/acs2023_5year'
OUT = ROOT / 'data/processed/census'
BASE = 'https://api.census.gov/data/2023/acs/acs5'
COUNTIES = {'005': 'Bronx', '047': 'Kings', '061': 'New York', '081': 'Queens',
            '085': 'Richmond', '029': 'Erie', '055': 'Monroe'}
FIELDS = {'B01003_001': 'population', 'B19013_001': 'median_household_income',
          'B23025_003': 'civilian_labor_force', 'B23025_005': 'unemployed'}
VARIABLES = [v + suffix for v in FIELDS for suffix in ('E', 'M', 'EA', 'MA')]

class Fetcher:
    def __init__(self):
        self.key = None
        self.calls = 0

    def get(self, filename, endpoint, params=None, authenticated=False):
        path = RAW / filename
        sidecar = path.with_suffix('.request.json')
        if path.exists() and sidecar.exists():
            content = path.read_bytes()
            if hashlib.sha256(content).hexdigest() != json.loads(sidecar.read_text())['sha256']:
                raise RuntimeError('Cached file checksum mismatch: ' + filename)
            return json.loads(content)
        if self.calls >= 10:
            raise RuntimeError('Hard limit of 10 network requests reached; no retries.')
        if authenticated and self.key is None:
            self.key = os.environ.get('CENSUS_API_KEY') or getpass.getpass('Census API key (hidden, not saved): ')
            if not self.key.strip():
                raise RuntimeError('API key is empty')
        query = dict(params or {})
        if authenticated:
            query['key'] = self.key
        if self.calls:
            time.sleep(2)
        self.calls += 1
        try:
            response = requests.get(endpoint, params=query, timeout=120, allow_redirects=False)
        except requests.RequestException:
            raise RuntimeError('Census network request failed; stopped without retry; URL suppressed.') from None
        if response.status_code != 200:
            raise RuntimeError(f'Census HTTP {response.status_code}; stopped without retry; response suppressed.')
        try:
            result = response.json()
        except ValueError:
            raise RuntimeError('Census returned non-JSON; stopped; response suppressed.') from None
        if authenticated and (not isinstance(result, list) or len(result) < 2):
            raise RuntimeError('Unexpected or empty Census data response')
        if not authenticated and (not isinstance(result, dict) or 'variables' not in result):
            raise RuntimeError('Unexpected Census metadata response')
        content = response.content
        if self.key and self.key.encode() in content:
            raise RuntimeError('Response contains credential; refusing to save')
        path.write_bytes(content)
        sidecar.write_text(json.dumps({'endpoint': endpoint, 'params': params or {},
            'authenticated': authenticated, 'retrieved_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'sha256': hashlib.sha256(content).hexdigest(), 'http_status': 200,
            'raw_modified': False}, indent=2) + '\n')
        print('Saved ' + filename, flush=True)
        return result

def numeric(value):
    if value in (None, '', 'null'):
        return None
    value = float(value)
    return value if value >= 0 else None

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    fetch = Fetcher()
    dictionary = {}
    for group in ('B01003', 'B19013', 'B23025'):
        meta = fetch.get(group + '.json', BASE + '/groups/' + group + '.json')
        for variable in VARIABLES:
            if variable.startswith(group + '_'):
                dictionary[variable] = meta['variables'][variable]
    (OUT / 'variable_dictionary.json').write_text(json.dumps(dictionary, indent=2) + '\n')
    rows, counts, missing = [], {}, {name: 0 for name in FIELDS.values()}
    for county, county_name in COUNTIES.items():
        table = fetch.get('county_' + county + '.json', BASE,
            {'get': ','.join(['NAME'] + VARIABLES), 'for': 'block group:*',
             'in': f'state:36 county:{county} tract:*'}, authenticated=True)
        header = table[0]
        assert set(VARIABLES + ['state', 'county', 'tract', 'block group']).issubset(header)
        counts[county_name] = len(table) - 1
        for values in table[1:]:
            assert len(values) == len(header)
            source = dict(zip(header, values))
            assert source['state'] == '36' and source['county'] == county
            geoid = ''.join(source[k] for k in ('state', 'county', 'tract', 'block group'))
            assert len(geoid) == 12 and geoid.isdigit()
            row = {'geoid': geoid, 'name': source['NAME'], 'county_fips': county,
                   'study_city_candidate': 'Buffalo' if county == '029' else 'Rochester' if county == '055' else 'New York City',
                   'geography_scope': 'county block groups; city/site spatial join required',
                   'acs_period': '2019-2023', 'available_at': '2024-12-12', 'prediction_year': 2025}
            for variable, name in FIELDS.items():
                row[name] = numeric(source[variable + 'E'])
                row[name + '_moe90'] = numeric(source[variable + 'M'])
                row[name + '_annotation'] = source[variable + 'EA']
                row[name + '_moe_annotation'] = source[variable + 'MA']
                missing[name] += row[name] is None
            denom, numerator = row['civilian_labor_force'], row['unemployed']
            assert denom is None or numerator is None or numerator <= denom
            row['unemployment_rate'] = numerator / denom if denom and numerator is not None else None
            rows.append(row)
    assert len({r['geoid'] for r in rows}) == len(rows)
    with (OUT / 'block_group_context.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {'dataset': BASE, 'acs_period': '2019-2023', 'available_at': '2024-12-12',
        'release_source': 'https://www.census.gov/programs-surveys/acs/news/data-releases/2023/release.html',
        'rows': len(rows), 'county_counts': counts, 'missing_or_sentinel_estimates': missing,
        'network_requests_this_run': fetch.calls, 'request_policy': 'Sequential; 2 seconds between requests; 10 maximum; no automatic retries; stop on any HTTP error; checksum cache',
        'limitations': ['County extracts include areas outside Buffalo and Rochester; spatial join is required.',
          'Population density requires matching 2023 block-group land area; population is not density.',
          'No ATM-site features have been assigned by this download.',
          'ACS values are multiyear survey estimates; negative special values are null in processed data and unchanged in raw data.',
          'Income is in 2023 inflation-adjusted dollars. MOEs are 90% Census MOEs.',
          'Unemployment rate is unemployed / civilian labor force; component MOEs retained, ratio MOE not computed.',
          'This release is suitable for the 2025 cutoff, not for predictions starting before 2024-12-12.',
          'Live API retrieval does not independently establish whether values were revised after initial release.']}
    (OUT / 'download_report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, KeyError, AssertionError) as exc:
        raise SystemExit(str(exc) or 'Census validation failed') from None
