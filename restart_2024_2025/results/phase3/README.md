# Phase 3 — common environmental features, 2024–2025

Computationally complete and validated: **2,442 site-year rows**, **14 primary** and **3 sensitivity** predictors. Independent scientific review remains pending.

- [Work completed](docs/01_work_completed.md)
- [Methods and limitations](docs/02_methods.md)
- [Results and quality findings](docs/03_results.md)
- [Reproduction](docs/04_reproduce.md)
- [Primary matrix](data/features_primary.csv), [sensitivity matrix](data/features_sensitivity.csv), [frozen schema](data/feature_schema.json), [dictionary](data/feature_dictionary.csv)
- [Raw context](data/site_context_raw.csv), [site lookup/QA](data/site_lookup_and_quality.csv), [validation](qa/validation.json)

Both years use the fixed pre-2024 ACS vintage and EPA SLD 2021. ATM competition and crime background use each year's prior-period data. No labels are predictors and no models were fitted. Read the results for missingness and redundancy flags before modeling.
