# Phase 5 results

**Computational validation: PASS.** Completed 7,380 model evaluations using 7,155 unique saved models, 610,572 predictions and 1,476 complete target-year evaluation vectors. All training is from 2024 and all testing from 2025. There are 267 constant single-class fits, 0 unsupported evaluations and 0 captured estimator-warning rows.

Transfer effects are mixed across cities, model families, source cities and adaptation fractions. Adding source data sometimes helps and sometimes harms the exactly matched local-only model; there is no demonstrated universal transfer benefit.

## Direction of mean matched benefits

| city | positive_mean_conditions | negative_mean_conditions | conditions |
|---|---|---|---|
| New York City | 11 | 7 | 18 |
| Buffalo | 5 | 13 | 18 |
| Rochester | 14 | 4 | 18 |


These counts describe the 18 source/fraction/model combinations per city. They are not independent significance tests, and a positive mean does not imply that every seed benefits.

## Pooled-source matched benefits

| city | fraction | model | mean_benefit | sd | seed_p025 | seed_p975 | negative_seeds |
|---|---|---|---|---|---|---|---|
| New York City | 0.1 | M0 | 0.0086 | 0.0056 | -0.0006 | 0.0160 | 1 |
| New York City | 0.1 | M1 | -0.0168 | 0.0216 | -0.0488 | 0.0221 | 16 |
| New York City | 0.1 | M2 | -0.0124 | 0.0151 | -0.0398 | 0.0112 | 17 |
| New York City | 0.25 | M0 | 0.0055 | 0.0020 | 0.0028 | 0.0096 | 0 |
| New York City | 0.25 | M1 | 0.0044 | 0.0160 | -0.0305 | 0.0229 | 8 |
| New York City | 0.25 | M2 | -0.0025 | 0.0132 | -0.0211 | 0.0277 | 14 |
| Buffalo | 0.1 | M0 | -0.0127 | 0.0420 | -0.0856 | 0.0441 | 11 |
| Buffalo | 0.1 | M1 | -0.0422 | 0.0465 | -0.1082 | 0.0427 | 17 |
| Buffalo | 0.1 | M2 | 0.0184 | 0.0395 | -0.0370 | 0.0894 | 8 |
| Buffalo | 0.25 | M0 | -0.0063 | 0.0386 | -0.0599 | 0.0481 | 11 |
| Buffalo | 0.25 | M1 | 0.0010 | 0.0605 | -0.0938 | 0.0859 | 9 |
| Buffalo | 0.25 | M2 | 0.0176 | 0.0247 | -0.0213 | 0.0567 | 5 |
| Rochester | 0.1 | M0 | -0.0410 | 0.0447 | -0.1437 | -0.0006 | 19 |
| Rochester | 0.1 | M1 | 0.0694 | 0.0632 | -0.0527 | 0.1397 | 4 |
| Rochester | 0.1 | M2 | 0.0422 | 0.0251 | -0.0127 | 0.0720 | 1 |
| Rochester | 0.25 | M0 | -0.0727 | 0.0637 | -0.2102 | 0.0079 | 19 |
| Rochester | 0.25 | M1 | 0.0698 | 0.0629 | -0.0608 | 0.1412 | 3 |
| Rochester | 0.25 | M2 | 0.0470 | 0.0353 | -0.0279 | 0.0863 | 3 |


The paired target-only control always uses exactly the same earlier target rows. `seed_p025` and `seed_p975` are empirical percentiles across the same 20 sampling seeds, **not confidence intervals**. The full individual-source and pooled-source table follows below.

## Local-full and zero-shot performance

