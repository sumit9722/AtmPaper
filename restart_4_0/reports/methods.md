# Methods and interpretation

The [frozen protocol](../protocol/restart_spec.md) and
[permutation-resolution amendment](../protocol/inference_resolution_amendment.md)
define this release. The amendment increased all Phase 5 permutation counts
before those experiments, because 999 permutations could not resolve the
first threshold in a 54-test Holm correction. No outcome-based stopping occurred.

Phases 1–2 inherit the validated 1,201-site 2024 and 1,241-site 2025 annual
cohorts. Archived inputs and their original provenance are retained in previous
release directories; 342 original raw-file digests were checked again. Training
labels are 2024 events reported before 2025; test labels are archived 2025
occurrences. Both years were inspected previously. Full-year inventory
membership is retrospective and does not prove continuous ATM operation.

Phase 3 joins eight housing and thirteen other environmental variables by exact
site-year identifier, alongside prior-year 200–500 m background crime. Six new
lagged crime predictors use 25/50/100 m counts, robbery/burglary separately at
50 m, and July–December crime at 50 m. All six require prior-year occurrence
and a known report date before January 1. Counts are transformed by log1p.
Every site-year count was independently recomputed by scanning geodesic
distances to all eligible events in its city. Unknown report dates are excluded.

The candidate family consists of background alone or background plus one
predictor, each fitted with L2 logistic regression C=1. Every distinct actual
training sample gets its own feature selection using three spatial groups
(saved 2024 fold modulo 3) and a 1,500 m purge. Imputation and scaling use
inner training rows only. Fewer than two valid folds triggers background-only
fallback. Small samples may also have one outcome class; these yield explicit
constant-probability artifacts. The batched selection solver matches sklearn;
final saved models use sklearn/XGBoost, and representative selections are
independently refitted with sklearn. The displayed feature leaderboard averages
dependent inner-fold results for description; it is not a second selection rule
or an independent estimate of generalization.

Phase 4 uses five simultaneous cross-city spatial folds and three city-held-out
fits. All fits use 2024 labels, all evaluation uses 2025 labels, and every
training site is at least 1,500 m from every held-out site. Primary M1 is fixed
in advance. M2 is a secondary shallow-tree model with the M1-selected features.
The primary numerical criterion is AP gain at least .01 and a positive paired
95% spatial-bootstrap lower bound. Secondary Phase 4 intervals are descriptive
and are not individually multiplicity-corrected.

Phase 5 uses target-specific folds. It evaluates local-full, each individual
source, pooled sources, and each source plus nested uniform 10%/25% local
samples. The paired local-only control always receives exactly those same
target labels. Twenty seeds describe training-sample variation. Deterministic
local/zero-shot fits are counted once; identical memberships share cached fits.
Feature selection for adaptation uses only the sampled target rows and its
permitted source rows. It cannot use the rest of the target training cohort.

Average precision (AP) is the primary ranking score. ROC-AUC, Brier score,
calibration error and top-decile precision/recall accompany it. The top decile
uses ceil(.1*n) and site-ID tie breaking. AP is prevalence dependent, and
NYC dominates pooled metrics; report city-specific results as well.

For uncertainty, 2,000 paired bootstrap replicates resample saved 2 km blocks
within cities. Phase 5 resamples the same blocks jointly across all 20 seed
vectors and averages their AP differences; seeds are not independent test
populations and their predictions are not averaged into an ensemble. The
two-sided randomization test swaps each complete seed-pair vector at the
spatial-block level for 9,999 permutations with add-one correction, then applies
Holm across all 54 comparisons. The null assumes prediction-pair exchangeability
at the block level. These calculations condition on fitted predictions, do not
refit training models, and do not account for prior analyses or all sources of
spatial dependence. They are exploratory conditional evidence.

Nearby robbery/burglary is not verified ATM targeting. Rounded coordinates in
Buffalo, uncertain facility identities, historical inventory continuity,
retrospective police revisions, housing-survey uncertainty and overlapping
incident neighborhoods remain limitations. Small Buffalo/Rochester samples
make transfer conclusions fragile. Independent source, offense, linkage,
coordinate, facility and feature review remains pending. A new untouched time
period is needed for confirmatory evaluation.

Method references: separating selection from outer evaluation follows the
[scikit-learn nested-validation guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).
Ranking is computed with the documented
[average precision metric](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).
The randomized p-value uses the conservative add-one convention described in
the [SciPy permutation-test documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).
Our resampling unit is a spatial block and the two-sided statistic uses the
absolute AP difference; this is a custom implementation, not a direct call to
SciPy's test or a claim that its assumptions have been externally verified.
