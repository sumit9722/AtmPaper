# What was completed

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