| city | condition | source | model | n | positives | average_precision | brier_score | ece_10bins | top_decile_recall |
|---|---|---|---|---|---|---|---|---|---|
| New York City | local_full | target | M0 | 1160 | 652 | 0.7251 | 0.2101 | 0.0385 | 0.1334 |
| New York City | local_full | target | M1 | 1160 | 652 | 0.7158 | 0.2151 | 0.0636 | 0.1242 |
| New York City | local_full | target | M2 | 1160 | 652 | 0.7277 | 0.2200 | 0.0498 | 0.1442 |
| New York City | source_only | Buffalo | M0 | 1160 | 652 | 0.4257 | 0.4423 | 0.4336 | 0.0337 |
| New York City | source_only | Buffalo | M1 | 1160 | 652 | 0.5618 | 0.4078 | 0.3715 | 0.0936 |
| New York City | source_only | Buffalo | M2 | 1160 | 652 | 0.5456 | 0.3012 | 0.2526 | 0.0491 |
| New York City | source_only | Rochester | M0 | 1160 | 652 | 0.4257 | 0.4791 | 0.4710 | 0.0337 |
| New York City | source_only | Rochester | M1 | 1160 | 652 | 0.4883 | 0.5273 | 0.5144 | 0.0644 |
| New York City | source_only | Rochester | M2 | 1160 | 652 | 0.5621 | 0.3435 | 0.3121 | 0.0966 |
| New York City | source_only | pooled | M0 | 1160 | 652 | 0.4257 | 0.4557 | 0.4472 | 0.0337 |
| New York City | source_only | pooled | M1 | 1160 | 652 | 0.5650 | 0.4298 | 0.3988 | 0.1043 |
| New York City | source_only | pooled | M2 | 1160 | 652 | 0.5001 | 0.3541 | 0.3313 | 0.0567 |
| Buffalo | local_full | target | M0 | 50 | 14 | 0.3038 | 0.2034 | 0.0261 | 0.0714 |
| Buffalo | local_full | target | M1 | 50 | 14 | 0.2809 | 0.2569 | 0.1738 | 0.0714 |
| Buffalo | local_full | target | M2 | 50 | 14 | 0.2870 | 0.2031 | 0.0399 | 0.0714 |
| Buffalo | source_only | New York City | M0 | 50 | 14 | 0.2938 | 0.2219 | 0.1839 | 0.0714 |
| Buffalo | source_only | New York City | M1 | 50 | 14 | 0.3033 | 0.2699 | 0.2704 | 0.0000 |
| Buffalo | source_only | New York City | M2 | 50 | 14 | 0.3277 | 0.2458 | 0.2052 | 0.0714 |
| Buffalo | source_only | Rochester | M0 | 50 | 14 | 0.2710 | 0.2267 | 0.1929 | 0.0000 |
| Buffalo | source_only | Rochester | M1 | 50 | 14 | 0.3235 | 0.3136 | 0.2924 | 0.0714 |
| Buffalo | source_only | Rochester | M2 | 50 | 14 | 0.2800 | 0.2025 | 0.0300 | 0.2857 |
| Buffalo | source_only | pooled | M0 | 50 | 14 | 0.2938 | 0.2213 | 0.1825 | 0.0714 |
| Buffalo | source_only | pooled | M1 | 50 | 14 | 0.3036 | 0.2429 | 0.2040 | 0.0000 |
| Buffalo | source_only | pooled | M2 | 50 | 14 | 0.3355 | 0.2429 | 0.1760 | 0.0714 |
| Rochester | local_full | target | M0 | 31 | 8 | 0.3336 | 0.2289 | 0.2842 | 0.2500 |
| Rochester | local_full | target | M1 | 31 | 8 | 0.2830 | 0.3939 | 0.5082 | 0.1250 |
| Rochester | local_full | target | M2 | 31 | 8 | 0.2139 | 0.2175 | 0.1954 | 0.0000 |
| Rochester | source_only | New York City | M0 | 31 | 8 | 0.2210 | 0.2439 | 0.2255 | 0.0000 |
| Rochester | source_only | New York City | M1 | 31 | 8 | 0.3380 | 0.2830 | 0.3459 | 0.1250 |
| Rochester | source_only | New York City | M2 | 31 | 8 | 0.2758 | 0.2640 | 0.2464 | 0.0000 |
| Rochester | source_only | Buffalo | M0 | 31 | 8 | 0.4700 | 0.1770 | 0.1166 | 0.2500 |
| Rochester | source_only | Buffalo | M1 | 31 | 8 | 0.4041 | 0.1863 | 0.1664 | 0.1250 |
| Rochester | source_only | Buffalo | M2 | 31 | 8 | 0.3890 | 0.2043 | 0.0942 | 0.3750 |
| Rochester | source_only | pooled | M0 | 31 | 8 | 0.2210 | 0.2455 | 0.2394 | 0.0000 |
| Rochester | source_only | pooled | M1 | 31 | 8 | 0.3414 | 0.2748 | 0.3025 | 0.1250 |
| Rochester | source_only | pooled | M2 | 31 | 8 | 0.2883 | 0.2613 | 0.2557 | 0.0000 |


