# Reproduction

From the repository root, use the existing environment:

```bash
.venv/bin/python restart5_0/scripts/run_all.py
```

This is an offline rebuild from restart5_0/data/raw. It requires no model fitting and does not rewrite earlier releases. It verifies current raw input hashes and the stored parts of the large link table before rebuilding, then rebuilds crime normalization, exposure, panels, manifests, independent validation and reports. A failure stops the run. The final artifact manifest hashes stored derived tables, protocol, scripts, reports and figures, excluding the manifest itself. The large link CSV is regenerated locally and checked against the checksum in ../large_artifacts.json; its tracked byte parts are included in the manifest. Input retrieval timestamps remain fixed; environment metadata may differ on another machine.

For direct inspection on a fresh checkout, run `python3 scripts/large_artifacts.py restore restart5_0/data/processed/event_atm_links.csv` from the repository root. This concatenates the tracked parts and verifies the exact original SHA-256. The complete CSV is intentionally ignored by Git.

Python dependencies are in restart5_0/requirements.txt; exact installed versions and Python version are recorded in reports/environment.json. The existing environment runs Python 3.14. For a new environment, install the listed packages. The generated source register and request sidecars record URLs, filters, retrieval dates and original SHA-256 digests.

## Acquisition provenance

The earlier ten-year acquisition fetched 2015–2025 crime; the active study uses only 2022–2025 plus NYC current-feed late reports of those occurrences. These earlier unused raw partitions remain preserved and labeled. Thirty-three original source partitions plus four NYC late-report partitions are reconciled. NYC historic/current scopes are robbery and burglary; Buffalo includes all published crime types; Rochester includes all Part I categories.

Acquisition scripts are resumable and preserve hashed cached responses. `acquire.py` initially acquired the broader ten-year corpus; running it now checks cached files and late-report supplementation. `prepare_inputs.py` was used once to copy and verify older official ATM/boundary downloads with provenance. Offline rebuilds do not require any earlier restart directory. `acquire_atm.py` recovered indexed February–November 2023 archives; its export-preparation requests create public download copies, not source edits. Source-discovery failures are retained as evidence, not ingested data. A fresh source vintage should go in a separate release rather than overwrite this one.

## Main files

- data/processed/atm_panel_full_year_2024_2025.csv — primary full-year cohorts, 366/365 supported days.
- data/processed/atm_panel_partial_2023.csv — separate 313-day address-continuity cohort.
- data/processed/atm_panel_continuity_2023_2025.csv — convenience union of the two above, with duration and cohort columns.
- data/processed/atm_panel_exact_supported_2023_2025.csv — alternative exact-identity interval sensitivity; do not stack with the continuity panel.
- data/processed/event_atm_links.csv.part001–part004 — tracked byte parts of all cohort-specific outcome/background links; restore the exact CSV using the command above. Counts include overlap between alternative cohorts.
- data/processed/qa/exact_exposure_intervals.csv — authoritative supported-day union for exact identity.
- data/processed/atm_site_month_panel.csv — supported monthly exposure/outcome subdivisions, reconciled to annual rows; no repeated annual baseline predictors.
- data/processed/crime_primary_2022_2025.csv — deduplicated geocoded robbery/burglary, with source references.
- data/processed/qa/ — attrition, exclusions, source conflicts, sensitivity tables and independent-review work queues.
- reports/validation.json — independent computational checks.
- reports/phase_status.json — computational completion and pending scientific gates.

The static map is self-contained and works offline. Figures are supplied as PNG and SVG. They describe data and sensitivity; they are not prediction or causal results.
