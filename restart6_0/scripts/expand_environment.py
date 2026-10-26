"""Expand the frozen Phase 3 cohort to all core EPA SLD environmental measures.

Run with --acquire once; subsequent runs reproduce the release offline.
"""
import argparse
import collections
import datetime as dt
import json
import math

from acquire_phase3 import get, SLD
from phase3_common import (ROOT, OUT, definitions, fingerprint, manifest_check,
                           read, savejson, sha, verify_phase12, write)

DEST = ROOT / 'results/phase3_environment_expanded'
CACHE = ROOT / 'environment_expansion/raw'
SPEC = ROOT / 'protocol/environment_expansion.json'
GUIDE = 'https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf'
NUMERIC = {'esriFieldTypeInteger', 'esriFieldTypeDouble', 'esriFieldTypeSmallInteger'}


def clean(value):
    """Core SLD quantities are nonnegative; retain source codes in raw exports."""
    if value is None or value == '':
        return None
    result = float(value)
    return result if math.isfinite(result) and result >= 0 else None


def core_fields(metadata):
    # The service appends Smart Location Calculator inputs and coefficients after
    # the original SLD + Walkability fields. Those are retained only as raw data.
    fields = metadata['fields']
    end = next(i for i, field in enumerate(fields) if field['name'] == 'Region')
    return [f for f in fields[:end] if f['type'] in NUMERIC]


def units(field):
    name = field['name']
    if name == 'D1_FLAG':
        return 'binary flag (0/1)'
    if name.startswith('Ac_'):
        return 'acres'
    if name in ('P_WrkAge', 'Pct_AO0', 'Pct_AO1', 'Pct_AO2p', 'R_PCTLOWWAGE', 'E_PctLowWage'):
        return 'fraction (source labels say percent; values use 0-1 scale)'
    if name.endswith('_Ranked'):
        return 'ordinal national rank (1-20; D4A uses 1 and 13-20)'
    if name == 'NatWalkInd':
        return 'index score (1-20)'
    if name == 'D1A':
        return 'housing units per acre of unprotected land'
    if name == 'D1B':
        return 'persons per acre of unprotected land'
    if name == 'D1D':
        return 'jobs plus housing units per acre of unprotected land'
    if name.startswith('D1C'):
        return 'jobs per acre of unprotected land'
    if name == 'D2A_JPHH':
        return 'jobs per household'
    if name == 'D2A_WRKEMP':
        return 'resident workers per job'
    if name.startswith('D2'):
        return 'dimensionless index'
    if name.startswith('D3A'):
        return 'facility miles per square mile'
    if name.startswith('D3B'):
        return 'intersections per square mile (D3B weighted)'
    if name == 'D4A':
        return 'metres from population-weighted block-group centroid'
    if name.startswith('D4B'):
        return 'fraction of employment'
    if name == 'D4C':
        return 'transit departures per hour during evening peak'
    if name == 'D4D':
        return 'transit departures per hour per square mile'
    if name == 'D4E':
        return 'transit departures per hour per person'
    if name in ('D5AR', 'D5BR'):
        return 'travel-time-weighted jobs'
    if name in ('D5AE', 'D5BE'):
        return 'travel-time-weighted working-age persons'
    if name.startswith('D5'):
        return 'dimensionless regional ratio/index'
    return 'count (entity identified in description)'


def acquire(geoids, acquire_enabled):
    metadata_path = CACHE / 'layer.json'
    paths = []

    def fetch(path, url, params):
        if not acquire_enabled and not path.exists():
            raise FileNotFoundError(f'{path}: run with --acquire first')
        if not acquire_enabled:
            side = json.loads(path.with_name(path.name + '.request.json').read_text())
            assert side['sha256'] == sha(path)
            assert side['url'] == url and side['params'] == params
            result = json.loads(path.read_text())
        else:
            result = get(path, url, params)
        paths.extend([path, path.with_name(path.name + '.request.json')])
        return result

    metadata = fetch(metadata_path, SLD, {'f': 'json'})
    records = {}
    for offset in range(0, len(geoids), 100):
        batch = geoids[offset:offset + 100]
        where = 'GEOID20 IN (' + ','.join("'" + g + "'" for g in batch) + ')'
        result = fetch(CACHE / f'attributes_{offset:05d}.json', SLD + '/query',
                       {'where': where, 'outFields': '*', 'returnGeometry': 'false',
                        'orderByFields': 'GEOID20', 'f': 'json'})
        assert not result.get('exceededTransferLimit'), 'Incomplete source response'
        rows = [f['attributes'] for f in result['features']]
        assert len(rows) == len(batch)
        assert {r['GEOID20'] for r in rows} == set(batch)
        for row in rows:
            assert row['GEOID20'] not in records
            records[row['GEOID20']] = row
        print(f'EPA attributes reconciled: {len(records)}/{len(geoids)} block groups', flush=True)
    return metadata, records, paths


