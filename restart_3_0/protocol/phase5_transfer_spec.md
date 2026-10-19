# Phase 5 — earlier-label city-transfer experiments

Prepared 19 October 2026 before this restart's phase 5 fits. This is a retrospective working specification, not preregistration. The primary phase 4 improvement criterion failed. The user requested phase 5 computation; these are descriptive transfer experiments with no confirmatory or deployment claim. Prior scientific-review gates remain pending.

## Frozen population, outcome and spatial split

Reuse phase 4's validated inputs, primary 50 m labels, feature allowlist and both annual spatial assignments without modification. Training uses only 2024 labels reported before 2025-01-01; testing uses archived 2025 occurrences. All 1,241 2025 sites are evaluated once per condition/model/seed across five folds in each target city. Phase 2's cohort remains retrospectively selected using monthly membership; source revisions, positional issues and prior inspection of both outcome years remain limitations.

For each target city and its 2025 spatial fold, use eligible 2024 target-city rows at least 1,500 m WGS84 from every held-out site as the local pool. Source pools use 2024 rows from each other city, under the same purge. Pooled sources are the union of the two other-city pools. Phase 5's target-specific tests differ from phase 4's simultaneous all-city outer tests; do not assume identical fitted training sets. Record all pools and test membership, including purge counts and minimum separation. Never tune on target test labels.

## Transfer ladder and deterministic sampling

For each target/fold and M0/M1/M2 run:

1. Local-full: all eligible 2024 target-city rows.
2. Each-source zero-shot: either other city's eligible 2024 rows, separately.
3. Pooled-source zero-shot: both other cities combined.
4. Target-only 10% and 25%: earlier local labels sampled as below.
5. Each source plus 10%/25% target and pooled sources plus those same target subsets.

Use seeds 20261001 through 20261020. Sort the local pool by site-year row ID and uniformly permute it with NumPy default_rng(seed). Select ceil(fraction × pool size), nesting the 10% sample in the 25% sample. Use exactly the same subset in target-only and all corresponding augmented conditions. Do not stratify, redraw or reject samples based on classes or performance. Samples and splits are frozen before fitting. Local-full/zero-shot baselines are deterministic and recorded with seed 0; do not duplicate them 20 times.

## Model settings and safeguards

Use fixed, prespecified capacities from the original transfer plan, not settings selected from the restart's 2025 results: M0 unpenalized logistic; M1 L2 logistic C=1; M2 XGBoost depth=2, reg_lambda=10, 150 trees, learning_rate=.05, min_child_weight=5, subsample=colsample_bytree=1, histogram trees, seed 20261001 and one CPU thread. Logistic models use lbfgs, max_iter=3000, tol=1e-8. No class weighting or oversampling.

Fit a median imputer separately to each training membership; keep empty columns with zero fallback. Logistic scaling is fitted only on that membership. No sigmoid calibration is fitted in phase 5. Use the schema allowlist only: background alone for M0; all 9 primary features for M1/M2. No city, coordinates, identifiers, outcomes or exposure variables are predictors.

Single-class training uses a flagged constant probability equal to its training prevalence. Empty training pools are unsupported and must be reported. Do not use test data to rescue these conditions. Cache identical model family/sorted training-membership fits only; different memberships never share learned preprocessing. Preserve each unique model or explicit constant artifact, parameters, membership hashes, preprocessing values, warnings and probabilities. Computing predictions on additional 2025 rows does not make them fit inputs; only the condition's held-out fold enters its evaluation.

## Evaluation and uncertainty

Aggregate each condition's held-out folds into one complete target-year prediction vector. Primary metric is non-interpolated average precision. Also report ROC-AUC, Brier, ten equal-width-bin ECE, mean probability minus prevalence and top-decile precision/recall/lift, with ceil(0.1*n) and row-ID tie-breaking. Undefined metrics remain missing; no test-based choice of probability calibration, threshold or model family.

Transfer gap = local-full AP − source-only AP; positive means source-only is worse than local-full. Matched transfer benefit = source-plus-target AP − exactly matched target-only AP; positive means adding source data helps. Improvement over zero-shot is separate and cannot establish the benefit of source data by itself. Report each source and pooled source, both fractions and every seed/model/target. Summarize 20 seed differences using mean, sample SD, empirical 2.5/97.5 percentiles and positive/negative counts. These percentiles describe sampling variation; they are not confidence intervals or independent test-set replications. Do not promote a condition to a confirmatory result based on its seed distribution.

Report native probability calibration and source-to-target feature range extrapolation. Range diagnostics use 2024 source values and 2025 target feature values, preserve missingness and do not use target labels or select predictors. They are city-level coverage diagnostics, not fold-specific learned transformations. No phase 4-style bootstrap improvement gate is added after seeing results.

## Release and validation

Save the full experiment registry and frozen protocol/splits before training. Validate exact temporal/city membership, 1,500 m separation, deterministic nested samples, matched controls, cached-fit identity, fitted preprocessing, saved predictions and metrics. Reconcile all gaps, seed summaries and extrapolation tables. Keep primary-source and result checksums, package versions, progress logs, and step-by-step methods/results/reproduction documentation. All prior releases remain preserved. Computational completion does not resolve independent offense, linkage, facility, coordinate-precision, continuity or feature approval.
