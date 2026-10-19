# Methods and interpretation

The primary construct is future nearby police-recorded robbery/burglary at a bank-owned/in-bank ATM location. No event is asserted to target a machine. Units are annual site-periods with separately documented exposure duration. The 2023 partial cohort is a duration-annotated extension; it is not a full-year zero-filled backcast.

## Exposure and location

Full-year cohorts require fourteen monthly observations: previous December through following January, all unique for city/normalized address and within 50 m of the initial point. The 2023 partial cohort applies the same spatial and identity rule to twelve observations beginning 22 February; only 313 days are supported. There are no extrapolated January/early-February outcomes. Each year is assembled independently, avoiding a requirement to survive throughout all study years.

The exact-identity sensitivity intersects membership between adjacent monthly snapshots, requires a single-month step and a gap <=62 days, clips to the calendar year, and merges touching intervals. Its row-level start/end fields bound the union; they do not imply uninterrupted exposure if supported_interval_count exceeds one. The authoritative exact interval union is qa/exact_exposure_intervals.csv. Actual operating duration is unknown for every cohort.

The prior-year annulus is calculated at that period's fixed site coordinate, irrespective of whether the ATM was present in the baseline year; it describes surrounding place context. All input events are clipped to the same municipal polygon, so background and even outcome neighborhoods can be truncated near a boundary. Annulus coverage is a diagnostic in the city-specific UTM projection, using 64 polygon segments per quadrant. The boundary-clear sensitivity excludes sites within 502 projected metres of the polygon edge.

## Case, date and source rules

NYC historical and current-year feeds are joined using their persistent complaint identifiers. Buffalo uses case_number and Rochester Case_Number. Only primary categories are an aligned NYC extraction; other cities' nonprimary rows support quality audits. The city-case hierarchy is robbery > burglary > other, later occurrence, then deterministic source-file/index order. Conflicts remain in the duplicate queue; this convention is subject to independent review.

Rochester epoch times are converted to America/New_York before date assignment. NYC and Buffalo date strings retain source local-date semantics. Report dates earlier than occurrence are marked invalid. Report filtering uses calendar dates strictly before January 1; unknown or invalid reporting times never count as known-available. NYC current-year late-report supplementation prevents treating the historical feed alone as a complete current occurrence-year extract. Eventual reporting and revision remain incomplete and heterogeneous across cities.

Buffalo created_at is an ingestion timestamp, not a validated date first reported to police. Missing timestamps create incomplete baseline availability. background_has_unknown_availability and background_measurement_status prevent interpreting a known-available count of zero as proof of no actual surrounding crime. No modeling is performed here.

## Geodesic linkage and sensitivities

Candidate lookup uses EPSG:32618 for New York City and EPSG:32617 for Buffalo/Rochester, with a 502 m radius. WGS84 geodesics determine all final <=25/50/100 m outcomes and >200/<=500 m backgrounds. For partial rows an event must also fall in the supported interval union. Nearest-site flags rank eligible exposed sites separately for each cohort/year/event; ties use site ID. The full-year and sensitivity cohorts intentionally overlap and are never combined for inference.

Buffalo's rounding scenario perturbs an event by at most the geodesic diagonal of a half-cell (0.0005 degrees in each coordinate). Distance plus that amount <=radius is definitely inside under this hypothetical scenario; distance minus that amount <=radius is possibly inside. The scenario does not bound block-centroid displacement, ATM-location error or systematic geocoding error. It is not a confidence interval, correction, or evidence that 50 m inference is defensible.

The study remains exploratory: earlier releases exposed 2024/2025 outcomes; known-available reporting does not reconstruct a historical source vintage; full-year stability can induce selection; and partial-year prevalence differs in observation duration. Later environmental modeling requires ex-ante feature provenance, a new analysis specification, rolling-origin temporal checks with repeated-site/spatial safeguards, and explicit handling of incomplete baselines. Prior nearby crime measures temporal persistence and must be distinguished from environmental increment.
