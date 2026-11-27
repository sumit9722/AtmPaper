"""Compare explicit ATM-location labels across crime datasets; no model fitting.

Run from the repository root:
    python3 restart6_0/analysis/compare_atm_labeled_crime.py

Add another CSV or JSON dataset (repeatable):
    python3 restart6_0/analysis/compare_atm_labeled_crime.py \
        --dataset 'New York City=/path/to/original_nyc_records.csv'

An added city replaces that city's default inputs to prevent double counting.
Only robbery/burglary records are included. An ATM location label does NOT
establish that the machine was attacked or that a victim was using it.
No distances, addresses or bank names are used to infer ATM involvement.
Missing location fields produce UNKNOWN, never zero confirmed ATM cases.
City totals describe source extracts, not comparable citywide crime rates.
LA cross-system case IDs may not reconcile perfectly; conflicts are exported.
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCATION_FIELDS = ('location_description', 'premis_desc', 'prem_typ_desc',
                   'premises_description', 'premise_description', 'location_type')
CASE_FIELDS = ('case_number', 'caseno', 'dr_no', 'cmplnt_num', 'native_case_id', 'event_id')
DATE_FIELDS = ('date_occ', 'cmplnt_fr_dt', 'event_date', 'date', 'occurrence_datetime_local')
EXACT_ATM_LABELS = {
    'ATM', 'ATM AUTOMATIC TELLER MACHINE', 'ATM AUTOMATED TELLER MACHINE',
    'AUTOMATIC TELLER MACHINE', 'AUTOMATED TELLER MACHINE', 'ATM MACHINE',
}


def normalize(value):
    return re.sub(r'[^A-Z0-9]+', ' ', str(value or '').upper()).strip()


def first(row, fields):
    return next((str(row[k]).strip() for k in fields if row.get(k) not in (None, '')), '')


def records(path):
    if path.suffix.lower() == '.csv':
        with path.open(newline='', encoding='utf-8-sig') as f:
            yield from csv.DictReader(f)
    else:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if isinstance(data, dict):
            data = data.get('records', data.get('data'))
        if not isinstance(data, list) or any(not isinstance(r, dict) for r in data):
            raise ValueError(f'{path}: expected CSV or a JSON list of record objects')
        yield from data


def category(row):
    # Prefer explicit category fields; use LA source codes only as a fallback.
    text = normalize(first(row, ('primary_type', 'ofns_desc', 'category', 'native_offense')))
    if text in ('ROBBERY', 'BURGLARY'):
        return text.lower()
    nibr = str(row.get('nibr_code', '')).strip()
    legacy = str(row.get('crm_cd', '')).strip()
    if nibr == '120' or legacy in ('210', '220'):
        return 'robbery'
    if nibr == '220' or legacy in ('310', '320'):
        return 'burglary'
    return None


def year_of(row):
    value = first(row, DATE_FIELDS)
    if re.match(r'^\d{4}-\d{2}-\d{2}', value):
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').year
        except ValueError:
            return None
    for fmt in ('%m/%d/%Y', '%m/%d/%y'):
        try:
            return datetime.strptime(value.split(' ')[0], fmt).year
        except ValueError:
            pass
    return None


def location_status(row, fields):
    values = [str(row[f]).strip() for f in fields if row.get(f) not in (None, '')]
    labels = [normalize(v) for v in values]
    if not labels:
        return 'UNKNOWN', values
    exact = [v in EXACT_ATM_LABELS for v in labels]
    if all(exact):
        return 'EXPLICIT_ATM_LOCATION', values
    if any(exact) or any(re.search(r'\bATM\b|\b(?:AUTOMATIC|AUTOMATED) TELLER\b', v) for v in labels):
        return 'REVIEW_ATM_MENTION_OR_CONFLICT', values
    return 'OTHER_RECORDED_LOCATION', values


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--dataset', action='append', default=[], metavar='CITY=PATH')
    parser.add_argument('--location-field', action='append', default=[], help='Additional explicit location-description column')
    parser.add_argument('--years', type=int, nargs='+', default=[2022, 2023, 2024, 2025])
    parser.add_argument('--output', type=Path, default=ROOT / 'results/atm_labeled_comparison')
    args = parser.parse_args()
    inputs = {
        'Chicago': [('chicago', p) for p in sorted((ROOT / 'data/raw/crime/chicago').glob('*/page_*.json')) if '.request.' not in p.name],
        'Los Angeles': [(source, p) for source in ('la_legacy', 'la_nibrs')
                        for p in sorted((ROOT / f'data/raw/crime/{source}').glob('*/page_*.json')) if '.request.' not in p.name],
        # This inherited export lacks premise labels; it will correctly be UNKNOWN.
        'New York City': [('nyc_inherited', ROOT / 'data/raw/inherited/crime_nyc_2022_2025.csv')],
    }
    overrides = defaultdict(list)
    for item in args.dataset:
        if '=' not in item:
            parser.error('--dataset must be CITY=PATH')
        city, filename = item.split('=', 1)
        overrides[city.strip()].append(('external', Path(filename).expanduser()))
    inputs.update(overrides)
    fields = tuple(dict.fromkeys(LOCATION_FIELDS + tuple(args.location_field)))
    groups = defaultdict(list)
    inventory, exclusions = [], []
    label_counts = Counter()
    for city, sources in inputs.items():
        if not sources:
            raise FileNotFoundError(f'No source files for {city}')
        for source, path in sources:
            count = included = unknown = 0
            observed_fields = set()
            for index, original in enumerate(records(path)):
                count += 1
                row = {str(k).lower(): v for k, v in original.items()}
                observed_fields.update(k for k in fields if k in row)
                crime = category(row)
                year = year_of(row)
                if crime is None or year not in args.years:
                    exclusions.append({'city': city, 'source': source, 'file': str(path), 'row': index,
                                       'reason': 'offense_not_recognized_as_robbery_burglary' if crime is None else 'date_invalid_or_outside_requested_years'})
                    continue
                status, labels = location_status(row, fields)
                included += 1
                unknown += status == 'UNKNOWN'
                for label in labels:
                    label_counts[(city, year, source, label, status)] += 1
                case = re.sub(r'[^A-Z0-9]', '', first(row, CASE_FIELDS).upper())
                # Missing IDs remain separate rows; never merge unrelated cases.
                identity = case or f'MISSING_ID:{path}:{index}'
                groups[(city, identity)].append({'city': city, 'case_id': case, 'year': year,
                    'crime_type': crime, 'atm_status': status, 'location_labels': labels,
                    'source': source, 'file': str(path), 'row': index})
            inventory.append({'city': city, 'source': source, 'file': str(path), 'raw_rows': count,
                'eligible_rows': included, 'unknown_location_rows': unknown,
                'location_fields_present': '|'.join(sorted(observed_fields))})

    cases, conflicts = [], []
    for (city, identity), members in sorted(groups.items()):
        years = sorted({m['year'] for m in members})
        statuses = {m['atm_status'] for m in members}
        known = statuses - {'UNKNOWN'}
        if len(years) != 1:
            conflicts.append({'city': city, 'case_id': identity, 'reason': 'conflicting_occurrence_years_excluded_from_summary', 'records': members})
            continue
        status = next(iter(known)) if len(known) == 1 else 'UNKNOWN' if not known else 'REVIEW_ATM_MENTION_OR_CONFLICT'
        types = {m['crime_type'] for m in members}
        cases.append({'city': city, 'case_id': members[0]['case_id'], 'year': years[0],
            'crime_type': 'robbery' if 'robbery' in types else 'burglary', 'atm_status': status,
            'location_labels': '|'.join(sorted({v for m in members for v in m['location_labels']})),
            'sources': '|'.join(sorted({m['source'] for m in members})), 'source_rows': len(members),
            'missing_case_id': not bool(members[0]['case_id']), 'offense_conflict': len(types) > 1})
        if len(members) > 1:
            conflicts.append({'city': city, 'case_id': identity, 'reason': 'duplicate_case_rows_or_conflicting_labels', 'records': members})

    summary = []
    for city in inputs:
        for year in sorted(set(args.years)):
            subset = [r for r in cases if r['city'] == city and r['year'] == year]
            c = Counter(r['atm_status'] for r in subset)
            known_n = len(subset) - c['UNKNOWN']
            explicit = [r for r in subset if r['atm_status'] == 'EXPLICIT_ATM_LOCATION']
            summary.append({'city': city, 'year': year, 'eligible_case_records': len(subset),
                'cases_with_location_information': known_n, 'unknown_location_cases': c['UNKNOWN'],
                'explicit_atm_cases': len(explicit) if known_n else '',
                'explicit_atm_robbery': sum(r['crime_type'] == 'robbery' for r in explicit) if known_n else '',
                'explicit_atm_burglary': sum(r['crime_type'] == 'burglary' for r in explicit) if known_n else '',
                'atm_mentions_or_conflicts_for_review': c['REVIEW_ATM_MENTION_OR_CONFLICT'],
                'explicit_atm_share_among_cases_with_location': len(explicit)/known_n if known_n else '',
                'comparison_status': 'NO_ELIGIBLE_RECORDS' if not subset else 'LOCATION_INFORMATION_UNAVAILABLE' if not known_n else 'DESCRIPTIVE_SOURCE_COUNTS_ONLY'})

    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError('Choose an empty --output directory; existing results are not overwritten')
    args.output.mkdir(parents=True, exist_ok=True)
    case_fields = ['city','case_id','year','crime_type','atm_status','location_labels','sources','source_rows','missing_case_id','offense_conflict']
    write_csv(args.output/'comparison_by_city_year.csv', summary, list(summary[0]))
    write_csv(args.output/'explicit_atm_cases.csv', [r for r in cases if r['atm_status']=='EXPLICIT_ATM_LOCATION'], case_fields)
    write_csv(args.output/'cases_needing_review.csv', [r for r in cases if r['atm_status']=='REVIEW_ATM_MENTION_OR_CONFLICT'], case_fields)
    write_csv(args.output/'source_inventory.csv', inventory, ['city','source','file','raw_rows','eligible_rows','unknown_location_rows','location_fields_present'])
    write_csv(args.output/'location_label_counts.csv', [dict(zip(['city','year','source','location_label','atm_status','raw_rows'], (*key,n))) for key,n in sorted(label_counts.items())], ['city','year','source','location_label','atm_status','raw_rows'])
    write_csv(args.output/'excluded_rows.csv', exclusions, ['city','source','file','row','reason'])
    (args.output/'duplicate_and_conflict_records.json').write_text(json.dumps(conflicts, indent=2))
    (args.output/'interpretation.json').write_text(json.dumps({
        'definition': 'Explicit ATM location label; not verified ATM-targeting or ATM-use narrative',
        'offenses': ['robbery','burglary'], 'years': args.years,
        'matching_rule': 'Exact normalized ATM labels only; broader ATM mentions require review',
        'exact_labels': sorted(EXACT_ATM_LABELS), 'location_fields': fields,
        'deduplication': 'City and normalized case ID; robbery takes precedence for multi-offense cases; conflicting years excluded',
        'limitations': ['Original NYC premise fields are absent from the default inherited export.',
            'No new city-boundary clipping is performed: counts describe the supplied extracts.',
            'LA reporting systems may use incompatible case IDs; cross-system duplication can remain.',
            'Counts and label completeness are not directly comparable crime rates across cities.',
            'No distance-based near-ATM matches are classified as explicit ATM cases.'],
    }, indent=2))
    print(args.output)


if __name__ == '__main__':
    main()
