# Phase 3 — common features for the 2024–2025 restart

Prepared 17 October 2026, before this restart's feature extraction and any model fitting. This is a retrospective analyst specification, not independent approval or preregistration. Preserve every phase 2 site-year, including missing feature values. Prediction cutoffs are 2024-01-01 and 2025-01-01.

## Sources and timing

Use a fixed ACS 2018–2022 five-year vintage for both years, released 7 December 2023. Use official 2022 TIGER/Line block-group geometry and land area. The previously archived TIGERweb ACS2022 service has identifiers inconsistent with the ACS API and is retained for provenance but excluded from calculations. Attach ACS and EPA independently; their geographic identifiers are not interchangeable.

Use EPA Smart Location Database version 3 (2021 release; 2019 block-group geography, despite the GEOID20 field name). Its underlying measurements predate both outcome years, but some are substantially older. These are archived responses retrieved later, not exact historical database snapshots. Use statewide prior-December DFS ATM inventories (2023-12-15 for 2024, 2024-12-15 for 2025). Use phase 2's report-date-filtered prior-year crime counts. No outcome-year crime, outcome labels, later ATM membership, exposure days or survival flags enter the predictor matrix.

## Frozen dictionary

| Raw feature | Definition/source | Raw unit | Transform | Role |
|---|---|---|---|---|
| background_primary | Phase 2 prior-year robbery/burglary >200–500 m, report before cutoff | cases | log1p | Primary baseline |
| population_density | ACS B01003_001E / TIGER ALAND × 1e6 | residents/km² land | log1p | Primary |
| median_household_income | ACS B19013_001E | 2022 USD | log1p | Primary |
| unemployment_rate | ACS B23025_005E / B23025_003E | fraction | identity | Primary |
| employment_density | EPA D1C | jobs/unprotected acre | log1p | Primary |
| retail_employment_density | EPA D1C5_RET | retail jobs/unprotected acre | log1p | Primary |
| employment_mix | EPA D2B_E5MIXA | entropy 0–1 | identity | Primary |
| road_network_density | EPA D3A | facility miles/mi² land | log1p | Primary |
| auto_road_density | EPA D3AAO | auto-oriented facility miles/mi² land | log1p | Primary |
| intersection_density | EPA D3B | weighted pedestrian intersections/mi² | log1p | Primary |
| transit_service_density | EPA D4D | evening-peak departures/hour/mi² | log1p | Primary |
| auto_job_accessibility | EPA D5AR | travel-time-weighted jobs | log1p | Primary |
| atm_density_500m | Other prior-December DFS identities within 500 m / (pi × 0.5²) | sites/km² circle | log1p | Primary |
| nearest_other_atm | Minimum WGS84 distance to another prior-December DFS identity | metres | log1p | Primary |
| transit_centroid_distance | EPA D4A, block-group population centroid to transit | metres | log1p | Sensitivity |
| transit_job_accessibility | EPA D5BR | travel-time-weighted jobs | log1p | Sensitivity |
| background_unfiltered | Phase 2 prior-year annulus count without report-date cutoff | cases | log1p | Sensitivity |

The 14 primary and three sensitivity columns are fixed. Use common definitions and transformations across all cities and years. No global imputation, scaling, feature selection, fitting or target-dependent decisions. Future preprocessing must be learned inside training folds. Keep labels, city, coordinates and exposure information in separate files; only the schema allowlist is a predictor set.

## Spatial calculations and source handling

Accept exactly one polygon covering the ATM baseline point. Leave unmatched or ambiguous layers missing; preserve candidate identifiers. No nearest-polygon substitution. Repair invalid polygons only if Polygon/MultiPolygon output and relative area change <1e-6; save diagnostics and preserve raw files. Flag proximity within 10 m of block-group boundaries and within 500 m of municipal boundaries.

Preserve ACS E/M/EA/MA fields (estimates, 90% margins of error and annotations). Convert negative/nonfinite numeric sentinels to missing, retain true zeros, and leave zero-denominator rates/densities missing. Flag top/bottom-coded income. Do not treat transit missing values as zero service. EPA attributes describe block groups, not the 50 m outcome buffer; centroid transit distance is not an ATM-to-transit distance. Road density and job accessibility are proxies, not direct major-road distance. Police-station distance is omitted pending a comparable historical source. Do not add protected-demographic variables or current OSM POIs.

For competition, normalize address and round coordinates to seven decimals as in phase 2, collapse exact identities, exclude the focal identity, retain different co-located identities and flag those within 10 m. Accept parseable statewide snapshot points inside the broad New York bounding rectangle; this does not certify each geocode. Include neighbors outside study-city boundaries. Independent ATMs and other states remain outside coverage. Do not filter neighbor sites using future survival. The phase 2 denominator itself is retrospectively selected and remains provisional.

## QA and release

Report join coverage, missingness, quantiles, constant features and pairwise Spearman correlations by city/year and pooled. Flag >20% missingness and absolute correlation >=0.90 without silently removing features or rows. Check date availability, raw hashes/counts, deterministic formulas, all matrix values, independent sample polygon membership and geodesic ATM distances. Freeze inputs and outputs with checksums. Keep confirmatory_modeling_ready=false pending independent phase 2 review and feature approval. Both outcome years were examined in earlier work; neither is a pristine confirmatory holdout.
