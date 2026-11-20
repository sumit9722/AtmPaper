# Restart 7 Phase 4 results

**The primary exploratory numerical continuation rule FAILED. Stop expanding environmental models on these same outcomes. Report the negative or inconclusive result; do not replace the primary endpoint, cities, radius or feature set with a favorable sensitivity.**

## What was tested

The assessed release was ready for a limited retrospective benchmark: verified
files, a common two-variable crime-history baseline, 855 earlier-year training
rows and 935 later-year test rows, with usable spatially separated folds.
It was not certified as a physical ATM-risk dataset. All models below predict
the released-coordinate endpoint, with the original unresolved scientific gates.

Primary M0 is logistic regression on prior local and annular crime. M1 adds
the 19 frozen environmental predictors. Both use training-only imputation,
scaling and nested selection of regularization strength. B0/B1 are paired
secondary boosted-tree models using the same respective feature sets.
`prior_local_rank` is the direct crime-history ranking score; it has no valid
probability interpretation or Brier score. `training_prevalence` uses only each
outer training set's prevalence.

Training uses 2024; testing uses 2025. The five spatial test folds purge nearby
training sites within 1,500 m and shared site/component/ACS/EPA geography groups.
This evaluates spatial extrapolation as well as the year change. These outcome
years were previously inspected and cannot be described as a pristine holdout.

## Primary pooled performance

| model | n | prevalence | average_precision | roc_auc | brier_score | top_decile_precision |
| --- | --- | --- | --- | --- | --- | --- |
| B0 | 935 | 0.5016 | 0.7849 | 0.7871 | 0.1925 | 0.9362 |
| B1 | 935 | 0.5016 | 0.7737 | 0.7897 | 0.1911 | 0.9043 |
| M0 | 935 | 0.5016 | 0.8042 | 0.7936 | 0.1929 | 0.9468 |
| M1 | 935 | 0.5016 | 0.7954 | 0.7994 | 0.1884 | 0.9149 |
| prior_local_rank | 935 | 0.5016 | 0.7553 | 0.7678 |  | 0.9468 |
| training_prevalence | 935 | 0.5016 | 0.4754 | 0.4563 | 0.2554 | 0.4043 |

M1−M0 AP gain: **-0.0088**, conditional 2 km spatial
95% interval **[-0.0286, +0.0125]**.
The numerical rule requires an AP gain >=0.01, positive lower confidence bound,
and no worse Brier score. The threshold is an exploratory working convention,
not a demonstrated operational benefit.

## Cities and uncertainty

| city | model | n | positive | average_precision | roc_auc | brier_score |
| --- | --- | --- | --- | --- | --- | --- |
| New York City | M0 | 611 | 345 | 0.8195 | 0.7735 | 0.1920 |
| Chicago | M0 | 212 | 87 | 0.7650 | 0.7932 | 0.2059 |
| Los Angeles | M0 | 112 | 37 | 0.7852 | 0.8595 | 0.1729 |
| New York City | M1 | 611 | 345 | 0.8105 | 0.7722 | 0.1937 |
| Chicago | M1 | 212 | 87 | 0.7662 | 0.8040 | 0.1874 |
| Los Angeles | M1 | 112 | 37 | 0.7477 | 0.8486 | 0.1616 |
| New York City | prior_local_rank | 611 | 345 | 0.7725 | 0.7429 |  |
| Chicago | prior_local_rank | 212 | 87 | 0.7179 | 0.7862 |  |
| Los Angeles | prior_local_rank | 112 | 37 | 0.7578 | 0.8393 |  |

The test contains 611 NYC, 212 Chicago and 112 LA sites; LA has 37 positives.
Pooled results are influenced by NYC. Equal-city averages are saved separately
in [macro_metrics.csv](results/macro_metrics.csv). Small-city estimates should
be interpreted with their conditional intervals, not as independent large-sample
confirmations. Repeated object/geography structure and shared incidents limit
effective information.

Paired AP intervals resample 2 km test blocks within each city 2,000 times;
the primary pooled contrast also has a 5 km sensitivity. They condition on the
fitted predictions and do not cover refitting, measurement error or prior study
selection. Secondary intervals are descriptive and unadjusted.

## Prespecified sensitivities

