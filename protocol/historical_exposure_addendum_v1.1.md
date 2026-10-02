# Historical exposure addendum v1.1

2026-10-01, before any model fitting or performance inspection.

The public DFS change history exposes monthly archives. The December 2024 through January 2026 versions (270–283) were successfully prepared through the portal's export API. These 14 snapshots replace the current-cohort backcast as the preferred basis for 2025 exposure. The original backcast remains a separately labeled sensitivity artifact.

For each exact normalized-address plus WGS84 coordinate identity, record membership in every snapshot. Collapse duplicate records at identical address/coordinates within a snapshot. Do not require membership in September 2026: sites that disappeared before the current snapshot remain part of the historical denominator.

A site observed in two consecutive snapshots is assumed continuously active in the interval [earlier snapshot date, later snapshot date). Accept a maximum gap of 62 days, truncate intervals to [2025-01-01, 2026-01-01), and count incidents only within supported intervals. No forward fill beyond the next snapshot, no backward extrapolation from a first appearance and no imputation of missing coordinates. An address or coordinate change creates a new identity; this conservative rule may fragment a continuing physical site and must be reviewed before interpreting closures or openings.

The full-year binary analysis cohort requires 365 supported days. Partial-year rows remain available for exposure-aware secondary analysis; their outcomes are not comparable to full-year binary probabilities without adjustment. Actual opening/closing dates and machine operating days remain unknown. The interval days are supported only under the stated continuity assumption.

This historical reconstruction resolves the absence of archived ATM membership, but does not resolve operational continuity, coordinate precision, source reporting delays, codebook review or co-located facility adjudication. Therefore all rows retain confirmatory_eligible=false until these scientific checks and the blueprint's independent review are completed.

The lagged baseline is 2024 robbery/burglary at >200–500 m around the site, regardless of whether the ATM existed during 2024. Also retain a report-date-cutoff version where the source supports it. Current police extracts may contain later revisions; neither version is a recovered as-of-2025 police database. Buffalo's created_at is retained as a source timestamp proxy and is not certified to be the report date.
