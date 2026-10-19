# Artifact guide

| File or folder | Purpose |
|---|---|
| data/modeling_cohort.csv | Reused annual labels, feature keys, city and frozen spatial assignments |
| data/splits.csv | Exact test, local and source pools for every target/fold |
| data/target_samples.csv | Every 10%/25% earlier-target subset for all 20 seeds |
| data/predictions.csv.gz | Every held-out 2025 probability, outcome and experimental key |
| data/metrics.csv | 1,476 full target-year metric vectors |
| data/calibration_bins.csv | Native observed rates, mean probabilities and bin counts for every test vector |
| data/condition_summary.csv | Per-condition seed-mean metrics and AP sampling ranges |
| data/transfer_gaps.csv | Local-full minus source-only AP |
| data/transfer_benefits.csv | Per-seed augmented minus exactly matched target-only AP, plus improvement over zero-shot |
| data/benefit_summary.csv | All 54 city/source/fraction/model benefit summaries across 20 seeds |
| data/extrapolation.csv | All 81 source/target/feature observed-range and missingness diagnostics |
| models/ | Every unique fitted pipeline or explicit constant model |
| qa/training_members.csv.gz | Exact training membership of each unique fit |
| qa/model_fits.csv | Fixed parameters, membership hashes, class counts, fallback flags and artifact hashes |
| qa/preprocessing.csv | Training medians/scalers and all-empty-column flags for nonconstant fits |
| qa/evaluations.csv | 7,380 condition/fold/model evaluations, cached fit references and separation |
| qa/verified_pool_separation.csv | Independently reconstructed candidate/retained/purged counts and minimum distances |
| qa/warnings.csv | Captured estimator warnings; header-only if none |
| qa/protocol_freeze.json, qa/split_freeze.json | Before-fitting protocol and sample fingerprints |
| qa/experiment_registry.json | Fixed seeds, model settings, fractions and previous primary-gate status |
| qa/run_environment.json | Actual packages, timestamps and thread count |
| qa/validation.json, qa/status.json | Computational validation, run totals and distinct scientific-review status |
| qa/input_manifest.csv, qa/implementation_manifest.csv, qa/output_manifest.csv | Input, final code and output SHA-256 manifests |
| figures/ | Mean matched-benefit, pooled-source Brier and reference calibration figures in PNG/PDF |

The `site_id` in prediction files is the site-year **row_id** used in phase 4; it is not a permanent machine identifier. Join to phase 2 using row_id. `physical_site_id` in the modeling cohort is the coordinate-based phase 2 identity and may change at the same address between years. Repeated predictions across conditions/seeds are evaluations of the same held-out sites, not independent new samples. `fraction=1, seed=0` denotes local-full; `fraction=0, seed=0` denotes deterministic zero-shot; adaptation/control rows use the registered fractions and seeds.
