# Restart 7 — review-driven revision of Restart 6, phases 1–3

Recorded 2026-10-28. The user authorized a new restart based on Restart 6,
reusing existing work and applying the findings in `PAPER_REVIEW.md`.
This is an exploratory retrospective revision. Both outcome years and earlier
results have already been inspected. This document is not a preregistration.

## Question and limits

Does neighborhood context add information beyond prior local and surrounding
crime for a retrospective benchmark of police-recorded crime-coordinate
proximity to mapped ATM-enabled locations in NYC, Chicago and Los Angeles?

The outcome remains at least one retained robbery or structural-burglary case
with a released coordinate within 50 m of the mapped location; publish 25/100 m
alternatives and robbery/burglary components. Keeping 50 m preserves the previous
benchmark, not a claim that the source coordinates have 50 m accuracy. No radius
in these files is certified as the true physical incident-to-ATM distance.
Do not infer ATM targeting, actual operating exposure, a causal environmental
effect, or an ATM-specific mechanism. There are no non-ATM comparison sites.
The original crime geocodes cannot be repaired using these cached data.

## Reuse and phase boundaries

Restart 6 is immutable input. Verify consumed outputs against its existing
manifests and freeze their hashes in this release. Reuse the reconstructed OSM
cohorts, municipal and environmental joins, geodesic event links, monthly
exposure, ACS/SLD measurements, and neighbor audits. Reaggregate only the
offense-dependent counts and affected model matrices. No downloads, fresh
exposure reconstruction, global rematching, new environmental acquisition or
model fitting are part of this restart. A small independent distance audit is
validation, not a rebuild of all links. Record source and code dependencies.

Keep all 2,731 full-year 2024–2025 rows as the corrected master cohort, and all
1,287 partial-2023 rows as a separate supplement. Exact-identity alternative
panels remain in Restart 6 and are not revised or suitable for mixing with the
new offense definition. Historical membership still conditions on subsequent
OSM presence. It is a retrospective survivor sample, not an inventory available
at the beginning of the prediction year.

## Offense correction

Exclude NYC PD codes 231, 233 and 234 (truck burglary), and Chicago IUCR 0760
(burglary from motor vehicle), from outcomes AND all preceding-year predictors.
LA's existing vehicle-burglary exclusion remains. Retain robbery, including
carjacking, because robbery is a separate common offense family. Existing
attempt inclusion and incident-level priority remain. Preserve excluded cases,
the original category, source provenance and all before/after count changes.
Check discarded duplicate rows: if an excluded winning case hides a retained
alternative offense, stop rather than silently dropping the case.

Produce an explicit codebook decision for every native code/description.
Flag contradictions between source codes and descriptions (including LA NIBRS
220 descriptions that do not describe burglary) for review; retain authoritative
source-code classification with a separate exclusion sensitivity. This is an
automated rule audit, not independent codebook approval. Unknown cross-system
case equivalence and LA's March 2024 reporting transition remain open.

## Cohorts and location safeguards

The conservative main subset requires a full-year inherited row, point geometry,
maximum inherited coordinate drift <=10 m, a clear 500 m municipal boundary
buffer, and no other mapped object within 10 m in the preceding December
inventory or inherited facility-pair audit. Exclude every member of an unresolved
pair; do not choose a winner or assert that nearby objects are one facility.
Keep a separate point-only subset and a stricter `amenity=atm` subset.
All exclusions are reversible views of the corrected master, with a row-level
eligibility ledger and sequential attrition by city/year. Partial 2023 remains
supplementary because its inventory and feature availability differ.

Point bank objects tagged `atm=yes` remain mapped ATM-enabled locations, not
verified machine positions. Centroids and close pairs stay available in the
master sensitivity, with explicit flags. Nearest-site outcome assignments must
be recomputed within each selected cohort from cached distances, because the
nearest retained site can change after cohort restriction.

## Comparable information and timing

The common three-city baseline is two fixed predictors: log1p(previous calendar
year retained crime within 50 m) and log1p(previous calendar year retained crime
at >200–500 m). Both use occurrence-year counts from the latest cached extracts
in EVERY city. This is explicitly retrospective and does not claim historical
data availability. Never use report-filtered counts in some cities and
unfiltered counts in another within the same model specification.

Provide a separate NYC/LA sensitivity with both predictors report-filtered
strictly before January 1, and earlier training labels reported before the next
January 1. Chicago's corresponding fields remain missing. Report-filtering a
modern extract does not reconstruct an archived historical database.

## Phase 3 and subsequent modeling commitments

Freeze 19 inherited ACS/SLD environmental predictors for the primary extension;
place the two OSM competition measures in sensitivity because mapped objects
are not adjudicated facilities. Baseline = the two fixed crime predictors;
environmental extension = the identical baseline plus those 19 predictors.
Publish a direct prior-local-crime ranking benchmark for future evaluation.
Do not allow selection to remove the fixed local-crime baseline in small samples.

Retain the expanded environmental collection as an exploratory supplement.
Remove three CBSA totals and six predefined redundant aliases from its predictor
export, after checking equality on the complete inherited main/partial inventory.
Preserve their original values in Restart 6 and record the exclusions. No
outcome-guided feature search, global imputation or scaling is performed.
EPA/ACS vintages and partial-2023 missingness remain unchanged.

Future evaluation must report each city, prevalence, AP, ROC-AUC, Brier and
calibration. Use temporal separation and spatial purging, group repeated OSM
identities/nearby components, and report source-geography replication. Compare
transfer to the SAME fixed-feature local model with the SAME local labels, plus
local-full and the direct lag score. Distinguish low-sample failure from transfer
benefit. Seeds are repeated training samples, not independent test populations.
Neither 2024 nor 2025 is an untouched holdout. Any future feature selection and
preprocessing must use training data only. No phases 4–5 are executed here.

## Completion

Phases 1–3 can be computationally complete with independently checked arithmetic,
preserved input hashes, corrected panels and declared feature matrices. Physical
facility checks, source ascertainment, location precision and LA system
comparability remain scientific gates. Do not mark those PASS based on code
execution. `confirmatory_eligible=false` and `models_fitted=false` throughout.
