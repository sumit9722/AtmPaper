# Census context for the ATM-site study

`block_group_context.csv` contains the Census ACS component of the environmental feature inputs for the working 2025 outcome panel. GEOIDs are 12-character strings: import them as text.

The 2019–2023 ACS five-year release was published on December 12, 2024, before the January 1, 2025 prediction cutoff. Source: https://www.census.gov/programs-surveys/acs/news/data-releases/2023/release.html . These are five-year estimates, not single-year 2023 observations. The live extract may incorporate later Census revisions.

Selected inputs follow the project plans' population and limited income/unemployment controls:

| Field | Census estimate | Meaning |
|---|---|---|
| population | B01003_001E | Total resident population |
| median_household_income | B19013_001E | Median household income, 2023 inflation-adjusted dollars |
| civilian_labor_force | B23025_003E | Civilian labor force, population age 16 and over |
| unemployed | B23025_005E | Unemployed civilian labor force |
| unemployment_rate | Derived | Unemployed divided by civilian labor force, fraction 0–1 |

Each source estimate includes its Census 90% margin of error and annotation fields. Negative Census sentinel values become empty cells in the processed CSV, with original values preserved in raw JSON. Zero denominators produce missing unemployment rates. Component margins of error are retained; the derived rate has no calculated margin of error. No race, ethnicity, sex, or other protected-demographic breakdowns were selected. The feature selection is an extraction choice; the complete phase-3 feature dictionary still requires the review described in the study protocol.

Coverage is all block groups in Bronx, Kings, New York, Queens, Richmond, Erie and Monroe counties. `study_city_candidate` indicates the intended study city, not verified city membership. Erie and Monroe include substantial areas outside Buffalo and Rochester. Keep complete county extracts for boundary context; assign ATM sites using matching 2023 block-group polygons and the project's city polygons before modeling. This downloader does not create those spatial joins. Population density remains to be derived using matching land area; resident population is not ambient or daytime population. Roads, transit, employment density and EPA Smart Location data are separate source tasks.

Raw API responses and credential-free provenance/checksums are in `data/raw/census/acs2023_5year/`. `variable_dictionary.json` preserves the selected official field definitions. `download_report.json` records validation counts and missing estimates.

To reproduce from the repository root:

```bash
.venv/bin/python scripts/download_census.py
```

Completed files are reused after checksum verification, so a complete rerun uses zero network requests and needs no key. For missing data, the script reads `CENSUS_API_KEY` or prompts without echo; credentials are never written to files or URLs in logs. Requests run sequentially, with two-second pauses, no automatic retries, and a maximum of ten per invocation (three metadata plus seven county extracts). Any HTTP error, including throttling or authentication errors, stops the run. Do not schedule repeated invocations after an error without investigating it.
