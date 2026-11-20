# Restart 8 — ATM-specific attribute search

**Result: one site attribute passed every pre-declared criterion.** The amount
of deposits held by the FDIC bank branch co-located with the ATM (within 50 m)
predicts crime that police code as happening *at an ATM*. It does so beyond the
Restart 7 crime-history baseline, out of sample (2024 → 2025, spatially purged),
in both NYC and Chicago, and it replicates in a third year (2023). It does
**not** predict the R7 robbery/burglary-within-50 m endpoint. In other words,
it is specific to ATM crime, not a proxy for a high-crime block.

Exploratory. Candidates and acceptance rules were frozen in
[protocol.md](protocol.md) before outcome linkage; all robustness checks below
were run afterwards and are labelled post hoc.

## What was tested

Eight site-level ATM attributes (not neighbourhood census context) were each
added to the R7 baseline **M0 = log1p(prior-year crime ≤50 m) + log1p(prior-year
crime 200–500 m)**. Every candidate was measured before the outcome year: OSM
tags from the preceding December snapshot, and FDIC Summary of Deposits from the
preceding June. The R7 Phase 4 code was imported unchanged: the same 2 km hash
folds, the 1,500 m and geography-group purge, nested C, training-only
preprocessing, and the 2 km within-city block bootstrap.

Two outcomes:

* **Primary R7 endpoint:** any robbery or structural burglary within 50 m (core cohort,
  3 cities, 935 test site-years, prevalence 50%).
* **ATM-premise crime (new, Restart 8 raw pull):** any incident whose police
  *premise code is ATM*, any offence, within 100 m. NYC and Chicago only, with 823
  test site-years and 137 positives. LA was excluded before modelling because its 2025
  NIBRS file releases coordinates rounded to 0.01° (~1 km).

## Frozen candidates (test year 2025, gain vs M0)

| id | attribute | primary AP gain [95% CI] | ATM-premise AP gain [95% CI] | train Holm p | accept |
|----|-----------|------|------|------|------|
| C1 | standalone ATM (OSM amenity=atm) | −0.001 [−0.005, +0.003] | +0.027 [−0.032, +0.063] | 0.149 | no |
| C2 | drive-through | −0.012 [−0.024, −0.001] | +0.001 [−0.037, +0.011] | 0.535 | no |
| C3 | open 24/7 | −0.015 [−0.027, −0.003] | +0.010 [−0.044, +0.032] | 0.946 | no |
| **C4** | **log deposits of FDIC branch ≤50 m** | +0.004 [−0.001, +0.010] | **+0.038 [+0.009, +0.069]** | **0.010** | **yes** |
| **C5** | **FDIC branch ≤50 m (yes/no)** | −0.004 [−0.016, +0.011] | **+0.027 [+0.013, +0.054]** | **0.014** | **yes** |
| C6 | megabank brand | −0.005 [−0.020, +0.011] | +0.042 [−0.023, +0.105] | 0.031 | no (CI) |
| C7 | ATM density 500 m | −0.020 [−0.035, −0.005] | −0.000 [−0.004, +0.005] | 0.434 | no |
| C8 | branch age | −0.011 [−0.023, −0.000] | +0.017 [−0.008, +0.037] | 0.083 | no |

For ATM-premise crime, M0 alone is weak (AP 0.188, ROC-AUC 0.577). Adding C4
gives AP 0.226, ROC-AUC 0.660 and Brier 0.1399 → 0.1379, with a positive gain in both
cities (NYC +0.029, Chicago +0.045). C5 is a coarser version of C4. Full
tables: [results_frozen.csv](results_frozen.csv),
[by city](results_frozen_by_city.csv).

## Dose-response (NYC + Chicago, 2024–2025)

| deposits at co-located branch | site-years | ATM-premise crime | robbery/burglary ≤50 m |
|---|---|---|---|
| no FDIC branch within 50 m | 569 | 7.9% | 47.6% |
| Q1 (median $35 M) | 201 | 11.9% | 62.7% |
| Q2 ($89 M) | 200 | 13.0% | 56.5% |
| Q3 ($171 M) | 201 | 19.9% | 62.2% |
| Q4 ($312 M) | 199 | 25.6% | 65.3% |
| Q5 ($696 M) | 200 | **35.0%** | 64.0% |