| city | source | model | local_ap | source_ap | transfer_gap |
|---|---|---|---|---|---|
| New York City | Buffalo | M0 | 0.7251 | 0.4257 | 0.2994 |
| New York City | Buffalo | M1 | 0.7158 | 0.5618 | 0.1539 |
| New York City | Buffalo | M2 | 0.7277 | 0.5456 | 0.1820 |
| New York City | Rochester | M0 | 0.7251 | 0.4257 | 0.2994 |
| New York City | Rochester | M1 | 0.7158 | 0.4883 | 0.2275 |
| New York City | Rochester | M2 | 0.7277 | 0.5621 | 0.1656 |
| New York City | pooled | M0 | 0.7251 | 0.4257 | 0.2994 |
| New York City | pooled | M1 | 0.7158 | 0.5650 | 0.1508 |
| New York City | pooled | M2 | 0.7277 | 0.5001 | 0.2276 |
| Buffalo | New York City | M0 | 0.3038 | 0.2938 | 0.0100 |
| Buffalo | New York City | M1 | 0.2809 | 0.3033 | -0.0224 |
| Buffalo | New York City | M2 | 0.2870 | 0.3277 | -0.0406 |
| Buffalo | Rochester | M0 | 0.3038 | 0.2710 | 0.0328 |
| Buffalo | Rochester | M1 | 0.2809 | 0.3235 | -0.0426 |
| Buffalo | Rochester | M2 | 0.2870 | 0.2800 | 0.0070 |
| Buffalo | pooled | M0 | 0.3038 | 0.2938 | 0.0100 |
| Buffalo | pooled | M1 | 0.2809 | 0.3036 | -0.0227 |
| Buffalo | pooled | M2 | 0.2870 | 0.3355 | -0.0485 |
| Rochester | New York City | M0 | 0.3336 | 0.2210 | 0.1125 |
| Rochester | New York City | M1 | 0.2830 | 0.3380 | -0.0550 |
| Rochester | New York City | M2 | 0.2139 | 0.2758 | -0.0619 |
| Rochester | Buffalo | M0 | 0.3336 | 0.4700 | -0.1364 |
| Rochester | Buffalo | M1 | 0.2830 | 0.4041 | -0.1211 |
| Rochester | Buffalo | M2 | 0.2139 | 0.3890 | -0.1751 |
| Rochester | pooled | M0 | 0.3336 | 0.2210 | 0.1125 |
| Rochester | pooled | M1 | 0.2830 | 0.3414 | -0.0584 |
| Rochester | pooled | M2 | 0.2139 | 0.2883 | -0.0745 |


A positive gap means the source-only model is worse than local-full. These models use fixed phase 5 capacities and target-specific purging; their scores need not equal phase 4's tuned models.

## Every matched source/fraction/model comparison

