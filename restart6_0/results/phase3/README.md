# Restart 6 — Phase 3

**Computationally complete and validated.** Scientific review remains pending; no models were fitted.

Built **2,731 main site-years** (2024–2025) with **28 primary and 9 sensitivity predictors**, plus a separate **1,287-row partial-2023 supplement**. All 10 validation groups and four synthetic regression tests passed. Phase 1–2 artifacts are unchanged.

| City | Year | Site-years | Unique ACS joins | Unique EPA joins | ATM-density coverage |
| --- | --- | --- | --- | --- | --- |
| New York City | 2023 | 680 | 0 | 680 | 0 |
| Chicago | 2023 | 441 | 0 | 441 | 0 |
| Los Angeles | 2023 | 166 | 0 | 166 | 0 |
| New York City | 2024 | 702 | 702 | 702 | 702 |
| Chicago | 2024 | 443 | 443 | 443 | 440 |
| Los Angeles | 2024 | 174 | 174 | 174 | 174 |
| New York City | 2025 | 750 | 750 | 750 | 750 |
| Chicago | 2025 | 482 | 482 | 482 | 479 |
| Los Angeles | 2025 | 180 | 180 | 180 | 180 |

Chicago's report-filtered crime predictors stay missing because original report dates are unavailable. Partial 2023 lacks pre-cutoff ACS 2022 and December 2022 ATM competition. Missingness is explicit; there was no imputation or row dropping. `confirmatory_modeling_ready=false`.

[Work completed](docs/01_work_completed.md) · [Methods](docs/02_methods.md) · [Results](docs/03_results.md) · [Reproduce](docs/04_reproduce.md) · [Validation](qa/validation.json)

[Main feature matrix](data/features_primary_full_year_2024_2025.csv) · [Sensitivity matrix](data/features_sensitivity_full_year_2024_2025.csv) · [Schema](data/feature_schema.json) · [Dictionary](data/feature_dictionary.csv) · [Lookup and quality](data/site_lookup_and_quality.csv) · [Source register](data/source_register.csv)

```bash
.venv/bin/python restart6_0/scripts/run_phase3.py
```

OSM data © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright), via HeiGIT ohsome. Other inputs: US Census Bureau and EPA.
