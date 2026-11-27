# Chicago XGBoost: results and plain-language explanation

## Main finding

Adding environmental variables changed 2025 average precision by -0.0465; the 95% spatial-bootstrap interval is [-0.0873, -0.0035]. The interval supports worse performance in this evaluation.

The target is **any recorded robbery/burglary within 50 metres of an ATM location during the year**. This is not a verified ATM-targeted robbery label. Training uses 443 Chicago site-years from 2024; temporal evaluation uses 482 from 2025. The 25 m and 100 m outcomes are separate sensitivity experiments.

## Model comparison on 2025

| model | average_precision | roc_auc | brier | precision | recall | f1 | accuracy |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crime_only | 0.7047 | 0.7548 | 0.2031 | 0.6150 | 0.6847 | 0.6480 | 0.6867 |
| environment_only | 0.5817 | 0.7064 | 0.2198 | 0.5897 | 0.6798 | 0.6316 | 0.6660 |
| crime_plus_environment | 0.6582 | 0.7481 | 0.2057 | 0.6079 | 0.6798 | 0.6419 | 0.6805 |
| prevalence_baseline | 0.4212 | 0.5000 | 0.2495 | — | 0.0000 | 0.0000 | 0.5788 |

Average precision (AP) measures the quality of ranking crime-positive locations; higher is better. The no-information reference is the positive fraction. ROC AUC measures overall separation. Brier and log loss measure probability errors; lower is better. Precision asks how often a flagged location had nearby crime; recall asks how much nearby crime-positive activity was flagged. Threshold-dependent metrics above use 0.5, not a threshold picked from 2025. Undefined precision is blank when no sites are flagged.

## Strongest environmental associations (2025 descriptive)

| parameter | description | spearman_rho | spearman_ci_low | spearman_ci_high | cluster_bh_q |
| --- | --- | --- | --- | --- | --- |
| sld_D1A | Gross residential density (HU/acre) on unprotected land | 0.2759 | 0.1560 | 0.3887 | 0.0000 |
| sld_D1B | Gross population density (people/acre) on unprotected land | 0.2656 | 0.1477 | 0.3750 | 0.0000 |
| transit_service_density | Aggregate frequency of transit service [D4c] per square mile | 0.2631 | 0.1476 | 0.3767 | 0.0001 |
| sld_Ac_Land | Total land area (acres) | -0.2617 | -0.3602 | -0.1596 | 0.0000 |
| sld_Ac_Unpr | Total land area (acres) that is not protected from development (i.e., not a park, natural area or conservation area) | -0.2588 | -0.3577 | -0.1556 | 0.0000 |
| population_density | population_density | 0.2481 | 0.1291 | 0.3591 | 0.0001 |
| sld_Pct_AO0 | Percent of zero-car households in CBG, 2018 | 0.2445 | 0.1414 | 0.3427 | 0.0001 |
| sld_Ac_Total | Total geometric area (acres) of the CBG | -0.2425 | -0.3392 | -0.1410 | 0.0000 |
| sld_AutoOwn0 | Number of households in CBG that own zero automobiles, 2018 | 0.2221 | 0.1158 | 0.3260 | 0.0015 |
| sld_D5BE | Working age population within 45-minute transit commute, time decay (walk network travel time, GTFS schedules) weighted | 0.1974 | 0.0967 | 0.3008 | 0.0021 |
| sld_D5DE | Proportional Accessibility of Regional Destinations - Transit: Working age population accessibility expressed as a ratio of total MSA accessibility | 0.1974 | 0.0967 | 0.3008 | 0.0021 |
| sld_D5DEI | Regional Centrality Index – Transit: CBG [D5de] score relative to max CBSA [D5de] score | 0.1974 | 0.0967 | 0.3008 | 0.0021 |
| no_vehicle_household_share | no_vehicle_household_share | 0.1945 | 0.0911 | 0.3013 | 0.0032 |
| multifamily_housing_share | multifamily_housing_share | 0.1856 | 0.0824 | 0.2961 | 0.0093 |
| sld_D1D | Gross activity density (employment + HUs) on unprotected land | 0.1839 | 0.0732 | 0.3085 | 0.0115 |

Positive rho means larger values tend to occur at sites with nearby crime; negative rho means the opposite. Absolute rho ranks association strength. This is not the effect after controlling for other features. Intervals use block resampling. The q values adjust exploratory cluster-robust tests for multiple comparisons within this year/outcome; they do not certify causation or generalization.

## Environmental parameters most used by the combined model

