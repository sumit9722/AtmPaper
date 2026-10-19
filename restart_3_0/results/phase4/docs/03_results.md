# Phase 4 results

**Computational status: validated PASS.** The run trained on the 1,201-site 2024 cohort and tested the 1,241-site 2025 cohort with spatial purging. It produced **141 outer model artifacts** and **44,376 held-out prediction rows** across six variants and two schemes. Each eligible 2025 row is predicted exactly once per model/variant/scheme. No phase 5 experiments were run.

## Primary pooled native-probability performance

| scheme | model | n | positives | average_precision | roc_auc | brier_score | ece_10bins | top_decile_recall |
|---|---|---|---|---|---|---|---|---|
| forward_spatial | M0 | 1241 | 674 | 0.7195 | 0.7242 | 0.2112 | 0.0488 | 0.1424 |
| forward_spatial | M1 | 1241 | 674 | 0.7071 | 0.7140 | 0.2170 | 0.0639 | 0.1365 |
| forward_spatial | M2 | 1241 | 674 | 0.7001 | 0.6869 | 0.2247 | 0.0356 | 0.1409 |
| forward_leave_city_out | M0 | 1241 | 674 | 0.4077 | 0.2697 | 0.4410 | 0.4262 | 0.0341 |
| forward_leave_city_out | M1 | 1241 | 674 | 0.5177 | 0.4559 | 0.4182 | 0.3767 | 0.0861 |
| forward_leave_city_out | M2 | 1241 | 674 | 0.4746 | 0.3842 | 0.3473 | 0.3181 | 0.0475 |


## Primary paired environmental improvement

M1-M0: AP difference -0.0124, 95% interval [-0.0492, +0.0180], numerical gate not passed; M2-M0: AP difference -0.0193, 95% interval [-0.0723, +0.0256], numerical gate not passed.

Neither environmental model met the primary pooled numerical improvement criterion. This evaluation does not demonstrate reliable incremental improvement; it does not prove that environmental effects are absent.

Primary spatial Brier scores (lower is better) are 0.2112, 0.2170, and 0.2247 for M0/M1/M2. City-held-out Brier scores are 0.4410, 0.4182, and 0.3473. Assess probability accuracy separately from ranking; pooled metrics are dominated by NYC. This follow-up uses previously inspected outcomes, so numerical success remains exploratory.

| scheme | city | comparison | ap_difference | ci_low | ci_high | valid_replicates | exploratory_numerical_gate |
|---|---|---|---|---|---|---|---|
| forward_spatial | ALL | M1-M0 | -0.0124 | -0.0492 | 0.0180 | 2000 | False |
| forward_spatial | ALL | M2-M0 | -0.0193 | -0.0723 | 0.0256 | 2000 | False |
| forward_spatial | New York City | M1-M0 | -0.0121 | -0.0495 | 0.0197 | 2000 | False |
| forward_spatial | New York City | M2-M0 | -0.0047 | -0.0552 | 0.0388 | 2000 | False |
| forward_spatial | Buffalo | M1-M0 | 0.0395 | -0.0582 | 0.2015 | 2000 | False |
| forward_spatial | Buffalo | M2-M0 | -0.0201 | -0.0788 | 0.0718 | 2000 | False |
| forward_spatial | Rochester | M1-M0 | 0.0244 | -0.0089 | 0.2708 | 2000 | False |
| forward_spatial | Rochester | M2-M0 | 0.0260 | -0.0483 | 0.2304 | 2000 | False |
| forward_leave_city_out | ALL | M1-M0 | 0.1100 | 0.0784 | 0.1412 | 2000 | True |
| forward_leave_city_out | ALL | M2-M0 | 0.0669 | 0.0475 | 0.0872 | 2000 | True |
| forward_leave_city_out | New York City | M1-M0 | 0.1393 | 0.1027 | 0.1747 | 2000 | True |
| forward_leave_city_out | New York City | M2-M0 | 0.0744 | 0.0518 | 0.0954 | 2000 | True |
| forward_leave_city_out | Buffalo | M1-M0 | 0.0205 | -0.0272 | 0.1638 | 2000 | False |
| forward_leave_city_out | Buffalo | M2-M0 | 0.0417 | -0.0294 | 0.1200 | 2000 | False |
| forward_leave_city_out | Rochester | M1-M0 | 0.1204 | -0.0240 | 0.3091 | 2000 | False |
| forward_leave_city_out | Rochester | M2-M0 | 0.0673 | -0.0010 | 0.4671 | 2000 | False |


