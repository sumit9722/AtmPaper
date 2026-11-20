"""Generate a candid Phase 4 report directly from the complete result tables."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def table(rows, columns):
    def text(value):
        return f"{value:.4f}" if isinstance(value, float) else str(value)
    return "\n".join(["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"] +
                     ["| " + " | ".join(text(r[c]) for c in columns) + " |" for r in rows])


def generate(status, metrics, differences):
    selected = [r for r in metrics if r["scenario"] == "core_50m" and r["scheme"] == "forward_spatial" and r["city"] == "ALL"]
    city = [r for r in metrics if r["scenario"] == "core_50m" and r["scheme"] == "forward_spatial" and r["city"] != "ALL" and r["model"] in ("M0", "M1", "prior_local_rank")]
    loco = [r for r in metrics if r["scenario"] == "core_50m" and r["scheme"] == "forward_city_out" and r["model"] in ("M0", "M1")]
    gains = [r for r in differences if r["scheme"] == "forward_spatial" and r["city"] == "ALL" and r["comparison"] == "M1-M0"]
    decision = ("The primary exploratory numerical continuation rule PASSED. This supports an environmental increment for this recorded-coordinate benchmark, subject to the robustness results below. It does not resolve the measurement gates or authorize a general ATM-risk claim."
                if status["numerical_continuation_gate"] else
                "The primary exploratory numerical continuation rule FAILED. Stop expanding environmental models on these same outcomes. Report the negative or inconclusive result; do not replace the primary endpoint, cities, radius or feature set with a favorable sensitivity.")
    report = f"""# Restart 7 Phase 4 results

**{decision}**

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

{table(selected, ['model', 'n', 'prevalence', 'average_precision', 'roc_auc', 'brier_score', 'top_decile_precision'])}

M1−M0 AP gain: **{status['primary_ap_gain']:+.4f}**, conditional 2 km spatial
95% interval **[{status['primary_ap_gain_ci'][0]:+.4f}, {status['primary_ap_gain_ci'][1]:+.4f}]**.
The numerical rule requires an AP gain >=0.01, positive lower confidence bound,
and no worse Brier score. The threshold is an exploratory working convention,
not a demonstrated operational benefit.

## Cities and uncertainty

{table(city, ['city', 'model', 'n', 'positive', 'average_precision', 'roc_auc', 'brier_score'])}

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

{table(gains, ['scenario', 'block_km', 'ap_difference', 'ci_low', 'ci_high', 'valid_resamples'])}

The 25/100 m scenarios change both outcome and prior-local radius. The full
master includes the inherited centroids/ambiguous objects; the explicit-ATM
subset removes point banks tagged with ATMs. The source-conflict sensitivity
omits flagged cases from outcomes and baseline. The NYC/LA report-filtered
sensitivity uses training reports before 2025 and prior-crime reports before
each prediction-year cutoff, while evaluating eventual recorded 2025 outcomes.
Chicago remains excluded from that information regime.

Skipped scenarios due to frozen feasibility rules: **{', '.join(status['skipped_scenarios']) or 'none'}**.
All feasibility counts are in [feasibility.csv](results/feasibility.csv).

## Forward city-held-out check

{table(loco, ['city', 'model', 'average_precision', 'roc_auc', 'brier_score'])}

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

{status['models_fitted']} fitted models are saved and replayed exactly. Training-only
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
"""
    (ROOT / "README.md").write_text(report)
