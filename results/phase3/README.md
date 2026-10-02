# Phase 3 results

Phase 3 computational feature construction is complete and automated validation passed. This folder contains the common environmental inputs for the three-city ATM study. Research acceptance remains pending phase 2 review and approval of the feature definitions; it is not certification for confirmatory modeling.

- [What was done](docs/01_work_completed.md)
- [How it was done](docs/02_methods.md)
- [Results and limitations](docs/03_results.md)
- [Reproduction and file guide](docs/04_reproduce.md)

## Main results

| City | Historical sites | Full-year sites | Unique ACS joins | Unique EPA joins |
| --- | --- | --- | --- | --- |
| New York City | 2079 | 1117 | 2079 | 2000 |
| Buffalo | 96 | 46 | 96 | 96 |
| Rochester | 58 | 29 | 58 | 57 |

The main [full-year feature matrix](data/features_primary_full_year.csv) has **1,192 sites and 14 predictors**, plus a site ID. There are also [all-historical-site features](data/features_primary_all_historical.csv), [three sensitivity predictors](data/features_sensitivity_full_year.csv), [raw context values](data/site_context_raw.csv), and a [site lookup and quality table](data/site_lookup_and_quality.csv).

Use the [feature dictionary](data/feature_dictionary.csv) and [locked schema](data/feature_schema.json) to identify predictors. Outcome labels remain in the existing phase 2 panel and must be joined explicitly by `site_id` later. Geographic IDs, city, coordinates, exposure duration and quality flags are not automatically included as predictors.

987 of 1,192 full-year rows have all 14 primary values present. Missing values are intentional; do not interpret them as zero or automatically discard incomplete rows. Any later imputation must be fitted within training folds.

[Validation results](qa/validation.json) record 25 passed computational checks. [Phase status](qa/phase3_status.json) preserves `confirmatory_modeling_ready=false`. All data and documentation in this folder are covered by [release checksums](release_manifest.sha256).
