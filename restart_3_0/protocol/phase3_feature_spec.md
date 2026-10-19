# Fixed housing context experiment — restart 3.0

Frozen before new fitting on 19 October 2026. This is an exploratory follow-up after the earlier experiment, not an independent confirmatory replication. Retain all results, including failures; no predictor search using 2025 outcomes.

Use ACS 2018–2022 five-year estimates and 2022 block-group polygons for both prediction years. The machine-readable formulas in environment_variables.json are authoritative. Eight housing/context predictors replace the previous thirteen environmental variables; prior-year report-filtered crime remains the baseline. Vacancy and tenure describe occupancy; multifamily share is units in buildings with at least two units; crowding means more than one occupant per room; vehicle availability describes household transport; rent describes housing costs; age is 2022 minus median construction year; recent moves means 2021 or later in the 2022 release. These are neighborhood proxies, not direct ATM security measurements or causal exposures.

Preserve estimates, margins of error and annotations. Negative Census sentinels become missing. Ratios require all components and a positive denominator. Do not derive ratio margins of error. Use log1p for rent, age and crime; identity for proportions. No global imputation or scaling. Fit preprocessing on each training fold only. Unique polygon covers joins only; ambiguous joins remain missing. Retain all source hashes and missingness.

Train on 2024, evaluate 2025 using the previously specified spatial purge, models, grids, seeds, paired bootstrap and transfer samples. Primary success requires AP gain >=0.01 and a paired block-bootstrap 95% interval lower bound above zero. Report both environmental models and all sensitivities without selecting a favourable one as confirmatory evidence.

Source: https://api.census.gov/data/2022/acs/acs5/groups.html
