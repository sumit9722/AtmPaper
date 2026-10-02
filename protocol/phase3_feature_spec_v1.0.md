# Phase 3 feature specification v1.0

Prepared 2026-10-02 before GIS feature extraction or outcome-model fitting. This freezes the computational candidate dictionary and common transformations; it does not claim researcher approval or resolve phase 2 review gates.

## Scope and cutoff

Prediction cutoff: 2025-01-01. Outcome period: calendar 2025. Build features for all 2,233 interval-supported historical sites and publish a separate full-year subset using the existing phase 2 cohort. Preserve its provisional status. Do not use 2025 crime, future snapshot membership, supported days, or outcome labels as predictors. Cohort construction itself remains retrospective under the phase 2 exposure assumption.

## Common candidate dictionary

Each feature uses the same source and definition in NYC, Buffalo and Rochester. Natural log1p transforms are deterministic; scaling, imputation, model-specific feature selection and tuning must occur inside training folds later.

| Candidate | Source / formula | Unit before transform | Transform | Role |
|---|---|---|---|---|
| background_primary | Phase 2 2024 robbery/burglary, >200–500 m | incident count | log1p | M0 and M1/M2 baseline |
| population_density | ACS B01003_001E / matching 2023 TIGER AREALAND × 1e6 | residents/km² land | log1p | Primary candidate |
| median_household_income | ACS B19013_001E | 2023 USD | log1p | Primary candidate |
| unemployment_rate | ACS B23025_005E / B23025_003E | fraction | identity | Primary candidate |
| employment_density | EPA SLD D1C | jobs/unprotected acre | log1p | Primary candidate |
| retail_employment_density | EPA SLD D1C5_RET | retail jobs/unprotected acre | log1p | Primary candidate |
| employment_mix | EPA SLD D2B_E5MIXA | fixed-five-category entropy, 0–1 | identity | Primary candidate |
| road_network_density | EPA SLD D3A | road facility miles/mi² land | log1p | Primary candidate |
| auto_road_density | EPA SLD D3AAO | auto-oriented facility miles/mi² land | log1p | Primary candidate |
| intersection_density | EPA SLD D3B | weighted pedestrian-oriented intersections/mi² | log1p | Primary candidate |
| transit_service_density | EPA SLD D4D | evening-peak departures/hour/mi² | log1p | Primary candidate |
| auto_job_accessibility | EPA SLD D5AR | travel-time-weighted accessible jobs | log1p | Primary candidate |
| atm_density_500m | Other unique DFS sites within 500 m in Dec 2024 / (pi × 0.5²) | sites/km² circle | log1p | Primary candidate |
| nearest_other_atm | Minimum WGS84 distance to other Dec 2024 DFS site | metres | log1p | Primary candidate |
| transit_centroid_distance | EPA SLD D4A | metres walking distance from block-group population centroid | log1p | Sensitivity only |
| transit_job_accessibility | EPA SLD D5BR | travel-time-weighted accessible jobs | log1p | Sensitivity only |
| background_report_date_cutoff | Phase 2 background restricted by its report-date flag | incident count | log1p | Sensitivity baseline |

The 14 primary candidates are fixed before extraction. Sensitivity columns are explicitly excluded from the primary predictor list. High missingness (>20% within any city), zero variance, and pairwise absolute Spearman correlation >=0.90 will be reported. No labels are inspected to select features and no globally learned preprocessing is applied. A deficient candidate may require subsequent versioned, pre-model amendment; do not silently drop rows or fill missing values.

## Spatial and temporal definitions

Use the ACS 2019–2023 five-year release, available 2024-12-12, and January 1, 2023 TIGERweb block-group polygons. Preserve estimate margins of error and annotations. Density uses official land area, not total polygon area including water.

Use EPA SLD version 3 (2021 release), whose source measurements span earlier years and whose geometry uses 2019 block groups. Its GEOID20 field name does not make it 2020 geography. Join ATM points independently to SLD polygons and ACS polygons; never directly equate their GEOIDs. Preserve separate IDs, ambiguity flags, and unmatched sites. Use polygon covers; if multiple polygons cover the same point, mark primary join ambiguous and leave corresponding predictors missing. No nearest-polygon assignment or invented geocodes.

SLD supplies an established common road and intersection computation from 2018 HERE networks. Its auto-oriented road density is a neighborhood road-context proxy, not ATM-to-road distance or route accessibility. Its transit distances refer to a block-group centroid, not the ATM. Use raw absolute measures, not city-normalized SLD indices. No current OSM features. Police-station distance is omitted: a common verified historical location source has not been established. Do not substitute a current POI snapshot.

For ATM competition, use only the statewide 2024-12-15 DFS archive. Normalize address and deduplicate identical address/coordinates. Exclude the focal site's exact normalized-address/coordinate identity; preserve nearby different identities and flag co-location. Use all valid New York State points, including outside the three cities. Out-of-state and independent nonbank machines remain outside coverage. Do not use subsequent snapshots to select neighboring machines or to estimate 2025 density. Missing baseline membership is a QA flag, not an inferred opening date.

## Quality and release

Keep original source fields and hashes. Report city-level missingness, ranges/quantiles, join coverage, positional/boundary flags, and feature redundancy. Freeze data-only primary matrices, a separate site lookup/QA table, raw context values, and a manifest with hashes. Do not fit models. Keep confirmatory_modeling_ready=false until phase 2 review and feature-schema approval are complete. Current revisions of ACS, SLD and police archives do not constitute exact historical database snapshots; identify this limitation explicitly.
