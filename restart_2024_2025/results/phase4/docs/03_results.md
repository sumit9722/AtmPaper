# Phase 4 results

**Computational status: validated PASS.** The run trained on the 1,201-site 2024 cohort and tested the 1,241-site 2025 cohort with spatial purging. It produced **141 outer model artifacts** and **44,376 held-out prediction rows** across six variants and two schemes. Each eligible 2025 row is predicted exactly once per model/variant/scheme. No phase 5 experiments were run.

## Primary pooled native-probability performance

| scheme | model | n | positives | average_precision | roc_auc | brier_score | ece_10bins | top_decile_recall |
|---|---|---|---|---|---|---|---|---|
| forward_spatial | M0 | 1241 | 674 | 0.7195 | 0.7242 | 0.2112 | 0.0488 | 0.1424 |
| forward_spatial | M1 | 1241 | 674 | 0.7414 | 0.7169 | 0.2128 | 0.0138 | 0.1499 |
| forward_spatial | M2 | 1241 | 674 | 0.6886 | 0.6911 | 0.2210 | 0.0586 | 0.1395 |
| forward_leave_city_out | M0 | 1241 | 674 | 0.4077 | 0.2697 | 0.4410 | 0.4262 | 0.0341 |
| forward_leave_city_out | M1 | 1241 | 674 | 0.4929 | 0.3893 | 0.5074 | 0.4880 | 0.0890 |
| forward_leave_city_out | M2 | 1241 | 674 | 0.5095 | 0.4541 | 0.3546 | 0.3057 | 0.0786 |


## Primary paired environmental improvement

M1-M0: AP difference +0.0219, 95% interval [-0.0176, +0.0499], numerical gate not passed; M2-M0: AP difference -0.0309, 95% interval [-0.0838, +0.0131], numerical gate not passed.

Neither environmental model met the primary pooled numerical improvement criterion. This evaluation does not demonstrate reliable incremental improvement; it does not prove that environmental effects are absent.

In the primary spatial evaluation, M1's Brier score is 0.2128, versus 0.2112 for M0 (lower is better). Its ranking gain therefore does not establish better probability accuracy. In the pooled city-held-out evaluation, the native Brier scores are 0.4410, 0.5074 and 0.3546 for M0/M1/M2. Those larger ranking gains coexist with poor probability accuracy and severe source/target sample imbalance; they do not rescue the primary spatial gate or establish calibrated transfer.

| scheme | city | comparison | ap_difference | ci_low | ci_high | valid_replicates | exploratory_numerical_gate |
|---|---|---|---|---|---|---|---|
| forward_spatial | ALL | M1-M0 | 0.0219 | -0.0176 | 0.0499 | 2000 | False |
| forward_spatial | ALL | M2-M0 | -0.0309 | -0.0838 | 0.0131 | 2000 | False |
| forward_spatial | New York City | M1-M0 | 0.0253 | -0.0157 | 0.0538 | 2000 | False |
| forward_spatial | New York City | M2-M0 | -0.0330 | -0.0863 | 0.0105 | 2000 | False |
| forward_spatial | Buffalo | M1-M0 | 0.0481 | -0.0206 | 0.2026 | 2000 | False |
| forward_spatial | Buffalo | M2-M0 | 0.0425 | -0.0507 | 0.2523 | 2000 | False |
| forward_spatial | Rochester | M1-M0 | 0.1146 | -0.1108 | 0.3173 | 2000 | False |
| forward_spatial | Rochester | M2-M0 | 0.0846 | -0.1088 | 0.3060 | 2000 | False |
| forward_leave_city_out | ALL | M1-M0 | 0.0852 | 0.0600 | 0.1119 | 2000 | True |
| forward_leave_city_out | ALL | M2-M0 | 0.1018 | 0.0770 | 0.1249 | 2000 | True |
| forward_leave_city_out | New York City | M1-M0 | 0.1031 | 0.0753 | 0.1334 | 2000 | True |
| forward_leave_city_out | New York City | M2-M0 | 0.1062 | 0.0817 | 0.1298 | 2000 | True |
| forward_leave_city_out | Buffalo | M1-M0 | 0.0197 | -0.0234 | 0.0966 | 2000 | False |
| forward_leave_city_out | Buffalo | M2-M0 | 0.0458 | -0.0440 | 0.2656 | 2000 | False |
| forward_leave_city_out | Rochester | M1-M0 | 0.0217 | -0.1069 | 0.1372 | 2000 | False |
| forward_leave_city_out | Rochester | M2-M0 | 0.0857 | -0.1078 | 0.2299 | 2000 | False |


