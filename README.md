# Three-city ATM study — phases 1–5

The latest [Restart 6.0](restart6_0/README.md) completes phases 1–2 for **New York City, Chicago, and Los Angeles city**. Its exploratory historical OpenStreetMap cohort uses 108 verified city/date snapshots from February 2023–January 2026 and provides **2,731 full-year site-years for 2024–2025** plus **1,287 partial-2023 site-periods**. Ten validation groups passed, including checks of all 527,429 crime-to-site links and monthly/annual reconciliation. Start with the [execution report](restart6_0/reports/phase_1_2_report.md), [offline ATM map](restart6_0/reports/atm_locations_map.html), or [reproduction instructions](restart6_0/reports/reproduce.md). The NYC DFS reference cohort remains separate. Scientific review is pending; no models were fitted.

The preserved [Restart 5.0](restart5_0/README.md) completes phases 1–2 for the longest recovered continuous ATM snapshot period: February 2023–January 2026. It provides 2,442 full-year site-years for 2024–2025 and 1,271 separately labeled partial-2023 site-periods, with fresh crime extracts, exposure/precision/reporting audits and independent automated validation. The [execution report](restart5_0/reports/phase_1_2_report.md) records the user-directed replacement of the ten-year plan, lessons from previous attempts, and pending scientific review. No models were fitted in this restart.

The preserved [Restart 4.0](restart_4_0/README.md) is computationally complete and validated through Phase 5. Training-only selection identifies prior-year nearby crime as the strongest additional predictor; primary 2025 average precision improves from 0.7195 to 0.8254, with a paired spatial 95% interval of +0.0652 to +0.1336 for the gain. Corrected Phase 5 inference is complete: 9 of 54 transfer comparisons meet the declared support rule after Holm adjustment. The [Phase 5 report](restart_4_0/results/phase5/docs/03_results.md) includes every comparison. These findings remain exploratory; independent scientific review is pending.

The preserved [2024–2025 housing-context restart](restart_3_0/README.md) is computationally complete through Phase 5. Its [bullet-point professor report](restart_3_0/Research_Update_for_Professor.md) presents the earlier results and remaining research-review gates. The earlier releases below remain preserved.

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

Three generated CSVs exceeding GitHub's 100 MB file limit are stored as ordered, checksum-verified parts. Run `python3 scripts/large_artifacts.py restore` from the repository root to reconstruct all three exact CSVs before direct inspection; the release rebuild commands also regenerate their outputs. The original CSVs are ignored by Git. See [large_artifacts.json](large_artifacts.json) for sizes and SHA-256 hashes.
