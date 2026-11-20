# Restart 7 Phase 4 — exploratory predictive comparison

Authorized after the user requested a readiness assessment and Phase 4 only if
the revision supported a defensible analysis. The phase 1–3 release is immutable.
Its 96-artifact integrity check passed. An initial split-feasibility check found
855 training rows (2024), 935 test rows (2025), and 358–560 retained training rows
per spatial outer fold. Both classes remain represented in every outer fold.
This protocol is recorded before Phase 4 model fitting. Prior outcomes and prior
research choices were already inspected, so this is not a preregistration or an
untouched confirmatory test.

## Readiness decision and claim boundary

Proceed for the **retrospective released-coordinate benchmark** specified by
Restart 7. Its data alignment, common baseline and sample sizes support a modest
regularized comparison. Physical crime distance, ATM identity/operation, OSM
representativeness and LA reporting comparability remain unresolved. Thus this
phase cannot validate ATM-targeted crime risk, real-time forecasting, a causal
environmental effect, or suitability for security/placement decisions. Unknown
original Chicago report dates are not imputed. No Phase 5 transfer/adaptation
experiments are authorized by this protocol.

## Primary comparison

Outcome: `recorded_any_50m` in the conservative core. Use all eligible 2024
outcomes for training and 2025 outcomes for evaluation under the same explicitly
retrospective information regime. M0: regularized logistic regression on the
two fixed log1p prior-crime predictors (<=50 m and >200–500 m). M1: the identical
family, adding the 19 frozen environmental predictors. No feature selection
removes either baseline variable; the expanded 107-variable collection is unused.

Preprocessing is median imputation and standardization fitted on training rows
only. Entirely missing training columns receive zero via keep-empty imputation
and are reported. No missingness indicators, class weights, test-set calibration,
city identifiers, coordinates, exposure, or quality flags enter the predictors.

For each outer training set, choose C from [0.01, 0.1, 1, 10] using mean average
precision over usable inner folds. Break ties toward the smaller C. Inner folds
come from SHA256(`restart7_phase4_inner|` + spatial_block_2km), first eight hex
digits modulo three. Three inner folds are attempted, using the same spatial and
identity/geography exclusion rules as outer folds. At least two must be usable.
Usability requires >=30 fitting rows with >=5 in each class, and >=10 validation
rows containing both classes. These are computational safeguards, not evidence
of adequate statistical power. Logistic solver: lbfgs, max_iter=2000, tol=1e-8.
Convergence failure is a failed fit, not a silently accepted result.

## Outer evaluation

Primary: five deterministic spatial test folds, SHA256(`restart7_phase4|` +
spatial_block_2km), first eight hex digits modulo five. For each 2025 test fold,
remove 2024 rows within 1,500 m WGS84 distance of any test location, and remove
any training row sharing a stable OSM group, nearby component, ACS block group,
or EPA block group with the held-out rows. This intentionally measures prediction
in spatially separated locations, not ordinary forecasting at familiar sites.

Secondary: three forward city-held-out evaluations for the primary core 50 m
scenario only, using the two other cities' 2024 rows. Apply the same fitting
procedure. Report each city and pooled results; pooled results alone do not
demonstrate general transfer. This is an external-city check, not Phase 5
few-label adaptation.

Outer training usability requires >=50 rows and >=10 per class. A primary
feasibility failure stops fitting. A supplementary scenario with incomplete
feasibility is reported as not estimable, without changing its settings or
selecting only successful folds.

## Benchmarks and supplementary models

Save a training-prevalence constant-probability reference and a direct ranking
score equal to prior local crime (log1p is monotone). The latter is a ranking
benchmark, not a calibrated probability; report AP/AUC but no Brier for it.

On the primary scenario only, fit paired shallow gradient boosting models:
B0 uses the two baseline predictors; B1 uses the same 21 predictors as M1.
Use training-only median imputation, 100 estimators, learning_rate=0.05,
max_depth=2, min_samples_leaf=10, random_state=701. No boosting tuning. These
are secondary checks, with B1−B0 as the matched-family environmental comparison.

## Prespecified sensitivities

Repeat the logistic comparison with the same evaluation rules for: core 25 m,
core 100 m (matching the prior-local radius to the endpoint); corrected full
master at 50 m; explicit-ATM-tag conservative subset at 50 m; core excluding
source-code/description conflicts from both outcome and crime baseline; and
NYC/LA core using report-filtered predictors and 2024 training outcomes reported
before 2025-01-01. Its 2025 endpoint uses the same latest-extract occurrence-year
labels, appropriate to a retrospective evaluation of eventual recorded outcomes.
Sensitivity outcomes never replace the primary result after inspection. No
partial-2023 observations or expanded feature search are used.

## Metrics and uncertainty

Report noninterpolated AP, no-skill prevalence, ROC-AUC, Brier, top-decile precision
and recall, and calibration bins by city and pooled. Report equal-city mean AP
alongside pooled AP. Report all predictions, split membership, inner choices,
training-only preprocessing, fit warnings and models. Inspect overlap explicitly.

For paired AP differences, use 2,000 bootstrap resamples of 2 km test spatial
blocks within each city, seed 701, using identical resampled rows for both models.
For the primary M1−M0 pooled contrast also report 5 km block sensitivity. These
percentile intervals condition on fitted predictions; they omit model-development,
refitting, measurement and prior research-selection uncertainty. Secondary
intervals are descriptive, unadjusted and not independent confirmation.

The exploratory numerical continuation rule is primary pooled M1−M0 AP >=0.01,
2 km spatial 95% lower interval >0, and M1 Brier <=M0 Brier. The .01 threshold is
an inherited working convention, not a demonstrated practical-utility threshold.
Report the 5 km and city/sensitivity results even if they weaken the finding.
A numerical pass does not clear the scientific gates or authorize Phase 5.
A numerical failure means stop extending the environmental modeling pipeline;
report the negative/inconclusive result and identify measurement/design work.
