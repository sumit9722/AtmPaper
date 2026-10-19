# Phase 5 results

**Computational validation: PASS.** Completed 7,380 model evaluations using 7,155 unique saved models, 610,572 predictions and 1,476 complete target-year evaluation vectors. All training is from 2024 and all testing from 2025. There are 267 constant single-class fits, 0 unsupported evaluations and 0 captured estimator-warning rows.

Transfer effects are mixed across cities, model families, source cities and adaptation fractions. Adding source data sometimes helps and sometimes harms the exactly matched local-only model; there is no demonstrated universal transfer benefit.

## Direction of mean matched benefits

| city | positive_mean_conditions | negative_mean_conditions | conditions |
|---|---|---|---|
| New York City | 12 | 6 | 18 |
| Buffalo | 6 | 12 | 18 |
| Rochester | 10 | 8 | 18 |


These counts describe the 18 source/fraction/model combinations per city. They are not independent significance tests, and a positive mean does not imply that every seed benefits.

## Pooled-source matched benefits

| city | fraction | model | mean_benefit | sd | seed_p025 | seed_p975 | negative_seeds |
|---|---|---|---|---|---|---|---|
| New York City | 0.1 | M0 | 0.0086 | 0.0056 | -0.0006 | 0.0160 | 1 |
| New York City | 0.1 | M1 | -0.0201 | 0.0205 | -0.0532 | 0.0207 | 19 |
| New York City | 0.1 | M2 | 0.0036 | 0.0126 | -0.0138 | 0.0275 | 7 |
| New York City | 0.25 | M0 | 0.0055 | 0.0020 | 0.0028 | 0.0096 | 0 |
| New York City | 0.25 | M1 | -0.0028 | 0.0114 | -0.0186 | 0.0177 | 11 |
| New York City | 0.25 | M2 | 0.0082 | 0.0088 | -0.0068 | 0.0230 | 3 |
| Buffalo | 0.1 | M0 | -0.0127 | 0.0420 | -0.0856 | 0.0441 | 11 |
| Buffalo | 0.1 | M1 | -0.0061 | 0.0674 | -0.1623 | 0.0746 | 10 |
| Buffalo | 0.1 | M2 | 0.0151 | 0.0397 | -0.0303 | 0.0988 | 9 |
| Buffalo | 0.25 | M0 | -0.0063 | 0.0386 | -0.0599 | 0.0481 | 11 |
| Buffalo | 0.25 | M1 | -0.0023 | 0.0852 | -0.1809 | 0.0783 | 6 |
| Buffalo | 0.25 | M2 | 0.0341 | 0.0420 | -0.0239 | 0.1218 | 3 |
| Rochester | 0.1 | M0 | -0.0410 | 0.0447 | -0.1437 | -0.0006 | 19 |
| Rochester | 0.1 | M1 | -0.0302 | 0.0723 | -0.1805 | 0.0516 | 10 |
| Rochester | 0.1 | M2 | 0.0589 | 0.0246 | 0.0072 | 0.0908 | 1 |
| Rochester | 0.25 | M0 | -0.0727 | 0.0637 | -0.2102 | 0.0079 | 19 |
| Rochester | 0.25 | M1 | -0.1132 | 0.1133 | -0.2941 | 0.0644 | 17 |
| Rochester | 0.25 | M2 | 0.0634 | 0.0359 | -0.0157 | 0.0974 | 2 |


The paired target-only control always uses exactly the same earlier target rows. `seed_p025` and `seed_p975` are empirical percentiles across the same 20 sampling seeds, **not confidence intervals**. The full individual-source and pooled-source table follows below.

## Local-full and zero-shot performance

