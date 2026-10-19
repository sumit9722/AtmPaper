# Housing-context construction

1. Rebuild annual cohorts and labels from the preserved archives.
2. Freeze eight housing-context definitions before fitting, with prior-year crime as the ninth predictor.
3. Retrieve official ACS 2018–2022 estimates, margins of error and annotations for seven New York counties; retain raw responses and SHA-256 request records.
4. Join site points to 2022 block-group polygons using unique covers matches only.
5. Calculate proportions and fixed-vintage building age; retain missing values and use log1p only for rent, age and crime.
6. Independently verify every source component and formula, all baseline values and a stratified sample of brute-force spatial joins.
7. Release the unscaled, unimputed matrices for training-fold preprocessing.

Validation: PASS. This is an exploratory follow-up to already inspected outcomes. Neighborhood estimates do not measure ATM security directly. ACS margins of error are retained but measurement error is not propagated through the predictive models.

| Predictor | Rows | Missing |
|---|---:|---:|
| log1p_background_primary | 2442 | 0 |
| housing_vacancy_share | 2442 | 35 |
| renter_occupied_share | 2442 | 35 |
| multifamily_housing_share | 2442 | 35 |
| crowded_household_share | 2442 | 35 |
| no_vehicle_household_share | 2442 | 35 |
| log1p_median_gross_rent | 2442 | 268 |
| log1p_housing_age | 2442 | 70 |
| recent_move_share | 2442 | 35 |
| log1p_background_unfiltered | 2442 | 0 |

Definitions: ../../protocol/environment_variables.json. Official source: https://api.census.gov/data/2022/acs/acs5/groups.html
