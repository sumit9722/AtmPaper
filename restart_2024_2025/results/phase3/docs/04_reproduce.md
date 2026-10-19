# Reproduction

From the repository root, use the existing environment:

```bash
.venv/bin/python restart_2024_2025/scripts/build_phase3.py
.venv/bin/python restart_2024_2025/scripts/validate_phase3.py
.venv/bin/python restart_2024_2025/scripts/report_phase3.py
```

For a standalone copy, create a Python environment, install `requirements-phase3.txt`, then run the same three scripts from the restart's `scripts/` directory with that Python. PyShp reads the official TIGER/Line ZIP. All inputs are copied into the restart; the pipeline never reads parent-project data. No network access or credentials are needed for rebuilding. Do not run with Python `-O`, which disables validation assertions.

Prerequisite: completed phase 2 combined panel. The feature specification and schema are frozen; changing the specification requires an explicit version amendment before rebuilding. Build writes feature exports and QA; validation writes PASS only when its checks succeed; report runs only after PASS and refreshes the documentation/output manifest. A failed/restarted build invalidates prior validation status. Do not use previously saved validation for changed inputs.

Use `data/features_primary.csv` and `data/feature_schema.json` for the combined primary matrix. Separate annual matrices and `features_sensitivity*.csv` are available. Join to phase 2 labels only by row_id in a later modeling pipeline. site_lookup_and_quality.csv is metadata, not a predictor matrix. site_context_raw.csv preserves components and uncertainty.

Input manifest hashes are relative to the restart root; output manifest hashes are relative to the phase 3 folder. To verify any manifest, recompute SHA-256 of each listed file and compare with the sha256 column. Never infer independent scientific approval from automated PASS.
