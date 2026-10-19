"""Phases 1–3: inherit audited cohorts and independently build lagged crime."""
from common import *
from scipy.spatial import cKDTree
from pyproj import Geod, Transformer

def main():
    out = ROOT/'results/phase3'
    spec = ROOT/'protocol/restart_spec.md'
    freeze(ROOT/'reports/protocol_freeze.json', {'sha256': sha(spec)})
    assert json.loads((PREVIOUS/'reports/validation.json').read_text())['status'] == 'PASS'
    Xold, y, meta, housingnames, distance = previous.load()
    environmental = PROJECT/'restart_2024_2025/results/phase3'
    assert json.loads((environmental/'qa/validation.json').read_text())['status'] == 'PASS'
    for r in read(environmental/'qa/output_manifest.csv'):
        assert sha(environmental/r['file']) == r['sha256'], r['file']
    panel = PREVIOUS/'data/processed/atm_panel_2024_2025_full_year.csv'
    crimefile = PREVIOUS/'data/processed/crime_primary_2023_2025.csv'
    # Both inputs are also checked against the phase-2 validation manifest below.
    phase2manifest = PREVIOUS/'reports/output_manifest.csv'
    if phase2manifest.exists():
        for r in read(phase2manifest):
            assert sha(PREVIOUS/r['file']) == r['sha256'], r['file']
    envrows = {r['row_id']: r for r in read(environmental/'data/features_primary.csv')}
    envnames = json.loads((environmental/'data/feature_schema.json').read_text())['primary_predictors'][1:]
    assert set(envrows) == {r['site_id'] for r in meta}
    lagnames = ['log1p_prior_crime_25m', 'log1p_prior_crime_50m', 'log1p_prior_crime_100m',
                'log1p_prior_robbery_50m', 'log1p_prior_burglary_50m', 'log1p_prior_recent_crime_50m']
    names = housingnames + envnames + lagnames
    events = read(crimefile)
    assert len({e['event_id'] for e in events}) == len(events)
    geod = Geod(ellps='WGS84'); links = []; rows = []; checks = []
    for city in CITIES:
        trans = Transformer.from_crs(4326, 32618 if city == 'New York City' else 32617, always_xy=True)
        for year in [2024, 2025]:
            eligible = [e for e in events if e['city'] == city and int(e['event_date'][:4]) == year-1
                        and e['report_datetime'] and e['report_datetime'][:10] < f'{year}-01-01']
            lon = np.array([float(e['longitude']) for e in eligible]); lat = np.array([float(e['latitude']) for e in eligible])
            tree = cKDTree(np.column_stack(trans.transform(lon, lat)))
            for i, r in enumerate(meta):
                if r['city'] != city or r['year'] != year: continue
                lo, la = float(r['longitude']), float(r['latitude'])
                ix = tree.query_ball_point(trans.transform(lo, la), 102.)
                counts = np.zeros(6, dtype=int)
                for j in sorted(ix):
                    d = float(geod.inv(lo, la, lon[j], lat[j])[2])
                    if d > 100: continue
                    e = eligible[j]
                    increment = np.array([d<=25, d<=50, True, d<=50 and e['common_category']=='robbery',
                                          d<=50 and e['common_category']=='burglary', d<=50 and int(e['event_date'][5:7])>=7], dtype=int)
                    counts += increment
                    links.append({'row_id': r['site_id'], 'event_id': e['event_id'], 'distance_m': d,
                                  'event_date': e['event_date'], 'report_datetime': e['report_datetime'],
                                  'category': e['common_category']})
                # Independent full-city distance scan also detects missed tree neighbors.
                direct = geod.inv(np.full(len(lon), lo), np.full(len(lat), la), lon, lat)[2]
                near = np.flatnonzero(direct <= 100)
                actual = np.array([sum(direct[j]<=25 for j in near), sum(direct[j]<=50 for j in near), len(near),
                                   sum(direct[j]<=50 and eligible[j]['common_category']=='robbery' for j in near),
                                   sum(direct[j]<=50 and eligible[j]['common_category']=='burglary' for j in near),
                                   sum(direct[j]<=50 and int(eligible[j]['event_date'][5:7])>=7 for j in near)], dtype=int)
                assert np.array_equal(counts, actual), r['site_id']
                values = list(Xold[i])+[old.safe(envrows[r['site_id']][n]) for n in envnames]+list(np.log1p(counts))
                rows.append({'row_id': r['site_id'], 'city': city, 'year': year} |
                            {n: float(v) if np.isfinite(v) else '' for n,v in zip(names, values)})
                checks.append({'row_id': r['site_id'], 'prior_year': year-1, 'eligible_city_events':len(eligible),
                               'direct_geodesic_reconstruction': 'PASS', 'prior_count_50m': int(counts[1])})
            print('Reconstructed and independently checked',city,year,flush=True)
    write(out/'data/features.csv', sorted(rows, key=lambda r:r['row_id']))
    write(out/'data/modeling_cohort.csv', meta)
    gzwrite(out/'data/prior_event_links.csv.gz', links)
    write(out/'qa/direct_geodesic_validation.csv', checks)
    save(out/'data/feature_schema.json', {'predictors': names, 'selection_candidates':len(names),
         'training_year':2024,'test_year':2025,'primary_outcome':'any robbery/burglary within 50 m',
         'new_feature_formula':'log1p(count of prior-year events reported before prediction cutoff)',
         'single_added_predictor_candidates':names[1:],'imputation':'within each training membership'})
    paths=[spec,panel,crimefile,PREVIOUS/'reports/validation.json',PREVIOUS/'results/phase4/qa/output_manifest.csv',
           PREVIOUS/'results/phase3/data/features_primary.csv',environmental/'data/features_primary.csv',
           PREVIOUS/'scripts/phase4_common.py',PREVIOUS/'scripts/phase5_common.py',PREVIOUS/'scripts/run_phase4.py']
    write(ROOT/'reports/input_manifest.csv',[{'file':str(p.relative_to(PROJECT)), 'sha256':sha(p)} for p in paths])
    save(out/'qa/validation.json', {'status':'PASS','site_years':len(rows),'features':len(names),
         'new_lag_features':6,'event_links':len(links),'direct_distance_reconstructions':len(checks),
         'future_event_predictors':0,'joins':'exact row ID','inherited_validations':'PASS'})
    save(ROOT/'reports/phase_status.json',{'phase_1':'complete: documented retrospective protocol',
         'phase_2':'complete: inherited validated cohorts and archived sources',
         'phase_3':'complete: feature reconstruction and independent validation',
         'phase_4':'pending','phase_5':'pending','confirmatory_complete':False})
    print('Phases 1–3 complete:',len(rows),'rows;',len(names),'features.',flush=True)

if __name__=='__main__': main()
