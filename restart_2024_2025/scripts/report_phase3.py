"""Document the completed phase 3 release after validation."""
import csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/phase3'
def read(name):
    with (OUT/name).open() as f:return list(csv.DictReader(f))
def main():
    v=json.loads((OUT/'qa/validation.json').read_text());assert v['status']=='PASS'
    summary=read('qa/city_year_summary.csv');stats=read('qa/feature_distributions.csv');corr=read('qa/feature_correlations.csv')
    table='| Year | City | Rows | ACS unique joins | EPA unique joins | Within 500 m of city edge |\n|---|---|---:|---:|---:|---:|\n'+''.join(f"| {r['year']} | {r['city']} | {r['rows']} | {r['acs_unique']} | {r['sld_unique']} | {r['near_city_edge_500m']} |\n" for r in summary)
    incomplete=sum(int(r['rows'])-int(r['sld_unique']) for r in summary)
    high=[r for r in stats if r['year']!='ALL' and r['city']!='ALL' and r['high_missingness_gt20pct']=='True']
    missing='| Year | City | Feature | Missing |\n|---|---|---|---:|\n'+''.join(f"| {r['year']} | {r['city']} | {r['feature']} | {int(r['missing'])}/{r['rows']} ({float(r['missing_fraction']):.1%}) |\n" for r in high) if high else 'No city/year feature exceeds 20% missingness.'
    highcorr=[r for r in corr if r['abs_rho_ge_0_90']=='True'];constant=[r for r in stats if r['year']!='ALL' and r['city']!='ALL' and r['zero_variance']=='True']
    docs={
    '01_work_completed.md':'''# Phase 3 work completed

1. Reviewed the execution blueprint and phase 2 restart. Froze a common 14-feature primary schema and three sensitivity features in `protocol/phase3_feature_spec.md` before extraction.
2. Copied archived ACS2022 estimates/uncertainty fields, official 2022 TIGER/Line geometry and EPA SLD version 3 sources into this restart. No new network retrieval or API credential was needed. Preserved request metadata and hashes.
3. Verified matching ACS geometry/attribute identifiers, retaining the incompatible archived TIGERweb response as excluded provenance.
4. Assigned every annual ATM baseline point independently to ACS and EPA block groups, preserving ambiguous/missing matches and boundary diagnostics.
5. Attached common socioeconomic and built-environment context, computed prior-December statewide ATM competition and used the phase 2 prior-year report-filtered crime background.
6. Exported outcome-free primary and sensitivity matrices, combined and separately by year, plus raw context, uncertainty fields, lookup and QA tables. No rows or candidate features were dropped based on results.
7. Checked missingness, distributions, ranges, constant features and redundancy, then ran independent source/formula/spatial validation.
8. Published methods, results, reproduction instructions and input/output manifests. Computational completion does not resolve independent scientific review.
''',
    '02_methods.md':'''# Methods and source limitations

Prediction cutoffs are January 1, 2024 and January 1, 2025. Both years use ACS 2018–2022 five-year estimates (released December 7, 2023); income is in 2022 dollars. Fixing this vintage makes socioeconomic definitions comparable and avoids using a release unavailable in 2024. The official 2022 TIGER/Line archive supplies block groups and ALAND. The archived TIGERweb ACS2022 service has incompatible identifiers and is not used. EPA SLD version 3 was released in 2021 and uses 2019 block groups despite the GEOID20 field name; component data span earlier years. Sources are later-retrieved archived-vintage data, not proof of exact historical availability of each value.

Sources: [ACS2022 release](https://www.census.gov/programs-surveys/acs/news/data-releases/2022/release.html), [official TIGER/Line archive](https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_36_bg.zip), [EPA Smart Location Database](https://www.epa.gov/smartgrowth/smart-location-mapping), and [NYS DFS ATM inventory](https://data.ny.gov/Government-Finance/Bank-Owned-ATM-Locations-in-New-York-State/ndex-ad5r). Exact acquisition URLs and times are in `qa/source_register.csv` and copied request sidecars.

Each layer is joined separately with polygon covers. Exactly one polygon is accepted; ambiguous/unmatched assignments stay null with candidate identifiers recorded. Invalid geometry is repaired in memory only if area change is below 1e-6 and geometry remains Polygon/MultiPolygon. Distances to block-group and municipal boundaries use the city's UTM zone. Boundary flags identify points within 10 m of a block-group edge or 500 m of a city edge; they do not correct unknown public geocode errors.

Population density divides population by official land square metres and multiplies by 1e6. Unemployment divides unemployed civilian population by the civilian labor force. Zero denominators remain missing. ACS estimates, 90% margins of error and annotations are preserved; top/bottom-coded incomes are flagged. Negative/nonfinite sentinels become missing and genuine zero values remain zero. EPA raw attributes and sanitized values are both retained. A missing transit indicator is not silently treated as no transit service.

EPA employment, road, intersection, transit and job-access measures describe block-group neighborhoods, not 50 m ATM buffers. Road density is a proxy, not direct distance to a major road. Transit distance is measured from the block-group population centroid, not the ATM. No historical police-station measure or current OSM proxy is fabricated; this feature-family limitation remains explicit.

ATM competition uses December 15, 2023 for 2024 and December 15, 2024 for 2025, including statewide neighbors outside city boundaries. Normalize address, round coordinates to seven decimals and collapse exact duplicate identities. Exclude the focal identity; retain and flag distinct co-located identities. Calculate final WGS84 ellipsoidal distances. Density divides other sites within 500 m by pi × 0.5² km². Independent nonbank ATMs, other states and geocode accuracy remain coverage limitations. Neighbor selection does not depend on later survival.

Primary background is phase 2's prior-year robbery/burglary count in >200–500 m, restricted to reports before the prediction cutoff. Unfiltered background is a sensitivity. Buffalo created_at is an availability proxy. Phase 2's cohort conditions on later observed membership and fixes location to the prior-December point; it is a retrospective cohort, not a prospective enrollment. Coordinates/site_id may change between years at the same address. Use row_id to join site-year files; do not interpret site_id as a permanent machine ID.

Natural log1p transforms apply to specified nonnegative features; unemployment and entropy remain untransformed. No learned imputation, scaling, feature selection or fitting occurs here. Only feature_schema.json's primary allowlist may be used as primary predictors; metadata, outcomes, geography and exposure remain separate. Report missingness >20%, constant features and |Spearman rho| >=0.90 without automatically deleting variables. Future preprocessing/tuning must occur within training folds.
''',
    '03_results.md':f'''# Phase 3 results

Computational validation: **{v['status']}**. All **{v['site_years']:,}** phase 2 site-years were retained, with **14 primary predictors** and **three sensitivity predictors**. No models were fitted.

{table}

ACS uniquely joins every row. EPA lacks a unique match for **{incomplete} site-years**, all in 2025; their EPA values remain missing and the exact candidate-match status is preserved in the spatial audit. The 2025 coordinates are much more often within 10 m of a block-group boundary than the 2024 coordinates. This is consistent with the documented historical coordinate revision; it is not evidence of an environmental change. Boundary-sensitive feature changes need independent positional review.

## Missingness and redundancy

{missing}

There are {len(constant)} constant/all-missing city-year feature diagnostic rows and {len(highcorr)} correlation rows with |rho| >=0.90 across the city/year and pooled diagnostic groups. These are review flags, not independent statistical discoveries; groups overlap. Detailed ranges, quantiles, pairwise sample sizes and correlations are in `qa/feature_distributions.csv` and `qa/feature_correlations.csv`. No automatic feature removal or imputation was performed.

## Validation evidence

The validator checked all input hashes, archived source hashes, ACS geometry/attribute coverage, EPA API polygon counts, all raw attributes and transformations, annual exports and complete row alignment. It independently checked polygon membership and geodesic ATM competition for {v['spatial_sample_rows']} rows (five per city/year). This is exhaustive for formulas and source-value reconciliation, sampled for spatial computations. Validation does not certify source geocoding accuracy or human research acceptance.

Independent phase 2 review and feature-schema approval remain pending. Buffalo precision, historical ATM continuity, the permitted 50 m ATM drift, survival selection, city-edge truncation, stale neighborhood measures and current revisions of historical sources limit interpretation. Both outcome years were inspected previously. `confirmatory_modeling_ready=false` is preserved.
''',
    '04_reproduce.md':'''# Reproduction

From the repository root, use the existing environment:

```bash
.venv/bin/python restart_2024_2025/scripts/build_phase3.py
.venv/bin/python restart_2024_2025/scripts/validate_phase3.py
.venv/bin/python restart_2024_2025/scripts/report_phase3.py
```

For a standalone copy, create a Python environment, install `requirements-phase3.txt`, then run the same three scripts from the restart's `scripts/` directory with that Python. PyShp reads the official TIGER/Line ZIP. All inputs are copied into the restart; the pipeline never reads parent-project data. No network access or credentials are needed for rebuilding. Do not run with Python `-O`, which disables validation assertions.

Prerequisite: completed phase 2 combined panel. The feature specification and schema are frozen; changing the specification requires an explicit version amendment before rebuilding. Build writes feature exports and QA; validation writes PASS only when its checks succeed; report runs only after PASS and refreshes the documentation/output manifest. A failed/restarted build invalidates prior validation status. Do not use previously saved validation for changed inputs.

Use `data/features_primary.csv` and `data/feature_schema.json` for the combined primary matrix. Separate annual matrices and `features_sensitivity*.csv` are available. Join to phase 2 labels only by row_id in a later modeling pipeline. site_lookup_and_quality.csv is metadata, not a predictor matrix. site_context_raw.csv preserves components and uncertainty.

Input manifest hashes are relative to the restart root; output manifest hashes are relative to the phase 3 folder. To verify any manifest, recompute SHA-256 of each listed file and compare with the sha256 column. Never infer independent scientific approval from automated PASS.
'''}
    for name,text in docs.items():(OUT/'docs'/name).write_text(text)
    (OUT/'README.md').write_text(f'''# Phase 3 — common environmental features, 2024–2025

Computationally complete and validated: **{v['site_years']:,} site-year rows**, **14 primary** and **3 sensitivity** predictors. Independent scientific review remains pending.

- [Work completed](docs/01_work_completed.md)
- [Methods and limitations](docs/02_methods.md)
- [Results and quality findings](docs/03_results.md)
- [Reproduction](docs/04_reproduce.md)
- [Primary matrix](data/features_primary.csv), [sensitivity matrix](data/features_sensitivity.csv), [frozen schema](data/feature_schema.json), [dictionary](data/feature_dictionary.csv)
- [Raw context](data/site_context_raw.csv), [site lookup/QA](data/site_lookup_and_quality.csv), [validation](qa/validation.json)

Both years use the fixed pre-2024 ACS vintage and EPA SLD 2021. ATM competition and crime background use each year's prior-period data. No labels are predictors and no models were fitted. Read the results for missingness and redundancy flags before modeling.
''')
    sources=[]
    for folder in [ROOT/'data/raw/phase3',ROOT/'data/raw/temporal_extension/acs2022']:
        for p in sorted(folder.rglob('*.request.json')):
            m=json.loads(p.read_text());sources.append({'sidecar':str(p.relative_to(ROOT)),'url':m.get('url',''),'params':json.dumps(m.get('params',{}),sort_keys=True),'retrieved_utc':m.get('retrieved_utc',m.get('retrieved_at_utc','unknown'))})
    with (OUT/'qa/source_register.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['sidecar','url','params','retrieved_utc']);w.writeheader();w.writerows(sources)
    availability=[]
    for year in [2024,2025]:
        for source,date,note in [('acs2022','2023-12-07','2018–2022 five-year release'),('sld2021','2021-12-31','Conservative end-of-release-year bound, not exact publication day'),('prior_december_dfs',f'{year-1}-12-15','Snapshot membership; not machine opening date'),('prior_year_police','',f'Occurrence year {year-1}; report before {year}-01-01; latest extract, exact as-of unavailable')]:availability.append({'outcome_year':year,'prediction_cutoff':f'{year}-01-01','source':source,'available_by':date,'qualification':note})
    with (OUT/'qa/source_availability.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(availability[0]));w.writeheader();w.writerows(availability)
    manifest=[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='output_manifest.csv']
    with (OUT/'qa/output_manifest.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['file','bytes','sha256']);w.writeheader();w.writerows(manifest)
    phase_path=ROOT/'reports/phase_status.json'
    status=json.loads(phase_path.read_text())
    status.update(phase_3='computationally_complete',phase_3_validation='PASS',phase_3_primary_predictors=14,phase_3_sensitivity_predictors=3)
    phase_path.write_text(json.dumps(status,indent=2)+'\n')
    print(f'Documented {len(summary)} city-year groups; {len(high)} high-missingness flags; {len(highcorr)} high-correlation flags.')
if __name__=='__main__':main()