| city | source | fraction | model | mean_benefit | seed_p025 | seed_p975 | positive_seeds | negative_seeds |
|---|---|---|---|---|---|---|---|---|
| New York City | Buffalo | 0.1 | M0 | 0.0049 | -0.0016 | 0.0113 | 18 | 2 |
| New York City | Buffalo | 0.1 | M1 | 0.0147 | -0.0165 | 0.0542 | 15 | 5 |
| New York City | Buffalo | 0.1 | M2 | 0.0044 | -0.0245 | 0.0258 | 12 | 8 |
| New York City | Rochester | 0.1 | M0 | 0.0067 | 0.0017 | 0.0102 | 20 | 0 |
| New York City | Rochester | 0.1 | M1 | -0.0274 | -0.0582 | -0.0008 | 1 | 19 |
| New York City | Rochester | 0.1 | M2 | -0.0144 | -0.0424 | 0.0074 | 3 | 17 |
| New York City | pooled | 0.1 | M0 | 0.0086 | -0.0006 | 0.0160 | 19 | 1 |
| New York City | pooled | 0.1 | M1 | -0.0168 | -0.0488 | 0.0221 | 4 | 16 |
| New York City | pooled | 0.1 | M2 | -0.0124 | -0.0398 | 0.0112 | 3 | 17 |
| New York City | Buffalo | 0.25 | M0 | 0.0026 | 0.0003 | 0.0070 | 20 | 0 |
| New York City | Buffalo | 0.25 | M1 | 0.0264 | -0.0112 | 0.0551 | 18 | 2 |
| New York City | Buffalo | 0.25 | M2 | 0.0057 | -0.0086 | 0.0293 | 12 | 8 |
| New York City | Rochester | 0.25 | M0 | 0.0026 | 0.0016 | 0.0040 | 20 | 0 |
| New York City | Rochester | 0.25 | M1 | -0.0205 | -0.0337 | -0.0088 | 0 | 20 |
| New York City | Rochester | 0.25 | M2 | -0.0049 | -0.0183 | 0.0088 | 9 | 11 |
| New York City | pooled | 0.25 | M0 | 0.0055 | 0.0028 | 0.0096 | 20 | 0 |
| New York City | pooled | 0.25 | M1 | 0.0044 | -0.0305 | 0.0229 | 12 | 8 |
| New York City | pooled | 0.25 | M2 | -0.0025 | -0.0211 | 0.0277 | 6 | 14 |
| Buffalo | New York City | 0.1 | M0 | -0.0127 | -0.0856 | 0.0441 | 9 | 11 |
| Buffalo | New York City | 0.1 | M1 | -0.0448 | -0.1071 | 0.0416 | 3 | 17 |
| Buffalo | New York City | 0.1 | M2 | 0.0264 | -0.0276 | 0.0755 | 14 | 6 |
| Buffalo | Rochester | 0.1 | M0 | -0.0443 | -0.1195 | 0.0136 | 3 | 17 |
| Buffalo | Rochester | 0.1 | M1 | -0.0542 | -0.1226 | 0.0262 | 4 | 16 |
| Buffalo | Rochester | 0.1 | M2 | -0.0008 | -0.0175 | 0.0072 | 4 | 2 |
| Buffalo | pooled | 0.1 | M0 | -0.0127 | -0.0856 | 0.0441 | 9 | 11 |
| Buffalo | pooled | 0.1 | M1 | -0.0422 | -0.1082 | 0.0427 | 3 | 17 |
| Buffalo | pooled | 0.1 | M2 | 0.0184 | -0.0370 | 0.0894 | 12 | 8 |
| Buffalo | New York City | 0.25 | M0 | -0.0063 | -0.0599 | 0.0481 | 9 | 11 |
| Buffalo | New York City | 0.25 | M1 | -0.0019 | -0.0938 | 0.0861 | 9 | 11 |
| Buffalo | New York City | 0.25 | M2 | 0.0209 | -0.0295 | 0.0821 | 13 | 7 |
| Buffalo | Rochester | 0.25 | M0 | -0.0313 | -0.0872 | 0.0076 | 4 | 16 |
| Buffalo | Rochester | 0.25 | M1 | -0.0139 | -0.1059 | 0.0657 | 7 | 13 |
| Buffalo | Rochester | 0.25 | M2 | -0.0008 | -0.0126 | 0.0083 | 2 | 3 |
| Buffalo | pooled | 0.25 | M0 | -0.0063 | -0.0599 | 0.0481 | 9 | 11 |
| Buffalo | pooled | 0.25 | M1 | 0.0010 | -0.0938 | 0.0859 | 11 | 9 |
| Buffalo | pooled | 0.25 | M2 | 0.0176 | -0.0213 | 0.0567 | 15 | 5 |
| Rochester | New York City | 0.1 | M0 | -0.0410 | -0.1437 | -0.0006 | 1 | 19 |
| Rochester | New York City | 0.1 | M1 | 0.0632 | -0.0592 | 0.1328 | 15 | 5 |
| Rochester | New York City | 0.1 | M2 | 0.0302 | -0.0242 | 0.0618 | 19 | 1 |
| Rochester | Buffalo | 0.1 | M0 | 0.2086 | 0.1016 | 0.2834 | 20 | 0 |
| Rochester | Buffalo | 0.1 | M1 | 0.1156 | 0.0062 | 0.1857 | 20 | 0 |
| Rochester | Buffalo | 0.1 | M2 | 0.0426 | -0.0346 | 0.1264 | 15 | 5 |
| Rochester | pooled | 0.1 | M0 | -0.0410 | -0.1437 | -0.0006 | 1 | 19 |
| Rochester | pooled | 0.1 | M1 | 0.0694 | -0.0527 | 0.1397 | 16 | 4 |
| Rochester | pooled | 0.1 | M2 | 0.0422 | -0.0127 | 0.0720 | 19 | 1 |
| Rochester | New York City | 0.25 | M0 | -0.0727 | -0.2102 | 0.0079 | 1 | 19 |
| Rochester | New York City | 0.25 | M1 | 0.0700 | -0.0726 | 0.1338 | 17 | 3 |
| Rochester | New York City | 0.25 | M2 | 0.0342 | -0.0411 | 0.0720 | 15 | 5 |
| Rochester | Buffalo | 0.25 | M0 | 0.1792 | 0.0522 | 0.2450 | 20 | 0 |
| Rochester | Buffalo | 0.25 | M1 | 0.1205 | -0.0077 | 0.2092 | 19 | 1 |
| Rochester | Buffalo | 0.25 | M2 | 0.0816 | 0.0047 | 0.2041 | 20 | 0 |
| Rochester | pooled | 0.25 | M0 | -0.0727 | -0.2102 | 0.0079 | 1 | 19 |
| Rochester | pooled | 0.25 | M1 | 0.0698 | -0.0608 | 0.1412 | 17 | 3 |
| Rochester | pooled | 0.25 | M2 | 0.0470 | -0.0279 | 0.0863 | 17 | 3 |