def build(acquire_enabled=False):
    DEST.mkdir(parents=True, exist_ok=True)
    savejson(DEST / 'status.json', {'status': 'BUILDING'})
    verify_phase12()
    manifest_check(OUT / 'qa/input_manifest.csv')
    manifest_check(OUT / 'qa/output_manifest.csv')
    assert json.loads((OUT / 'qa/validation.json').read_text())['status'] == 'PASS'
    source = read(OUT / 'data/site_context_raw.csv')
    lookup = {r['row_id']: r for r in read(OUT / 'data/site_lookup_and_quality.csv')}
    assert len(source) == len(lookup) == 4018
    assert len({r['row_id'] for r in source}) == len(source)
    geoids = sorted({r['sld_geoid_2019'] for r in source if r['sld_geoid_2019']})
    metadata, records, paths = acquire(geoids, acquire_enabled)
    fields = core_fields(metadata)
    spec = json.loads(SPEC.read_text())
    assert [f['name'] for f in fields] == spec['epa_core_fields'], 'EPA schema drift'
    old_epa = [f for f in definitions() if f['source'] == 'EPA_SLD2021']
    inherited = [f for f in definitions() if f['source'] in ('ACS2022', 'prior_December_OSM')]
    aliases = {f['field']: f['name'] for f in old_epa}
    original_dictionary = {f['name']: f for f in read(OUT / 'data/feature_dictionary.csv')}
    dictionary = []
    for field in fields:
        name = aliases.get(field['name'], 'sld_' + field['name'])
        dictionary.append({'column': name, 'source': 'EPA_SLD2021', 'source_field': field['name'],
            'description': field['alias'], 'units': units(field),
            'role': 'quality_flag' if field['name'] == 'D1_FLAG' else 'exploratory_environment',
            'available_at': '2021-06-30', 'transform': 'identity',
            'spatial_support': 'CBSA' if field['name'].startswith('CBSA_') else '2019 EPA block group',
            'source_url': GUIDE, 'missing_policy': 'null/nonfinite/negative source codes or unusable spatial join -> blank'})
    for feature in inherited:
        old = original_dictionary[feature['name']]
        dictionary.append({'column': feature['name'], 'source': feature['source'],
            'source_field': '|'.join(feature.get('components', [])), 'description': feature['name'],
            'units': old['raw_unit'], 'role': 'exploratory_environment',
            'available_at': feature.get('available_at', 'prior December snapshot'),
            'transform': 'identity', 'spatial_support': old['spatial_support'],
            'source_url': 'inherited frozen Phase 3 data/feature_dictionary.csv',
            'missing_policy': 'inherited unchanged, including partial-2023 temporal exclusions'})
    columns = [d['column'] for d in dictionary]
    assert len(columns) == len(set(columns))
    metadata_columns = ['row_id', 'site_id', 'city', 'outcome_year', 'longitude', 'latitude',
                        'cohort', 'acs_geoid_2022', 'sld_geoid_2019']
    combined, missing = [], []
    overlap_checks = 0
    for original in source:
        rowid = original['row_id']
        info = lookup[rowid]
        attrs = records.get(original['sld_geoid_2019'], {})
        row = {k: original[k] if k in original else info[k] for k in metadata_columns}
        for feature in old_epa:
            # A new retrieval must agree with every already validated source value.
            expected = clean(original['sld_' + feature['field']])
            actual = clean(attrs.get(feature['field']))
            assert expected == actual, (rowid, feature['field'], expected, actual)
            overlap_checks += 1
        for field in fields:
            name = aliases.get(field['name'], 'sld_' + field['name'])
            value = attrs.get(field['name'])
            assert not attrs or field['name'] in attrs, field['name']
            row[name] = clean(value)
            if row[name] is None:
                reason = 'spatial_join_unavailable' if not attrs else 'source_null' if value is None else 'source_negative_or_nonfinite'
                missing.append({'row_id': rowid, 'column': name, 'reason': reason, 'source_value': value})
        for feature in inherited:
            name = feature['name']
            row[name] = clean(original[name])
            if row[name] is None:
                missing.append({'row_id': rowid, 'column': name,
                    'reason': 'source_unavailable_before_cutoff' if info['outcome_year'] == '2023' else 'inherited_source_or_coverage_missing',
                    'source_value': original[name]})
        combined.append(row)
    # Serialize all available source attributes, including non-predictor metadata
    # and calculator coefficients, separately from the environmental matrix.
    write(DEST / 'epa_all_source_attributes_by_block_group.csv', [records[g] for g in geoids])
    write(DEST / 'environment_dictionary.csv', dictionary)
    core_names = {f['name'] for f in fields}
    write(DEST / 'epa_source_field_catalog.csv', [
        {'field': f['name'], 'source_type': f['type'], 'source_description': f['alias'],
         'included_in_environment': f['name'] in core_names,
         'role': 'core SLD measure' if f['name'] in core_names else
                 'source identifier, geometry, or separate Smart Location Calculator attribute; raw export only'}
        for f in metadata['fields']])
    write(DEST / 'missingness_reasons.csv', missing, ['row_id', 'column', 'reason', 'source_value'])
    predictors = [d['column'] for d in dictionary if d['role'] != 'quality_flag']
    for suffix, years in [('full_year_2024_2025', {'2024', '2025'}), ('2024', {'2024'}),
                          ('2025', {'2025'}), ('partial_2023', {'2023'})]:
        selected = [r for r in combined if r['outcome_year'] in years]
        write(DEST / f'environment_{suffix}.csv', selected, metadata_columns + columns)
        write(DEST / f'predictors_{suffix}.csv',
              [{k: r[k] for k in ['row_id'] + predictors} for r in selected], ['row_id'] + predictors)
    groups = collections.defaultdict(list)
    for row in combined:
        groups[(row['city'], row['outcome_year'])].append(row)
    coverage = []
    for (city, year), rows in sorted(groups.items()):
        for col in columns:
            values = [r[col] for r in rows if r[col] is not None]
            coverage.append({'city': city, 'outcome_year': year, 'parameter': col,
                'rows': len(rows), 'available': len(values), 'missing': len(rows) - len(values),
                'coverage_fraction': len(values) / len(rows), 'distinct_values': len(set(values)),
                'minimum': min(values) if values else None, 'maximum': max(values) if values else None})
    write(DEST / 'coverage_by_city_year.csv', coverage)
    # Re-read every exported cell and validate it against the independent raw
    # source attribute or frozen Phase 3 cell, rather than the in-memory matrix.
    original_by_id = {r['row_id']: r for r in source}
    checked = 0
    for suffix, expected_count in [('full_year_2024_2025', 2731), ('partial_2023', 1287)]:
        exported = read(DEST / f'environment_{suffix}.csv')
        assert len(exported) == len({r['row_id'] for r in exported}) == expected_count
        expected_ids = {r['row_id'] for r in source if (lookup[r['row_id']]['outcome_year'] == '2023') == (suffix == 'partial_2023')}
        assert {r['row_id'] for r in exported} == expected_ids
        for row in exported:
            original = original_by_id[row['row_id']]
            attrs = records.get(original['sld_geoid_2019'], {})
            for entry in dictionary:
                value = attrs.get(entry['source_field']) if entry['source'] == 'EPA_SLD2021' else original[entry['column']]
                expected = None if value in (None, '') else float(value)
                if expected is not None and (not math.isfinite(expected) or expected < 0):
                    expected = None
                actual = None if row[entry['column']] == '' else float(row[entry['column']])
                assert actual == expected, (row['row_id'], entry['column'])
                checked += 1
            if suffix == 'partial_2023':
                assert all(row[f['name']] == '' for f in inherited)
        matrix = read(DEST / f'predictors_{suffix}.csv')
        assert list(matrix[0]) == ['row_id'] + predictors
        assert [r['row_id'] for r in matrix] == [r['row_id'] for r in exported]
        assert all(m[k] == r[k] for m, r in zip(matrix, exported) for k in predictors)
    manifest_check(OUT / 'qa/output_manifest.csv')
    paths.extend([SPEC, OUT / 'qa/input_manifest.csv', OUT / 'qa/output_manifest.csv',
                  OUT / 'data/site_context_raw.csv', OUT / 'data/site_lookup_and_quality.csv',
                  OUT / 'data/feature_dictionary.csv'])
    inputs = fingerprint(paths)
    frozen = DEST / 'input_manifest.csv'
    if frozen.exists():
        assert read(frozen) == [{k: str(v) for k, v in r.items()} for r in inputs], 'Expanded inputs changed'
    else:
        write(frozen, inputs)
    savejson(DEST / 'schema.json', {'key': 'row_id', 'environment_columns': columns,
        'exploratory_predictors': predictors, 'metadata_columns': metadata_columns,
        'quality_flags': [d['column'] for d in dictionary if d['role'] == 'quality_flag'],
        'epa_core_parameters': len(fields), 'inherited_acs_atm_parameters': len(inherited),
        'units': 'raw source units; no logarithm, imputation, scaling or feature selection',
        'outcomes_file': '../phase3/data/outcomes.csv', 'scientific_review': 'PENDING',
        'models_fitted': False, 'confirmatory_modeling_ready': False})
    summary = {'status': 'PASS', 'main_rows': 2731, 'partial_2023_rows': 1287,
        'epa_block_groups': len(records), 'environment_parameters': len(columns),
        'epa_core_parameters': len(fields), 'new_parameters': len(fields) - len(old_epa),
        'exploratory_predictors': len(predictors), 'exported_values_verified': checked,
        'existing_epa_values_reconciled': overlap_checks, 'original_phase3_integrity': 'PASS',
        'scientific_review': 'PENDING', 'models_fitted': False,
        'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    savejson(DEST / 'validation.json', summary)
    savejson(DEST / 'status.json', summary)
    artifacts = [p for p in DEST.iterdir() if p.is_file() and p.name != 'output_manifest.csv']
    artifacts.append(ROOT / 'scripts/expand_environment.py')
    write(DEST / 'output_manifest.csv', fingerprint(artifacts))
    manifest_check(DEST / 'output_manifest.csv')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquire', action='store_true')
    args = parser.parse_args()
    try:
        build(args.acquire)
    except BaseException as exc:
        savejson(DEST / 'status.json', {'status': 'INCOMPLETE', 'error': f'{type(exc).__name__}: {exc}'})
        raise
