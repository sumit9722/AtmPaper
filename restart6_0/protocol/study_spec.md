# Restart 6 — NYC, Chicago and Los Angeles

Retrospective working specification, prepared 2026-10-23 before building the new panels. The user requested replacing Rochester and Buffalo, reusing prior work, and explicitly accepted a separate exploratory historical OpenStreetMap (OSM) cohort. Scope follows Restart 5 phases 1–2: acquire, reconstruct exposure, harmonize, link and audit. No models are fitted or old model results transferred.

## Reuse and population

Retain New York City. Reuse verified Restart 5 NYC crime for 2022–2025, its separate DFS official ATM reference panels, the 36 monthly snapshot dates, 2023 partial / 2024–2025 full-year design, geodesic linkage, exposure sensitivity and site-month aggregation code. Preserve original releases. New Chicago and LA records must come from their own sources; changing city names is never a data conversion.

The common exploratory population is OSM objects tagged `amenity=atm` or `amenity=bank AND atm=yes`, in all three municipalities. Bank buildings without explicit ATM tags are excluded. Standalone ATMs may be independently operated. No bank ownership is inferred from a name, proximity or FDIC branch status. NYC DFS reference data stay separate and must not be pooled with the OSM cohort. OSM coverage and edit history are not a census of ATMs or evidence of actual opening/closing dates. OSM contributors/ODbL attribution must accompany derived outputs.

## Exposure

Query historical OSM states at the same 36 dates as Restart 5, 2023-02-22 through 2026-01-15. Retain stable OSM type/ID for continuity, and type/ID plus exact coordinates for the strict sensitivity. Full-year inclusion requires the object in all 14 snapshots from prior December through following January, adjacent monthly gaps <=62 days, and <=50 m displacement from the prior-December point. Save <=10/25/50 m sensitivity. Partial 2023 requires all 12 available February–January observations, begins 2023-02-22, and covers 313 days. Missing observations break continuity; do not fill missing years with zero or backcast current locations.

Use returned centroids for non-point OSM objects, explicitly flag them, and retain a point-only sensitivity. This is an OSM mapping-continuity assumption, not observed operational exposure. Multiple OSM objects within 10 m require facility review and must not silently become independent physical facilities.

## Crime and geography

Download Chicago `ijzp-q8t2`, LA legacy `2nrs-mtv8` and consolidated LA NIBRS `k7nn-b2ep`, for occurrence years 2022–2025. Preserve source metadata, queries, raw bytes and hashes. Reconcile source-row counts and unique row IDs before/after paginated downloads. A stable count cannot rule out same-count revisions during extraction.

Chicago includes primary types ROBBERY/BURGLARY. Legacy LA includes codes 210/220 (robbery/attempt) and 310/320 (burglary/attempt), excluding burglary from vehicles. NIBRS includes 120 (robbery) and 220 (burglary/breaking and entering). Combine LA feeds by normalized case number; do not sum offenses as independent incidents. If a case has multiple eligible rows, use robbery > burglary, then NIBRS > legacy, then deterministic source order. Retain conflicts and excluded rows for audit. This preserves Restart 5's incident hierarchy but does not eliminate LA's reporting-system break. Never infer a complete LA year solely from the legacy feed. Source presence and monthly counts establish observed extracts, not complete police ascertainment.

Chicago has no original report date in this feed. `updated_on` is not substituted for it. Leave report-filtered background counts missing when report availability is unknown; retain unfiltered occurrence-year background as explicitly retrospective context. NYC/LA use available report dates strictly before January 1 of the outcome year. Latest extracts are not databases frozen at historical cutoffs.

Use Census municipal polygons for NYC (3651000), Chicago (1714000), and Los Angeles city (0644000), not LA County. Document current-boundary vintage limitations. Projection EPSG:32618/32616/32611 respectively is used only for candidate searches and geometry; final distances use WGS84 ellipsoidal geodesics.

## Linkage and deliverables

Reproduce nearby robbery/burglary at <=25/50/100 m, and prior-year background at >200–500 m. Restrict partial outcomes to supported half-open dates. Save all matches, multiplicity and deterministic nearest-site sensitivity. Compute boundary distance and annulus fraction inside the city. Chicago and LA locations are public block-level geocodes; small-radius results measure proximity to released coordinates, not exact incident locations or ATM-targeted crimes. No arbitrary jitter or invented precision bounds.

Produce annual and monthly panels, coverage/exclusion/codebook/provenance tables, facility and sampled linkage review queues, an offline ATM-only map, source and artifact manifests, and executable automated validation. Report computational status separately from scientific acceptance. `confirmatory_eligible=false` throughout. Independent review remains required for source completeness, OSM selection bias and identity, block-coordinate suitability, LA system transition, and leakage-safe predictors.
