# ATM-site crime study restarted for 2024–2025

This separate project covers **1 January 2024 through 31 December 2025** in New York City, Buffalo and Rochester. Phase 1 working documentation, phase 2 data preparation and phase 3 environmental-feature construction, phase 4 temporal model comparisons and phase 5 city-transfer experiments are computationally complete. Independent research review remains pending.

Phase 5: [city-transfer experiments, complete results and reproduction](results/phase5/README.md). Completed 20-seed matched comparisons with 7,380 evaluations; transfer benefits vary by city, source and model.

Phase 4: [step-by-step procedure, models and results](results/phase4/README.md). Training uses 2024 and testing uses 2025 with spatial separation. Validation passed; the primary numerical improvement gate did not pass.

Phase 3: [feature datasets and documentation](results/phase3/README.md), including methods, results, validation and reproduction instructions. Install `requirements-phase3.txt` when rebuilding phase 3.

Start with the [execution report](reports/execution.md), [study specification](protocol/study_spec.md) and [validation results](reports/validation.json).

- [Combined 2024–2025 site-year panel](data/processed/atm_panel_2024_2025_full_year.csv)
- [2024 panel](data/processed/atm_panel_2024_full_year.csv) — 2023 background
- [2025 panel](data/processed/atm_panel_2025_full_year.csv) — 2024 background
- [City/year summary](data/processed/city_summary.csv), [data dictionary](data/processed/data_dictionary.csv) and [geographic review layer](data/processed/atm_sites_2024_2025.geojson)
- [Offense codebook](data/processed/crime_codebook.csv), [source register](data/processed/source_register.csv) and [raw checksum manifest](data/processed/source_manifest.csv)
- [Manual linkage queue](data/processed/qa/manual_linkage_audit.csv) and [facility review queue](data/processed/qa/facility_review.csv)

The primary panel contains annual full-year, address-continuity-supported sites. Strict exact-identity intervals, inventories and full-year sensitivity cohorts are retained under `data/processed/exposure_2024/` and `exposure_2025/`. No 2024/2025 outcome rows are pooled into one two-year outcome. Raw 2023 crime is baseline information only. The same incident can contribute to multiple nearby sites.

`row_id` is the unique site-year key. `site_id` includes the annual baseline coordinate and can change at the same address; it is not a permanent machine identifier. Main outcomes use latest-archive occurrences; report-date-filtered outcome sensitivities are also provided. Primary background excludes unknown/late reports. See the protocol for exact definitions.

## Reproduce in order

All required source data are copied into this folder; no parent-project output is read. From the repository root, use the existing environment:

```bash
.venv/bin/python restart_2024_2025/scripts/build.py
.venv/bin/python restart_2024_2025/scripts/validate.py
.venv/bin/python restart_2024_2025/scripts/report.py
```

Or move this folder elsewhere, create a Python environment, install `requirements.txt`, and run `python scripts/build.py`, `python scripts/validate.py`, then `python scripts/report.py` from its root. The builds are offline and regenerate derived outputs. Do not use Python's `-O` flag: validation deliberately uses assertions. Cached raw request metadata records acquisition filters, URLs and retrieval dates; this release does not claim fresh retrieval.

Build sequence: freeze the working protocol hash; reconstruct both annual ATM cohorts; normalize/deduplicate 2023–2025 crime; link each outcome year and its prior-year background; export panels/audits; independently validate; generate the report. Rerunning intentionally replaces this folder's derived outputs, leaving archived inputs intact.

The large `data/processed/crime_events_2023_2025.csv` is stored as tracked `.part001`–`.part003` byte parts. The build recreates the complete local CSV. To restore it directly on a fresh checkout, run `python3 scripts/large_artifacts.py restore restart_2024_2025/data/processed/crime_events_2023_2025.csv` from the repository root; the helper verifies the original SHA-256.

The original project is preserved. Phase 4 fold-model training and phase 5 transfer/adaptation experiments are complete. No deployment model is provided. Independent offense, facility, linkage, coordinate-precision and boundary review must be completed before any confirmatory claims.
