# Three-city ATM study — phases 1–5

Phase 3 environmental-feature results are available separately in [results/phase3](results/phase3/README.md), including the work completed, methods, results, quality checks and reproduction instructions. Computational validation is complete; the phase 2 research review gates still apply.

Phase 4 now includes a [2024-to-2025 temporal supplement](results/phase4/temporal_v2/README.md), alongside the preserved [original same-year release](results/phase4/README.md). Phase 5 [city-transfer experiments](results/phase5/README.md) compare individual and pooled sources, earlier-target adaptation, and exactly matched target-only controls across 20 seeds. The computational workflows are complete and validated; the phase 4 numerical improvement gate did not pass, and independent scientific review remains pending. The original phase 4 release describes its historical status; the temporal supplement records the extension.

New shared inputs and audited cohorts are documented in [results/temporal_data](results/temporal_data/README.md). Each phase has separate Markdown work, methods, results and reproduction files.

Start with [the execution report](reports/phase_1_2_report.md) and [the location map](reports/atm_locations_map.html).

The main dataset is [the 2025 full-year historical panel](data/processed/atm_panel_2025_full_year.csv). It contains each ATM's latitude/longitude, snapshot-supported exposure, nearby robbery/burglary counts at 25/50/100 metres, and 2024 background crime at >200–500 metres.

- [All historical site-period rows, including partial exposure](data/processed/atm_panel_2025_historical.csv)
- [Current ATM sites for all three cities](data/processed/atm_sites_three_cities.csv)
- [City reference coordinates](data/processed/city_coordinates.csv)
- [Data dictionary](data/processed/data_dictionary.csv)
- [Source register](data/processed/source_register.csv) and [raw-data SHA-256 manifest](data/processed/source_manifest.csv)
- [Phase 1 working specification](protocol/study_spec_v1.0.md) and [historical exposure addendum](protocol/historical_exposure_addendum_v1.1.md)
- [Validation results](reports/validation.json)

Raw downloads are under `data/raw/`; convenient source-field CSV exports are under `data/raw_tables/`. Original supplied files are unchanged. Derived outputs are under `data/processed/`. The OpenStreetMap exports are supplementary candidates, not the primary bank-owned denominator.

Historical exposure assumes continuous activity between adjacent monthly snapshots listing the same site. Actual opening/closing dates remain unknown. Buffalo coordinate precision, facility identity and independent crime/linkage review remain research gates. **The data are prepared for review, not yet certified for confirmatory modeling.**

Rebuild with the scripts listed in the execution report. Raw files are cached and checksummed. Model training is documented in the phase 4/5 result folders; no outcomes are fabricated.