| parameter | description | mean_abs_shap | shap_ci_low | shap_ci_high | shap_rank |
| --- | --- | --- | --- | --- | --- |
| transit_centroid_distance | Distance from the population-weighted centroid to nearest transit stop (meters) | 0.1060 | 0.0929 | 0.1191 | 3.0000 |
| transit_service_density | Aggregate frequency of transit service [D4c] per square mile | 0.1011 | 0.0899 | 0.1121 | 4.0000 |
| sld_D1B | Gross population density (people/acre) on unprotected land | 0.0817 | 0.0732 | 0.0903 | 5.0000 |
| sld_P_WrkAge | Percent of population that is working aged 18 to 64 years, 2018 | 0.0686 | 0.0614 | 0.0750 | 6.0000 |
| sld_E5_Ret | Retail jobs within a 5-tier employment classification scheme  | 0.0499 | 0.0462 | 0.0535 | 9.0000 |
| nearest_other_atm | nearest_other_atm | 0.0474 | 0.0437 | 0.0506 | 10.0000 |
| median_household_income | median_household_income | 0.0465 | 0.0425 | 0.0512 | 11.0000 |
| median_gross_rent | median_gross_rent | 0.0436 | 0.0386 | 0.0485 | 12.0000 |
| recent_move_share | recent_move_share | 0.0347 | 0.0334 | 0.0361 | 14.0000 |
| employment_mix | 5-tier employment entropy (denominator set to the static 5 employment types in the CBG) | 0.0317 | 0.0296 | 0.0336 | 15.0000 |
| sld_E_MedWageWk | Number of workers earning more than $1250/month but less than $3333/month (work location), 2017 | 0.0287 | 0.0258 | 0.0317 | 16.0000 |
| sld_TotPop | Population, 2018 | 0.0281 | 0.0239 | 0.0325 | 17.0000 |
| sld_D3BPO4 | Intersection density in terms of pedestrian-oriented intersections having four or more legs per square mile | 0.0267 | 0.0243 | 0.0291 | 18.0000 |
| sld_D5AE | Working age population within 45 minutes auto travel time, time-decay (network travel time) weighted | 0.0260 | 0.0230 | 0.0289 | 19.0000 |
| sld_R_HiWageWk | Count of workers earning $3333/month or more (home location), 2017 | 0.0238 | 0.0205 | 0.0273 | 20.0000 |

SHAP importance answers how much the fitted model used a parameter to move predictions, not whether changing that parameter changes crime. Mean absolute SHAP is in log-odds, not percentage points. A zero for a training-excluded parameter says nothing about its possible association in other cities.

## What was prepared and tested

- 116 environmental candidates plus seven explicitly retrospective past-crime candidates; every candidate has distributions, missingness, association statistics and an importance record.
- Four spatial folds within 2024; 2 km grid grouping, a 1 km train–validation separation and exclusion of shared Census/EPA areas. Eight prespecified configurations per model family and radius. Tuning maximizes mean fold AP.
- Native XGBoost missing-value handling; no zero filling, no global imputation/scaling and no outcome-guided correlation screening.
- Models: crime-only, environment-only, combined; training-prevalence baseline. Eight grid candidates × four folds × three families × three radii = 288 tuning fits, plus final and seed-stability fits.
- 1,000 block-bootstrap replicates by default; intervals for models, paired differences, correlations and SHAP. 1 km/4 km grid-size sensitivity for performance intervals. Permutation-repeat ranges measure shuffle variability, not sampling confidence.
- Training-only F1 threshold is additionally reported; its selected OOF scores are tuning diagnostics. Recurring/new-site, point-only and boundary-clear evaluations are in the detailed metrics.
- Source hashes, prediction reload equality, SHAP additivity, row identities, feature exclusions and split separation are checked. Exact versions and settings accompany saved models.

## Limits

Exploratory retrospective analysis. Chicago has no original report dates: the seven past-crime inputs use occurrence-year records from a later extract. No outcome-year crime, identifiers, future exposure fields or coordinates enter the models; historical reporting availability still cannot be verified. The 2025 data did not participate in tuning, exclusions, early stopping or threshold selection. Both years were already examined in earlier study decisions and are not pristine holdouts. Temporal evaluation permits recurring sites; it does not test unseen cities. OSM is incomplete and may duplicate facilities, and block geocodes limit 25–100 m precision. Correlations are pairwise associations; SHAP explains model predictions in log-odds; neither proves causation. Correlated variables can share or substitute importance. Spatial bootstrap intervals condition on the fitted model and chosen grid; adjacent blocks can remain dependent and source uncertainty is not captured. Missing is not zero. Constant and exact-duplicate candidates remain in the statistical report but are excluded using training data only.

## Files to open

- [Full readable report, searchable parameter-by-parameter](report.html)
- [Every association and outcome](statistics/associations_all_outcomes.csv)
- [Correlation rankings and ranking uncertainty](statistics/correlation_rankings.csv)
- [Every distribution and missingness statistic](statistics/distributions_all_parameters.csv)
- [Predictive importance: SHAP](explanations/crime_plus_environment_shap_ranking.csv)
- [Held-out permutation importance](explanations/crime_plus_environment_permutation_ranking.csv)
- [Model metrics](statistics/model_metrics.csv), [intervals](statistics/model_metric_intervals.csv), [paired differences](statistics/paired_model_differences.csv)
- [Seed stability](explanations/seed_stability.csv), [validation](validation.json), [run configuration](run_config.json)
- [Reproduction and GCP instructions](../../analysis/chicago_xgboost/README.md)

Technical methods: [XGBoost API](https://xgboost.readthedocs.io/en/stable/python/python_api.html), [TreeSHAP contributions](https://xgboost.readthedocs.io/en/stable/prediction.html), [grouped CV](https://scikit-learn.org/stable/modules/cross_validation.html), [permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html).
