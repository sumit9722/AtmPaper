# Restart 4.0: completed empirical simulation through Phase 5

This retrospective specification is written before the 4.0 model runs. Earlier
2024 and 2025 results have already been inspected. All inference is exploratory;
a significant result is an outcome to assess, not a constraint on the output.

## Phases 1–2: audited inheritance

Retain the 3.0 full-year annual cohorts, official archived police records,
report-date-filtered 2024 labels, 2025 labels, 50 m outcome definition, and
annual spatial assignments. Verify their saved validation and checksums.
Record inherited source paths and hashes; do not describe cached data as fresh
downloads. Independent offense, facility, exposure, coordinate and linkage
reviews remain pending. The unit is an ATM site-year; nearby crime is not
verified ATM-targeted crime.

## Phase 3: feature reconstruction

Combine the eight 3.0 housing predictors and thirteen 2.0 environmental
predictors, joining exact site-year IDs. Include the existing prior-year
200–500 m background predictor. Add six predictors computed independently from
prior-year robbery/burglary records: log(1+count) within 25, 50 and 100 m;
robbery and burglary separately within 50 m; and July–December crime within
50 m. Each event must occur in the preceding calendar year and have a known
report date strictly before January 1 of the outcome year. Reconstruct features
at each year's site coordinates. Preserve event links and missingness. These
new predictors represent temporal crime persistence, not housing effects.

## Models and selection

M0: background-only unpenalized logistic regression, matching the previous
baseline. M1: L2 logistic regression (C=1), choosing between background alone
and background plus exactly one candidate predictor. M2: shallow boosted trees
using the same selected variables as M1 (150 trees, depth 2, learning rate .05,
lambda 10, minimum child weight 5, no subsampling, one CPU thread).

For every distinct training membership, independently select the candidate
with maximum mean validation non-interpolated average precision on 2024 data.
Use three spatial groups (saved 2024 fold modulo 3), with a 1,500 m geodesic
purge between inner training and validation. Use common folds for all
candidates, requiring at least 10 inner training rows and both classes in
training and validation. With fewer than two valid folds, retain background
alone. Ties within 1e-12 retain the first candidate (background first).
All imputation and standardization are fitted inside each training fold.
No selection uses 2025 labels, including choice of source, radius, family,
capacity, adaptation fraction, seeds or bootstrap settings. Single-class final
training yields a flagged constant at training prevalence.

Selection uses a batched Newton solver for the same standardized penalized
logistic objective, checked against sklearn. Final artifacts use sklearn and
XGBoost. Persist all candidate scores, selected predictors, memberships,
preprocessing and probabilities. M2 is a secondary comparison, not an
opportunity to switch the primary family after inspecting test results.

## Phase 4

Train on 2024 and evaluate all 2025 sites using five spatial outer folds
(simultaneously across cities), plus leave-one-city-out transfer. Purge every
training site within 1,500 m of any outer test site. Retain the fixed 50 m
primary outcome. Primary comparison: M1 minus M0 pooled forward-spatial AP;
numerical success requires difference >= .01 and a positive 95% paired spatial
block-bootstrap lower limit. Report M2 and city/scheme comparisons separately.
Bootstrap 2,000 times within city, sampling saved 2 km blocks, conditional on
fitted predictions. A no-skill prevalence reference and Brier/ROC-AUC/top-decile
metrics accompany AP; high AP caused by prevalence alone is not improvement.

## Phase 5

Use exactly the same target-specific folds, 1,500 m purge, local-full,
individual-source, pooled-source, target-only and source-plus-target ladder as
3.0. Include fractions .10 and .25, seeds 20261001–20261020. Nested uniform
target samples and exactly matched controls are mandatory. Select features
using ONLY the actual training membership, including only the sampled target
labels in adapted fits. Cache identical memberships; selection is shared by
M1/M2. Source sample size is not artificially balanced or resampled.

Report every condition and mean AP benefit across seeds. Seeds are repeated
training subsamples, not independent target populations. For each of the 54
source/fraction/model comparisons, resample target spatial blocks jointly
across all 20 seed vectors (2,000 replicates). Report paired 95% intervals and
conditional block-swap randomization p-values (999 permutations, add-one
correction); use Holm adjustment across all 54 comparisons. A statistically
supported exploratory benefit requires mean AP gain >= .01, positive lower
interval and Holm-adjusted p < .05. The randomization null assumes prediction
pair exchangeability at the block level; neither test refits models or accounts
for all prior research choices. Small-city uncertainty and previously inspected
outcomes must accompany any significant finding. No optional stopping.

## Validation and reproduction

Complete all five phases, fail on checksums, future-event leakage, mismatched
cohorts, duplicate predictions, spatial violations or unmatched controls.
Independently reconstruct new feature counts using direct geodesic distances;
verify selected candidates against saved inner scores and representative
sklearn fits. Replay every final model's predictions. Recalculate metrics and
matched contrasts. Preserve 1.0–3.0. Publish scripts, tables, figures, manifests,
validation, limitations and one command for offline reproduction.
