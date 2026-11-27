# Restart 9 amendments

## A1 — data access (2026-11-27, before any outcome linkage)

ohsome v1 extraction endpoints (`elements/centroid`, `elements/geometry`) returned
HTTP 403 on the first download attempt; only `count` and `metadata` still respond.
Operational change, no definition changed:

* OSM layers: same ohsome data via the HeiGIT ohsome v2 single-snapshot extraction
  (the endpoint Restart 6 used). Same filters and snapshot dates. Non-point objects use
  the projected centroid of their geometry; highways keep their line geometry.
* A14 `atm_mapped_age_years`: first version matching the ATM filter, taken from the public
  OpenStreetMap API object history (`/api/0.6/{type}/{id}/history`) of each cohort
  object instead of ohsome full history.

## A2 — M9L withdrawn (2026-11-27, data audit, before any outcome linkage)

The NY State Liquor Authority lists cannot reconstruct which licences were active
on 15 December 2023/2024. In the active list, 21,816 of 24,821 NYC licences
(88%) have an "original issue date" in 2025–2026 and only 137 before 2024. This
suggests the records were re-issued under new IDs, so `originalissuedate` is not
the true first issue. As a result, the NYC off-premise count jumps from 2,332
(Dec 2023) to 4,320 (Dec 2024) for no real-world reason.
Counts at the cutoff would be strongly biased toward recent licences, so M9L is not
estimated. Chicago licence features are retained in `features_r9.csv` for reference
only. A1–A4 (OSM) remain the primary bar/liquor measures.
