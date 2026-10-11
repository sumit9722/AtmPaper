# Results

| model | average_precision | roc_auc | brier_score |
| --- | --- | --- | --- |
| M0 | 0.7189 | 0.7222 | 0.2115 |
| M1 | 0.7440 | 0.7180 | 0.2122 |
| M2 | 0.6899 | 0.6899 | 0.2212 |


| comparison | AP difference | 95% lower | 95% upper |
| --- | --- | --- | --- |
| M1-M0 | 0.0251 | -0.0154 | 0.0540 |
| M2-M0 | -0.0290 | -0.0845 | 0.0127 |


M1's pooled AP improvement is uncertain; M2's pooled point estimate is below M0. Every pooled and city-specific AP-difference interval includes zero. The working numerical gate therefore fails everywhere. The results do not establish reliable added predictive value from the environmental feature set. This negative finding is retained; phase 5 is a descriptive transfer study, not evidence that the phase 4 scientific gate passed.

The 2025 cohort has 650 positives among 1,192 sites (prevalence 54.53%); pooled metrics are dominated by New York City. Buffalo has 14/46 positives and Rochester 7/29. All city-specific, native and sigmoid-calibrated metrics are in `data/metrics.csv`. Rochester has 1,999 valid bootstrap replicates; the other strata have 2,000.

These are retrospective research results, not confirmed ATM-attack predictions or operational risk scores. The 2025 outcomes were inspected in the earlier phase 4 analysis, so 2025 is not a pristine confirmatory holdout. Training uses report-date-filtered latest extracts, not a database frozen at the historical cutoff. Buffalo uses record creation as a report-availability proxy. Monthly listings support inferred operation; they do not establish exact opening or closing dates. The 2024 address links and up-to-50-m coordinate revisions require independent review. Crime harmonization/linkage, facility identity, Buffalo coordinate precision, continuity, and feature acceptance remain research gates. No independent human sign-off is claimed. Small Buffalo/Rochester samples and limited positives make their estimates unstable. Current municipal boundaries and retrospective archive availability are additional limitations.