## Primary results by city

| scheme | city | model | n | positives | average_precision | roc_auc | brier_score | top_decile_recall |
|---|---|---|---|---|---|---|---|---|
| forward_spatial | New York City | M0 | 1160 | 652 | 0.7264 | 0.7199 | 0.2095 | 0.1350 |
| forward_spatial | New York City | M1 | 1160 | 652 | 0.7143 | 0.7093 | 0.2147 | 0.1288 |
| forward_spatial | New York City | M2 | 1160 | 652 | 0.7217 | 0.6940 | 0.2213 | 0.1365 |
| forward_spatial | Buffalo | M0 | 50 | 14 | 0.2996 | 0.5139 | 0.2261 | 0.0714 |
| forward_spatial | Buffalo | M1 | 50 | 14 | 0.3390 | 0.5883 | 0.2340 | 0.0714 |
| forward_spatial | Buffalo | M2 | 50 | 14 | 0.2794 | 0.4762 | 0.2391 | 0.0000 |
| forward_spatial | Rochester | M0 | 31 | 8 | 0.2221 | 0.3342 | 0.2494 | 0.0000 |
| forward_spatial | Rochester | M1 | 31 | 8 | 0.2465 | 0.3587 | 0.2743 | 0.1250 |
| forward_spatial | Rochester | M2 | 31 | 8 | 0.2481 | 0.3859 | 0.3284 | 0.1250 |
| forward_leave_city_out | New York City | M0 | 1160 | 652 | 0.4257 | 0.2764 | 0.4557 | 0.0337 |
| forward_leave_city_out | New York City | M1 | 1160 | 652 | 0.5650 | 0.4820 | 0.4298 | 0.1043 |
| forward_leave_city_out | New York City | M2 | 1160 | 652 | 0.5001 | 0.3911 | 0.3541 | 0.0567 |
| forward_leave_city_out | Buffalo | M0 | 50 | 14 | 0.2938 | 0.5089 | 0.2213 | 0.0714 |
| forward_leave_city_out | Buffalo | M1 | 50 | 14 | 0.3143 | 0.5665 | 0.2395 | 0.0000 |
| forward_leave_city_out | Buffalo | M2 | 50 | 14 | 0.3355 | 0.5665 | 0.2429 | 0.0714 |
| forward_leave_city_out | Rochester | M0 | 31 | 8 | 0.2210 | 0.3397 | 0.2455 | 0.0000 |
| forward_leave_city_out | Rochester | M1 | 31 | 8 | 0.3414 | 0.3967 | 0.2748 | 0.1250 |
| forward_leave_city_out | Rochester | M2 | 31 | 8 | 0.2883 | 0.5326 | 0.2613 | 0.0000 |


## Sensitivity results

These analyses retain the same split assignments and do not replace the primary result. All test labels are 2025 outcomes; training labels remain report-filtered 2024 outcomes. The unfiltered-background variant changes only background predictors. Full native and sigmoid metrics, including all city-specific sensitivities, are in `data/metrics.csv`.

