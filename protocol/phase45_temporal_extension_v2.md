# Phase 4 temporal extension and phase 5 transfer plan v2

Frozen 2026-10-03 before the new temporal fits. Existing 2025 spatial/transfer results have already been inspected, so this is a retrospective, outcome-aware project extension, not fresh preregistration or an untouched confirmatory experiment. User authorization permits acquisition and computation, not fabricated independent review.

## Data extension

Recover December 2023–November 2024 DFS monthly archives and combine them with the already archived December 2024–January 2026 snapshots. Construct 2024 annual exposure from consecutive positive exact-address/coordinate observations, gaps at most 62 days, clipped to the calendar year. Require 366 supported days in leap-year 2024. Preserve the existing 365-day 2025 cohort and original releases.

Acquire 2023 city crime records for lagged background. Use the same robbery/burglary native-offense definitions, case deduplication and municipal clipping as phase 2. Retain missing-coordinate, duplicate, report-date and boundary issues. Training labels for 2024 count records reported before 2025-01-01 where a report timestamp is published; Buffalo created_at remains an uncertified proxy. Preserve unfiltered counts as diagnostics. This does not reconstruct historical database revisions or prove absence of unreported crime. Retrospectively bracketed exposure also uses later archive observations.

Use a fixed 2018–2022 ACS five-year context for BOTH outcome years. This release was available 2023-12-07, before both prediction windows. Join to its matching 2022 geography, retaining margins of error/annotations and ambiguous matches. Reuse EPA SLD 2021. Recompute ATM competition from December 2023 for 2024 features and December 2024 for 2025 features. Exclude the focal identity but keep distinct co-located records flagged. Background predictors use prior-year primary events with available report timestamps before that outcome year's cutoff. Keep the same 14 predictor names/semantics, with fixed ACS 2022 income units and definitions. This is a versioned change from phase 3's ACS 2023 context, not an overwrite.

## Phase 4 temporal evaluation

Train only on 2024 labels and test only on 2025 labels. Use the previously frozen 2025 five spatial groups as the outer test assignments. For each fold, purge 2024 training locations within 1,500 m WGS84 of held-out 2025 centers; this leaves 500 m between 500 m context circles. All 2025 sites receive exactly one prediction per model. Same-site previous-year labels are thereby excluded in a held-out spatial neighborhood.

Form five outcome-independent training spatial groups from 2024 2 km grid blocks using the same seeded KMeans procedure. Within each outer training pool, use purged spatial inner folds for selection. Reuse phase 4 M0/M1/M2 grids, preprocessing, training-only sigmoid procedure, native-probability primary metrics, and 2,000 paired city-stratified 2 km block bootstrap draws. No 2025 labels enter preprocessing, selection, calibration or fitting. Report AP, ROC-AUC, Brier, calibration and top-decile capture by city and pooled. This completes the temporal computational comparison, subject to the remaining research limitations.

## Phase 5 experiments

For each target city and each of its five 2025 spatial test folds, define the candidate local pool as 2024 target-city rows at least 1,500 m from that fold's test locations. Source pools contain only other cities' 2024 rows, with the same spatial purge. All experiments for a target/fold use the identical 2025 test rows.

For each M0, M1 and M2 run:

- Local-full: all eligible 2024 target rows.
- Each-source zero-shot: each other city's eligible 2024 rows separately.
- Pooled-source: both other cities' eligible 2024 rows.
- Each source plus 10% / 25% target, and pooled sources plus those same target subsets.
- Target-only 10% / 25% controls with EXACTLY the same selected target rows as each augmented condition.

Use seeds 20261001–20261020. Within each seed/fold use a uniform permutation of the target pool, choosing ceil(fraction * pool size), with the 10% subset nested in the 25% subset. Never stratify or redraw to obtain more favorable class counts. Small subsets may contain one class: use a constant probability equal to that training subset's empirical prevalence, and explicitly flag this fallback. Empty training pools must be reported unsupported, not fabricated or filled with test observations.

For transfer comparisons, fix M0 unpenalized, M1 C=1, and M2 max_depth=2/reg_lambda=10 with the other phase 4 XGBoost settings. These prespecified settings avoid tuning zero-shot models on any target labels and keep augmented/control capacity the same; they are not selected from temporal or phase 5 test results. Fit imputation/scaling ONLY on each condition's own training rows. No sigmoid refit in phase 5; assess native-probability calibration rather than using target test outcomes to calibrate. Cache identical model training sets by model and sorted row IDs; no cross-condition information is learned by caching.

Aggregate held-out folds into one target-year prediction vector per experiment, model, seed and fraction. Report transfer gap = local-full AP minus source-only AP, and matched transfer benefit = augmented AP minus target-only AP separately. For each fraction, report the 20 seed outcomes, mean, SD and empirical 2.5/97.5 percentiles; these percentiles describe sampling variation and are NOT confidence intervals. Report negative differences, single-source vs pooled differences, both top-decile and probability metrics, and source-to-target feature range extrapolation. Phase 5 results are descriptive regardless of phase 4's numerical gate; do not imply confirmatory transfer established.

## Outputs and research acceptance

Preserve phase 4 v1. Write the temporal supplement under results/phase4/temporal_v2, common extended data under results/temporal_data and phase 5 under results/phase5. Provide Markdown work/method/result/reproduction documents, CSVs (gzip for potentially large tables), figures, model/sampling audits, source/code hashes and validation. Keep each new artifact below 100 MB for GitHub; no history rewrite or remote push is part of this task.

Computational status may be complete after all specified feasible experiments and checks pass. Scientific acceptance remains pending independent crime/linkage/facility review, Buffalo precision assessment, feature and continuity approval, and recognition of prior 2025 inspection and retrospective source revisions. No assistant-generated review is labeled independent human sign-off. If acquisition fails or a training condition is unsupported, record that precise limitation rather than declare full completion.