| city | condition | source | model | n | positives | average_precision | brier_score | ece_10bins | top_decile_recall |
|---|---|---|---|---|---|---|---|---|---|
| New York City | local_full | target | M0 | 1160 | 652 | 0.7251 | 0.2101 | 0.0385 | 0.1334 |
| New York City | local_full | target | M1 | 1160 | 652 | 0.7486 | 0.2101 | 0.0303 | 0.1503 |
| New York City | local_full | target | M2 | 1160 | 652 | 0.6917 | 0.2205 | 0.0608 | 0.1212 |
| New York City | source_only | Buffalo | M0 | 1160 | 652 | 0.4257 | 0.4423 | 0.4336 | 0.0337 |
| New York City | source_only | Buffalo | M1 | 1160 | 652 | 0.5324 | 0.5391 | 0.5391 | 0.1104 |
| New York City | source_only | Buffalo | M2 | 1160 | 652 | 0.5781 | 0.2890 | 0.2093 | 0.0874 |
| New York City | source_only | Rochester | M0 | 1160 | 652 | 0.4257 | 0.4791 | 0.4710 | 0.0337 |
| New York City | source_only | Rochester | M1 | 1160 | 652 | 0.5018 | 0.5361 | 0.5295 | 0.0813 |
| New York City | source_only | Rochester | M2 | 1160 | 652 | 0.5621 | 0.3435 | 0.3121 | 0.0966 |
| New York City | source_only | pooled | M0 | 1160 | 652 | 0.4257 | 0.4557 | 0.4472 | 0.0337 |
| New York City | source_only | pooled | M1 | 1160 | 652 | 0.5141 | 0.5346 | 0.5298 | 0.0982 |
| New York City | source_only | pooled | M2 | 1160 | 652 | 0.5270 | 0.3588 | 0.3272 | 0.0782 |
| Buffalo | local_full | target | M0 | 50 | 14 | 0.3038 | 0.2034 | 0.0261 | 0.0714 |
| Buffalo | local_full | target | M1 | 50 | 14 | 0.2920 | 0.2454 | 0.1834 | 0.0714 |
| Buffalo | local_full | target | M2 | 50 | 14 | 0.2870 | 0.2031 | 0.0399 | 0.0714 |
| Buffalo | source_only | New York City | M0 | 50 | 14 | 0.2938 | 0.2219 | 0.1839 | 0.0714 |
| Buffalo | source_only | New York City | M1 | 50 | 14 | 0.3164 | 0.2117 | 0.1671 | 0.0714 |
| Buffalo | source_only | New York City | M2 | 50 | 14 | 0.4216 | 0.1989 | 0.0929 | 0.1429 |
| Buffalo | source_only | Rochester | M0 | 50 | 14 | 0.2710 | 0.2267 | 0.1929 | 0.0000 |
| Buffalo | source_only | Rochester | M1 | 50 | 14 | 0.2558 | 0.3888 | 0.4060 | 0.0714 |
| Buffalo | source_only | Rochester | M2 | 50 | 14 | 0.2800 | 0.2025 | 0.0300 | 0.2857 |
| Buffalo | source_only | pooled | M0 | 50 | 14 | 0.2938 | 0.2213 | 0.1825 | 0.0714 |
| Buffalo | source_only | pooled | M1 | 50 | 14 | 0.3135 | 0.2106 | 0.2062 | 0.0714 |
| Buffalo | source_only | pooled | M2 | 50 | 14 | 0.3648 | 0.2033 | 0.1193 | 0.1429 |
| Rochester | local_full | target | M0 | 31 | 8 | 0.3336 | 0.2289 | 0.2842 | 0.2500 |
| Rochester | local_full | target | M1 | 31 | 8 | 0.3287 | 0.2808 | 0.2986 | 0.1250 |
| Rochester | local_full | target | M2 | 31 | 8 | 0.2139 | 0.2175 | 0.1954 | 0.0000 |
| Rochester | source_only | New York City | M0 | 31 | 8 | 0.2210 | 0.2439 | 0.2255 | 0.0000 |
| Rochester | source_only | New York City | M1 | 31 | 8 | 0.3385 | 0.2205 | 0.2495 | 0.2500 |
| Rochester | source_only | New York City | M2 | 31 | 8 | 0.2919 | 0.2286 | 0.2233 | 0.1250 |
| Rochester | source_only | Buffalo | M0 | 31 | 8 | 0.4700 | 0.1770 | 0.1166 | 0.2500 |
| Rochester | source_only | Buffalo | M1 | 31 | 8 | 0.5905 | 0.1654 | 0.1316 | 0.2500 |
| Rochester | source_only | Buffalo | M2 | 31 | 8 | 0.4991 | 0.1974 | 0.1047 | 0.2500 |
| Rochester | source_only | pooled | M0 | 31 | 8 | 0.2210 | 0.2455 | 0.2394 | 0.0000 |
| Rochester | source_only | pooled | M1 | 31 | 8 | 0.2427 | 0.2920 | 0.3554 | 0.1250 |
| Rochester | source_only | pooled | M2 | 31 | 8 | 0.2969 | 0.2184 | 0.2403 | 0.1250 |