## Probability accuracy and sampling variation

All 1,476 evaluations include native Brier, ECE, mean calibration error and top-decile metrics in `data/metrics.csv`. `data/condition_summary.csv` summarizes these across seeds while preserving the target sample size and AP seed range. The pooled-source probability figure compares mean Brier for augmented and matched local-only conditions, with local-full as a reference; lower is better. Calibration bins for every complete test vector are saved in `data/calibration_bins.csv`; the calibration figure shows local-full and pooled zero-shot references without averaging seed predictions into a new ensemble. The curves are descriptive, with no independent-sample inference. No recalibration or post-test choice between models was made. Negative seed counts and constant fits should be considered when interpreting seemingly large benefits in small cities.

## Feature extrapolation

14 source/target/feature rows have more than 20% of observed target values outside the observed source range. All 81 source/target/feature rows, including missingness, are preserved in `data/extrapolation.csv`. A range mismatch indicates limited source coverage; it is not proof of failure, and it was not used to select sources or features.

## Validation and scientific status

Validation reconstructed every local/source pool and deterministic sample, verified the exactly matched controls, reproduced every saved model's held-out probabilities and training-only preprocessing, independently refit representative local/augmented models, and reconciled all metrics, gaps, benefits, seed summaries and extrapolation calculations. Checksums and model artifacts are retained.

The experiments remain descriptive. Independent research review is pending, and both outcome years were inspected previously. No universal transfer, calibrated operational risk or confirmatory scientific success is claimed.
