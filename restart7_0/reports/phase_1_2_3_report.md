# Restart 7 execution report

## Phase 1 — revised design

[Study specification](../protocol/study_spec.md) freezes the retrospective
three-city coordinate-proximity question, offense correction, conservative
cohort rules, common information regime and stronger future baseline. This
revision follows the repository review; it is not a preregistration. No earlier
model result is attributed to this revised cohort.

## Phase 2 — corrected panels

Reused 4,018 main/partial rows without changing their exposure, coordinates or
historical identity. Removed 9,192 vehicle-burglary cases from
278,394 inherited cases, leaving 269,202. This includes Chicago
IUCR 0760 as well as NYC truck-burglary codes. The changes apply to outcomes,
annular background, prior local crime and monthly counts.

| city | year | base_cases | excluded_vehicle_cases | retained_cases |
| --- | --- | --- | --- | --- |
| New York City | 2022 | 33251 | 1272 | 31979 |
| New York City | 2023 | 30670 | 1266 | 29404 |
| New York City | 2024 | 29602 | 1153 | 28449 |
| New York City | 2025 | 27843 | 1232 | 26611 |
| Chicago | 2022 | 16465 | 0 | 16465 |
| Chicago | 2023 | 18445 | 1 | 18444 |
| Chicago | 2024 | 17438 | 773 | 16665 |
| Chicago | 2025 | 15370 | 3495 | 11875 |
| Los Angeles | 2022 | 23963 | 0 | 23963 |
| Los Angeles | 2023 | 23920 | 0 | 23920 |
| Los Angeles | 2024 | 22778 | 0 | 22778 |
| Los Angeles | 2025 | 18649 | 0 | 18649 |

At 50 m, 34 full-year master labels change from positive to negative:

| city | year | positive_to_negative_50m |
| --- | --- | --- |
| New York City | 2024 | 11 |
| New York City | 2025 | 4 |
| Chicago | 2024 | 2 |
| Chicago | 2025 | 17 |
| Los Angeles | 2024 | 0 |
| Los Angeles | 2025 | 0 |

These are offense-only changes on the same inherited sites; they do not combine
the effect of cohort exclusions with the offense change.

The core contains 1,790 site-years across 962 distinct mapped
OSM objects and 664 EPA block groups. These are repeated observational
units, not independent samples. Point-only and explicit-ATM-tag views are also
available; alternative views must not be stacked. Nearest assignments use the
eligible sites within each view.

| city | year | site_years | positive_50m | unique_epa_block_groups |
| --- | --- | --- | --- | --- |
| New York City | 2024 | 557 | 350 | 394 |
| New York City | 2025 | 611 | 345 | 429 |
| Chicago | 2024 | 190 | 111 | 134 |
| Chicago | 2025 | 212 | 87 | 145 |
| Los Angeles | 2024 | 108 | 37 | 72 |
| Los Angeles | 2025 | 112 | 37 | 74 |

The full master remains available for sensitivity. The source review identified
five LA burglary-code records with inconsistent descriptions; their native
classification is retained and a separate exclusion sensitivity is supplied.
This is flagged evidence, not an invented replacement offense. All original
632 facility-pair review records and 1,205 sampled linkage-review records retain
their human-review status. Core exclusions mitigate selected issues without
claiming that a human has adjudicated them.

## Phase 3 — usable feature specifications

The common baseline is fixed prior local crime within 50 m plus prior annular
crime at >200–500 m, both log1p transformed and both occurrence-year counts from
the latest cached extract in all three cities. The primary extension adds the
same 19 inherited ACS/SLD environmental predictors. The original mapped-ATM
competition measures are sensitivity variables, not facility-verified density.

Separate NYC/LA report-filtered matrices retain historical-report-date rules.
They are not combined with Chicago unfiltered predictors. Exported training-label
sensitivities identify reports before the following January 1. Neither filtering
nor these matrices establish an archived historical database.

The expanded exploratory export contains 107 predictors, dropping six exact
aliases and the three metropolitan totals. All retained environmental values and
the primary transforms are inherited unchanged. No imputation, scaling,
selection against outcomes, or modeling occurred. Partial 2023 retains missing
ACS and ATM-competition values.

## Validation and remaining limits

12 automated validation groups passed: input integrity,
unchanged exposure, offense conservation, independent cohort membership,
complete link/count replay, all subset nearest assignments, monthly reconciliation,
prior-cutoff rules, an independent geodesic omission check of 18 sites,
feature/label alignment, and preservation of human-review status.

Block-geocode accuracy, actual ATM identity/operation, mapping coverage, survivor
selection, LA source comparability and independent codebook review remain open.
The untouched later test period is absent. Phases 4–5 were not run. The result is
a corrected, reproducible exploratory data release, not certified ATM risk data.

See [review-by-review decisions](../qa/review_resolution.csv),
[sample/attrition tables](../qa/cohort_attrition.csv),
[changed cells](../qa/panel_changes.csv), and
[validation](../qa/validation.json).