| city | source | model | local_ap | source_ap | transfer_gap |
|---|---|---|---|---|---|
| New York City | Buffalo | M0 | 0.7251 | 0.4257 | 0.2994 |
| New York City | Buffalo | M1 | 0.7486 | 0.5324 | 0.2162 |
| New York City | Buffalo | M2 | 0.6917 | 0.5781 | 0.1136 |
| New York City | Rochester | M0 | 0.7251 | 0.4257 | 0.2994 |
| New York City | Rochester | M1 | 0.7486 | 0.5018 | 0.2468 |
| New York City | Rochester | M2 | 0.6917 | 0.5621 | 0.1297 |
| New York City | pooled | M0 | 0.7251 | 0.4257 | 0.2994 |
| New York City | pooled | M1 | 0.7486 | 0.5141 | 0.2345 |
| New York City | pooled | M2 | 0.6917 | 0.5270 | 0.1648 |
| Buffalo | New York City | M0 | 0.3038 | 0.2938 | 0.0100 |
| Buffalo | New York City | M1 | 0.2920 | 0.3164 | -0.0243 |
| Buffalo | New York City | M2 | 0.2870 | 0.4216 | -0.1346 |
| Buffalo | Rochester | M0 | 0.3038 | 0.2710 | 0.0328 |
| Buffalo | Rochester | M1 | 0.2920 | 0.2558 | 0.0362 |
| Buffalo | Rochester | M2 | 0.2870 | 0.2800 | 0.0070 |
| Buffalo | pooled | M0 | 0.3038 | 0.2938 | 0.0100 |
| Buffalo | pooled | M1 | 0.2920 | 0.3135 | -0.0215 |
| Buffalo | pooled | M2 | 0.2870 | 0.3648 | -0.0778 |
| Rochester | New York City | M0 | 0.3336 | 0.2210 | 0.1125 |
| Rochester | New York City | M1 | 0.3287 | 0.3385 | -0.0098 |
| Rochester | New York City | M2 | 0.2139 | 0.2919 | -0.0780 |
| Rochester | Buffalo | M0 | 0.3336 | 0.4700 | -0.1364 |
| Rochester | Buffalo | M1 | 0.3287 | 0.5905 | -0.2618 |
| Rochester | Buffalo | M2 | 0.2139 | 0.4991 | -0.2852 |
| Rochester | pooled | M0 | 0.3336 | 0.2210 | 0.1125 |
| Rochester | pooled | M1 | 0.3287 | 0.2427 | 0.0861 |
| Rochester | pooled | M2 | 0.2139 | 0.2969 | -0.0830 |


A positive gap means the source-only model is worse than local-full. These models use fixed phase 5 capacities and target-specific purging; their scores need not equal phase 4's tuned models.

## Every matched source/fraction/model comparison

