# Phase 4 exploratory analysis specification v1.0

Prepared 2026-10-02 before model fitting. This is a computational analysis specification, not an externally registered protocol or independent researcher approval.

## Scope and estimand

Compare M0 (previous-year surrounding crime only), M1 (regularized logistic regression with the same baseline plus phase 3 environment), and M2 (XGBoost with those same inputs). Use the 1,192 phase 2 sites with 365 snapshot-supported days in 2025. The primary endpoint is any police-recorded robbery/burglary within 50 m in 2025; it is not a verified ATM attack.

The only outcome year is 2025. Run **exploratory same-year spatial validation** and **exploratory leave-one-city-out evaluation**. They estimate spatial generalization within this retrospectively constructed cohort, not future-year prediction. The requested forward temporal test is blocked by missing additional exposure-supported years. Phase 2 review and phase 3 acceptance remain pending; confirmatory_modeling_ready and phase4_confirmatory_complete remain false irrespective of measured performance. No fabricated temporal split or substitution of within-2025 months for an annual future-year test.

## Freeze splits before fitting

Project site coordinates to UTM 18N for NYC and 17N for Buffalo/Rochester. Assign a fixed 2,000 m square block ID anchored at zero in projected coordinates. Per city, partition occupied block centers into five compact groups using KMeans, seed 20261001, n_init=20 and block site-count weights. Canonicalize labels by cluster-center east/north order. No labels or crime outcomes determine group membership.

Spatial outer fold k holds out group k in all cities. Exclude any training center within **1,500 m WGS84** of a held-out center. This leaves at least 500 m between two 500 m-radius site contexts. Buffers are applied across all pairs, including city boundaries. Leave-one-city-out holds out every site in one city, training on the other cities, with the same distance guard.

Inner validation uses remaining spatial group IDs within each outer training set, with the same 1,500 m purge. Outer test rows and outer-purged rows never enter inner training, tuning or calibration. A valid inner split needs at least ten training rows with both outcome classes and a validation set with both classes. Log skipped folds. With fewer than two valid inner splits, use the first predeclared candidate and leave probabilities uncalibrated; report this limitation rather than tuning on the test set. Never regenerate spatial partitions to improve scores.

## Predictors and models

Use exactly the phase 3 primary allowlist (14 columns); M0 gets its sole `log1p_background_primary` column. Geographic identifiers, city, coordinates, supported days, future membership, QA flags and outcomes are excluded. Keep all eligible rows including missing inputs.

Each training fold fits a median imputer with `keep_empty_features=True`; an entirely missing training feature gets the library's zero fallback and is recorded. No missingness indicator is added. Logistic models then fit StandardScaler on those imputed training rows. XGBoost uses imputed values without scaling. Class weights remain one; no oversampling or test-dependent prevalence correction.

- M0: unpenalized logistic regression, lbfgs, max_iter=3000, tol=1e-8.
- M1: L2 logistic regression, C in [0.1, 1, 10], lbfgs, max_iter=3000, tol=1e-8.
- M2: CPU XGBoost binary logistic, histogram tree method, 150 trees, learning_rate=0.05, min_child_weight=5, subsample=1, colsample_bytree=1, random_state=20261001, n_jobs=1. Candidate order: (max_depth=2, reg_lambda=10), (2,1), (3,10), (3,1).

Select hyperparameters by mean inner-fold average precision, not outer performance. Ties retain the first candidate. Refit the selected pipeline on the outer training rows only. Preserve prediction files, candidate scores, fitted preprocessing values, convergence diagnostics and fold model artifacts. No full-data deployment model or retrospective feature interpretation is part of this phase.

## Calibration

Primary ranking/metric results use native model probabilities. As a prespecified secondary diagnostic, fit a sigmoid to the selected candidate's inner out-of-fold logits and labels, all inside the outer training set. Constrain its slope to be nonnegative, use a small 1e-6 L2 slope penalty, and retain native probabilities if optimization fails or insufficient inner validation exists. Save both raw and sigmoid-calibrated probabilities. The outer test set is used only to assess calibration, never to fit or select the calibrator. No choice between raw and calibrated predictions is made after seeing outer results.

## Metrics and uncertainty

Primary AUPRC is **non-interpolated average precision**, not trapezoidal PR area. Also report ROC-AUC, Brier score, ten equal-width-bin calibration error, mean predicted probability minus observed prevalence, and top-decile precision/recall/lift. Select exactly ceil(0.10*n) rows for top-decile metrics, sorting ties by site ID. Report test sample size, positives and prevalence. Single-class test sets have undefined ROC-AUC; all-zero sets have undefined AP. Do not replace undefined values with apparent evidence.

For the primary 50 m analysis, compare M1−M0 and M2−M0 on paired out-of-fold predictions using **2,000 city-stratified spatial-block bootstrap replicates**, seed 20261001. Sample occupied 2 km blocks with replacement within each city, retaining all site rows and identical bootstrap weights for all models. Report percentile 95% intervals, valid replicate counts and the full replicate table. These intervals condition on fitted out-of-fold predictions and do not include retraining/tuning uncertainty. Report pooled and city-specific metrics separately; pooled performance is dominated by NYC and is not a city-balanced estimate.

The working numerical gate is absolute AP improvement >=0.01 with bootstrap lower 95% bound >0. It is a descriptive exploratory signal flag only; pending validity gates prohibit a confirmatory GO. If the flag fails, report no demonstrated improvement under this evaluation, not proof of no environmental effect. Report calibration alongside it; no operational absolute-risk claim follows from a ranking gain.

## Prespecified sensitivities

Run the same nested workflow for: 25 m endpoint, 100 m endpoint, nearest-site-only 50 m endpoint, report-date-cutoff background replacing the baseline column, and the primary endpoint after excluding Buffalo. Use the original spatial group labels; regenerate only membership/purging for the subset. These are sensitivity analyses, never replacements for the 50 m primary result. Do not compute additional bootstrap gates for these variants. Report-date cutoff still does not restore historical police database versions.

## Completion conditions

Deliver reproducible exploratory models and evaluation, frozen split manifests, paired uncertainty, calibration/top-decile metrics, plots, verification and Markdown documentation in `results/phase4/`. List the full temporal/confirmatory phase 4 as incomplete. Later phase 5 source+target adaptation requires earlier target-period labels and is not authorized implicitly by this phase.
