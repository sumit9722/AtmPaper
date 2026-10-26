# Reproduce Phase 3

From the repository root:

```bash
.venv/bin/python restart6_0/scripts/run_phase3.py
```

This performs an offline rebuild, checks frozen Phase 1–2 and Phase 3 inputs, runs the four synthetic regression tests, builds features, validates sources/formulas/links, renders diagnostics and writes manifests. It does not require the HeiGIT key. Dependencies are in `restart6_0/phase3/requirements.txt`; the existing environment already contains them.

For first-time public acquisition, run:

```bash
.venv/bin/python restart6_0/scripts/run_phase3.py --acquire
```

New raw inputs are under `restart6_0/phase3/raw`. Reused national ACS housing tables and NYC geography remain at their original repository paths, explicitly listed in `qa/input_manifest.csv`; those inputs must accompany this release for offline reproduction. If the ignored Phase 2 large CSVs are absent after checkout, first run `.venv/bin/python restart6_0/scripts/large_artifacts.py restore`.

Main matrices are `data/features_primary_full_year_2024_2025.csv` and `data/features_sensitivity_full_year_2024_2025.csv`. Separate year files and partial-2023 supplements are included. Join by `row_id` to `data/outcomes.csv` and `data/site_lookup_and_quality.csv`. Never feed lookup flags, labels, future exposure or sensitivity columns into a model by selecting all numeric columns. Use `data/feature_schema.json` and learn any preprocessing within training folds.

`qa/phase3_status.json` is the authoritative Phase 3 status. The original Phase 1–2 status and manifest stay frozen. `qa/output_manifest.csv` includes result files, scripts and tests; `qa/input_manifest.csv` includes raw/reused inputs and protocol hashes. These checks establish computational integrity, not independent scientific approval.