ATM-premise crime rises monotonically, 4.4× from the bottom to the top deposit
quintile. General nearby crime is flat across quintiles. Prior local crime is
also flat, at 0.64–0.86 on the log scale. [dose_response.csv](dose_response.csv)

## Adjusted odds ratio per SD of log deposits (cluster-robust, 2 km blocks)

| year | scope | adjusted for | OR [95% CI] |
|---|---|---|---|
| 2023 (separate partial cohort) | NYC+Chi | baseline | 1.74 [1.39, 2.19] |
| 2023 | NYC+Chi | baseline + prior ATM-premise crime | 1.66 [1.31, 2.10] |
| 2024 | NYC+Chi | baseline | 1.52 [1.18, 1.97] |
| 2025 | NYC+Chi | baseline | 1.97 [1.55, 2.51] |
| 2024 / 2025 | NYC | baseline | 1.49 / 1.97 |
| 2024 / 2025 | Chicago | baseline | 1.60 [0.97, 2.64] / 2.03 [1.18, 3.50] |
| 2024 / 2025 | NYC+Chi | baseline + prior ATM-premise crime | 1.36 / 1.87 |

[effect_sizes.csv](effect_sizes.csv), [replicate_2023.py](replicate_2023.py)

## Stress tests (post hoc; out-of-sample AP gain of C4, 2025)

| check | AP gain [95% CI] |
|---|---|
| baseline + prior-year ATM-premise crime | +0.037 [−0.019, +0.102] (ROC-AUC 0.662 → 0.713) |
| baseline + all 19 R7 environmental predictors | +0.027 [+0.007, +0.053] |
| baseline + prior ATM-premise crime + 19 environmental | +0.026 [+0.005, +0.054] |
| among branch-co-located sites only (amount, not presence) | +0.033 [+0.012, +0.057] |
| deposits on top of branch presence (C5) | +0.022 [−0.010, +0.039] |
| theft / robbery / other ATM crime only (fraud removed) | +0.025 [+0.008, +0.056] |
| ATM-premise outcome at 50 m instead of 100 m | +0.045 [+0.024, +0.085] |
| deposits winsorised at 95th pct (HQ booking) | +0.037 [+0.009, +0.067] |
| NYC only | +0.024 [+0.003, +0.048] |
| **falsification:** primary robbery/burglary outcome | −0.019 [−0.037, −0.001] |

Fraud-only and Chicago-only models were infeasible under the R7 minimum-class
rules. [robustness.csv](robustness.csv)

## Interpretation

Branch deposits measure how many people use the site and how much cash passes
through it. That is the "suitable target" term in routine-activity theory, and it
is ATM-specific: it does not track general neighbourhood crime. This is the
first attribute in Restarts 4–8 that adds information beyond the crime-history
baseline and also passes a falsification test.

## Limits

* Exploratory. The 2024/2025 years were inspected before. 2023 is a
  separate cohort, but many of its sites recur in 2024–2025.
* Premise coding is an officer's choice. Incidents at ATMs inside bank branches
  may be coded "ATM" more consistently than incidents at ATMs in shops, so part of
  the branch-presence (C5) effect may be ascertainment. The within-branch dose-response
  (R3b) is less exposed to this.
* Deposits proxy for footfall; they are not a measured transaction count and not a causal
  lever. HQ-booked deposits inflate a few branches (the winsorised check is unchanged).
* With prior-year ATM-premise crime in the baseline, the point gain is unchanged
  but the interval widens to include 0. The odds ratio stays significant in 2023, 2025
  and pooled 2024.
* LA cannot be evaluated (coordinate rounding). ATM-premise events are sparse
  (137 test positives), and the inherited R6/R7 location-precision gates still apply.

## Reproduce

```bash
PY=<python with pandas numpy scipy scikit-learn statsmodels pyproj pyarrow joblib threadpoolctl>
$PY -I restart8_0/attribute_search/build_attributes.py   # attributes.csv
$PY -I restart8_0/attribute_search/evaluate.py           # frozen C1–C8 test
$PY -I restart8_0/attribute_search/robustness.py         # post hoc stress tests + dose-response
$PY -I restart8_0/attribute_search/effect_sizes.py
$PY -I restart8_0/attribute_search/replicate_2023.py
```

Inputs are read-only: R7 phase-3 matrices, R6 OSM snapshots and R8 raw pulls. No
new downloads were made and no earlier release was modified.
