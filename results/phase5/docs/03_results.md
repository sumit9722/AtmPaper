# Results and interpretation

## Pooled-source versus local-full

| city | source | model | local AP | source AP | transfer gap |
| --- | --- | --- | --- | --- | --- |
| New York City | pooled | M0 | 0.7238 | 0.4277 | 0.2961 |
| New York City | pooled | M1 | 0.7515 | 0.5129 | 0.2386 |
| New York City | pooled | M2 | 0.6940 | 0.5248 | 0.1692 |
| Buffalo | pooled | M0 | 0.3529 | 0.3307 | 0.0223 |
| Buffalo | pooled | M1 | 0.3350 | 0.3741 | -0.0391 |
| Buffalo | pooled | M2 | 0.3180 | 0.4620 | -0.1440 |
| Rochester | pooled | M0 | 0.3513 | 0.2193 | 0.1320 |
| Rochester | pooled | M1 | 0.3168 | 0.2460 | 0.0709 |
| Rochester | pooled | M2 | 0.2152 | 0.2988 | -0.0836 |


A negative transfer gap means pooled sources outperform this local-full model on the shared test data; local-full is a benchmark, not a mathematical upper bound. Compare each model and city separately. The full table also reports both individual source cities.

## Does source data help with limited local labels?

| city | fraction | model | mean benefit | SD | negative seeds |
| --- | --- | --- | --- | --- | --- |
| New York City | 0.1 | M0 | 0.0076 | 0.0098 | 2 |
| New York City | 0.1 | M1 | -0.0243 | 0.0178 | 20 |
| New York City | 0.1 | M2 | -0.0018 | 0.0155 | 9 |
| New York City | 0.25 | M0 | 0.0061 | 0.0023 | 0 |
| New York City | 0.25 | M1 | 0.0010 | 0.0191 | 10 |
| New York City | 0.25 | M2 | 0.0109 | 0.0107 | 1 |
| Buffalo | 0.1 | M0 | -0.0004 | 0.0422 | 12 |
| Buffalo | 0.1 | M1 | 0.0341 | 0.0711 | 3 |
| Buffalo | 0.1 | M2 | 0.0785 | 0.0467 | 0 |
| Buffalo | 0.25 | M0 | 0.0072 | 0.0492 | 10 |
| Buffalo | 0.25 | M1 | 0.0484 | 0.0816 | 4 |
| Buffalo | 0.25 | M2 | 0.0858 | 0.0462 | 0 |
| Rochester | 0.1 | M0 | -0.0396 | 0.0531 | 17 |
| Rochester | 0.1 | M1 | -0.0154 | 0.0860 | 8 |
| Rochester | 0.1 | M2 | 0.0720 | 0.0236 | 1 |
| Rochester | 0.25 | M0 | -0.0718 | 0.0546 | 19 |
| Rochester | 0.25 | M1 | -0.0955 | 0.1321 | 15 |
| Rochester | 0.25 | M2 | 0.0709 | 0.0382 | 2 |


Pooled-source M2 has positive mean matched benefits in Buffalo at 10% (+0.0785 AP) and 25% (+0.0858), with no negative seeds in either condition. Rochester M2 also improves on average (+0.0720 and +0.0709), while Rochester M0/M1 have negative mean benefits at both fractions. In New York City, M1 at 10% loses AP in all 20 seeds (mean -0.0243); M2 at 25% improves on average (+0.0109), with one negative seed. These mixed results do not support a universal transfer claim.

Positive matched benefit supports descriptive usefulness of source data for that condition; negative values show negative transfer. The complete 54-row summary includes individual-source results, empirical seed percentiles and positive/negative counts. Never interpret improvement over zero-shot alone as proof of useful transfer. With small local pools, ceil rounding means nominal fractions differ slightly from realized percentages, and single-class controls can be common.

There are 207 unique constant-prevalence fallback fits. Consult the fit/evaluation audits before interpreting gains over tiny target-only models. Calibration and AP can tell different stories; examine Brier and the calibration plots before considering probabilities useful. The phase 4 AP-gain gate failed, so these phase 5 results do not establish confirmatory transportability.

These are retrospective research results, not confirmed ATM-attack predictions or operational risk scores. The 2025 outcomes were inspected in the earlier phase 4 analysis, so 2025 is not a pristine confirmatory holdout. Training uses report-date-filtered latest extracts, not a database frozen at the historical cutoff. Buffalo uses record creation as a report-availability proxy. Monthly listings support inferred operation; they do not establish exact opening or closing dates. The 2024 address links and up-to-50-m coordinate revisions require independent review. Crime harmonization/linkage, facility identity, Buffalo coordinate precision, continuity, and feature acceptance remain research gates. No independent human sign-off is claimed. Small Buffalo/Rochester samples and limited positives make their estimates unstable. Current municipal boundaries and retrospective archive availability are additional limitations.
