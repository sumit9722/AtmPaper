# Results and interpretation

The feature build and automated validation are complete. The data are provisional research inputs. No model accuracy, transfer gain or ATM risk score was calculated.

## Coverage

| City | Historical sites | Full-year sites | Unique ACS joins | Unique EPA joins |
| --- | --- | --- | --- | --- |
| New York City | 2079 | 1117 | 2079 | 2000 |
| Buffalo | 96 | 46 | 96 | 96 |
| Rochester | 58 | 29 | 58 | 57 |

Downloaded geometry covers 8,217 ACS block groups and 7,673 EPA block groups. All 2,233 sites have a unique ACS assignment. EPA assignment is unique for 2,153 sites (96.42%); 40 are unmatched and 40 have multiple covering polygons. Their EPA fields remain missing. In the 1,192-site full-year cohort, 46 sites lack a unique EPA match: 45 NYC, 0 Buffalo and 1 Rochester.

The pre-cutoff statewide competitor inventory contains 5,468 distinct address/coordinate identities. Another 104 raw rows could not be parsed as coordinates and were excluded with an audit record. Every full-year focal site appears in this December 2024 inventory. Some partial-year historical sites first appear later; their baseline membership is flagged rather than invented.

## Missingness and distributions

The main output has 14 primary predictors for 1,192 full-year sites. 987 sites (82.80%) have every primary predictor observed; 205 have at least one missing value. This is a completeness diagnostic, not a proposed complete-case cohort restriction.

Largest full-year primary missingness values:

| City | Feature | Missing / rows | Missing % |
| --- | --- | --- | --- |
| New York City | log1p_median_household_income | 159 / 1117 | 14.23 |
| Buffalo | log1p_median_household_income | 4 / 46 | 8.70 |
| New York City | log1p_transit_service_density | 46 / 1117 | 4.12 |
| New York City | log1p_employment_density | 45 / 1117 | 4.03 |
| New York City | log1p_retail_employment_density | 45 / 1117 | 4.03 |
| New York City | employment_mix | 45 / 1117 | 4.03 |

No primary predictor exceeds 20% missingness in any city in the full-year cohort. No primary predictor is constant within a city in that cohort. The complete [distribution table](../qa/feature_distributions.csv) reports both cohorts, medians, quartiles, extrema and missingness. Values remain unimputed for future training-fold preprocessing.

Across all historical sites, 111 income assignments are upper-coded and 1 is lower-coded. Raw annotations and censoring flags are retained. These are site assignments and may repeat the same block-group estimate; they are not counts of distinct surveyed areas.

## Ranges and redundancy

There are zero detected invalid feature ranges. No primary feature pair reached absolute Spearman correlation 0.90 in the pooled full-year sample or any city's full-year sample (0 flagged pairs; largest absolute correlation 0.860). This does not establish statistical independence or absence of multicollinearity. Small Buffalo and Rochester samples limit the stability of these diagnostics. No feature was removed using outcomes or these pooled diagnostics.

## Geographic quality

| City | Within 10 m of ACS boundary | Within 10 m of EPA boundary | Within 500 m of city boundary |
| --- | --- | --- | --- |
| New York City | 1336 | 1221 | 14 |
| Buffalo | 25 | 19 | 9 |
| Rochester | 13 | 13 | 5 |

These counts refer to all historical sites. Many coordinates lie close to road-based block-group boundaries, particularly in NYC. A unique polygon match is not proof that a noisy point belongs on that side of the boundary. Review location quality and consider boundary sensitivity before interpreting localized context effects. No point was shifted to obtain a desired match.

## What is ready and what remains

Ready: the common feature dictionary, cached sources, reproducible joins and calculations, primary/sensitivity matrices, missingness/range/correlation diagnostics, and checksum manifests. Automated validation passed 25 checks, including independent computational spot checks.

Still pending for research acceptance:

- Phase 2's independent offense/linkage review, historical identity adjudication and exposure-assumption approval.
- Buffalo crime-coordinate suitability for a 50 m outcome and city-edge background truncation.
- Review of the 80 unresolved EPA assignments and the many near-boundary points; retained missingness needs training-fold treatment or a documented revision.
- Researcher approval of the selected road-context proxy and the feature schema. Literal ATM-to-road distance and police-station distance were not calculated.
- A defensible additional outcome period for the blueprint's forward temporal validation. One 2025 outcome year remains insufficient.
- Recognition that the retrospectively selected full-year cohort and later-revised police data are not an exact prospective/as-of-2025 sample.

The status therefore records **computational phase 3 complete; confirmatory modeling not yet approved**. The package supports the next modeling preparation steps without claiming that these research gates have disappeared.
