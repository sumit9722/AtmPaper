# ATM-site crime study specification v1.0

Prepared 2026-10-01 before model fitting. This is an analyst-frozen working specification, not a signed or externally registered protocol. Independent crime-domain and GIS review remain required. No models are fitted in phases 1–2.

The research question is whether the environment of bank-owned/in-bank ATM sites predicts future physical acquisitive crime beyond lagged surrounding crime, and whether the signal transfers between New York City, Buffalo and Rochester. The outcome describes nearby police-recorded incidents, not verified attacks on ATM machines.

## Population and geography

Use NYS DFS dataset ndex-ad5r as the common ATM denominator. Preserve the supplied query.json and download a fresh copy. OSM nodes are supplementary candidates only: bank ownership, completeness and dates of operation are not established by an OSM tag. Never pool OSM-only machines into the primary DFS population.

Assign sites by WGS84 point-in-polygon against the Census TIGERweb incorporated-place polygons: New York 3651000, Buffalo 3611000, Rochester 3663000. Municipal postal names alone are insufficient. Boundary vintage is the downloaded current polygon; historical boundary stability is not independently established.

Use EPSG:32618 for NYC and EPSG:32617 for Buffalo/Rochester for spatial indexing. Final distances use the WGS84 ellipsoid. An exact normalized-address and coordinate match collapses DFS rows to one site; nearby sites within 10 m receive a connected-component cluster ID and are flagged for facility review. Nearby distinct addresses are retained until reviewed. Coordinates identify a location, not verified equipment availability.

## Outcome and periods

Primary outcome: any police-recorded robbery or burglary within 50 m of a site in a calendar year; retain counts too. Include attempts where the source classifies them in these categories; preserve attempt status where available. Exact city-native mappings are in the generated codebook. Narrow robbery-only and burglary-only counts are retained for sensitivity. Larceny/theft is a broad, exploratory sensitivity, excluding NYC descriptors explicitly mentioning credit cards, debit cards, identity theft, fraud, account or similar financial mechanisms; coarse Buffalo/Rochester theft remains potentially ambiguous and is never the primary endpoint. Exclude motor vehicle theft, theft of services, fraud, forgery, assault, weapons, vandalism and other nonprimary categories from the primary outcome.

Retrieve 2024–2025 records. The initial operational panel uses 2025 outcomes and qualifying 2024 crime at distances >200 m and <=500 m as background. Do not filter police data to ATM premises. Count unique city complaint/case identifiers, with duplicate source rows preserved in an audit. An incident may match multiple sites; retain multiplicity and nearest-site-only sensitivity. Use 25 m and 100 m as radius sensitivities. Report public-coordinate precision and boundary sensitivity.

Historical monthly ATM snapshots must be investigated before assigning past exposure. Unless source snapshots and an explicit continuity rule support the year, label the 2025 panel exploratory_current_snapshot_backcast and set confirmatory_eligible=false. Leave actual active_from, active_to and active_days null. Never convert a portal publication timestamp into an opening date. A prospective cohort may be enrolled from the current extract; future outcomes remain null, not zero, and follow-up depends on continuing ATM-status checks.

## Subsequent phases: fixed analysis plan

Primary M0: logistic regression using log1p(previous-year robbery/burglary in the 200–500 m annulus). M1: regularized logistic regression adding common ex-ante environmental variables. M2: gradient boosting with the same variables. Negative Binomial counts are a secondary formulation only if defensible exposure duration is available. Primary metric AUPRC; secondary ROC-AUC, Brier score, calibration, top-decile precision/recall and lift.

Use forward temporal validation, spatially grouped folds with at least 500 m separation between training and held-out site contexts, and leave-one-city-out evaluation. All imputation, scaling, tuning and calibration occur within training data. The present one-outcome-year panel cannot support credible forward temporal model validation; acquire additional exposure-supported years or prospective follow-up first.

Transfer ladder: local-full, each other-city zero-shot, pooled other cities, source+10% and +25% target, and exactly matched 10%/25% target-only subsets. Target adaptation data are disjoint from final target testing. Use 20 fixed sampling seeds (20261001 through 20261020). Report transfer gap and benefit separately.

Working practical-effect threshold chosen before fitting: absolute AUPRC gain >=0.01 over M0 with the lower bound of a paired spatial-block bootstrap 95% interval >0 (2,000 replicates). This is an analyst-selected convention, not a threshold supplied by the blueprint; PI ratification is pending. Require data validity and calibration assessment before transfer claims. A wide interval is inconclusive, not evidence of no effect.

No operational protected-demographic features. Phase 3 must separately freeze a common environmental feature dictionary and historical availability. The current OSM snapshot cannot be used as an ex-ante 2025 predictor. Placement optimization is outside phases 1–2.

## Decision log and release gate

2026-10-01: Chose robbery+burglary to avoid incompatible and potentially transactional theft definitions. Chose 2024 background/2025 outcome as a recent complete-calendar-year exploratory extraction, not as proof of historical ATM exposure. Retained all three cities but flag Buffalo's rounded/block-address coordinates. Full blueprint acceptance requires historical exposure adjudication, independent offense review, stratified manual linkage review and sign-off; computational completion does not substitute for those gates.
