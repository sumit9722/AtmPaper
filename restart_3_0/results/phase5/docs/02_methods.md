# Methods and limitations

## Population, timing and comparison design

The phase 2 address-continuity-supported cohort and phase 3 environmental features are unchanged. Training uses 2024 occurrences reported before January 1, 2025. Testing uses archived 2025 nearby robbery/burglary occurrences. Prior-year backgrounds remain report-filtered, with Buffalo creation timestamps only a proxy. Exposure uses retrospective monthly membership, not verified operation. Both outcome years were examined earlier.

For each target city and its five phase 4 spatial groups, keep the same 2025 test sites across all conditions. Retain only 2024 training centers at least 1,500 m WGS84 from those tests. This prevents previous-year labels from the held-out neighborhood from entering training. Unlike phase 4's simultaneous all-city fold holdouts, phase 5 purges against one target-city fold at a time; its local/source pools should not be mistaken for the original phase 4 fitted memberships.

Local-full is the all-available-local-label reference. Each-source and pooled-source zero-shot use no target labels. For seeds 20261001–20261020, uniformly permute the row-ID-sorted eligible local pool, then choose ceil(10% × pool size) and ceil(25% × pool size). Fractions are applied separately within each fold's eligible pool, not the entire city's cohort. The samples overlap and the 10% subset is nested in the 25% subset. No class balancing or outcome-dependent redraws occur. Target-only controls and all augmented conditions use precisely the same selected earlier-year target rows.

## Models, capacity and preprocessing

Model capacities are fixed from the original transfer plan, not optimized against the restart's test performance. M0 is unpenalized logistic on log1p background crime. M1 is L2 logistic C=1 with all 9 primary predictors. Logistic settings are lbfgs, max_iter=3000, tol=1e-8. M2 is CPU XGBoost with 150 trees, depth 2, lambda 10, learning rate .05, min_child_weight=5, subsample=colsample_bytree=1, histogram trees, seed 20261001 and one thread. No class weights or oversampling.

Each training membership learns its own median imputer, preserving entirely missing columns with a recorded zero fallback. Logistic models then learn a StandardScaler on that imputed training set. No phase 5 sigmoid calibration is fitted; native probabilities are assessed as produced. Metadata, city, coordinates, exposure and labels are not predictors. A single-class fit predicts its empirical prevalence, possibly exactly zero or one, and is flagged. It is never rescued with test labels. An empty pool would be recorded unsupported.

Identical sorted training memberships and model families share a cached fit. Distinct memberships never share learned preprocessing. All unique pipelines and constant predictors are saved with hashes and exact membership. Predictions may be computed for all 2025 rows for cache efficiency, but only each condition's own held-out test rows enter its metrics. Test features and labels never determine fitted statistics or parameters.

## Metrics and interpretation

AUPRC is non-interpolated average precision. Also report ROC-AUC, Brier score, ten equal-width-bin calibration error, mean predicted probability minus prevalence and top-decile precision/recall/lift. The top decile is exactly ceil(0.1*n), with row-ID tie-breaking. Undefined metrics remain missing. No post-test threshold selection or probability recalibration is performed.

Transfer gap = local-full AP − source-only AP; positive means local-full ranks better. Matched transfer benefit = source-plus-target AP − exactly matched target-only AP; positive means adding source labels improves ranking for that sample. Improvement over zero-shot only demonstrates a benefit from adding target labels, and cannot by itself establish a benefit from source data. A negative benefit is a substantive result, not a sample to discard.

For each source/target/model/fraction, summarize 20 paired seed differences using mean, sample SD, empirical 2.5/97.5 percentiles and positive/negative counts. Percentiles describe randomness in choosing earlier target labels; they are not population confidence intervals, and the 20 seeds are not independent test cohorts. Models, fractions and source choices are multiple descriptive comparisons, not separately confirmed effects. Positive average ranking benefit does not establish calibrated probabilities or a causal effect.

The feature-range table compares all observed 2025 target values with observed 2024 other-city ranges, separately for every feature/source. Missing values are counted separately. This city-level diagnostic uses no target outcomes, does not choose models and is not a fold-specific preprocessing step. The figures show mean paired AP benefits and native Brier scores; they do not imply statistical significance.

## Remaining research gates

The primary numerical comparison is reported in the phase 4 results. Transfer experiments do not provide automatic scientific approval. Independent offense, linkage, facility/continuity, Buffalo precision, boundary and feature-schema reviews remain pending. City sample sizes are highly unequal, and small adaptation samples often have one class. Coordinate revisions and up-to-50-m identity drift can change neighborhood assignments. Missing ACS attributes require training-only imputation, which cannot recover their true values. Monthly membership implies survival selection, municipal clipping can truncate backgrounds, and later-retrieved archived data do not reconstruct historical database vintages. These nearby-crime outcomes are not verified ATM attacks, and no deployment or location-optimization claim is made.