| city | source | fraction | model | mean_benefit | seed_p025 | seed_p975 | positive_seeds | negative_seeds |
|---|---|---|---|---|---|---|---|---|
| New York City | Buffalo | 0.1 | M0 | 0.0049 | -0.0016 | 0.0113 | 18 | 2 |
| New York City | Buffalo | 0.1 | M1 | 0.0100 | -0.0105 | 0.0533 | 12 | 8 |
| New York City | Buffalo | 0.1 | M2 | 0.0058 | -0.0143 | 0.0265 | 12 | 8 |
| New York City | Rochester | 0.1 | M0 | 0.0067 | 0.0017 | 0.0102 | 20 | 0 |
| New York City | Rochester | 0.1 | M1 | -0.0122 | -0.0331 | 0.0228 | 5 | 15 |
| New York City | Rochester | 0.1 | M2 | -0.0072 | -0.0464 | 0.0222 | 7 | 13 |
| New York City | pooled | 0.1 | M0 | 0.0086 | -0.0006 | 0.0160 | 19 | 1 |
| New York City | pooled | 0.1 | M1 | -0.0201 | -0.0532 | 0.0207 | 1 | 19 |
| New York City | pooled | 0.1 | M2 | 0.0036 | -0.0138 | 0.0275 | 13 | 7 |
| New York City | Buffalo | 0.25 | M0 | 0.0026 | 0.0003 | 0.0070 | 20 | 0 |
| New York City | Buffalo | 0.25 | M1 | 0.0003 | -0.0180 | 0.0179 | 11 | 9 |
| New York City | Buffalo | 0.25 | M2 | 0.0091 | -0.0022 | 0.0223 | 18 | 2 |
| New York City | Rochester | 0.25 | M0 | 0.0026 | 0.0016 | 0.0040 | 20 | 0 |
| New York City | Rochester | 0.25 | M1 | -0.0000 | -0.0168 | 0.0221 | 9 | 11 |
| New York City | Rochester | 0.25 | M2 | -0.0016 | -0.0118 | 0.0096 | 9 | 11 |
| New York City | pooled | 0.25 | M0 | 0.0055 | 0.0028 | 0.0096 | 20 | 0 |
| New York City | pooled | 0.25 | M1 | -0.0028 | -0.0186 | 0.0177 | 9 | 11 |
| New York City | pooled | 0.25 | M2 | 0.0082 | -0.0068 | 0.0230 | 17 | 3 |
| Buffalo | New York City | 0.1 | M0 | -0.0127 | -0.0856 | 0.0441 | 9 | 11 |
| Buffalo | New York City | 0.1 | M1 | 0.0011 | -0.1509 | 0.0654 | 11 | 9 |
| Buffalo | New York City | 0.1 | M2 | 0.1006 | 0.0476 | 0.1550 | 20 | 0 |
| Buffalo | Rochester | 0.1 | M0 | -0.0443 | -0.1195 | 0.0136 | 3 | 17 |
| Buffalo | Rochester | 0.1 | M1 | -0.0630 | -0.2047 | 0.0521 | 4 | 16 |
| Buffalo | Rochester | 0.1 | M2 | -0.0008 | -0.0175 | 0.0072 | 4 | 2 |
| Buffalo | pooled | 0.1 | M0 | -0.0127 | -0.0856 | 0.0441 | 9 | 11 |
| Buffalo | pooled | 0.1 | M1 | -0.0061 | -0.1623 | 0.0746 | 10 | 10 |
| Buffalo | pooled | 0.1 | M2 | 0.0151 | -0.0303 | 0.0988 | 11 | 9 |
| Buffalo | New York City | 0.25 | M0 | -0.0063 | -0.0599 | 0.0481 | 9 | 11 |
| Buffalo | New York City | 0.25 | M1 | 0.0047 | -0.1631 | 0.0878 | 14 | 6 |
| Buffalo | New York City | 0.25 | M2 | 0.0759 | 0.0352 | 0.1254 | 20 | 0 |
| Buffalo | Rochester | 0.25 | M0 | -0.0313 | -0.0872 | 0.0076 | 4 | 16 |
| Buffalo | Rochester | 0.25 | M1 | -0.0608 | -0.2247 | 0.0763 | 3 | 17 |
| Buffalo | Rochester | 0.25 | M2 | -0.0008 | -0.0126 | 0.0083 | 2 | 3 |
| Buffalo | pooled | 0.25 | M0 | -0.0063 | -0.0599 | 0.0481 | 9 | 11 |
| Buffalo | pooled | 0.25 | M1 | -0.0023 | -0.1809 | 0.0783 | 14 | 6 |
| Buffalo | pooled | 0.25 | M2 | 0.0341 | -0.0239 | 0.1218 | 17 | 3 |
| Rochester | New York City | 0.1 | M0 | -0.0410 | -0.1437 | -0.0006 | 1 | 19 |
| Rochester | New York City | 0.1 | M1 | 0.0595 | -0.1059 | 0.1483 | 16 | 4 |
| Rochester | New York City | 0.1 | M2 | 0.0488 | -0.0018 | 0.0757 | 19 | 1 |
| Rochester | Buffalo | 0.1 | M0 | 0.2086 | 0.1016 | 0.2834 | 20 | 0 |
| Rochester | Buffalo | 0.1 | M1 | 0.2268 | 0.1133 | 0.4926 | 20 | 0 |
| Rochester | Buffalo | 0.1 | M2 | -0.0246 | -0.0749 | 0.0480 | 5 | 15 |
| Rochester | pooled | 0.1 | M0 | -0.0410 | -0.1437 | -0.0006 | 1 | 19 |
| Rochester | pooled | 0.1 | M1 | -0.0302 | -0.1805 | 0.0516 | 10 | 10 |
| Rochester | pooled | 0.1 | M2 | 0.0589 | 0.0072 | 0.0908 | 19 | 1 |
| Rochester | New York City | 0.25 | M0 | -0.0727 | -0.2102 | 0.0079 | 1 | 19 |
| Rochester | New York City | 0.25 | M1 | -0.0276 | -0.2168 | 0.1542 | 9 | 11 |
| Rochester | New York City | 0.25 | M2 | 0.0632 | -0.0168 | 0.1020 | 18 | 2 |
| Rochester | Buffalo | 0.25 | M0 | 0.1792 | 0.0522 | 0.2450 | 20 | 0 |
| Rochester | Buffalo | 0.25 | M1 | 0.0890 | -0.0472 | 0.2328 | 16 | 4 |
| Rochester | Buffalo | 0.25 | M2 | 0.0277 | -0.0485 | 0.0959 | 11 | 9 |
| Rochester | pooled | 0.25 | M0 | -0.0727 | -0.2102 | 0.0079 | 1 | 19 |
| Rochester | pooled | 0.25 | M1 | -0.1132 | -0.2941 | 0.0644 | 3 | 17 |
| Rochester | pooled | 0.25 | M2 | 0.0634 | -0.0157 | 0.0974 | 18 | 2 |


