# Chicago XGBoost exploratory analysis

Written before model fitting for the user's request to model Chicago and produce detailed parameter statistics. This new analysis supersedes the earlier no-model scope for this extension only. Existing Phase 1–3 releases remain unchanged. Independent scientific review remains pending; this is not a preregistration or confirmatory study.

## Population, outcome and estimand

- Use only the main full-year Chicago OSM cohort: 2024 training/development, 2025 temporal evaluation. Exclude the partial 2023 cohort and alternative overlapping cohorts.
- Primary target: at least one robbery/burglary within 50 m during the outcome year. Independently specified sensitivity targets: the corresponding 25 m and 100 m indicators. Also describe correlations with incident counts and with separate 50 m robbery and burglary counts; these are not additional fitted model targets.
- The estimand is proximity to released public crime coordinates, not confirmed ATM-targeted robbery. Chicago coordinates are block geocodes and do not establish small-radius accuracy. OSM mapping continuity does not prove ATM operation; duplicate physical facilities and survival selection remain unresolved.

## Chicago report dates and temporal limits

The seven original report-filtered crime predictors are entirely unavailable in Chicago. Do not impute them or call them zero. To satisfy the requested past-crime comparison, use seven explicitly named retrospective unfiltered prior-calendar-year measures (200–500 m background; 25/50/100 m nearby crime; robbery and burglary at 50 m; July–December crime at 50 m). This is a retrospective benchmark, not proof of deployable historical forecasting. Late reporting/revisions cannot be eliminated without historical database vintages. No outcome-year crime enters predictor matrices.

## Candidate features and missingness

Use the 116 exploratory environmental fields from the expanded release, excluding its quality flag and all identifiers, coordinates, year, exposure, cohort/survival fields and outcomes. Keep all 123 candidates in descriptive statistics. Report the seven unavailable report-filtered fields separately. Training-only removal of all-missing, single-valued and exact-duplicate columns; preserve a reason for each excluded feature. Regional constants are unlearnable in a one-city model. XGBoost handles numeric NaNs natively; no imputation or scaling. No correlation-based or outcome-based screening before fitting.

## Model selection and evaluation

- Model families: retrospective past-crime-only; environment-only; retrospective past-crime-plus-environment. Include a training-prevalence constant-probability baseline.
- XGBoost binary logistic, histogram trees on CPU; prespecified small grid of tree depth, regularization and tree counts. Four spatially grouped folds within 2024, with fixed 2 km UTM grid groups and a 1 km purge around validation sites. Also purge shared ACS/EPA areas. Learn feature exclusions separately in each fold. Maximize mean fold average precision; deterministic tie-break by grid order. No 2025 early stopping, tuning, filtering, threshold selection or refitting.
- Threshold 0.5 is primary. A secondary threshold maximizing F1 on selected-configuration 2024 out-of-fold predictions is frozen before evaluation; those OOF scores are selection diagnostics, not unbiased validation performance. The 2025 temporal test is the primary model evaluation.
- Report AP, ROC AUC, Brier score, log loss, accuracy, balanced accuracy, precision, recall, specificity, NPV, F1, MCC, confusion counts, top-10% precision/recall/lift, prevalence, calibration bins and curves. AP is average precision, not trapezoidal PR area.
- Primary random seed 17; seeds 41 and 73 measure fitting variability for the primary target using the same selected hyperparameters. The seed is never selected on test performance.
- Temporal evaluation may include the same sites in both years, intentionally testing next-year risk at recurring locations. Report recurring/new-site performance and counts. Also report point-only and boundary-clear subsets without retuning. Spatial CV is a different, harder task with less training data; it is not directly interchangeable with temporal performance.

## Uncertainty and parameter statistics

- Use 1,000 spatial-cluster bootstrap replicates for 2025 metrics and paired model differences. Resample 2 km blocks; report 95% percentile intervals, valid replicate counts and sensitivity to 1 km/4 km blocks. These intervals condition on the fitted model and observed cohort; no claim they cover all model, source or sampling uncertainty.
- Every candidate gets separate 2024 and 2025 missingness, distribution, quantile, zero-count, class-conditional and source/unit summaries. Spearman associations with binary and count outcomes, Pearson/point-biserial and Kendall associations, and parameter–parameter Spearman correlations. Do not pool repeated sites across years for inference.
- Spearman confidence intervals use spatial-cluster bootstrap with within-replicate reranking. Approximate cluster-robust score-test p-values for ranks are reported alongside naive IID p-values; both are exploratory. Benjamini–Hochberg adjustments are applied separately within each year/outcome family across candidates. Bootstrap intervals, especially at sparse outcomes, are not causal or confirmatory evidence.
- Correlation rankings use absolute Spearman rho, preserve sign and uncertainty, and label constants/unavailable fields unrankable. 2025 associations are post-fit descriptive findings, never used for model selection.
- Compute exact native XGBoost TreeSHAP contributions in log-odds, check their sum against prediction margins, and report mean absolute importance, signed means, quantiles, spatial-bootstrap intervals/rank ranges and seed variability for every candidate. Excluded candidates get zero model contribution with an explicit exclusion reason, not a claim of no real association. Report held-out AP permutation importance separately (permutation repeat variability is not a sampling CI). Correlated features can split or substitute importance.

## Deliverables and reproducibility

New scripts, pinned requirements, synthetic tests, prepared Chicago data, source hashes, split memberships, tuning records, saved JSON models, prediction records, full parameter statistics/rankings, SHAP values, figures, readable HTML/Markdown reports, validation report and output manifest. Frozen source hashes are checked before and after execution. Include strict-schema prediction and drift auditing for later NYC/LA evaluation; do not use their outcomes now. Include local and CPU GCP commands, without provisioning or incurring cloud costs.

Technical references: [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html), [prediction contributions](https://xgboost.readthedocs.io/en/stable/prediction.html), [grouped CV](https://scikit-learn.org/stable/modules/cross_validation.html), [permutation importance](https://scikit-learn.org/stable/modules/permutation_importance.html).
