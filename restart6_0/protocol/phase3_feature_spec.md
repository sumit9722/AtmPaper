# Restart 6 Phase 3 — environmental, housing and prior-crime features

Working specification written before Phase 3 extraction on 2026-10-24.
The user authorized Phase 3 after completion of phases 1–2. Reuse the latest
Restart 4 feature families (21 environmental/housing candidates, six nearby
prior-crime candidates and the prior-year annulus baseline), with new source
joins for NYC, Chicago and Los Angeles city. This is an exploratory extension,
not an independently approved or preregistered analysis. Fit no models.

## Population and timing

Keep all 2,731 full-year 2024–2025 OSM site-years. Preserve all 1,287 partial
2023 rows as a separately labeled supplement. Do not stack alternative
exact-coordinate cohorts. Annual predictor cutoff is January 1 of the outcome
year; partial 2023 uses January 1, 2023, not its first observed snapshot.
Coordinates and cohort membership are the retrospectively constructed Phase 2
baseline locations; this is not a genuinely prospective ATM inventory.

Use fixed ACS 2018–2022 five-year estimates, released December 7, 2023, and
official 2022 TIGER/Line block groups and ALAND. The release precedes both main
prediction years but not 2023: leave every ACS feature missing in that
supplement. Use EPA Smart Location Database v3 (2021 release, 2019 block-group
geometry) for all three years. Join ACS and EPA independently; GEOID20 in EPA
does not imply 2020 geometry. Preserve vintage and retrieval dates separately.

## Features and source values

The machine-readable `phase3_variables.json` freezes formulas, transforms and
roles. Retain the eight prior housing formulas without outcome-guided changes,
plus population density, income, unemployment, eight EPA context measures and
two ATM competition measures. Natural log1p and ratios are deterministic;
perform no global imputation, scaling, selection or outcome-based filtering.

Preserve source estimates and 90% margins of error. Public ACS table-based
summary files supply numeric sentinel values; retain them and derive only the
standard documented jam-value annotations. Other API-only annotations are
unavailable and must not be invented. Negative/nonfinite estimates are missing;
ratios require every component and a positive denominator. Do not calculate
ratio margins of error. Preserve genuine zero values and flag income coding.

Unique polygon covers joins only. Leave ambiguous/unmatched joins missing.
Material geometry errors fail the build; allow make_valid only for polygonal
results with relative area change below 1e-6 and save a repair audit. Preserve
distance to polygon boundaries and existing municipal-boundary flags.

## Historical ATM competition

Replace the earlier DFS competition population with the same historical OSM
tag definition as Restart 6. Use all raw objects in each city's original query
bounding box at 2023-12-15 or 2024-12-15, including outside the municipal
polygon. Exclude the focal type/ID, retain other co-located objects, and save
their identities. Never restrict neighbors using later survival. Non-point
features use projected centroids, consistent with Phase 2.

Density is other mapped objects within geodesic 500 m divided by pi*0.5^2 km².
Nearest distance is the WGS84 distance to another object. The bounding-box
inventory is incomplete outside its query region: leave density missing if
the 500 m circle is not safely contained; leave nearest distance missing unless
the found distance is smaller than the conservative distance to the query
boundary. Use a 1% projection safety margin. Retain coverage flags. There is no
December 2022 snapshot; both competition measures stay missing for 2023.

## Prior crime and leakage

Reconstruct preceding-calendar-year robbery/burglary at <=25/50/100 m, robbery
and burglary separately at <=50 m, and July–December crime at <=50 m. Primary
counts require a usable original report date strictly before the cutoff.
Keep unfiltered occurrence-year versions as explicit retrospective sensitivity
features. Chicago has no original report dates: all seven report-filtered
crime predictors, including the inherited annulus baseline, stay missing.
Zero is not a substitute for unknown availability. For NYC/LA, retain counts
and flags for missing or late report dates. Preserve all prior-event links.

No outcome-year crime, labels, future ATM membership, exposure days, city IDs,
coordinates, or survival flags appear in predictor matrices. Store lookup,
quality fields and labels separately. Keep every cohort row despite missing
features. Later model preprocessing must be learned within training folds.

## Validation and deliverables

Freeze Phase 3 inputs separately from the unchanged phases 1–2 release.
Reuse existing sources only after checksum verification, recording original
paths and retrieval metadata. New inputs live under `phase3/raw`; results
under `results/phase3`. Leave the original Phase 1–2 manifest and status intact.

Publish primary/sensitivity matrices, raw components, joins, prior-crime and
ATM neighbor links, source and feature dictionaries, by-city/year missingness,
quantiles, constant-feature and Spearman >=0.90 flags, standalone plots,
methods/results/reproduction notes, frozen manifests and executable validation.
Independently check formulas, polygon membership, temporal eligibility,
geodesic omission checks and row preservation. Test missingness and cutoff
edge cases with synthetic fixtures kept separate from research outputs.
`confirmatory_modeling_ready=false`; scientific review remains pending.

References: [ACS release schedule](https://www.census.gov/programs-surveys/acs/news/updates/2023.html),
[ACS summary files](https://www2.census.gov/programs-surveys/acs/summary_file/2022/table-based-SF/),
[TIGER 2022 block groups](https://www2.census.gov/geo/tiger/TIGER2022/BG/),
[EPA Smart Location Database](https://www.epa.gov/smartgrowth/smart-location-mapping).
