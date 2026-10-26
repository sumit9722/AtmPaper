# Expanded environmental dataset

The existing NYC, Chicago and Los Angeles cohort now has **117 environmental columns: 116 exploratory measures and one EPA density-quality flag**. This adds **94 columns** to the earlier 23 environmental measures (21 primary and two sensitivity measures).

The expansion includes all 104 numeric core EPA Smart Location Database / National Walkability fields, plus the existing 11 ACS housing and socioeconomic measures and two historical ATM competition measures. It covers development density, land-use mix, road and pedestrian networks, intersections, transit coverage and service, job and workforce access, walkability, employment, demographics and land area. “All” refers to this defined source inventory; it does not include new weather, pollution, vegetation, lighting or site-security observations.

## Files

- [Main dataset: 2,731 site-years, 2024–2025](environment_full_year_2024_2025.csv), including site identifiers, coordinates, year and source geography keys.
- [2024](environment_2024.csv) and [2025](environment_2025.csv) exports.
- [Partial-2023 supplement: 1,287 rows](environment_partial_2023.csv).
- [Predictor-only main matrix](predictors_full_year_2024_2025.csv), containing `row_id` and 116 exploratory variables; the density-quality flag and site metadata are excluded. Separate year and partial-2023 matrices are also provided.
- [Field dictionary with definitions, units and sources](environment_dictionary.csv) and [machine-readable schema](schema.json).
- [Coverage by city, year and variable](coverage_by_city_year.csv) and [cell-level missingness reasons](missingness_reasons.csv).
- [All retrieved EPA attributes for 987 block groups](epa_all_source_attributes_by_block_group.csv) and [source field catalog](epa_source_field_catalog.csv). The raw export also preserves EPA calculator inputs and coefficients; those are not additional environmental predictors.
- [Validation](validation.json), [input checksums](input_manifest.csv) and [output checksums](output_manifest.csv).

## Interpretation

Values use original units. The earlier Phase 3 modeling matrices applied log1p to selected variables; this export provides the untransformed values. Existing EPA variables retain their descriptive names; newly added EPA columns use `sld_` followed by the official field code. The source dictionary retains EPA's own aliases, including its apparent retail-label typo for `D1C8_PUB`; that field represents public-administration employment density.

EPA 2021 measures describe block-group context using mixed earlier measurement years. They are fixed across outcome years and are not annually updated observations. EPA's fields labeled “percent” use fractional values in this release; the dictionary identifies those scales. Regional quantities describe the CBSA. The EPA `GEOID20` join key uses the frozen EPA geography, separate from ACS 2022 geography.

The original validated spatial joins are reused, including the conservative invalid-geometry exclusion. Additional attributes were fetched only for the 987 already matched EPA block groups. Every previously used EPA value was checked against the new download. No new geometries or joins were introduced.

Missing values stay blank. Raw nulls and negative source codes remain available in the source export and missingness audit. Partial 2023 still has no eligible ACS 2022 or December-2022 ATM competition data. Some EPA transit quantities are unavailable even when a block group has a valid join. No rows were dropped and no values were imputed.

Outcome labels remain in [the Phase 3 outcomes table](../phase3/data/outcomes.csv), joinable by `row_id`. Crime predictors remain in the original Phase 3 matrices. This environmental expansion does not fit models or select features using outcomes. Highly related measures, alternative employment classifications and fixed regional totals require care in later modeling; preprocessing and selection must be learned within training folds. Independent scientific review remains pending.

## Reproduce

From the repository root, using the existing environment:

```bash
.venv/bin/python restart6_0/scripts/expand_environment.py
```

This rebuilds offline using checksummed downloads under `restart6_0/environment_expansion/raw/`, verifies the original Phase 3 release, and checks every exported environmental value against its source. On first acquisition only, append `--acquire`. Downloads are resumable and require no API key. The field inventory is recorded in [the expansion specification](../../protocol/environment_expansion.json).

Validation checks row identities, the predictor allowlist, partial-2023 temporal exclusions, all 470,106 exported environmental values, all 40,180 overlapping EPA values and the original Phase 3 checksums. Existing phase 1–3 artifacts remain frozen.

Sources: [EPA Smart Location Database](https://www.epa.gov/smartgrowth/smart-location-mapping), [EPA technical guide](https://www.epa.gov/system/files/documents/2023-10/epa_sld_3.0_technicaldocumentationuserguide_may2021_0.pdf), and the [original Phase 3 methods](../phase3/docs/02_methods.md). Historical ATM data © OpenStreetMap contributors, ODbL, via HeiGIT ohsome.
