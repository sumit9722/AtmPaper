"""Adapt Restart 5 incident harmonization to Chicago and both LA reporting systems."""
import collections
import datetime as dt
import json
import re
from common import *

def valid_date(value):
    try:
        return dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None

def normalize(raw, slug, year, path, index):
    if slug == 'chicago':
        city = 'Chicago'
        case, occ, report = raw.get('case_number', ''), raw.get('date', ''), ''
        category = raw['primary_type'].lower()
        code, description = raw['iucr'], raw.get('description', '')
        lon, lat = number(raw.get('longitude')), number(raw.get('latitude'))
        address, attempt = raw.get('block', ''), 'ATTEMPT' if 'ATTEMPT' in description else 'not_separately_published'
    elif slug == 'la_legacy':
        city = 'Los Angeles'
        case, occ, report = raw.get('dr_no', ''), raw.get('date_occ', ''), raw.get('date_rptd', '')
        code, description = raw['crm_cd'], raw.get('crm_cd_desc', '')
        category = 'robbery' if code in ('210', '220') else 'burglary'
        lon, lat = number(raw.get('lon')), number(raw.get('lat'))
        address, attempt = raw.get('location', ''), 'ATTEMPT' if code in ('220', '320') else 'COMPLETED'
    else:
        city = 'Los Angeles'
        case, occ, report = raw.get('caseno', ''), raw.get('date_occ', ''), raw.get('date_rptd', '')
        code, description = raw['nibr_code'], raw.get('nibr_description', '')
        category = 'robbery' if code == '120' else 'burglary'
        lon, lat = number(raw.get('hndrdth_lon')), number(raw.get('hndrdth_lat'))
        address, attempt = raw.get('hndrdth_loc_chk', ''), 'not_separately_published'
    # Only formatting normalization. No invented cross-system identifier crosswalk.
    case = re.sub(r'[^A-Z0-9]', '', str(case).upper())
    od, rd = valid_date(occ), valid_date(report)
    return {'city': city, 'event_id': f'{CITIES[city]}:{case}' if case else '',
        'native_case_id': case, 'native_row_id': raw['source_row_id'],
        'occurrence_datetime_local': occ, 'event_date': str(od) if od else '', 'event_year': od.year if od else '',
        'report_datetime': report, 'report_date': str(rd) if rd else '',
        'report_date_usable': bool(od and rd and rd >= od), 'report_before_occurrence': bool(od and rd and rd < od),
        'report_time_is_ingestion_proxy': False, 'category': category, 'primary_included': True,
        'native_offense': category.upper(), 'native_code': code, 'native_description': description,
        'attempt_status': attempt, 'longitude': lon, 'latitude': lat, 'address_raw': address,
        'source_file': str(path.relative_to(ROOT)), 'source_row_index': index, 'source_partition_year': year,
        'coordinate_precision_flag': 'public_block_geocode', 'source_system': slug,
        'updated_on_not_report_date': raw.get('updated_on', ''),
        'native_offense_id': raw.get('uniquenibrno', raw.get('id', ''))}