## Primary results by city

| scheme | city | model | n | positives | average_precision | roc_auc | brier_score | top_decile_recall |
|---|---|---|---|---|---|---|---|---|
| forward_spatial | New York City | M0 | 1160 | 652 | 0.7264 | 0.7199 | 0.2095 | 0.1350 |
| forward_spatial | New York City | M1 | 1160 | 652 | 0.7517 | 0.7161 | 0.2106 | 0.1442 |
| forward_spatial | New York City | M2 | 1160 | 652 | 0.6934 | 0.6801 | 0.2208 | 0.1319 |
| forward_spatial | Buffalo | M0 | 50 | 14 | 0.2996 | 0.5139 | 0.2261 | 0.0714 |
| forward_spatial | Buffalo | M1 | 50 | 14 | 0.3476 | 0.6062 | 0.2132 | 0.0714 |
| forward_spatial | Buffalo | M2 | 50 | 14 | 0.3420 | 0.5218 | 0.2155 | 0.1429 |
| forward_spatial | Rochester | M0 | 31 | 8 | 0.2221 | 0.3342 | 0.2494 | 0.0000 |
| forward_spatial | Rochester | M1 | 31 | 8 | 0.3367 | 0.2880 | 0.2949 | 0.2500 |
| forward_spatial | Rochester | M2 | 31 | 8 | 0.3067 | 0.2880 | 0.2372 | 0.1250 |
| forward_leave_city_out | New York City | M0 | 1160 | 652 | 0.4257 | 0.2764 | 0.4557 | 0.0337 |
| forward_leave_city_out | New York City | M1 | 1160 | 652 | 0.5288 | 0.4070 | 0.5260 | 0.1104 |
| forward_leave_city_out | New York City | M2 | 1160 | 652 | 0.5319 | 0.4626 | 0.3645 | 0.0782 |
| forward_leave_city_out | Buffalo | M0 | 50 | 14 | 0.2938 | 0.5089 | 0.2213 | 0.0714 |
| forward_leave_city_out | Buffalo | M1 | 50 | 14 | 0.3135 | 0.5556 | 0.2106 | 0.0714 |
| forward_leave_city_out | Buffalo | M2 | 50 | 14 | 0.3396 | 0.5546 | 0.2089 | 0.1429 |
| forward_leave_city_out | Rochester | M0 | 31 | 8 | 0.2210 | 0.3397 | 0.2455 | 0.0000 |
| forward_leave_city_out | Rochester | M1 | 31 | 8 | 0.2427 | 0.2826 | 0.2920 | 0.1250 |
| forward_leave_city_out | Rochester | M2 | 31 | 8 | 0.3068 | 0.3098 | 0.2205 | 0.1250 |


## Sensitivity results

These analyses retain the same split assignments and do not replace the primary result. All test labels are 2025 outcomes; training labels remain report-filtered 2024 outcomes. The unfiltered-background variant changes only background predictors. Full native and sigmoid metrics, including all city-specific sensitivities, are in `data/metrics.csv`.

