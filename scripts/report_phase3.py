"""Generate phase 3 Markdown documentation and an output checksum manifest."""
import csv
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/phase3'
def read(name):
    with (OUT/name).open() as f:return list(csv.DictReader(f))
def md(name,text):(OUT/name).write_text(text.strip()+'\n')
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    status=json.loads((OUT/'qa/phase3_status.json').read_text())
    validation=json.loads((OUT/'qa/validation.json').read_text())
    assert validation['status']=='PASS' and status['validation_status']=='PASS'
    schema=json.loads((OUT/'data/feature_schema.json').read_text())
    cities=read('qa/city_summary.csv');quality=read('data/site_lookup_and_quality.csv')
    context=read('data/site_context_raw.csv');matrix=read('data/features_primary_full_year.csv')
    complete=sum(all(v!='' for v in r.values()) for r in matrix)
    stats=read('qa/feature_distributions.csv')
    full_stats=[r for r in stats if r['cohort']=='full_year' and r['city']!='ALL' and r['feature'] in schema['primary_predictors']]
    missing=sorted([r for r in full_stats if int(r['missing'])],key=lambda r:float(r['missing_fraction']),reverse=True)
    joins=read('qa/spatial_join_audit.csv')
    full_ids={r['site_id'] for r in matrix}
    full_sld_bad=sum(r['layer']=='sld2021' and r['status']!='unique' and r['site_id'] in full_ids for r in joins)
    full_by_city={c:sum(r['site_id'] in full_ids and r['city']==c and r['sld_join_matches']!='1' for r in quality) for c in ['New York City','Buffalo','Rochester']}
    corr=read('qa/feature_correlations.csv')
    max_corr=max((abs(float(r['spearman_rho'])) for r in corr if r['spearman_rho']),default=0)
    high=sum(r['abs_rho_ge_0_90']=='True' for r in corr)
    city_table=table(['City','Historical sites','Full-year sites','Unique ACS joins','Unique EPA joins'],
        [[r['city'],r['historical_sites'],r['full_year_sites'],r['acs_unique_join'],r['sld_unique_join']] for r in cities])
    md('README.md',f'''# Phase 3 results

Phase 3 computational feature construction is complete and automated validation passed. This folder contains the common environmental inputs for the three-city ATM study. Research acceptance remains pending phase 2 review and approval of the feature definitions; it is not certification for confirmatory modeling.

- [What was done](docs/01_work_completed.md)
- [How it was done](docs/02_methods.md)
- [Results and limitations](docs/03_results.md)
- [Reproduction and file guide](docs/04_reproduce.md)

## Main results

{city_table}

The main [full-year feature matrix](data/features_primary_full_year.csv) has **1,192 sites and 14 predictors**, plus a site ID. There are also [all-historical-site features](data/features_primary_all_historical.csv), [three sensitivity predictors](data/features_sensitivity_full_year.csv), [raw context values](data/site_context_raw.csv), and a [site lookup and quality table](data/site_lookup_and_quality.csv).

Use the [feature dictionary](data/feature_dictionary.csv) and [locked schema](data/feature_schema.json) to identify predictors. Outcome labels remain in the existing phase 2 panel and must be joined explicitly by `site_id` later. Geographic IDs, city, coordinates, exposure duration and quality flags are not automatically included as predictors.

{complete} of 1,192 full-year rows have all 14 primary values present. Missing values are intentional; do not interpret them as zero or automatically discard incomplete rows. Any later imputation must be fitted within training folds.

[Validation results](qa/validation.json) record {len(validation['checks'])} passed computational checks. [Phase status](qa/phase3_status.json) preserves `confirmatory_modeling_ready=false`. All data and documentation in this folder are covered by [release checksums](release_manifest.sha256).
''')
    md('docs/01_work_completed.md','''# What was completed

The blueprint's phase 3 task is to create one common environmental feature layer for New York City, Buffalo and Rochester before outcome-model tuning. This delivery completes that computational work with a documented, deliberately limited feature dictionary.

## Work performed

1. Wrote the [phase 3 specification](../../../protocol/phase3_feature_spec_v1.0.md) before extracting the GIS feature values. Defined the January 1, 2025 cutoff, 14 primary candidates, three sensitivity variables, missing-value rules and quality checks.
2. Reused the existing 2019–2023 ACS extract. Downloaded matching 2023 Census block-group polygons and official land areas for the seven study counties.
3. Downloaded the EPA Smart Location Database version 3 context variables and their own 2019 polygons. Independently assigned both geography vintages to historical ATM coordinates.
4. Derived population density, retained income/unemployment controls, and attached employment, retail activity, employment mix, road, intersection, transit and destination-accessibility measures.
5. Rebuilt a statewide, deduplicated December 2024 DFS neighbor inventory. Calculated ATM density within 500 m and nearest-other-ATM distance without consulting 2025 neighbor membership.
6. Carried forward the specified 2024 background-crime baseline and retained a report-date-cutoff sensitivity.
7. Published separate primary and sensitivity predictor matrices for historical and full-year cohorts, plus original-unit values and quality flags.
8. Checked source counts, spatial joins, formulas, missingness, distributions, ranges, correlations, temporal metadata and checksums. Independently recomputed sample spatial matches and geodesic distances.
9. Wrote this documentation and a reproducible output manifest.

## Scope decisions

Road and intersection features use EPA's existing common computation from the 2018 HERE network. Auto-oriented road density is the selected major-road-context proxy. This delivery does not calculate literal ATM-to-road distance or a fresh 500 m street graph. Those would be different feature definitions and require a versioned extension.

Police-station distance is omitted because no verified common historical POI layer was established. Current OSM points are not used for historical prediction. EPA transit-centroid distance is retained only as a sensitivity measure because it is not the ATM's walking distance.

The primary feature matrix is computationally frozen. PI/researcher approval is still pending. Phase 2 audits, Buffalo crime-coordinate uncertainty and the missing forward temporal validation period remain open. No prediction model, transfer result or causal conclusion was produced.
''')
    md('docs/02_methods.md','''# How phase 3 was built

## Sources and timing

| Source | Vintage / availability | Use |
|---|---|---|
| [ACS five-year release](https://www.census.gov/programs-surveys/acs/news/data-releases/2023/release.html) | 2019–2023 survey period; released December 12, 2024 | Population, income and unemployment |
| [Census ACS 2023 TIGERweb](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer/10) | January 1, 2023 geography | Block-group assignment and official land area |
| [EPA Smart Location Database](https://www.epa.gov/smartgrowth/smart-location-mapping) | Version 3 released in 2021; 2019 block-group geometry | Common built-environment context |
| [EPA service](https://geodata.epa.gov/arcgis/rest/services/OA/SmartLocationDatabase/MapServer/1) | Version 3; inputs mainly 2017–2020 | Selected raw indicators and polygons |
| Archived NY DFS version 270 | December 15, 2024 membership snapshot | Pre-cutoff bank-owned/in-bank ATM competition |
| Phase 2 police background | 2024 incident dates; later-retrieved/revised extracts | Previous-year robbery/burglary at >200–500 m |

The EPA [technical guide](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf) is archived under `data/raw/phase3/`. EPA's availability field uses December 31, 2021 as a conservative upper bound within its documented release year, not a claimed exact publication day. Service retrieval dates and SHA-256 hashes are retained separately. These live archived-vintage services do not prove the exact values visible to a user on January 1, 2025. Police background has no asserted exact historical availability date.

Acquisition used 31 sequential public requests: two layer metadata requests, one EPA guide and 28 count/geometry requests. Each request after the first in an invocation was separated by two seconds. Completed responses are cached and checksum-verified. There are no automatic retries and no use of the Census API key. An initial sandbox-blocked connection was followed by an authorized network run.

## Spatial assignment

Each ATM point is joined separately to ACS 2023 and EPA 2019 block groups. EPA's field `GEOID20` is a source identifier for its 2019 geography; it must not be mistaken for 2020 Census geometry. The output retains `acs_geoid_2023`, `sld_geoid_2019`, and the source's older `GEOID10` separately.

The builder uses a Shapely spatial index and polygon `covers` logic. Exactly one match is accepted. Zero matches remain unmatched; multiple matches remain ambiguous. No nearest-polygon substitution or arbitrary tie-break is used. Ambiguous and unmatched values are null, with candidate IDs in the audit.

Two Census polygons and one EPA polygon contained self-intersections. GEOS `make_valid` repaired copies in memory. Repairs were allowed only when the result remained Polygon/MultiPolygon and relative area change was below 0.0001%. The observed maximum was about 0.0000231%. Raw files remain unchanged and repair details are saved in QA. This is a geometry hygiene step, not new geocoding.

Boundary-distance diagnostics use UTM zone 18N for NYC and 17N for Buffalo/Rochester. Sites within 10 m of a block-group boundary and within 500 m of a municipal edge are flagged. The latter uses the phase 2 current city polygon and is only a warning of possible annulus truncation.

## Feature calculations

Population density = ACS population / official Census land square metres × 1,000,000. Water area is excluded from the denominator. Income uses ACS reported 2023 dollars. Unemployment = unemployed civilian population / civilian labor force; zero or missing denominators remain null. Original 90% margins of error and annotations remain available. Top/bottom-coded income is flagged: a reported threshold is not an exact income estimate.

EPA indicators are attached without city-specific rescaling. Density units and definitions remain source-specific: for example, job density uses unprotected acres and road density uses facility miles per square mile. They are neighborhood context, not measurements inside each ATM's 50 m crime buffer. Source negative sentinels, including -99999, become missing; genuine zeros remain zero. Transit sentinels may represent absent service, insufficient GTFS coverage or distance thresholds, so they are not silently recoded as no service.

For ATM competition, deduplicate the December 2024 archive by normalized street address plus coordinates rounded to seven decimal places, matching the identity precision in phase 2. Use all parseable coordinates inside a broad New York bounding rectangle; this removes malformed locations but does not certify geocode accuracy. Exclude only the focal identity. Preserve distinct co-located identities and flag neighbors within 10 m for facility review.

Other-ATM density = other December 2024 sites within 500 m / (pi × 0.5²) square kilometres. Nearest-other-ATM distance is the minimum WGS84 ellipsoidal distance across that statewide inventory. This avoids city-boundary clipping of the ATM denominator, but excludes other states and independent nonbank ATMs. Physical-site identity and operation remain subject to phase 2 review.

All selected right-skewed nonnegative variables use natural log(1 + value); unemployment and entropy remain untransformed. No global imputation, scaling, outlier trimming, learned feature selection or model fitting is performed. The primary list was fixed before extraction; pooled and city-wise correlations are diagnostics only.

## Quality checks and freeze

Missingness and quantiles are reported separately for every city and cohort. Missingness above 20% and absolute pairwise Spearman correlation at least 0.90 are predefined review flags. Correlations use available pairs, report their sample sizes, and do not change the frozen feature set. Validation checks the source counts and source attributes, verifies all deterministic transformations, samples spatial joins without the builder's spatial index, and recomputes sample ATM distances individually. Source and output manifests allow subsequent changes to be detected.

Outcome labels, exposure duration, city, coordinates and administrative geography IDs are stored separately from predictor matrices. Downstream code should use the schema allowlist, not every numeric column in the raw context or lookup tables. Any later source/identity correction must trigger a rebuild and a versioned release before model tuning.
''')
    worst_table=table(['City','Feature','Missing / rows','Missing %'],[[r['city'],r['feature'],f"{r['missing']} / {r['rows']}",f"{100*float(r['missing_fraction']):.2f}"] for r in missing[:6]])
    edge_table=table(['City','Within 10 m of ACS boundary','Within 10 m of EPA boundary','Within 500 m of city boundary'],
        [[r['city'],r['acs_near_boundary_10m'],r['sld_near_boundary_10m'],r['near_city_edge_500m']] for r in cities])
    topcoded=sum(r['income_topcoded']=='True' for r in context);bottomcoded=sum(r['income_bottomcoded']=='True' for r in context)
    md('docs/03_results.md',f'''# Results and interpretation

The feature build and automated validation are complete. The data are provisional research inputs. No model accuracy, transfer gain or ATM risk score was calculated.

## Coverage

{city_table}

Downloaded geometry covers 8,217 ACS block groups and 7,673 EPA block groups. All 2,233 sites have a unique ACS assignment. EPA assignment is unique for 2,153 sites (96.42%); 40 are unmatched and 40 have multiple covering polygons. Their EPA fields remain missing. In the 1,192-site full-year cohort, {full_sld_bad} sites lack a unique EPA match: {full_by_city['New York City']} NYC, {full_by_city['Buffalo']} Buffalo and {full_by_city['Rochester']} Rochester.

The pre-cutoff statewide competitor inventory contains 5,468 distinct address/coordinate identities. Another 104 raw rows could not be parsed as coordinates and were excluded with an audit record. Every full-year focal site appears in this December 2024 inventory. Some partial-year historical sites first appear later; their baseline membership is flagged rather than invented.

## Missingness and distributions

The main output has 14 primary predictors for 1,192 full-year sites. {complete} sites ({100*complete/1192:.2f}%) have every primary predictor observed; {1192-complete} have at least one missing value. This is a completeness diagnostic, not a proposed complete-case cohort restriction.

Largest full-year primary missingness values:

{worst_table}

No primary predictor exceeds 20% missingness in any city in the full-year cohort. No primary predictor is constant within a city in that cohort. The complete [distribution table](../qa/feature_distributions.csv) reports both cohorts, medians, quartiles, extrema and missingness. Values remain unimputed for future training-fold preprocessing.

Across all historical sites, {topcoded} income assignments are upper-coded and {bottomcoded} is lower-coded. Raw annotations and censoring flags are retained. These are site assignments and may repeat the same block-group estimate; they are not counts of distinct surveyed areas.

## Ranges and redundancy

There are zero detected invalid feature ranges. No primary feature pair reached absolute Spearman correlation 0.90 in the pooled full-year sample or any city's full-year sample ({high} flagged pairs; largest absolute correlation {max_corr:.3f}). This does not establish statistical independence or absence of multicollinearity. Small Buffalo and Rochester samples limit the stability of these diagnostics. No feature was removed using outcomes or these pooled diagnostics.

## Geographic quality

{edge_table}

These counts refer to all historical sites. Many coordinates lie close to road-based block-group boundaries, particularly in NYC. A unique polygon match is not proof that a noisy point belongs on that side of the boundary. Review location quality and consider boundary sensitivity before interpreting localized context effects. No point was shifted to obtain a desired match.

## What is ready and what remains

Ready: the common feature dictionary, cached sources, reproducible joins and calculations, primary/sensitivity matrices, missingness/range/correlation diagnostics, and checksum manifests. Automated validation passed {len(validation['checks'])} checks, including independent computational spot checks.

Still pending for research acceptance:

- Phase 2's independent offense/linkage review, historical identity adjudication and exposure-assumption approval.
- Buffalo crime-coordinate suitability for a 50 m outcome and city-edge background truncation.
- Review of the 80 unresolved EPA assignments and the many near-boundary points; retained missingness needs training-fold treatment or a documented revision.
- Researcher approval of the selected road-context proxy and the feature schema. Literal ATM-to-road distance and police-station distance were not calculated.
- A defensible additional outcome period for the blueprint's forward temporal validation. One 2025 outcome year remains insufficient.
- Recognition that the retrospectively selected full-year cohort and later-revised police data are not an exact prospective/as-of-2025 sample.

The status therefore records **computational phase 3 complete; confirmatory modeling not yet approved**. The package supports the next modeling preparation steps without claiming that these research gates have disappeared.
''')
    md('docs/04_reproduce.md','''# Reproduction and file guide

Run from the project root with the existing Python environment. No additional packages are required beyond `requirements.txt`.

```bash
# Optional: restore missing GIS downloads; complete caches require no network calls.
.venv/bin/python scripts/download_phase3.py --stage data

# Offline feature build, independent computational validation, and documentation.
.venv/bin/python scripts/build_phase3.py
.venv/bin/python scripts/validate_phase3.py
.venv/bin/python scripts/report_phase3.py
```

Raw responses are cached under `data/raw/phase3/`. Their `.request.json` sidecars store URLs, parameters, timestamps, byte counts and SHA-256 hashes. Existing ACS data are reused from `data/processed/census/` and `data/raw/census/`. The December 2024 DFS snapshot and historical panels come from phase 2. No network access or API key is needed for a complete cached rebuild.

## Result files

| File / folder | Purpose |
|---|---|
| `data/features_primary_full_year.csv` | Main 1,192-row, 14-predictor matrix plus site ID |
| `data/features_primary_all_historical.csv` | Same predictor definitions for all 2,233 historical sites |
| `data/features_sensitivity_*.csv` | Three separate sensitivity predictors for each cohort |
| `data/site_context_raw.csv` | Original-unit inputs, both geography IDs, ACS uncertainty/annotations and source EPA values |
| `data/site_lookup_and_quality.csv` | City/coordinates, exposure cohort, membership and boundary-quality flags |
| `data/atm_baseline_dec2024.csv` | Deduplicated statewide pre-cutoff neighbor inventory |
| `data/feature_dictionary.csv` | Formulas, units, transforms, vintages, availability qualifications and roles |
| `data/feature_schema.json` | Ordered allowlists and specification hash |
| `qa/city_summary.csv` | Coverage and spatial-quality counts |
| `qa/spatial_join_audit.csv` | Accepted, missing and ambiguous matches with candidate IDs |
| `qa/geometry_repairs_*.csv` | Source geometry issues and constrained in-memory repairs |
| `qa/atm_baseline_exclusions.csv` | Unparseable baseline-coordinate rows |
| `qa/feature_distributions.csv` | Missingness, quantiles and variation by cohort and city |
| `qa/feature_correlations.csv` | Pairwise full-year Spearman diagnostics and sample sizes |
| `qa/range_violations.csv` | Header-only when no invalid range was found |
| `qa/input_manifest.csv` | Hashes of consumed sources, specification and implementation files |
| `qa/validation.json` | Passed checks and remaining independent-review distinction |
| `qa/phase3_status.json` | Computational status and research readiness |
| `release_manifest.sha256` | SHA-256 hashes for every other result artifact |

CSV missing values are empty cells. Import geographic identifiers as strings. Boolean QA fields use `True`/`False`. Model matrices contain only `site_id` and allowlisted predictors; use the lookup table for city/spatial grouping and join outcomes from phase 2 by exact `site_id`.

The builder checks the existing frozen schema against the specification. For a deliberate feature change, preserve this release and make a versioned amendment instead of bypassing that check. Correcting phase 2 identities requires rebuilding dependent phase 3 results before tuning models. Do not silently remove incomplete rows or include QA/identity fields as model inputs.

To check this release from inside `results/phase3`:

```bash
sha256sum --check release_manifest.sha256
```
''')
    paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='release_manifest.sha256')
    (OUT/'release_manifest.sha256').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in paths))
    print(f'Wrote five Markdown files and a {len(paths)}-file result manifest.')

if __name__=='__main__':main()
