# Artifact guide

| Location | Contents / use |
|---|---|
| data/modeling_cohort.csv | Both annual site-year keys, coordinates, spatial groups, labels and label vintages; metadata only |
| data/outer_split_membership.csv | Training, held-out and distance-purged rows for each variant/scheme/fold |
| data/inner_split_membership.csv | Training, validation and purged rows inside each outer training set |
| data/predictions.csv | All held-out 2025 native and sigmoid probabilities, labels, model and split keys |
| data/inner_search_scores.csv | Every candidate's usable inner-fold AP, mean score and membership hashes |
| data/metrics.csv | Both probability types, all variants, both schemes, pooled and city-specific metrics |
| data/calibration_bins.csv | Bin counts, observed rates, average probabilities and descriptive Wilson intervals |
| data/paired_ap_comparisons.csv | Primary M1−M0 / M2−M0 AP differences, block intervals and numerical flags |
| data/paired_bootstrap_replicates.csv | All 2,000 paired draws per primary scheme/city grouping |
| models/ | 141 saved fold pipelines, predictor allowlists and training-only sigmoid parameters |
| qa/fitted_preprocessing.csv | Per-fit training medians, all-empty flags and logistic scaling values |
| qa/model_fit_audit.csv | Selected parameters, training/test hashes, sizes, artifact hashes, calibration settings |
| qa/calibration_training_oof.csv | Training-internal OOF predictions and labels used by sigmoid fits |
| qa/fit_warnings.csv | Skipped inner folds and captured library warnings |
| qa/split_separation.csv | Minimum outer/inner WGS84 separation, training/test/purged counts |
| qa/protocol_freeze.json, qa/split_freeze.json | Before-fitting specification and split fingerprints |
| qa/experiment_registry.json | Fixed variants, candidate grids, seeds and temporal parameters |
| qa/run_environment.json | Actual package versions, timestamps and thread count |
| qa/validation.json, qa/phase4_status.json | Computational validation and distinct research-acceptance status |
| qa/input_manifest.csv | Inputs and training implementation hashes frozen for the run |
| qa/implementation_manifest.csv | Final runner, common code, validator, reporter, protocol and requirements hashes |
| qa/output_manifest.csv | Final output hashes, including models, documentation and figures |
| figures/ | Pooled primary average-precision and calibration plots, PNG and PDF |

The prediction column named site_id is the **site-year row_id** (including the year suffix); physical_site_id in the modeling cohort is the phase 2 coordinate-based site identity. Join to phase 2 via row_id. Do not interpret those identities as permanent machine IDs. Each scheme provides its own complete test vector; never concatenate schemes or variants as if they were independent observations.
