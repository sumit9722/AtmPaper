# Quality audit and descriptive sensitivities

## Reporting completeness

| year | primary_cases | missing_invalid_report_primary | reported_after_year_primary | primary_coordinates_on_3dp_grid |
| --- | --- | --- | --- | --- |
| 2022 | 1713 | 1212 | 0 | 1713 |
| 2023 | 1804 | 1396 | 4 | 1804 |
| 2024 | 1761 | 0 | 7 | 1761 |
| 2025 | 1630 | 0 | 11 | 1630 |


The missing/invalid count is a record-level audit. Site baselines use the preceding year, so missing 2023 dates affect 2024 prediction inputs. These missing dates are excluded from known-available counts, never silently filled. Even nonmissing Buffalo timestamps remain unverified ingestion proxies.

## Exposure attrition and coordinate movement

| city | outcome_year | available_snapshots | inventory_identities | full_year_sites | drift_10m_full_year_sites | drift_25m_full_year_sites | exact_full_year_sites |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New York City | 2023 | 12 | 3477 | — | — | — | 0 |
| Buffalo | 2023 | 12 | 165 | — | — | — | 0 |
| Rochester | 2023 | 12 | 92 | — | — | — | 0 |
| New York City | 2024 | 14 | 4127 | 1129 | 93 | 1022 | 0 |
| Buffalo | 2024 | 14 | 177 | 48 | 1 | 29 | 0 |
| Rochester | 2024 | 14 | 115 | 24 | 1 | 17 | 0 |
| New York City | 2025 | 14 | 2092 | 1160 | 1139 | 1150 | 1117 |
| Buffalo | 2025 | 14 | 98 | 50 | 47 | 50 | 46 |
| Rochester | 2025 | 14 | 60 | 31 | 30 | 31 | 29 |


A blank 2023 full-year count means unsupported coverage, not zero ATMs. Strict exact identity yields no full-year 2024 cohort; the working 50 m address-continuity rule is therefore a substantive assumption. Smaller drift cutoffs show its effect. Exact identities can fragment physical facilities, which explains why the exact-supported panel has many more rows than the continuity panel. Annual cohorts and reference coordinates differ: the radius figure is not an identified time trend or evidence that crime risk changed at unchanged facilities.

## Full-year 50 m sensitivities

| city | year | sites | positive_sites | positive_reported_by_year_end | positive_nearest_only | event_site_links | multiply_matched_links | boundary_clear_sites | boundary_clear_positive | sites_with_unknown_background_availability |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| New York City | 2024 | 1129 | 662 | 662 | 598 | 2098 | 538 | 1123 | 659 | 0 |
| Buffalo | 2024 | 48 | 16 | 16 | 16 | 33 | 0 | 45 | 16 | 48 |
| Rochester | 2024 | 24 | 6 | 6 | 6 | 19 | 2 | 23 | 6 | 0 |
| New York City | 2025 | 1160 | 655 | 652 | 583 | 2102 | 575 | 1153 | 653 | 0 |
| Buffalo | 2025 | 50 | 14 | 14 | 13 | 23 | 4 | 47 | 14 | 0 |
| Rochester | 2025 | 31 | 8 | 8 | 8 | 11 | 0 | 27 | 6 | 0 |


Repeated event-site links are not independent crimes. Nearest-only and boundary-clear results are descriptive alternatives; no sensitivity has been selected by model performance. Radius-specific results for every cohort are in sensitivity_summary.csv and the radius figure.

## Buffalo conditional rounding scenario

| year | sites | positive_sites | rounding_scenario_definitely_positive | rounding_scenario_possibly_positive |
| --- | --- | --- | --- | --- |
| 2023 | 57 | 17 | 0 | 38 |
| 2024 | 48 | 16 | 0 | 33 |
| 2025 | 50 | 14 | 0 | 37 |


The range above is conditional on rounding error alone. Block-address geocoding can introduce larger displacement, so these columns do not repair positional uncertainty or license confirmatory 50 m claims.

## Comparison with the earlier 2024–2025 data release

| city | year | previous_sites | new_sites | matched_locations | changed_50m_counts | changed_background_counts |
| --- | --- | --- | --- | --- | --- | --- |
| New York City | 2024 | 1129 | 1129 | 1129 | 1 | 0 |
| Buffalo | 2024 | 48 | 48 | 48 | 0 | 0 |
| Rochester | 2024 | 24 | 24 | 24 | 0 | 0 |
| New York City | 2025 | 1160 | 1160 | 1160 | 7 | 0 |
| Buffalo | 2025 | 50 | 50 | 50 | 0 | 0 |
| Rochester | 2025 | 31 | 31 | 31 | 0 | 0 |


Location matching uses city, normalized address, numerical coordinates and year, not the changed hash formatting. Differences are source-vintage and documented data-rule differences. The previous release remains preserved. Do not attribute changed descriptive counts to prediction improvement.

## Independent review

| gate | status | required_evidence |
| --- | --- | --- |
| Construct and offense mapping | PENDING | Independent crime-domain adjudication of robbery/burglary codebook, attempts and case-level duplicate rule |
| Facility identity and continuity | PENDING | Review unique-address matching, coordinate drift, institution changes and nearby facilities; monthly listings do not prove actual operation |
| Incident-site linkage | PENDING | Independent adjudication of stratified event-site audit with reasoned accept/reject decisions |
| Buffalo coordinates | PENDING | Better incident coordinates or approved coarser design; 50 m results are exploratory |
| Temporal availability and reporting | PENDING | Validate Buffalo created_at proxy and missing timestamps; current revisions do not recreate historical availability |
| Historical boundaries and selection | PENDING | Verify municipal vintage and selection from survival/unique-address restrictions; inspect boundary sensitivity |
| Scientific approval and later modeling | PENDING | PI approval of construct, practical-effect threshold and features; independent later holdout still required |


The review queues include source references, geodesic distances, strata and blank reviewer fields. Automatic validation is complete; human adjudication has not occurred.
