# Restart 7 — review fixes through phases 1–3

Computationally complete and validated. Built incrementally from verified
Restart 6 artifacts; **no source downloads, global spatial rematching or model
fitting**. Scientific review remains pending.

- Corrected master: **2,731 full-year site-years**, 2024–2025.
- Conservative core: **1,790 site-years**, 962 distinct OSM objects.
- Separate partial-2023 supplement: **1,287 rows**.
- **9,192 vehicle-burglary cases** excluded consistently from outcomes and prior crime.
- Primary matrix: **2 fixed crime predictors + 19 environmental predictors**.
- Expanded exploratory supplement: **107 environmental predictors**, after removing six redundant aliases and three city proxies.

| city | year | site_years | positive_50m | unique_epa_block_groups |
| --- | --- | --- | --- | --- |
| New York City | 2024 | 557 | 350 | 394 |
| New York City | 2025 | 611 | 345 | 429 |
| Chicago | 2024 | 190 | 111 | 134 |
| Chicago | 2025 | 212 | 87 | 145 |
| Los Angeles | 2024 | 108 | 37 | 72 |
| Los Angeles | 2025 | 112 | 37 | 74 |

The core excludes centroids, unresolved close objects, coordinate drift >10 m
and boundary-truncated background buffers. Point bank objects tagged with ATMs
remain mapped locations, not verified machine positions. All three cities use
the same explicitly retrospective crime baseline. Report-filtered NYC/LA
matrices are separate sensitivities; Chicago's report dates are not invented.

The 50 m endpoint describes proximity to **released coordinates**. Physical
distance accuracy, ATM operation and ATM targeting are unverified. No radius
has been certified. The surviving cohort and old environmental vintages remain
retrospective limitations; this release establishes no predictive improvement.

[Execution report](reports/phase_1_2_3_report.md) ·
[Methods](reports/methods.md) · [Reproduce](reports/reproduce.md) ·
[Review resolution](qa/review_resolution.csv) · [Validation](qa/validation.json) ·
[Remaining scientific gates](qa/research_review_gates.csv)

[Core panel](data/processed/atm_panel_core_2024_2025.csv) ·
[Corrected full panel](data/processed/atm_panel_full_year_2024_2025.csv) ·
[Core feature matrix](results/phase3/data/features_primary_core_2024_2025.csv) ·
[Feature schema](results/phase3/data/feature_schema.json) ·
[Outcomes](results/phase3/data/outcomes.csv) ·
[Lookup and grouping keys](results/phase3/data/site_lookup_and_quality.csv)

```bash
.venv/bin/python restart7_0/scripts/run_all.py
```

This is a dependent incremental release: keep the referenced Restart 6 files.
Original cached source paths are interpreted relative to Restart 6 when their
`source_path_base` is `release_root`, and relative to the repository when it is
`project_root`. Input/output manifests and a reuse register document the chain.

OSM © OpenStreetMap contributors, [ODbL](https://www.openstreetmap.org/copyright),
via HeiGIT ohsome. See [source decisions](protocol/source_decisions.md).
