"""Reuse verified NYC rows, keeping the original source dependency explicit."""
import csv
import json
from pathlib import Path
from common import *

def main():
    previous = PROJECT/'restart5_0'
    expected = {r['file']: r['sha256'] for r in read(previous/'reports/artifact_manifest.csv')}
    files = {
        'data/processed/crime_primary_2022_2025.csv': 'crime_nyc_2022_2025.csv',
        'data/processed/atm_panel_full_year_2024_2025.csv': 'dfs_nyc_full_year_2024_2025.csv',
        'data/processed/atm_panel_partial_2023.csv': 'dfs_nyc_partial_2023.csv',
        'data/processed/qa/crime_quality_by_city_year.csv': 'crime_nyc_quality.csv',
    }
    provenance = []
    for relative, name in files.items():
        source = previous/relative
        digest = sha(source)
        if digest != expected[relative]:
            raise RuntimeError(f'Restart 5 artifact changed: {source}')
        with source.open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = [r for r in reader if r['city'] == 'New York City']
        target = RAW/'inherited'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        provenance.append({'source_file': str(source.relative_to(PROJECT)), 'source_sha256': digest,
            'target_file': str(target.relative_to(ROOT)), 'target_sha256': sha(target), 'rows': len(rows),
            'transformation': 'filter city == New York City; preserve fields',
            'original_source_provenance': 'restart5_0/data/processed/source_manifest.csv'})
    write('inherited_sources.csv', provenance)
    # The raw files retain the exact snapshot dates and their upstream names for audit.
    dates = [p.name[4:14] for p in sorted((previous/'data/raw/atm_history').glob('dfs_*.csv'))]
    savejson(RAW/'inherited/snapshot_dates.json', dates)
    freeze()
    print('Reused verified NYC inputs:', len(provenance), flush=True)

if __name__ == '__main__':
    main()
