# What was completed

Phase 4 asks whether environmental information improves held-out near-ATM crime prediction beyond prior surrounding crime. This delivery runs the comparisons supported by the available single-year panel and documents the missing temporal component.

1. Froze the [analysis specification](../../../protocol/phase4_analysis_spec_v1.0.md) before model fitting and recorded its hash.
2. Joined the full-year phase 3 feature matrix to the phase 2 binary outcomes using exact site IDs. Retained all 1,192 sites, including missing features.
3. Created outcome-independent spatial groups and froze outer/inner split membership before fitting. Applied a 1,500 m center-to-center exclusion to each training/validation boundary.
4. Fit M0 crime-only logistic regression, M1 regularized logistic regression and M2 CPU XGBoost. Tuned only inside outer training sets.
5. Evaluated five spatial holdouts and three leave-one-city-out tests. Performed five predeclared sensitivity analyses with their corresponding splits.
6. Saved native and training-only sigmoid-calibrated predictions. Computed AP, ROC-AUC, Brier, calibration and top-decile metrics by city and pooled.
7. Computed 2,000 paired, city-stratified spatial-block bootstrap draws for each primary comparison scope.
8. Preserved 141 model artifacts, preprocessing values, parameter searches, warnings, split manifests, prediction files and source checksums.
9. Ran focused metric/preprocessing tests and 13 artifact-validation checks. Generated five research figures in both PNG and PDF and this documentation.

## What remains incomplete

The existing sources provide only one exposure-supported outcome year. Spatial and leave-one-city-out tests use 2025 labels on both sides of geographically separated splits; they are not forecasts of a later year. A true forward temporal experiment requires additional annual cohorts and features available before each prediction period.

Phase 2's independent offense/linkage/identity reviews, Buffalo coordinate assessment, exposure assumptions and phase 3 feature acceptance remain open. This package keeps `full_blueprint_phase4_complete=false` and `confirmatory_modeling_ready=false` even if an exploratory numerical threshold passes. Phase 5 target adaptation and substantive feature attribution are not part of this delivery.
