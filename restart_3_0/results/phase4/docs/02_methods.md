# Methods and interpretation

## Population and temporal design

The cohort is the restart's address-continuity-supported DFS bank-owned/in-bank population, built independently for 2024 and 2025. The outcome measures police-recorded robbery/burglary near ATM coordinates, not verified attacks on machines. Training is exclusively 2024; testing exclusively 2025. Report-filtered 2024 labels reduce late-report leakage but cannot reconstruct a database frozen in January 2025. Exposure itself is retrospective and conditions on later snapshot membership. Both outcome years were examined in previous project analyses.

Primary forward-spatial evaluation tests future-year locations outside the training neighborhoods. It is more restrictive than predicting the next year at familiar sites. Secondary forward leave-city-out measures transport from earlier-year other-city data. It is not the phase 5 adaptation experiment. City cohorts are highly unequal: NYC dominates pooled metrics, while leave-NYC-out training has only 72 sites. Excluding Buffalo leaves only 24 Rochester training sites for the NYC city-held-out sensitivity. City-specific results and sample sizes must accompany pooled claims.

Five group assignments are made from 2 km UTM block centers using weighted KMeans, without labels. Train/test and inner train/validation pairs are separated by at least 1,500 m WGS84; two 500 m contexts therefore have at least a 500 m gap. A block cannot be split across outer groups within its annual cohort. Years are grouped independently, but the cross-year distance purge protects against neighborhood overlap despite changed coordinates. The grid origin and seed are fixed; groups are not regenerated to improve performance.

## Models, preprocessing and calibration

M0 is logistic regression on log1p report-filtered prior-year robbery/burglary in >200–500 m. M1 adds the 8 frozen housing-context predictors and uses L2 regularization, C in [0.1, 1, 10]. Both use lbfgs, max_iter=3000, tol=1e-8. M0 uses C=infinity, equivalent to no regularization in the installed implementation. M2 uses CPU XGBoost: 150 trees, learning_rate=0.05, min_child_weight=5, subsample=colsample_bytree=1, histogram trees, seed 20261001, one thread; candidate (max_depth, reg_lambda) pairs are (2,10), (2,1), (3,10), (3,1). No class weights or oversampling are used.

Each fitting subset independently learns median imputation, retaining all-empty columns with zero fallback. Logistic fits then independently learn scaling; boosting is not scaled. No preprocessing is learned from outer tests or outer-purged rows. Candidate selection uses mean inner-fold average precision; test labels are untouched by tuning. Fewer than two valid inner splits invokes the first fixed candidate. All skipped inner splits, library warnings, selected parameters and fitted preprocessing are recorded.

The optional sigmoid uses only the chosen candidate's inner out-of-fold probabilities and labels, with slope >=0 and a 1e-6 slope penalty. This is training-internal calibration, not a second independent tuning set; its assessment is the outer test. Failed or unsupported calibration retains native probabilities. Both variants are reported, but all primary ranking comparisons and bootstrap gates use native probabilities.

The predictor definitions follow phase 3: eight housing-context measures from ACS 2018–2022 and prior-year crime. Missing housing values are imputed within training, never assigned from a nearest polygon. Housing measures are neighborhood proxies. IDs and coordinates are excluded from predictors. Model artifacts are fold models, not a deployment model. Count regression is not used: daily machine operation is unverified and the registered primary estimand is binary annual nearby crime.

## Metrics and uncertainty

AUPRC means non-interpolated average precision. ROC-AUC is undefined in a single-class test; AP is undefined with zero positives. The top decile contains exactly ceil(0.1*n) rows, with row-ID tie-breaking. Brier, ten equal-width-bin expected calibration error and mean predicted probability minus prevalence describe probability quality. Calibration-bin Wilson intervals are descriptive binomial intervals and ignore spatial dependence; they are not the spatial bootstrap uncertainty interval.

For each primary scheme and city/pooled cohort, draw occupied 2 km blocks with replacement within cities, retaining all their rows. Use identical row weights for all models for 2,000 replicates, seed 20261001. Report percentile 95% intervals for paired AP differences. These intervals condition on the fitted prediction vectors; they do not include model-refit, tuning or cohort-selection uncertainty. City-stratified pooling is still dominated by NYC site counts and is not a city-balanced average.

The working numerical flag requires AP gain >=0.01 and lower paired 95% bound >0. It is exploratory and does not correct for all examined comparisons. Sensitivity results, nonlinear-only benefits or city heterogeneity must be reported as such. A wide interval is inconclusive, not evidence of no effect. Useful ranking does not imply calibrated absolute risk, a causal environmental effect or justified deployment.

## Continuing limitations

Independent offense, event linkage, facility/continuity, Buffalo coordinate-precision and feature-schema approval remain pending. Address identity and baseline coordinates can change across years; positional changes can change neighborhood context. Municipal clipping truncates some annuli. Archived sources are later revisions, not historical as-of databases. Small target cohorts and very small source cohorts limit transport estimates. No independent sign-off, untouched holdout or operational risk validity is claimed.
