# Restart 7 Phase 3

Use [the schema](data/feature_schema.json) and
[primary core matrix](data/features_primary_core_2024_2025.csv).
The baseline contains two fixed crime-history predictors; the extension adds
19 inherited ACS/SLD predictors. [Core baseline](data/features_baseline_core_2024_2025.csv)
and separate 2024/2025 files are available.

[Outcomes](data/outcomes.csv) and [metadata](data/site_lookup_and_quality.csv)
join by `row_id`. The primary endpoint is `recorded_any_50m`, defined using
released coordinates. It is not verified ATM-targeted crime or exact physical
proximity. Repeated-site and spatial grouping keys belong to evaluation metadata.

[Report-filtered sensitivity](data/features_report_filtered_core_2024_2025.csv)
uses only NYC/LA; Chicago's original report dates remain unavailable.
[Source-conflict sensitivity](data/features_no_source_conflicts_core_2024_2025.csv)
must be paired with `no_source_conflicts_any_50m` in the outcomes table.
[Other sensitivity predictors](data/features_sensitivity_core_2024_2025.csv)
include alternative crime radii, mapped-object competition and transit measures.

[Expanded environment](data/features_expanded_environment_core_2024_2025.csv)
contains 107 untransformed exploratory fields. It does not include crime
predictors; join explicitly to the baseline if later authorized. Do not mix raw
and transformed versions of the same variable without an explicit specification.
Full-cohort and partial-2023 versions are separate exports.

[Missingness](../../qa/feature_missingness.csv),
[column decisions](../../qa/environment_column_decisions.csv),
[sample replication](../../qa/repeated_units.csv),
[methods](../../reports/methods.md), and [reproduction](../../reports/reproduce.md).
No imputation, scaling or models were fitted. Scientific review remains pending.
