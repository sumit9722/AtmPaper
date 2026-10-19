"""Generate the phase completion report and geographic review artifact."""
import collections,csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'data/processed'
def read(name):
    with (OUT/name).open() as f:return list(csv.DictReader(f))
def main():
    validation=json.loads((ROOT/'reports/validation.json').read_text());assert validation['status']=='PASS'
    panel=read('atm_panel_2024_2025_full_year.csv'); summary=read('city_summary.csv')
    table='| Outcome year | City | Full-year sites | Sites with crime within 50 m |\n|---|---|---:|---:|\n'+''.join(f"| {r['year']} | {r['city']} | {r['full_year_sites']} | {r['positive_50m']} |\n" for r in summary)
    exact={year:len(read(f'exposure_{year}/qa/exact_identity_full_year.csv')) for year in [2024,2025]}
    events=read('crime_primary_2023_2025.csv'); counts=collections.Counter((e['event_date'][:4],e['city']) for e in events)
    event_table='| Crime year | City | Unique valid primary cases |\n|---|---|---:|\n'+''.join(f'| {year} | {city} | {n} |\n' for (year,city),n in sorted(counts.items()))
    text=f'''# Phases 1 and 2 — 2024–2025 restart

Prepared 17 October 2026. Computational work and automated validation are complete. Independent scientific acceptance remains pending. The study covers **1 January 2024 through 31 December 2025** as two annual site panels, not a single pooled two-year label. No models were fitted.

## Phase 1: define and document the study

1. Fixed the three municipal populations and the DFS bank-owned ATM denominator in `protocol/study_spec.md`.
2. Defined robbery/burglary as the primary nearby-crime outcome, 50 m as the primary radius and 25/100 m as sensitivities. Stored all observed offense mappings in `data/processed/crime_codebook.csv`.
3. Specified 2023 background for 2024 outcomes and 2024 background for 2025 outcomes. The primary prior-year count uses report dates before the outcome year; unfiltered and missing/late-report alternatives are retained.
4. Defined one consistent address-continuity exposure rule for both years, independently of crime counts, and retained the exact-identity sensitivity. Frozen specification hash: `reports/protocol_freeze.json`.
5. Recorded the later model/evaluation plan and independent acceptance gates. This is retrospective documentation after previous analyses; it is not preregistered or researcher-signed.

## Phase 2: acquire, clean, link and validate

1. Copied official archived raw data and request metadata into this standalone folder. Inputs are preserved downloads from the earlier work, not new downloads. Raw crime coverage includes 2023–2025 and ATM snapshots span December 2023–January 2026. NYC 2023 covers robbery/burglary; NYC 2024–2025 also includes selected larceny; Buffalo/Rochester include all returned categories. Source URLs, retrieval times and SHA-256 checksums are registered.
2. Selected municipalities by WGS84 point-in-polygon. Retained original event fields, offense mappings, excluded records, duplicate-case audit and monthly coverage. One city case contributes once across the extraction, prioritized by offense and datetime as specified.
3. Reconstructed monthly exact-identity intervals, including partial-year exposure and inventory. Exact-identity full-year counts: **{exact[2024]} in 2024; {exact[2025]} in 2025**. The coordinate revision makes the strict 2024 cohort empty. These tables remain available under `data/processed/exposure_2024/` and `exposure_2025/`.
4. Built the working full-year cohort separately for each year: unique city/address in all 14 bracketing snapshots, maximum coordinate displacement 50 m from the prior-December baseline. Supported days are 366 and 365. This assumes continuity between observations; actual active days and opening/closing dates are deliberately blank. The annual baseline coordinate can differ between years. `row_id` uniquely identifies a site-year; `site_id` includes coordinates and must not be treated as a permanent equipment ID.
5. Linked primary incidents by final WGS84 ellipsoidal distances. Saved outcome and prior-year annulus links, counts, binary labels, report-date sensitivity, offense components, multiplicity and nearest-cohort-site sensitivity. Nearest assignment is within the eligible annual cohort. Generated nearby-facility and stratified manual-linkage review queues.
6. Independently checked raw hashes and API counts/object IDs, both annual exposures, unique site-year keys, all link distances, count reconciliation, nearest/multiple assignments and brute-force candidate-search completeness on up to ten sites per city/year. Saved result: **{validation['status']}** in `reports/validation.json`.

## Results

{table}

Total: **{len(panel):,} site-year rows**. The same physical address can appear in both years, so this is not a count of distinct machines. The 2025 cohort differs from the original release's 1,192 exact-identity sites because the restart applies the same address-continuity rule to both years. The old release remains unchanged.

{event_table}

There are {validation['link_rows']:,} event–site links across the two panels, including backgrounds. One incident can link to multiple sites and 2024 incidents can be both 2024 outcomes and 2025 background. Main outcome counts use occurrences in the latest archive; the `primary_reported_count_*` sensitivity requires reporting before the next year. Both are retrospective proxies, not an as-of database reconstruction.

## Deliverables and remaining gates

The combined dataset is `data/processed/atm_panel_2024_2025_full_year.csv`; separate annual CSVs, a data dictionary, city summary and GeoJSON are alongside it. Raw inputs, normalized crime data, source register, manifest, interval inventories and review queues are included. Reproduction commands are in README.md.

Independent offense/codebook review, facility/address-continuity review, manual spatial-link review, Buffalo coordinate-precision assessment and boundary-vintage/edge assessment remain pending. A 50 m allowed ATM-coordinate drift is substantial relative to the outcome radius and needs sensitivity review. Historical monthly membership does not prove continuous operation. Buffalo created_at is an availability proxy; municipal clipping can truncate surrounding crime. These limitations keep `confirmatory_eligible=false`. Automated passing checks do not complete human research approval.
'''
    (ROOT/'reports/execution.md').write_text(text)
    (ROOT/'reports/phase_status.json').write_text(json.dumps({'coverage_start':'2024-01-01','coverage_end':'2025-12-31','background_years':[2023,2024],'phase_1':'working_documentation_complete','phase_2':'computationally_complete','automated_validation':'PASS','independent_scientific_review':'PENDING','site_year_rows':len(panel)},indent=2)+'\n')
    features=[{'type':'Feature','geometry':{'type':'Point','coordinates':[float(p['longitude']),float(p['latitude'])]},'properties':p} for p in panel]
    (OUT/'atm_sites_2024_2025.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
    print('Report, phase status and GeoJSON generated.')
if __name__=='__main__':main()
