# Phase 1 and phase 2 execution report

Prepared 2026-10-01. The computational data work is complete. Scientific acceptance remains conditional on the independent review and precision checks listed below. No crime outcomes or ATM coordinates were invented. No predictive model was fitted.

## Main dataset

Use `data/processed/atm_panel_2025_full_year.csv` for the full-year historical cohort. `atm_panel_2025_historical.csv` additionally contains partial-year exposure. Both use archived ATM membership, not the 2026 list as presumed 2025 history. All outcome counts are police-recorded robbery/burglary near ATM sites, not verified attacks on machines.

| City | Historical sites with intervals | Full-year sites | Partial-year sites | Full-year sites with ≥1 primary incident within 50 m |
|---|---:|---:|---:|---:|
| New York City | 2079 | 1117 | 962 | 629 |
| Buffalo | 96 | 46 | 50 | 14 |
| Rochester | 58 | 29 | 29 | 7 |

These are descriptive linkage counts, not validated risk predictions. Multiple sites can share the same incident. The full-year restriction is fixed by exposure evidence, not chosen from model performance.

## Raw-data acquisition

| City | Downloaded crime records, 2024–2025 | Current DFS site records after exact-site collapse |
|---|---:|---:|
| New York City | 363194 | 1426 |
| Buffalo | 26448 | 69 |
| Rochester | 15635 | 37 |

NYC retrieval includes robbery, burglary, grand larceny and petit larceny with 17 selected native fields; Buffalo and Rochester retain every returned category and field within the date window. These are complete extracts for the stated filters, not complete all-crime NYC history. Every final extract was checked against its API count or object-ID list. An incomplete initial NYC offset download is preserved separately under `initial_offset_attempt` and is not ingested.

Original source responses are in `data/raw/`. Convenient CSV representations preserving source field names are in `data/raw_tables/`. The original user-supplied files remain unchanged. Fourteen historical DFS CSV archives span 2024-12-15 through 2026-01-15. Request sidecars store retrieval times, URLs and hashes; `source_manifest.csv` hashes all raw inputs. Initial metadata and supplied files do not have a known original retrieval time; the manifest says so.

The supplied `sorted_data.csv` has 7,537 NYC rows, all with ATM premises, spanning 1998–2025. It is not suitable for the surrounding-crime baseline and was not mixed into the official complete-window extracts. The supplied OSM exports contain 733, 19 and 13 candidate nodes. They are linked to their nearest DFS site for comparison but never automatically added to the primary bank-owned population.

## Phase 1

The working specification freezes cities, polygon assignment, bank-owned/in-bank population, robbery+burglary primary outcome, annual period, 50 m primary radius, 25/100 m sensitivities, >200–500 m lagged baseline, model ladder, metrics, transfer comparisons and an analyst-selected AUPRC effect threshold. The codebook lists every observed native offense/code mapping. Theft stays exploratory because its mechanism is not consistently known across cities. The protocol is timestamped working documentation, not an externally registered or signed preregistration.

## Phase 2

WGS84 point-in-polygon assignment selects municipalities. UTM coordinates accelerate candidate lookup; final distances use the WGS84 ellipsoid. Exact-address/coordinate duplicate ATM rows collapse to one site. Distinct nearby sites receive a 10 m cluster identifier for facility review. Crime records are de-duplicated by city case identifier, with all dropped rows and rules retained. Primary and broad crime counts remain separate. Backgrounds use only the previous calendar year and exclude the outcome buffer.

Historical site identity is exact normalized address plus coordinate. Presence in adjacent monthly snapshots supports the intervening interval under a continuity assumption, with gaps limited to 62 days. All intervals are clipped to 2025. Missing membership creates an unsupported interval; no blanket forward or backward filling is used. The full-year file requires 365 supported days. Actual opening dates, closing dates and operating days are blank. Site identity changes can fragment a continuing physical site and require review. `historical_snapshot_coverage.csv` tracks these changes, and `historical_identity_review.csv` lists potential continuations sharing an address or exact point. They are not automatically merged. The full-year cohort is therefore conservative and may be selectively composed.

Event links record distance, all three radius flags, match multiplicity and nearest-site assignment. Historical outcomes are counted only during supported intervals. `manual_linkage_audit_historical.csv` contains a deterministic sample stratified by city, distance band, offense eligibility and multiple matches. Its reviewer decisions remain PENDING.

The current-snapshot backcast is retained only as `atm_panel_2025_EXPLORATORY.csv`. `prospective_cohort_PENDING.csv` has blank future outcomes. Neither file should be mistaken for observed prospective results.

## Coordinates

| City | Census reference latitude | Census reference longitude |
|---|---:|---:|
| Rochester | +43.1688606 | -077.6159307 |
| New York City | +40.6624941 | -073.9389041 |
| Buffalo | +42.8922399 | -078.8594380 |

City reference points are provided for orientation only. The panels contain the latitude and longitude of each individual ATM. Crime tables retain each incident point. `reports/atm_locations_map.html` is a self-contained interactive location map.

## Remaining research gates

- Buffalo coordinates are rounded and addresses refer to street blocks. At this latitude, a 0.001-degree grid is roughly 111 m north–south and 81 m east–west; this is comparable to the 50 m radius. Exact-distance arithmetic cannot recover hidden positional precision. Evaluate better geocodes or approve a coarser design before confirmatory cross-city claims.
- Independently adjudicate the primary codebook, stratified event–ATM matches, possible duplicate facilities and historical identity breaks. The generated audit is a work queue, not a completed human review.
- Monthly membership is not proof of uninterrupted machine operation. Review the continuity assumption and address/coordinate changes. Preserve exposure sensitivity analyses.
- Police extracts are current revisions. Report-date filtering reduces late-report leakage but does not reconstruct an as-of-2025 database. Buffalo created_at is a proxy, not a verified report timestamp.
- Municipal boundary clipping can truncate an ATM’s background annulus near the city edge. The current polygons also do not establish historical boundary stability.
- One outcome year does not support forward temporal model evaluation. Additional exposure-supported years or prospective follow-up are required before the blueprint’s modeling stages.
- The working effect threshold, protocol and final category choices still need researcher ratification. `confirmatory_eligible` therefore remains false.

## Reproduction

Install `requirements.txt` in a Python virtual environment. Run `scripts/download_sources.py` and `scripts/download_atm_history.py` to populate/cache raw extracts, then `scripts/build_phase12.py`, `scripts/build_historical_panel.py`, `scripts/make_deliverables.py`, and `scripts/validate_phase12.py` in that order. Download commands need network access; builds use only archived inputs. The included raw metadata/history index fixes the snapshot selection. For a fresh acquisition, preserve a separate dated directory rather than replacing this archived release.

Validation checks are recorded in `reports/validation.json`. The raw-source manifest, generated data dictionary, source register, monthly coverage and exclusion tables are part of the deliverable.
