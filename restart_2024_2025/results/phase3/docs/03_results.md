# Phase 3 results

Computational validation: **PASS**. All **2,442** phase 2 site-years were retained, with **14 primary predictors** and **three sensitivity predictors**. No models were fitted.

| Year | City | Rows | ACS unique joins | EPA unique joins | Within 500 m of city edge |
|---|---|---:|---:|---:|---:|
| 2024 | New York City | 1129 | 1129 | 1129 | 6 |
| 2024 | Buffalo | 48 | 48 | 48 | 2 |
| 2024 | Rochester | 24 | 24 | 24 | 1 |
| 2025 | New York City | 1160 | 1160 | 1112 | 7 |
| 2025 | Buffalo | 50 | 50 | 50 | 3 |
| 2025 | Rochester | 31 | 31 | 30 | 4 |


ACS uniquely joins every row. EPA lacks a unique match for **49 site-years**, all in 2025; their EPA values remain missing and the exact candidate-match status is preserved in the spatial audit. The 2025 coordinates are much more often within 10 m of a block-group boundary than the 2024 coordinates. This is consistent with the documented historical coordinate revision; it is not evidence of an environmental change. Boundary-sensitive feature changes need independent positional review.

## Missingness and redundancy

No city/year feature exceeds 20% missingness.

There are 0 constant/all-missing city-year feature diagnostic rows and 0 correlation rows with |rho| >=0.90 across the city/year and pooled diagnostic groups. These are review flags, not independent statistical discoveries; groups overlap. Detailed ranges, quantiles, pairwise sample sizes and correlations are in `qa/feature_distributions.csv` and `qa/feature_correlations.csv`. No automatic feature removal or imputation was performed.

## Validation evidence

The validator checked all input hashes, archived source hashes, ACS geometry/attribute coverage, EPA API polygon counts, all raw attributes and transformations, annual exports and complete row alignment. It independently checked polygon membership and geodesic ATM competition for 30 rows (five per city/year). This is exhaustive for formulas and source-value reconciliation, sampled for spatial computations. Validation does not certify source geocoding accuracy or human research acceptance.

Independent phase 2 review and feature-schema approval remain pending. Buffalo precision, historical ATM continuity, the permitted 50 m ATM drift, survival selection, city-edge truncation, stale neighborhood measures and current revisions of historical sources limit interpretation. Both outcome years were inspected previously. `confirmatory_modeling_ready=false` is preserved.
