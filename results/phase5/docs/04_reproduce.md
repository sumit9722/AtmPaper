# Reproduction and files

From the repository root, install `requirements-phase5.txt` into the virtual environment. All acquired raw data are cached. Reproduction uses no Census requests or API key:

```bash
.venv/bin/python scripts/build_temporal_data.py
.venv/bin/python scripts/run_phase4_temporal.py
.venv/bin/python scripts/run_phase5.py
.venv/bin/python scripts/validate_phase45.py
.venv/bin/python scripts/report_phase45.py
```

The acquisition script has separate bounded, cached `history`, `crime`, `geography`, `tiger`, and `acs` stages. Do not refetch valid cached inputs. Only `acs` needs the user's key through hidden input or an environment variable; no key is stored in source, URLs, or sidecars. The incompatible archived `geography` response is preserved for audit, but models use `tiger`.

`data/` contains predictions, metrics and experiment/sampling tables. `qa/` contains splits, preprocessing, memberships, warnings, status, validation and release hashes. Large transfer prediction and membership tables use `.csv.gz`, readable with Python gzip/csv or pandas compression inference. `figures/` contains PNG and PDF figures. Temporal phase 4 saves joblib models under `models/`; phase 5 saves reproducible fit membership/parameter/preprocessing audits instead of thousands of model binaries. Never load untrusted joblib files.

`protocol/phase45_temporal_extension_v2.md` specifies the experiments. Boundary and continuity addenda document pre-fit corrections. `results/temporal_data/qa/` preserves source and protocol hashes. Frozen split hashes are checked before rerunning. All new files remain below GitHub's 100-MB per-file limit. No remote push is performed.

Validation is a separate computation checking source integrity, outcome reconciliation, historical membership, temporal/spatial separation, exact seeded adaptation subsets, training-only preprocessing, saved temporal-model predictions, metrics and matched benefits. It is not independent human scientific review.
