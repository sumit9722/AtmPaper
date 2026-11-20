# Reproduce the incremental release

From the repository root:

```bash
.venv/bin/python restart7_0/scripts/run_all.py
```

Install `restart7_0/requirements.txt` in a Python environment if necessary.
The runner executes rule regression tests, verifies the frozen base inputs,
rebuilds only the revision, independently validates it and regenerates reports
and output checksums. It has no network/acquisition option and fits no models.

Keep the consumed Restart 6 outputs listed in `qa/input_manifest.csv`, the base
artifact manifests, and `PAPER_REVIEW.md`. If a checkout lacks the two original
large CSVs, restore them using Restart 6's checksum-verified parts first:

```bash
.venv/bin/python restart6_0/scripts/large_artifacts.py restore
```

The new large tables use deterministic gzip compression and need no splitting.
All retained environmental values, exposure fields and distance links come from
the base release. Incremental reproduction does not require reimporting ACS,
downloading OSM or rerunning Restart 6. To audit the entire upstream source
construction, follow Restart 6's separate reproduction instructions.

Validate an existing build without rebuilding:

```bash
.venv/bin/python restart7_0/scripts/validate.py
.venv/bin/python restart7_0/scripts/verify_release.py
```

For modeling, use explicit predictor lists from the feature schema. The primary
core matrix has two fixed crime features and 19 environmental features; labels
join through `row_id` to `outcomes.csv`. The metadata lookup contains city, year,
OSM/component/geographic grouping keys and quality flags. Never select all numeric
columns from a panel as predictors. Report-filtered matrices contain NYC/LA only.
Use report-filtered training labels in that sensitivity. 2023 is partial and
must not be pooled with annual binary outcomes.

Changes to frozen protocol/input files fail instead of silently refreshing a
release. The manifest is a reproducibility record, not independent scientific
approval. Rerunning does not adjudicate human review queues or create a new
uninspected holdout.
