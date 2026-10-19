# Phases 1 and 2 — 2024–2025 restart

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
3. Reconstructed monthly exact-identity intervals, including partial-year exposure and inventory. Exact-identity full-year counts: **0 in 2024; 1192 in 2025**. The coordinate revision makes the strict 2024 cohort empty. These tables remain available under `data/processed/exposure_2024/` and `exposure_2025/`.
4. Built the working full-year cohort separately for each year: unique city/address in all 14 bracketing snapshots, maximum coordinate displacement 50 m from the prior-December baseline. Supported days are 366 and 365. This assumes continuity between observations; actual active days and opening/closing dates are deliberately blank. The annual baseline coordinate can differ between years. `row_id` uniquely identifies a site-year; `site_id` includes coordinates and must not be treated as a permanent equipment ID.
5. Linked primary incidents by final WGS84 ellipsoidal distances. Saved outcome and prior-year annulus links, counts, binary labels, report-date sensitivity, offense components, multiplicity and nearest-cohort-site sensitivity. Nearest assignment is within the eligible annual cohort. Generated nearby-facility and stratified manual-linkage review queues.
6. Independently checked raw hashes and API counts/object IDs, both annual exposures, unique site-year keys, all link distances, count reconciliation, nearest/multiple assignments and brute-force candidate-search completeness on up to ten sites per city/year. Saved result: **PASS** in `reports/validation.json`.

## Results

| Outcome year | City | Full-year sites | Sites with crime within 50 m |
|---|---|---:|---:|
| 2024 | New York City | 1129 | 662 |
| 2024 | Buffalo | 48 | 16 |
| 2024 | Rochester | 24 | 6 |
| 2025 | New York City | 1160 | 652 |
| 2025 | Buffalo | 50 | 14 |
| 2025 | Rochester | 31 | 8 |


Total: **2,442 site-year rows**. The same physical address can appear in both years, so this is not a count of distinct machines. The 2025 cohort differs from the original release's 1,192 exact-identity sites because the restart applies the same address-continuity rule to both years. The old release remains unchanged.

| Crime year | City | Unique valid primary cases |
|---|---|---:|
| 2023 | Buffalo | 1804 |
| 2023 | New York City | 30666 |
| 2023 | Rochester | 1489 |
| 2024 | Buffalo | 1761 |
| 2024 | New York City | 29595 |
| 2024 | Rochester | 1366 |
| 2025 | Buffalo | 1630 |
| 2025 | New York City | 27709 |
| 2025 | Rochester | 970 |


There are 163,052 event–site links across the two panels, including backgrounds. One incident can link to multiple sites and 2024 incidents can be both 2024 outcomes and 2025 background. Main outcome counts use occurrences in the latest archive; the `primary_reported_count_*` sensitivity requires reporting before the next year. Both are retrospective proxies, not an as-of database reconstruction.

## Deliverables and remaining gates

The combined dataset is `data/processed/atm_panel_2024_2025_full_year.csv`; separate annual CSVs, a data dictionary, city summary and GeoJSON are alongside it. Raw inputs, normalized crime data, source register, manifest, interval inventories and review queues are included. Reproduction commands are in README.md.

Independent offense/codebook review, facility/address-continuity review, manual spatial-link review, Buffalo coordinate-precision assessment and boundary-vintage/edge assessment remain pending. A 50 m allowed ATM-coordinate drift is substantial relative to the outcome radius and needs sensitivity review. Historical monthly membership does not prove continuous operation. Buffalo created_at is an availability proxy; municipal clipping can truncate surrounding crime. These limitations keep `confirmatory_eligible=false`. Automated passing checks do not complete human research approval.
