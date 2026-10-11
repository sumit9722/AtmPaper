# Shared 2024–2025 temporal data

This separate result folder extends the original data without changing earlier phase releases.

| year | city | full_year_sites | positive_50m |
| --- | --- | --- | --- |
| 2024 | New York City | 1129 | 662 |
| 2024 | Buffalo | 48 | 16 |
| 2024 | Rochester | 24 | 6 |
| 2025 | New York City | 1117 | 629 |
| 2025 | Buffalo | 46 | 14 |
| 2025 | Rochester | 29 | 7 |


The 2024 cohort has 1,201 sites and 684 positives; the 2025 cohort has 1,192 sites and 650 positives. All confirmatory-eligibility flags are false.

Sources: [NY DFS bank-owned ATM inventory](https://data.ny.gov/Government-Finance/Bank-Owned-ATM-Locations-in-New-York-State/ndex-ad5r), its archived monthly snapshots (December 2023–January 2025), [2022 ACS release information](https://www.census.gov/programs-surveys/acs/news/data-releases/2022/release.html), [official 2022 TIGER/Line block groups](https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_36_bg.zip), and the existing phase 3 EPA SLD2021 sources. Police acquisition endpoints and request provenance are preserved under `data/raw/temporal_extension/crime2023`; 2024/2025 police extracts remain from phase 2.

The ACS 2018–2022 estimates were released December 7, 2023, before both prediction years. Seven county attribute requests and three metadata requests were made, sequentially with pauses and caching; the credential was not saved. All remaining downloads were public and used no Census key.

`data/context_raw.csv` preserves raw feature components and ACS uncertainty/annotation fields; `data/features.csv` applies the frozen 14-feature schema; `data/cohort.csv` stores labels and historical cutoffs. The baseline competition inventories are statewide. Background crime uses the previous year, >200–500 m, and report availability before January 1 of the prediction year. `data/outcome_links_2024.csv` allows direct label reconciliation.

Two pre-fit amendments are essential. The archived ACS2022 map service's identifiers did not match the API; the official 2022 TIGER/Line archive does. The service response is retained but not used for fitting. Exact address-plus-coordinate identities produce zero full-year 2024 sites because of historical coordinate revisions. The amended cohort requires a unique normalized city/address in all 14 snapshots and all locations within 50 m of December 2023 coordinates. Use that baseline coordinate for context and labels. The original exact-identity exposure inventory remains in `qa/`; amended links are in `qa/continuity_links_2024.csv`.

The intervals support inferred 366-day continuity, not verified daily operation. The cohort conditions on later observed survival, which can limit prospective generalization. Compare against the old 2025 cohort with caution: its continuity method is unchanged, while 2024 uses the explicit amendment. No nearest-polygon or outcome-informed identity imputation is used. All raw inputs and protocol changes are checksummed under `qa/`.

These are retrospective research results, not confirmed ATM-attack predictions or operational risk scores. The 2025 outcomes were inspected in the earlier phase 4 analysis, so 2025 is not a pristine confirmatory holdout. Training uses report-date-filtered latest extracts, not a database frozen at the historical cutoff. Buffalo uses record creation as a report-availability proxy. Monthly listings support inferred operation; they do not establish exact opening or closing dates. The 2024 address links and up-to-50-m coordinate revisions require independent review. Crime harmonization/linkage, facility identity, Buffalo coordinate precision, continuity, and feature acceptance remain research gates. No independent human sign-off is claimed. Small Buffalo/Rochester samples and limited positives make their estimates unstable. Current municipal boundaries and retrospective archive availability are additional limitations.

Reproduce using the scripts in [phase 5 reproduction instructions](../phase5/docs/04_reproduce.md).
