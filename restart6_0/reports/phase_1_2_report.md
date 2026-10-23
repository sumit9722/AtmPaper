# Restart 6 — phases 1–2 execution report

Computational build and automated validation passed. Independent scientific review remains pending; `confirmatory_eligible=false`. No models were fitted.

## Population and exposure

The requested cities are **New York City, Chicago, and Los Angeles city**. The common exploratory cohort uses historical OpenStreetMap ATM objects and banks explicitly tagged `atm=yes`. The inherited official NYC DFS cohort remains separately available under `data/raw/inherited/dfs_nyc_*.csv`.

| City | 2024 full-year sites | 2025 full-year sites | 2023 partial sites |
| --- | --- | --- | --- |
| New York City | 702 | 750 | 680 |
| Chicago | 443 | 482 | 441 |
| Los Angeles | 174 | 180 | 166 |

There are 2,731 full-year site-years for 2024–2025 and 1,287 partial-2023 site-periods. Partial 2023 covers February 22–December 31 (313 days). The 36 snapshot dates match Restart 5. All 14 observations must support a full year; OSM type/ID continuity allows at most 50 m coordinate drift. Exact-coordinate, <=10/25 m drift, point-only and boundary-clear sensitivities are published separately. Mapping history is not verified operating history. Do not stack the alternative panels.

## Crime inputs

| City | 2022 baseline | 2023 | 2024 | 2025 |
| --- | --- | --- | --- | --- |
| New York City | 33251 | 30670 | 29602 | 27843 |
| Chicago | 16465 | 18445 | 17438 | 15370 |
| Los Angeles | 23963 | 23920 | 22778 | 18649 |

Counts are unique valid robbery/burglary cases after clipping, exclusions and declared duplicate resolution. LA combines legacy and consolidated NIBRS data; the legacy feed alone has no 2025 records. Case-number matches are collapsed, but an authoritative cross-system ID mapping is unavailable, so residual duplicates/comparability remain a review gate. Chicago's original report date is unavailable; its report-filtered background and reported-outcome counts are blank. Its unfiltered background remains labeled retrospective context.

## Reuse

Reused verified Restart 5 NYC crime and official reference panels, monthly dates, full/partial-year design, exposure-continuity algorithm, WGS84 distance matching, 25/50/100 m outcomes, >200–500 m prior-year background, nearest-site sensitivity, boundary diagnostics and site-month aggregation. `inherited_sources.csv` records source and filtered-copy hashes. Chicago/LA need new sources, city-specific UTM projections and crime adapters. Older releases and model results were preserved.

## Validation and limitations

10 validation groups passed, including source hashes and pagination, raw OSM reconciliation, independently reconstructed full-year membership, all 527,429 link distances/time windows, full count replay, 36 sampled sites checked against every eligible event without the builder's spatial index, and monthly/annual reconciliation. These are automated checks performed in this session, not independent human scientific approval.

Chicago and LA crime points are public block geocodes. Small-radius counts describe proximity to those released points and cannot establish exact ATM exposure or ATM-targeted crime. OSM coverage and duplicate physical facilities, LA's March 2024 reporting break, unavailable Chicago report dates, latest-extract timing, and current municipal boundaries limit interpretation. See `qa/research_review_gates.csv` and the saved source metadata.

## Files

- [Full-year panel](../data/processed/atm_panel_full_year_2024_2025.csv)
- [Partial 2023 panel](../data/processed/atm_panel_partial_2023.csv)
- [Monthly panel](../data/processed/atm_site_month_panel.csv)
- [Offline ATM map](atm_locations_map.html)
- [Validation](validation.json)
- [Reproduction](reproduce.md)
- [Source register](../data/processed/source_register.csv)

OSM data © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), extracted via HeiGIT ohsome API v2. Crime sources: [Chicago](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2), [LA legacy](https://data.lacity.org/Public-Safety/Crime-Data-from-2020-to-2024/2nrs-mtv8), [LA NIBRS](https://data.lacity.org/Public-Safety/LAPD-NIBRS-Offenses-Dataset/k7nn-b2ep), and the inherited [NYPD release](https://data.cityofnewyork.us/Public-Safety/NYPD-Complaint-Data-Historic/qgea-i56i).
