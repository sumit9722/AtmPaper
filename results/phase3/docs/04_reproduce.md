# Reproduction and file guide

Run from the project root with the existing Python environment. No additional packages are required beyond `requirements.txt`.

```bash
# Optional: restore missing GIS downloads; complete caches require no network calls.
.venv/bin/python scripts/download_phase3.py --stage data

# Offline feature build, independent computational validation, and documentation.
.venv/bin/python scripts/build_phase3.py
.venv/bin/python scripts/validate_phase3.py
.venv/bin/python scripts/report_phase3.py
```

Raw responses are cached under `data/raw/phase3/`. Their `.request.json` sidecars store URLs, parameters, timestamps, byte counts and SHA-256 hashes. Existing ACS data are reused from `data/processed/census/` and `data/raw/census/`. The December 2024 DFS snapshot and historical panels come from phase 2. No network access or API key is needed for a complete cached rebuild.

## Result files

| File / folder | Purpose |
|---|---|
| `data/features_primary_full_year.csv` | Main 1,192-row, 14-predictor matrix plus site ID |
| `data/features_primary_all_historical.csv` | Same predictor definitions for all 2,233 historical sites |
| `data/features_sensitivity_*.csv` | Three separate sensitivity predictors for each cohort |
| `data/site_context_raw.csv` | Original-unit inputs, both geography IDs, ACS uncertainty/annotations and source EPA values |
| `data/site_lookup_and_quality.csv` | City/coordinates, exposure cohort, membership and boundary-quality flags |
| `data/atm_baseline_dec2024.csv` | Deduplicated statewide pre-cutoff neighbor inventory |
| `data/feature_dictionary.csv` | Formulas, units, transforms, vintages, availability qualifications and roles |
| `data/feature_schema.json` | Ordered allowlists and specification hash |
| `qa/city_summary.csv` | Coverage and spatial-quality counts |
| `qa/spatial_join_audit.csv` | Accepted, missing and ambiguous matches with candidate IDs |
| `qa/geometry_repairs_*.csv` | Source geometry issues and constrained in-memory repairs |
| `qa/atm_baseline_exclusions.csv` | Unparseable baseline-coordinate rows |
| `qa/feature_distributions.csv` | Missingness, quantiles and variation by cohort and city |
| `qa/feature_correlations.csv` | Pairwise full-year Spearman diagnostics and sample sizes |
| `qa/range_violations.csv` | Header-only when no invalid range was found |
| `qa/input_manifest.csv` | Hashes of consumed sources, specification and implementation files |
| `qa/validation.json` | Passed checks and remaining independent-review distinction |
| `qa/phase3_status.json` | Computational status and research readiness |
| `release_manifest.sha256` | SHA-256 hashes for every other result artifact |

CSV missing values are empty cells. Import geographic identifiers as strings. Boolean QA fields use `True`/`False`. Model matrices contain only `site_id` and allowlisted predictors; use the lookup table for city/spatial grouping and join outcomes from phase 2 by exact `site_id`.

The builder checks the existing frozen schema against the specification. For a deliberate feature change, preserve this release and make a versioned amendment instead of bypassing that check. Correcting phase 2 identities requires rebuilding dependent phase 3 results before tuning models. Do not silently remove incomplete rows or include QA/identity fields as model inputs.

To check this release from inside `results/phase3`:

```bash
sha256sum --check release_manifest.sha256
```
