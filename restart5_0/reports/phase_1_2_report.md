# Restart 5.0 — phases 1 and 2

The user replaced the original ten-year request with the longest recovered continuous ATM snapshot period. **Both computational phases are complete and validated for that revised scope.** Independent scientific acceptance remains pending. No predictive models were fitted.

## Period and denominator

Thirty-six monthly DFS snapshots cover **22 February 2023–15 January 2026**. This supports **2024 and 2025 as complete calendar years**, plus a separately labeled **313-day 2023 cohort** (22 February–31 December). The source investigation does not establish that older records cannot exist elsewhere; it establishes the longest continuous series recovered from the assessed public sources. The current public archive resolves requested versions 1, 200 and 247 to version 248, dated February 2023 in the saved index. Two indexed Wayback captures (April 2021 and November 2022) are isolated and do not establish monthly continuity. Future incomplete 2026 outcomes cannot add a third complete year as of this release.

The primary annual location follows a unique normalized city/address across all required monthly snapshots, with displacement no greater than 50 m from the initial coordinate. Each year is selected separately. This retains **2,442 full-year site-years** and **1,271 partial-2023 site-periods**. The combined continuity file has **3,713 rows**. A separate exact-coordinate sensitivity has **10,003 supported identity-years** and may split a physical facility after a coordinate revision. Never stack these alternative cohorts or interpret their combined row count as independent ATMs.

| city | outcome_year | site_years | supported_site_days | positive_50m | prevalence_50m |
| --- | --- | --- | --- | --- | --- |
| New York City | 2024 | 1129 | 413214 | 662 | 0.5863596102745793 |
| Buffalo | 2024 | 48 | 17568 | 16 | 0.3333333333333333 |
| Rochester | 2024 | 24 | 8784 | 6 | 0.25 |
| New York City | 2025 | 1160 | 423400 | 655 | 0.5646551724137931 |
| Buffalo | 2025 | 50 | 18250 | 14 | 0.28 |
| Rochester | 2025 | 31 | 11315 | 8 | 0.25806451612903225 |
| New York City | 2023 | 1192 | 373096 | 696 | 0.5838926174496645 |
| Buffalo | 2023 | 57 | 17841 | 17 | 0.2982456140350877 |
| Rochester | 2023 | 22 | 6886 | 5 | 0.22727272727272727 |


The 2023 binary prevalence is based on 313 days and is not directly comparable to annual prevalence. Full-year restriction and address/coordinate stability can select a nonrepresentative subset. Actual operation and opening/closing dates remain unknown.

## Phase 1 — construct and study design

The [working specification](../protocol/study_spec.md) freezes three municipalities, bank-owned/in-bank DFS locations, robbery/burglary, a 50 m endpoint with 25/100 m sensitivities, and a previous-year >200–500 m baseline. It distinguishes nearby incidents from attacks on machines, report availability from latest occurrence records, and computational completion from independent approval. The [scope amendment](../protocol/scope_amendment.md) preserves the user's change of direction. Source-completeness and partial-2023 amendments document subsequent data-quality work. The original protocol and hash are retained as superseded records.

The observed native [crime codebook](../data/processed/crime_codebook.csv), [data dictionary](../data/processed/data_dictionary.csv), [source register](../data/processed/source_register.csv), [lessons from previous attempts](lessons_from_previous_attempts.md), [later-phase analytical commitments](../protocol/future_analysis_plan.md), and explicit review gates complete the computational construct deliverables. The plan specifies M0/M1/M2, metrics, temporal/spatial evaluation, matched transfer controls and uncertainty; none is fitted here. This is a retrospective working protocol, not a signed preregistration.

## Phase 2 — sources, exposure and linkage

The active 2022–2025 extracts contain **209,413 source rows**, reconciled against API counts or exact ArcGIS object IDs. After exclusions and global city-case deduplication, **205,429 unique valid cases** remain, including **133,620 robbery/burglary cases**. There are **3,937 excluded source rows** and **47 duplicate case rows**, all retained with reasons. NYC extracts contain primary categories only; Buffalo and Rochester preserve their broader published categories for audit, not a comparable all-crime endpoint. 2022 supplies background only. Earlier raw crime acquired under the abandoned ten-year design is preserved but not analyzed.

The NYC current-year feed adds 146 earlier-occurrence records, including 134 dated 2025. These are included in occurrence-based outcomes and excluded by the applicable reporting cutoff from historical predictors/labels. Current feed coverage is quarterly and source updates differ across cities; no claim of eventual final counts or a historical as-of database is made.

ATM coordinates are assigned to archived Census municipal polygons. Exact duplicate locations collapse, distinct neighboring addresses remain separate and receive facility review pairs/components. Events are deduplicated by city case with robbery > burglary > other, later occurrence, and deterministic source order. All dropped rows and conflicts remain auditable.

The release saves **963,025 event-site links across the alternative cohorts**. Candidate search is conservative UTM; every final distance uses the WGS84 ellipsoid. Outcomes in partial cohorts require supported exposure on the event date. A case can link to multiple sites; multiplicity and nearest-eligible-site sensitivities are explicit. Previous-year backgrounds exclude <=200 m and require a usable reporting date before the outcome year. Missing/invalid and late reporting are separate columns. Buffalo created_at remains an ingestion proxy. The [site-month table](../data/processed/atm_site_month_panel.csv) materializes supported monthly days and outcome counts and reconciles back to each annual row; unsupported months are absent, not zero-filled.

## Validation and limits

Independent validation passed 24 check groups: raw hashes, source-row conservation, monthly grids, raw-snapshot cohort reconstruction, every supported exposure day, every link distance, report cutoffs, count reconciliation, multiplicity/nearest assignment, and sampled direct geodesic searches that bypass the spatial index. See [validation.json](validation.json).

The [quality and sensitivity report](quality_and_sensitivity.md) quantifies the most material limitations: coordinate revisions leave no strict exact-coordinate full-year 2024 sites; Buffalo earlier reporting timestamps are extensively missing; its incident coordinates sit on a 0.001-degree grid; and boundary clipping can truncate nearby context. Review decisions remain PENDING, and confirmatory_eligible is false. A successful computational check cannot resolve these source limitations or provide independent scientific approval.

[Reproduce](reproduce.md) · [Methods](methods.md) · [Map](atm_locations_map.html) · [Exposure figure](figures/exposure_coverage.png) · [Radius sensitivity](figures/radius_sensitivity.png)