def main():
    freeze()
    polys = polygons()
    events, excluded, duplicates = [], [], []
    counts, codebook = collections.Counter(), {}
    for r in read(RAW/'inherited/crime_nyc_2022_2025.csv'):
        for field in ('longitude', 'latitude', 'easting_m', 'northing_m'):
            r[field] = float(r[field])
        for field in ('report_date_usable','report_before_occurrence','report_time_is_ingestion_proxy','primary_included',
                      'coordinates_on_3dp_grid','coordinates_on_4dp_grid','coordinates_on_5dp_grid'):
            r[field] = r[field] == 'True'
        r['event_year'] = int(r['event_year'])
        r['source_system'] = 'nyc_inherited_restart5'
        r['source_file'] = 'restart5_0/'+r['source_file']
        r['source_path_base'] = 'project_root'
        # Recheck membership against the new boundary vintage; preserve exclusions explicitly.
        if locate(r['longitude'], r['latitude'], polys) != 'New York City':
            excluded.append(r | {'exclusion_reasons': 'outside_current_city_polygon'})
        else:
            events.append(r)
        ck = (r['city'],r['source_system'],r['native_code'],r['native_description'])
        if ck not in codebook:
            codebook[ck] = {k:r[k] for k in ('city','source_system','native_code','native_description','category')}
            codebook[ck].update(source_rows=0,count_unit='inherited_valid_incidents',reviewer_decision='PENDING')
        codebook[ck]['source_rows'] += 1
    grouped = {}
    for slug in ('chicago', 'la_legacy', 'la_nibrs'):
        for year in range(2022, 2026):
            counts[(slug, year)] += 0
            folder = RAW/f'crime/{slug}/{year}'
            if not (folder/'count_after.json').exists():
                raise RuntimeError(f'Missing reconciled crime partition: {slug}/{year}')
            for path in sorted(folder.glob('page_*.json')):
                if '.request.' in path.name:
                    continue
                for index, raw in enumerate(json.loads(path.read_text())):
                    counts[(slug, year)] += 1
                    r = normalize(raw, slug, year, path, index)
                    r['source_path_base'] = 'release_root'
                    ck = (r['city'], slug, r['native_code'], r['native_description'])
                    if ck not in codebook:
                        codebook[ck] = {k:r[k] for k in ('city','source_system','native_code','native_description','category')}
                        codebook[ck].update(source_rows=0, count_unit='raw_source_rows', reviewer_decision='PENDING')
                    codebook[ck]['source_rows'] += 1
                    reasons = []
                    if not r['event_id']:
                        reasons.append('missing_case_id')
                    if r['event_year'] != year:
                        reasons.append('invalid_or_mismatched_occurrence_date')
                    if r['longitude'] is None or r['latitude'] is None:
                        reasons.append('missing_invalid_coordinates')
                    elif locate(r['longitude'], r['latitude'], polys) != r['city']:
                        reasons.append('outside_city_polygon_or_zero_coordinate')
                    if reasons:
                        excluded.append(r | {'exclusion_reasons': '|'.join(reasons)})
                        continue
                    key = r['event_id']
                    if key in grouped:
                        old = grouped[key]
                        priority = lambda x: (x['category']=='robbery', x['source_system']=='la_nibrs',
                                              x['occurrence_datetime_local'],x['source_file'],x['source_row_index'])
                        keep, drop = (r, old) if priority(r) > priority(old) else (old, r)
                        grouped[key] = keep
                        duplicates.append(drop | {'kept_source_file_at_resolution': keep['source_file'],
                            'coordinate_conflict': (old['longitude'],old['latitude'])!=(r['longitude'],r['latitude']),
                            'date_conflict': old['event_date']!=r['event_date'],
                            'category_conflict': old['category']!=r['category'],
                            'cross_system': old['source_system']!=r['source_system'],
                            'rule':'city_case; robbery>burglary; NIBRS>legacy; later_occurrence; source_order',
                            'reviewer_decision': 'PENDING'})
                    else:
                        grouped[key] = r
    for r in grouped.values():
        r['easting_m'], r['northing_m'] = TRANS[r['city']].transform(r['longitude'],r['latitude'])
        for dp in (3,4,5):
            r[f'coordinates_on_{dp}dp_grid'] = all(abs(v-round(v,dp))<1e-8 for v in (r['longitude'],r['latitude']))
        events.append(r)
    events.sort(key=lambda r:(r['city'],r['event_date'],r['event_id']))
    fields = list(dict.fromkeys(k for r in events for k in r))
    write('crime_primary_2022_2025.csv', events, fields)
    write('qa/crime_exclusions.csv', excluded, list(dict.fromkeys(fields+['exclusion_reasons'])))
    write('qa/crime_duplicates.csv', duplicates, list(dict.fromkeys(fields+[
        'kept_source_file_at_resolution','coordinate_conflict','date_conflict','category_conflict','cross_system','rule','reviewer_decision'])))
    write('crime_codebook.csv', codebook.values())
    coverage = []
    for city in CITIES:
        for year in range(2022,2026):
            es = [r for r in events if r['city']==city and r['event_year']==year]
            for month in range(1,13):
                selected = [r for r in es if r['event_date'].startswith(f'{year}-{month:02d}')]
                coverage.append({'city':city,'month':f'{year}-{month:02d}','primary_cases':len(selected),
                    'legacy_cases':sum(r['source_system']=='la_legacy' for r in selected),
                    'nibrs_cases':sum(r['source_system']=='la_nibrs' for r in selected),
                    'original_report_date_usable':sum(r['report_date_usable'] for r in selected),
                    'observation_status':'observed_extract_not_certified_complete',
                    'la_reporting_system_break':city=='Los Angeles'})
    write('crime_monthly_coverage.csv', coverage)
    quality = []
    for city in CITIES:
        for year in range(2022,2026):
            es = [r for r in events if r['city']==city and r['event_year']==year]
            quality.append({'city':city,'year':year,'primary_cases':len(es),
                'missing_invalid_report_primary':sum(not r['report_date_usable'] for r in es),
                'public_block_geocodes':sum(r['coordinate_precision_flag']=='public_block_geocode' for r in es),
                **{f'coordinates_on_{dp}dp_grid':sum(r[f'coordinates_on_{dp}dp_grid'] for r in es) for dp in (3,4,5)}})
    write('qa/crime_quality_by_city_year.csv', quality)
    conservation = []
    for (slug,year),count in sorted(counts.items()):
        kept = sum(r['source_system']==slug and int(r['source_partition_year'])==year for r in events)
        ex = sum(r['source_system']==slug and int(r['source_partition_year'])==year for r in excluded)
        du = sum(r['source_system']==slug and int(r['source_partition_year'])==year for r in duplicates)
        assert count == kept+ex+du, (slug,year,count,kept,ex,du)
        conservation.append({'source':slug,'year':year,'raw_rows':count,'retained':kept,'excluded':ex,'duplicates':du})
    write('qa/crime_source_conservation.csv', conservation)
    print('Crime:',len(events),'valid incidents;',len(excluded),'excluded;',len(duplicates),'duplicates',flush=True)

if __name__ == '__main__':
    main()
