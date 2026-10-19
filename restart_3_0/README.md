# Restart 3.0: housing context and nearby crime, 2024–2025

## Current status

**Phases 1–5 are computationally complete and automated validation passed.** The annual panel contains 1,201 site-years in 2024 and 1,241 in 2025. Phase 3 joins eight fixed housing-context measures to both years. Phase 4 trains on 2024 and tests on 2025; neither housing model met the prespecified pooled improvement criterion. Phase 5 completes matched cross-city transfer comparisons over 20 seeds and finds mixed benefits. Independent scientific review remains pending, and both outcome years were inspected in earlier work.

Read the [bullet-point report for the professor](Research_Update_for_Professor.md), [Phase 3 results](results/phase3/docs/execution.md), [Phase 4 results](results/phase4/docs/03_results.md) and [Phase 5 results](results/phase5/docs/03_results.md). Detailed methods, artifacts and reproduction instructions accompany Phases 4 and 5.

## Data and methods

1. Reconstructed 2024 and 2025 annual ATM cohorts and prior-year crime context from preserved archives. These are new computations from existing downloads, not newly retrieved police histories.
2. Validated source checksums, cohort membership, event links, distance calculations and label reconciliation in `reports/validation.json`.
3. Froze eight housing variables in `protocol/environment_variables.json`, then imported official 2018–2022 ACS detailed-table estimates and margins of error for 8,217 block groups in seven study counties. The public [Census table-based summary files](https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/data/5YRData/) supplied the data without an API credential. Standard numeric-jam annotations were reconstructed; other API-only annotation qualifiers are unavailable from those files. The independent full-source reconciliation is in `reports/environment_bulk_validation.json`.
4. Joined all 2,442 site-years uniquely to 2022 block-group polygons, retained missing values, and validated every derived feature formula. Prior-year crime remains the ninth, baseline predictor.
5. Trained baseline logistic, housing logistic and boosted-tree models on 2024 labels and evaluated 2025 labels under fixed spatial and city-held-out schemes. The primary pooled AP differences were −0.0124 for housing logistic and −0.0193 for boosted trees relative to baseline; both paired intervals include zero.
6. Evaluated local, individual-source and pooled-source transfer, plus 10% and 25% target-label adaptation against exactly matched target-only controls. All 7,380 evaluations and 7,155 unique fits passed Phase 5 validation.

## Reproduce

From the parent project directory, using its existing virtual environment:

```bash
.venv/bin/python restart_3_0/scripts/run_all.py
```

The offline command uses the saved official source files and regenerates derived outputs. To acquire the public housing tables afresh before the complete pipeline, use `--download-bulk`. The alternate `--download` route uses `CENSUS_API_KEY` or a hidden prompt for the Census API. No credential was used or saved for this release. The runner stops on errors; direct stage commands follow the ordered script list in `scripts/run_all.py`.

The large `data/processed/crime_events_2023_2025.csv` is stored as tracked `.part001`–`.part003` byte parts. The build recreates the complete local CSV. To restore it directly on a fresh checkout, run `python3 scripts/large_artifacts.py restore restart_3_0/data/processed/crime_events_2023_2025.csv` from the repository root; the helper verifies the original SHA-256.

## Interpretation

This follow-up was designed after earlier results were inspected, so it is exploratory rather than an independent confirmation. Nearby robbery/burglary is not verified ATM targeting. Monthly inventories do not prove continuous machine operation. Coordinate precision, city boundaries, retrospective reporting vintages and housing-survey uncertainty remain limitations. Housing attributes describe neighborhoods and do not establish causal effects or justify deployment. Independent offense, linkage, facility, coordinate-precision, boundary and feature review remains necessary.