| variant | scheme | model | n | average_precision | brier_score | top_decile_recall |
|---|---|---|---|---|---|---|
| radius_25m | forward_spatial | M0 | 1241 | 0.5284 | 0.2088 | 0.1714 |
| radius_25m | forward_spatial | M1 | 1241 | 0.4824 | 0.2232 | 0.1573 |
| radius_25m | forward_spatial | M2 | 1241 | 0.4745 | 0.2310 | 0.1620 |
| radius_25m | forward_leave_city_out | M0 | 1241 | 0.5053 | 0.2517 | 0.1667 |
| radius_25m | forward_leave_city_out | M1 | 1241 | 0.3832 | 0.2745 | 0.1103 |
| radius_25m | forward_leave_city_out | M2 | 1241 | 0.3451 | 0.2803 | 0.0704 |
| radius_100m | forward_spatial | M0 | 1241 | 0.9489 | 0.1172 | 0.1207 |
| radius_100m | forward_spatial | M1 | 1241 | 0.9461 | 0.1228 | 0.1207 |
| radius_100m | forward_spatial | M2 | 1241 | 0.9453 | 0.1242 | 0.1187 |
| radius_100m | forward_leave_city_out | M0 | 1241 | 0.9317 | 0.1337 | 0.1158 |
| radius_100m | forward_leave_city_out | M1 | 1241 | 0.8727 | 0.1746 | 0.1109 |
| radius_100m | forward_leave_city_out | M2 | 1241 | 0.8170 | 0.1544 | 0.0952 |
| nearest_only_50m | forward_spatial | M0 | 1241 | 0.6456 | 0.2211 | 0.1445 |
| nearest_only_50m | forward_spatial | M1 | 1241 | 0.6310 | 0.2279 | 0.1429 |
| nearest_only_50m | forward_spatial | M2 | 1241 | 0.5958 | 0.2385 | 0.1412 |
| nearest_only_50m | forward_leave_city_out | M0 | 1241 | 0.3651 | 0.3964 | 0.0365 |
| nearest_only_50m | forward_leave_city_out | M1 | 1241 | 0.4723 | 0.3766 | 0.0930 |
| nearest_only_50m | forward_leave_city_out | M2 | 1241 | 0.4243 | 0.3168 | 0.0532 |
| unfiltered_background | forward_spatial | M0 | 1241 | 0.7194 | 0.2107 | 0.1424 |
| unfiltered_background | forward_spatial | M1 | 1241 | 0.7100 | 0.2162 | 0.1365 |
| unfiltered_background | forward_spatial | M2 | 1241 | 0.7008 | 0.2256 | 0.1469 |
| unfiltered_background | forward_leave_city_out | M0 | 1241 | 0.4110 | 0.3537 | 0.0326 |
| unfiltered_background | forward_leave_city_out | M1 | 1241 | 0.4787 | 0.3950 | 0.0757 |
| unfiltered_background | forward_leave_city_out | M2 | 1241 | 0.4716 | 0.3180 | 0.0504 |
| exclude_buffalo | forward_spatial | M0 | 1191 | 0.7237 | 0.2105 | 0.1379 |
| exclude_buffalo | forward_spatial | M1 | 1191 | 0.7099 | 0.2163 | 0.1364 |
| exclude_buffalo | forward_spatial | M2 | 1191 | 0.7090 | 0.2243 | 0.1379 |
| exclude_buffalo | forward_leave_city_out | M0 | 1191 | 0.4163 | 0.4729 | 0.0303 |
| exclude_buffalo | forward_leave_city_out | M1 | 1191 | 0.4637 | 0.4509 | 0.0606 |
| exclude_buffalo | forward_leave_city_out | M2 | 1191 | 0.5541 | 0.3415 | 0.0848 |


## Calibration and fit diagnostics

| scheme | model | probabilities | average_precision | brier_score | ece_10bins | calibration_mean_error |
|---|---|---|---|---|---|---|
| forward_spatial | M0 | raw | 0.7195 | 0.2112 | 0.0488 | 0.0360 |
| forward_spatial | M0 | sigmoid | 0.7169 | 0.2119 | 0.0563 | 0.0321 |
| forward_spatial | M1 | raw | 0.7071 | 0.2170 | 0.0639 | 0.0563 |
| forward_spatial | M1 | sigmoid | 0.7054 | 0.2153 | 0.0415 | 0.0215 |
| forward_spatial | M2 | raw | 0.7001 | 0.2247 | 0.0356 | -0.0081 |
| forward_spatial | M2 | sigmoid | 0.6820 | 0.2311 | 0.0192 | -0.0057 |
| forward_leave_city_out | M0 | raw | 0.4077 | 0.4410 | 0.4262 | -0.3793 |
| forward_leave_city_out | M0 | sigmoid | 0.4097 | 0.3694 | 0.3526 | -0.3066 |
| forward_leave_city_out | M1 | raw | 0.5177 | 0.4182 | 0.3767 | -0.3568 |
| forward_leave_city_out | M1 | sigmoid | 0.5007 | 0.3394 | 0.2917 | -0.2719 |
| forward_leave_city_out | M2 | raw | 0.4746 | 0.3473 | 0.3181 | -0.2725 |
| forward_leave_city_out | M2 | sigmoid | 0.4740 | 0.3114 | 0.2523 | -0.2295 |


There are 0 outer model fits with fewer than two valid inner folds and 0 without an applied sigmoid calibrator. The warning audit has 21 rows, including skipped-fold notices and any estimator warnings; these are retained for review. Figure files summarize pooled primary ranking and calibration. Raw probabilities remain the primary result regardless of secondary calibration performance.

Independent research acceptance remains pending. Neither a numerical gain nor automated PASS makes these previously inspected retrospective results confirmatory. See the methods for source, exposure, coordinate and sample-imbalance limitations.
