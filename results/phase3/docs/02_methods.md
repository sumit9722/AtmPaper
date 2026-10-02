# How phase 3 was built

## Sources and timing

| Source | Vintage / availability | Use |
|---|---|---|
| [ACS five-year release](https://www.census.gov/programs-surveys/acs/news/data-releases/2023/release.html) | 2019–2023 survey period; released December 12, 2024 | Population, income and unemployment |
| [Census ACS 2023 TIGERweb](https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer/10) | January 1, 2023 geography | Block-group assignment and official land area |
| [EPA Smart Location Database](https://www.epa.gov/smartgrowth/smart-location-mapping) | Version 3 released in 2021; 2019 block-group geometry | Common built-environment context |
| [EPA service](https://geodata.epa.gov/arcgis/rest/services/OA/SmartLocationDatabase/MapServer/1) | Version 3; inputs mainly 2017–2020 | Selected raw indicators and polygons |
| Archived NY DFS version 270 | December 15, 2024 membership snapshot | Pre-cutoff bank-owned/in-bank ATM competition |
| Phase 2 police background | 2024 incident dates; later-retrieved/revised extracts | Previous-year robbery/burglary at >200–500 m |

The EPA [technical guide](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf) is archived under `data/raw/phase3/`. EPA's availability field uses December 31, 2021 as a conservative upper bound within its documented release year, not a claimed exact publication day. Service retrieval dates and SHA-256 hashes are retained separately. These live archived-vintage services do not prove the exact values visible to a user on January 1, 2025. Police background has no asserted exact historical availability date.

Acquisition used 31 sequential public requests: two layer metadata requests, one EPA guide and 28 count/geometry requests. Each request after the first in an invocation was separated by two seconds. Completed responses are cached and checksum-verified. There are no automatic retries and no use of the Census API key. An initial sandbox-blocked connection was followed by an authorized network run.

## Spatial assignment

Each ATM point is joined separately to ACS 2023 and EPA 2019 block groups. EPA's field `GEOID20` is a source identifier for its 2019 geography; it must not be mistaken for 2020 Census geometry. The output retains `acs_geoid_2023`, `sld_geoid_2019`, and the source's older `GEOID10` separately.

The builder uses a Shapely spatial index and polygon `covers` logic. Exactly one match is accepted. Zero matches remain unmatched; multiple matches remain ambiguous. No nearest-polygon substitution or arbitrary tie-break is used. Ambiguous and unmatched values are null, with candidate IDs in the audit.

Two Census polygons and one EPA polygon contained self-intersections. GEOS `make_valid` repaired copies in memory. Repairs were allowed only when the result remained Polygon/MultiPolygon and relative area change was below 0.0001%. The observed maximum was about 0.0000231%. Raw files remain unchanged and repair details are saved in QA. This is a geometry hygiene step, not new geocoding.

Boundary-distance diagnostics use UTM zone 18N for NYC and 17N for Buffalo/Rochester. Sites within 10 m of a block-group boundary and within 500 m of a municipal edge are flagged. The latter uses the phase 2 current city polygon and is only a warning of possible annulus truncation.

## Feature calculations

Population density = ACS population / official Census land square metres × 1,000,000. Water area is excluded from the denominator. Income uses ACS reported 2023 dollars. Unemployment = unemployed civilian population / civilian labor force; zero or missing denominators remain null. Original 90% margins of error and annotations remain available. Top/bottom-coded income is flagged: a reported threshold is not an exact income estimate.

EPA indicators are attached without city-specific rescaling. Density units and definitions remain source-specific: for example, job density uses unprotected acres and road density uses facility miles per square mile. They are neighborhood context, not measurements inside each ATM's 50 m crime buffer. Source negative sentinels, including -99999, become missing; genuine zeros remain zero. Transit sentinels may represent absent service, insufficient GTFS coverage or distance thresholds, so they are not silently recoded as no service.

For ATM competition, deduplicate the December 2024 archive by normalized street address plus coordinates rounded to seven decimal places, matching the identity precision in phase 2. Use all parseable coordinates inside a broad New York bounding rectangle; this removes malformed locations but does not certify geocode accuracy. Exclude only the focal identity. Preserve distinct co-located identities and flag neighbors within 10 m for facility review.

Other-ATM density = other December 2024 sites within 500 m / (pi × 0.5²) square kilometres. Nearest-other-ATM distance is the minimum WGS84 ellipsoidal distance across that statewide inventory. This avoids city-boundary clipping of the ATM denominator, but excludes other states and independent nonbank ATMs. Physical-site identity and operation remain subject to phase 2 review.

All selected right-skewed nonnegative variables use natural log(1 + value); unemployment and entropy remain untransformed. No global imputation, scaling, outlier trimming, learned feature selection or model fitting is performed. The primary list was fixed before extraction; pooled and city-wise correlations are diagnostics only.

## Quality checks and freeze

Missingness and quantiles are reported separately for every city and cohort. Missingness above 20% and absolute pairwise Spearman correlation at least 0.90 are predefined review flags. Correlations use available pairs, report their sample sizes, and do not change the frozen feature set. Validation checks the source counts and source attributes, verifies all deterministic transformations, samples spatial joins without the builder's spatial index, and recomputes sample ATM distances individually. Source and output manifests allow subsequent changes to be detected.

Outcome labels, exposure duration, city, coordinates and administrative geography IDs are stored separately from predictor matrices. Downstream code should use the schema allowlist, not every numeric column in the raw context or lookup tables. Any later source/identity correction must trigger a rebuild and a versioned release before model tuning.
