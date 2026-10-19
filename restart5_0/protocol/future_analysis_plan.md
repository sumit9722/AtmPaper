# Phase 1 analytical commitments for later phases

This is a retrospective working plan recorded as part of Phase 1. It does not authorize or claim execution of phases 3–5, and it is not a preregistration. Previous releases exposed both complete outcome years. Numeric choices below retain earlier working conventions; PI ratification remains pending.

## Models and estimands

M0 is logistic regression on log(1 + prior-year robbery/burglary cases in the >200–500 m annulus). M1 is L2-regularized logistic regression adding the common historically available environmental feature set to the same baseline. M2 is shallow gradient boosting using the same environmental feature set. Phase 3 must freeze that feature dictionary, source vintages, missingness rules and training-only tuning search before any fit. Do not quietly redefine M1 as a best-performing prior-crime feature: nearby prior-year crime is a separately labeled temporal-persistence sensitivity and does not establish an environmental effect.

The primary binary comparison uses full-year 2024 training and full-year 2025 evaluation, retaining report-before-2025 labels for training. The 2023 313-day cohort is supplementary: its binary labels are not interchangeable with a complete year. Negative-binomial counts with a log-supported-days offset are a secondary analysis only after an explicit exposure/dispersion specification and approval of the membership-continuity assumption; supported days are not known operating days. Three calendar labels here provide only two complete outcome years and one complete forward annual comparison.

Do not fit a nominally complete M0 baseline to rows with unknown report availability without a separately frozen handling rule and sensitivity. Buffalo created_at remains an ingestion proxy even when present. Missingness flags, complete-measurement subsets or carefully justified alternatives must be evaluated transparently; zero imputation is not a default solution. Any city exclusion changes the cross-city claim and must be documented.

## Evaluation hierarchy and leakage prevention

Primary evaluation is forward temporal plus spatial separation, followed by leave-one-city-out transportability. Use five fixed spatial outer groups and 2 km spatial blocks; apply a 1,500 m WGS84 purge from held-out site coordinates to training sites, covering the inherited 500 m context radii with an additional margin. Check repeated physical-site/address identities and near-duplicate facilities across years, not only hashed coordinates. Fit imputation, scaling, hyperparameters and calibration inside training only. Where tuning is used, use inner spatial splits and the same purge; retain a declared simple fallback if too few groups/classes remain.

An independent, uninspected later outcome period is required for confirmatory claims. The existing 2025 observations cannot become an untouched holdout through a directory restart. Report every city and split, including negative and degenerate conditions; flag a constant-prevalence fallback for single-class training. Training-set-only feature selection cannot undo previous inspection of outcomes.

## Metrics and continuation criterion

Primary metric: non-interpolated average precision (AP), labeled precisely rather than conflated with trapezoidal PR area. Report the no-skill prevalence reference. Secondary metrics: ROC-AUC, Brier score, calibration, top-decile precision/recall and lift. Do not promote secondary metrics after a failed primary comparison.

The inherited exploratory continuation threshold is M1 minus M0 AP >=0.01 with a positive lower limit of a paired 95% spatial-block bootstrap interval, using 2,000 resamples within city. This analyst-selected threshold awaits PI approval. State whether uncertainty is conditional on fitted predictions; it does not cover feature-selection history or model-fitting uncertainty unless the whole procedure is refitted. Data validity and calibration are additional gates, so a numerical improvement alone does not certify scientific acceptance.

## Transfer ladder

For each target city, compare local-full, each individual other-city zero-shot source, pooled other-city sources, source + 10% and +25% earlier target labels, and exactly matched target-only 10%/25% controls. Adaptation labels come from the earlier period and remain disjoint and spatially purged from final target testing. Use nested uniform samples with seeds 20261001–20261020. The same sampled local labels, preprocessing protocol and evaluation membership must be used in each transfer/control pair.

Report transfer gap (local-full minus source-only) separately from transfer benefit (source+target minus matched target-only). Treat seeds as repeated training subsamples, not independent target populations. Preserve the complete family of comparisons; use jointly resampled target spatial blocks across seeds and Holm correction for the prespecified family when reporting multiple inferential contrasts. The previous 4.0 run needed a Monte Carlo-resolution amendment: set any permutation count and correction family before running tests, verify attainable p-value resolution, and prohibit optional stopping for significance.

## Review gate

The scientific review queue remains PENDING. These choices supply the model/metric/transfer/uncertainty commitments required by the blueprint's Phase 1; they do not resolve offense, exposure, reporting, positional or historical-boundary validity. Phase 3 onward has not been started in Restart 5.0.