| variant | scheme | model | n | average_precision | brier_score | top_decile_recall |
|---|---|---|---|---|---|---|
| radius_25m | forward_spatial | M0 | 1241 | 0.5284 | 0.2088 | 0.1714 |
| radius_25m | forward_spatial | M1 | 1241 | 0.4642 | 0.2320 | 0.1549 |
| radius_25m | forward_spatial | M2 | 1241 | 0.4585 | 0.2251 | 0.1690 |
| radius_25m | forward_leave_city_out | M0 | 1241 | 0.5053 | 0.2517 | 0.1667 |
| radius_25m | forward_leave_city_out | M1 | 1241 | 0.4254 | 0.4436 | 0.1479 |
| radius_25m | forward_leave_city_out | M2 | 1241 | 0.3511 | 0.2795 | 0.0775 |
| radius_100m | forward_spatial | M0 | 1241 | 0.9489 | 0.1172 | 0.1207 |
| radius_100m | forward_spatial | M1 | 1241 | 0.9344 | 0.1241 | 0.1217 |
| radius_100m | forward_spatial | M2 | 1241 | 0.9366 | 0.1286 | 0.1187 |
| radius_100m | forward_leave_city_out | M0 | 1241 | 0.9317 | 0.1337 | 0.1158 |
| radius_100m | forward_leave_city_out | M1 | 1241 | 0.8162 | 0.2709 | 0.1030 |
| radius_100m | forward_leave_city_out | M2 | 1241 | 0.8021 | 0.1830 | 0.0824 |
| nearest_only_50m | forward_spatial | M0 | 1241 | 0.6456 | 0.2211 | 0.1445 |
| nearest_only_50m | forward_spatial | M1 | 1241 | 0.6546 | 0.2250 | 0.1495 |
| nearest_only_50m | forward_spatial | M2 | 1241 | 0.6380 | 0.2262 | 0.1495 |
| nearest_only_50m | forward_leave_city_out | M0 | 1241 | 0.3651 | 0.3964 | 0.0365 |
| nearest_only_50m | forward_leave_city_out | M1 | 1241 | 0.4416 | 0.4576 | 0.0930 |
| nearest_only_50m | forward_leave_city_out | M2 | 1241 | 0.4634 | 0.3223 | 0.0847 |
| unfiltered_background | forward_spatial | M0 | 1241 | 0.7194 | 0.2107 | 0.1424 |
| unfiltered_background | forward_spatial | M1 | 1241 | 0.7476 | 0.2098 | 0.1499 |
| unfiltered_background | forward_spatial | M2 | 1241 | 0.6824 | 0.2195 | 0.1306 |
| unfiltered_background | forward_leave_city_out | M0 | 1241 | 0.4110 | 0.3537 | 0.0326 |
| unfiltered_background | forward_leave_city_out | M1 | 1241 | 0.4836 | 0.5208 | 0.0801 |
| unfiltered_background | forward_leave_city_out | M2 | 1241 | 0.5145 | 0.3506 | 0.0816 |
| exclude_buffalo | forward_spatial | M0 | 1191 | 0.7237 | 0.2105 | 0.1379 |
| exclude_buffalo | forward_spatial | M1 | 1191 | 0.7472 | 0.2115 | 0.1485 |
| exclude_buffalo | forward_spatial | M2 | 1191 | 0.6871 | 0.2219 | 0.1303 |
| exclude_buffalo | forward_leave_city_out | M0 | 1191 | 0.4163 | 0.4729 | 0.0303 |
| exclude_buffalo | forward_leave_city_out | M1 | 1191 | 0.4971 | 0.5194 | 0.0773 |
| exclude_buffalo | forward_leave_city_out | M2 | 1191 | 0.5567 | 0.3408 | 0.0848 |


## Calibration and fit diagnostics

| scheme | model | probabilities | average_precision | brier_score | ece_10bins | calibration_mean_error |
|---|---|---|---|---|---|---|
| forward_spatial | M0 | raw | 0.7195 | 0.2112 | 0.0488 | 0.0360 |
| forward_spatial | M0 | sigmoid | 0.7169 | 0.2119 | 0.0563 | 0.0321 |
| forward_spatial | M1 | raw | 0.7414 | 0.2128 | 0.0138 | 0.0055 |
| forward_spatial | M1 | sigmoid | 0.7313 | 0.2175 | 0.0234 | -0.0010 |
| forward_spatial | M2 | raw | 0.6886 | 0.2210 | 0.0586 | 0.0442 |
| forward_spatial | M2 | sigmoid | 0.6680 | 0.2246 | 0.0531 | 0.0134 |
| forward_leave_city_out | M0 | raw | 0.4077 | 0.4410 | 0.4262 | -0.3793 |
| forward_leave_city_out | M0 | sigmoid | 0.4097 | 0.3694 | 0.3526 | -0.3066 |
| forward_leave_city_out | M1 | raw | 0.4929 | 0.5074 | 0.4880 | -0.4754 |
| forward_leave_city_out | M1 | sigmoid | 0.4836 | 0.3330 | 0.2893 | -0.2735 |
| forward_leave_city_out | M2 | raw | 0.5095 | 0.3546 | 0.3057 | -0.2907 |
| forward_leave_city_out | M2 | sigmoid | 0.5053 | 0.3505 | 0.2983 | -0.2926 |


There are 0 outer model fits with fewer than two valid inner folds and 0 without an applied sigmoid calibrator. The warning audit has 21 rows, including skipped-fold notices and any estimator warnings; these are retained for review. Figure files summarize pooled primary ranking and calibration. Raw probabilities remain the primary result regardless of secondary calibration performance.

Independent research acceptance remains pending. Neither a numerical gain nor automated PASS makes these previously inspected retrospective results confirmatory. See the methods for source, exposure, coordinate and sample-imbalance limitations.