| scenario | block_km | ap_difference | ci_low | ci_high | valid_resamples |
| --- | --- | --- | --- | --- | --- |
| core_100m | 2 | 0.0056 | -0.0053 | 0.0163 | 2000 |
| core_25m | 2 | 0.0185 | -0.0184 | 0.0603 | 2000 |
| core_50m | 2 | -0.0088 | -0.0286 | 0.0125 | 2000 |
| core_50m | 5 | -0.0088 | -0.0236 | 0.0060 | 2000 |
| explicit_atm_50m | 2 | -0.0467 | -0.0910 | -0.0038 | 2000 |
| master_50m | 2 | -0.0062 | -0.0259 | 0.0116 | 2000 |
| no_source_conflicts_50m | 2 | -0.0088 | -0.0287 | 0.0124 | 2000 |
| report_filtered_50m | 2 | -0.0359 | -0.0667 | -0.0024 | 2000 |

The 25/100 m scenarios change both outcome and prior-local radius. The full
master includes the inherited centroids/ambiguous objects; the explicit-ATM
subset removes point banks tagged with ATMs. The source-conflict sensitivity
omits flagged cases from outcomes and baseline. The NYC/LA report-filtered
sensitivity uses training reports before 2025 and prior-crime reports before
each prediction-year cutoff, while evaluating eventual recorded 2025 outcomes.
Chicago remains excluded from that information regime.

Skipped scenarios due to frozen feasibility rules: **none**.
All feasibility counts are in [feasibility.csv](results/feasibility.csv).

## Forward city-held-out check

| city | model | average_precision | roc_auc | brier_score |
| --- | --- | --- | --- | --- |
| ALL | M0 | 0.7980 | 0.7877 | 0.1908 |
| New York City | M0 | 0.8194 | 0.7793 | 0.1918 |
| Chicago | M0 | 0.7686 | 0.8003 | 0.1985 |
| Los Angeles | M0 | 0.7901 | 0.8470 | 0.1713 |
| ALL | M1 | 0.7076 | 0.7479 | 0.2306 |
| New York City | M1 | 0.7245 | 0.7032 | 0.2566 |
| Chicago | M1 | 0.7248 | 0.7983 | 0.1837 |
| Los Angeles | M1 | 0.7560 | 0.8468 | 0.1774 |

This uses the other two cities' earlier-year training data. It does not test
few-label local adaptation or establish that environmental effects transport.
Assess calibration and city-level performance together with AP. The complete
conditional difference table includes unfavorable comparisons.

## What to do next

If the environmental increment fails or is fragile, retain the strong crime
baseline and write the environmental result honestly as negative/inconclusive.
Do not search the expanded 107 predictors or repeatedly change cohorts to obtain
significance on these same years. An exploratory negative result can be useful.

For a stronger ATM-specific paper, prioritize independently reviewed site and
offense samples, defensible crime-location precision, and LA source comparability.
Seek actual machine/entrance locations where feasible. If accurate locations
cannot be obtained, define a street-block or neighborhood question supported by
the source resolution, and justify the spatial unit independently of performance.
A larger radius alone is not proof of positional validity.

To investigate environmental value, collect a small, theory-motivated set of
reliable site observations such as visibility, access conditions or security,
where feasible and appropriate. Such measurements may or may not improve
prediction. Evaluate a frozen specification on an uninspected period after the
measurement decisions are settled. No positive result is guaranteed.

## Artifacts and reproducibility

- [Frozen protocol](protocol.md)
- [All metrics](results/metrics.csv), [all paired differences](results/paired_differences.csv)
- [Calibration bins](results/calibration_bins.csv), [held-out predictions](results/predictions.csv)
- [Outer split membership](results/split_membership.csv), [inner membership](results/inner_membership.csv)
- [Tuning scores](results/inner_scores.csv), [fit inventory](results/model_fits.csv)
- [Validation](results/validation.json), [status](results/status.json)
- [Input hashes](results/input_manifest.csv), [output hashes](results/output_manifest.csv)

92 fitted models are saved and replayed exactly. Training-only
preprocessing, split separation, label alignment and complete test coverage are
checked. The separate phases 1–3 manifest remains unchanged. No new source data
were downloaded and no Phase 5 adaptation experiment was run.

Reproduce from the repository root using the existing environment:

```bash
.venv/bin/python -m unittest discover -s restart7_0/phase4 -p 'test_*.py' -v
.venv/bin/python restart7_0/phase4/run.py
```

Dependencies are in `phase4/requirements.txt`. The runner checks frozen input and
code hashes before fitting. A changed design requires a separately documented
revision. Original phase 1–3 scripts need not be rerun.
