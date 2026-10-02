# Methods

## Cohort and outcome

Use the 1,192 sites in the existing 2025 full-year historical panel. Each has 365 days supported by the phase 2 adjacent-snapshot continuity assumption, not directly observed uninterrupted operation. The main outcome is any police-recorded robbery/burglary within 50 m during 2025. Counts are converted to binary for the nearest-site-only sensitivity. No label or coordinate was invented.

The data remain observational and retrospectively assembled. Full-year membership itself uses future snapshots relative to January 2025; this selection may affect transportability. Police extracts may include later revisions. These limitations prevent a claim of exact prospective deployment simulation.

## Spatial and city holdouts

Each city uses 2 km square blocks in its designated UTM coordinate system, anchored at zero easting/northing. Five compact groups are created from occupied block centers using KMeans, fixed seed 20261001 and n_init=20, weighted by site counts. Group numbers are canonicalized by center coordinates. Neither outcomes nor model performance influence these partitions.

For each of five spatial folds, hold out one group from every city. Remove potential training sites within 1,500 m WGS84 distance of any held-out center. Thus two 500 m context circles remain at least 500 m apart. Leave-one-city-out tests train on the other cities' sites, with the same distance rule. Outer test rows and excluded rows never enter inner tuning.

Inner folds use the existing group IDs within the outer training set and repeat the purge. Inner validation must contain both classes; training must have at least ten rows and both classes. Invalid folds are logged and skipped. With fewer than two valid inner folds, the fixed first candidate is used and no sigmoid is fitted. This prevents test-set tuning but can weaken model selection in the smallest source-city samples.

These are same-year spatial evaluation schemes. They do not meet the blueprint's future-period requirement. Spatial folds are not forced to have equal size; preserve and inspect their coverage instead of changing partitions to obtain better metrics.

## Model fitting and tuning

M0 receives only log1p(2024 primary background incidents at >200–500 m). M1 and M2 use all 14 frozen phase 3 predictors: that baseline plus 13 environmental/context variables. City, coordinates, geography IDs, exposure duration, future membership and quality flags are excluded from inputs.

Within every training split, missing values are imputed with training medians; features entirely missing in training receive the explicit zero fallback. Logistic models also fit scaling within that split. No rows are dropped for feature missingness, no oversampling is used, and no held-out prevalence adjustment is applied.

| Model | Fixed settings | Inner search |
|---|---|---|
| M0 | Unpenalized logistic regression, lbfgs, max_iter 3000, tolerance 1e-8 | None |
| M1 | L2 logistic regression, same solver/convergence settings | C = 0.1, 1, 10 |
| M2 | CPU XGBoost, 150 trees, learning rate 0.05, min_child_weight 5, all rows/features per tree, histogram method | depth 2/3 × lambda 10/1 |

Candidate selection maximizes mean inner-fold average precision; ties retain the first candidate. The selected pipeline is refitted on outer training rows, then scored once on the held-out rows. Relevant implementation references are [scikit-learn logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) and the [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html). Exact installed versions are recorded separately.

## Calibration

Primary results use the native probabilities. A secondary sigmoid maps the selected model's inner out-of-fold logits to probabilities using only outer-training labels. Its slope is constrained nonnegative, with a small 1e-6 slope penalty. Failed or unsupported fits fall back to native probabilities and are recorded. Raw and sigmoid results are both reported; no choice between them is made based on test performance. Evaluation reliability bins use ten fixed probability intervals. The [calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) motivates using predictions from data excluded from base-model fitting to train the probability mapping.

## Metrics

AUPRC is represented by non-interpolated [average precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html), not trapezoidal area. AP depends on prevalence, so city sample sizes and positive fractions accompany it. ROC-AUC measures ranking; Brier measures squared probability error. Calibration diagnostics include mean predicted probability minus observed prevalence, ten-bin expected calibration error, and reliability tables. Binwise Wilson intervals are descriptive and do not adjust for spatial clustering.

For top-decile capture, select exactly ceil(0.10 × number of test sites), sorting equal probabilities by site ID. Precision is the positive fraction among selected sites; recall is their share of all positives; lift divides precision by overall prevalence. Single-class tests have undefined ROC-AUC, and no-positive tests have undefined AP. Pooled scores combine untouched predictions from the respective outer folds and are dominated by NYC, not city-balanced.

## Paired uncertainty and decision

For the primary endpoint, resample occupied 2 km blocks with replacement within each city, retain all rows in each sampled block, and apply the same replicate weights to M0/M1/M2. Use 2,000 replicates and fixed seed 20261001. Compute percentile 95% intervals for AP(M1)−AP(M0) and AP(M2)−AP(M0), pooled and by city. The implementation handles ties and zero sample weights and is checked against the library AP calculation.

These intervals condition on the saved out-of-fold predictions. They do not refit or retune models, do not fully represent algorithm-training uncertainty, and depend on the chosen block size. Small numbers of city blocks limit inference. No multiplicity correction is applied; city and sensitivity results remain exploratory.

The working numerical flag requires AP gain at least 0.01 and a lower interval bound above zero. It is not a confirmatory approval gate because the data validity and temporal requirements remain unmet. A failed flag is not proof of no environmental effect. Calibration is reported independently; passing a ranking threshold alone does not justify operational probability estimates.

## Sensitivities

The five fixed sensitivities are 25 m, 100 m, nearest-site-only 50 m, report-date-cutoff background, and excluding Buffalo. Each reruns the same nested process using the original spatial groups; the Buffalo-exclusion variant removes that city from both source and test sets. Sensitivities are not used to replace the main 50 m result, and no additional bootstrap decision flags are calculated for them. Report-date filtering still does not recreate an as-of-2025 police database.