## Probability accuracy and sampling variation

All 1,476 evaluations include native Brier, ECE, mean calibration error and top-decile metrics in `data/metrics.csv`. `data/condition_summary.csv` summarizes these across seeds while preserving the target sample size and AP seed range. The pooled-source probability figure compares mean Brier for augmented and matched local-only conditions, with local-full as a reference; lower is better. Calibration bins for every complete test vector are saved in `data/calibration_bins.csv`; the calibration figure shows local-full and pooled zero-shot references without averaging seed predictions into a new ensemble. The curves are descriptive, with no independent-sample inference. No recalibration or post-test choice between models was made. Negative seed counts and constant fits should be considered when interpreting seemingly large benefits in small cities.

## Feature extrapolation

34 source/target/feature rows have more than 20% of observed target values outside the observed source range. All 126 source/target/feature rows, including missingness, are preserved in `data/extrapolation.csv`. A range mismatch indicates limited source coverage; it is not proof of failure, and it was not used to select sources or features.

## Validation and scientific status

Validation reconstructed every local/source pool and deterministic sample, verified the exactly matched controls, reproduced every saved model's held-out probabilities and training-only preprocessing, independently refit representative local/augmented models, and reconciled all metrics, gaps, benefits, seed summaries and extrapolation calculations. Checksums and model artifacts are retained.

The experiments remain descriptive. The phase 4 primary improvement gate failed, independent research review is pending, and both outcome years were inspected previously. No universal transfer, calibrated operational risk or confirmatory scientific success is claimed.
