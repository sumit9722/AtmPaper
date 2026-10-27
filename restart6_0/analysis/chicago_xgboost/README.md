# Chicago XGBoost: reproduction and transfer

This is a new exploratory analysis authorized by the user. It preserves the original Restart 6 releases. The original Phase 1–3 status files correctly describe those earlier releases and are not overwritten with the status of this extension.

Start with [the analysis plan](analysis_plan.md), then [the generated summary](../../results/chicago_xgboost/README.md) or [the detailed HTML report](../../results/chicago_xgboost/report.html).

## Run locally

From the repository root, using Python 3.13:

```bash
python3.13 -m venv .venv-chicago
.venv-chicago/bin/python -m pip install -r restart6_0/analysis/chicago_xgboost/requirements.txt
.venv-chicago/bin/python -m unittest discover -s restart6_0/analysis/chicago_xgboost -p 'test_*.py' -v
.venv-chicago/bin/python restart6_0/analysis/chicago_xgboost/pipeline.py run --threads 4 --bootstrap 1000
```

The current run used macOS ARM64 and CPU XGBoost. Linux CPU is supported. OpenMP is required (libomp on macOS, libgomp on Linux). No `shap` package is needed: native XGBoost `pred_contribs=True` provides exact TreeSHAP contributions and the pipeline verifies their additivity.

The default output is `restart6_0/results/chicago_xgboost/`. To preserve a run, use `--output restart6_0/results/chicago_xgboost_replication`. Replacing an existing analysis requires explicit `--overwrite`. Do not use a Phase 1–3 folder as an output directory.

The build downloads no research data and requires no API key. It reads only the small prepared main panel, Phase 3 raw context, expanded environment table, environment dictionary and schema, plus the three existing manifests that certify those inputs. The large split crime/link CSVs do not need restoration. Input column counts, IDs and recorded source hashes are verified.

The saved models use 2024 only. They are not refitted on 2025. Their JSON schemas freeze feature order, training exclusions, ranges and classification thresholds; model configurations and dependency versions are stored separately.

For independent post-build verification or presentation-only regeneration:

```bash
.venv-chicago/bin/python restart6_0/analysis/chicago_xgboost/validate_results.py
.venv-chicago/bin/python restart6_0/analysis/chicago_xgboost/render_report.py
```

The validator replays saved models, recomputes all 1,476 pairwise outcome correlations and checks every output checksum. The renderer preserves all model, prediction and statistical files. The delivered release retains the exact training script in `qa/training_pipeline.py.txt`; a subsequent presentation-only correction uses stepwise precision–recall curves and includes selected settings directly in the HTML. Its provenance is recorded in `qa/presentation_refresh.json`.

## GCP server

No GCP server was accessed or provisioned. For this dataset, a CPU machine with 4 vCPUs and about 8 GB RAM is a reasonable starting configuration; a GPU is unnecessary. Runtime and cost depend on your instance. Use your existing server rather than starting extra resources automatically.

Copy/checkout this repository, including this analysis and the prepared Restart 6 tables, to the server. Do not upload the local virtual environment or credentials. Install Python 3.13 and the OS OpenMP runtime if missing. From the repository root, run the same environment, dependency and test commands above. Then:

```bash
mkdir -p restart6_0/results/chicago_xgboost_gcp
nohup .venv-chicago/bin/python -u restart6_0/analysis/chicago_xgboost/pipeline.py run \
  --threads 4 --bootstrap 5000 \
  --output restart6_0/results/chicago_xgboost_gcp \
  > restart6_0/results/chicago_xgboost_gcp_run.log 2>&1 &
```

Use only as many threads as the instance provides. More bootstrap replicates refine Monte Carlo precision; they do not add observations or fix missing reporting dates. CPU/platform differences can produce small numerical variations; compare metrics and intervals, not byte-identical figures. Preserve the source hashes and frozen training/test policy when comparing replications. Shut down an otherwise unused instance through your normal GCP process after downloading results.

## Later prediction in NYC or LA

This command performs inference with the frozen Chicago model and exports a range/missingness drift audit. It does not inspect target-city outcomes for evaluation unless `--evaluate` is explicitly added.

```bash
.venv-chicago/bin/python restart6_0/analysis/chicago_xgboost/pipeline.py transfer \
  --city 'New York City' --year 2025 --radius 50 \
  --output restart6_0/results/chicago_transfer_nyc

.venv-chicago/bin/python restart6_0/analysis/chicago_xgboost/pipeline.py transfer \
  --city 'Los Angeles' --year 2025 --radius 50 \
  --output restart6_0/results/chicago_transfer_la
```

When ready for a separate target-city evaluation, add `--evaluate` and choose a new output directory. Predictions reuse the **unfiltered retrospective** prior-crime definitions used in Chicago, not the report-filtered alternatives. Do not silently change definitions between cities. The prepared inputs already contain the same environmental units/schema. This does not prove transportability; inspect drift, source comparability, target prevalence and calibration. Fields constant in Chicago remain excluded, even if they vary elsewhere. No city-transfer results are claimed in the Chicago report.

## Output guide

| Location | Contents |
| --- | --- |
| `README.md`, `report.html` | Plain-language summary and searchable detailed report, with all 123 candidate parameter sections |
| `data/` | Chicago prepared rows, dictionary, unavailable report-filtered fields, training OOF predictions and 2025 evaluation predictions |
| `statistics/distributions_all_parameters.csv` | Per-year missingness, means, SD, quantiles, skewness/kurtosis, zero counts and crime-positive/negative summaries |
| `statistics/associations_all_outcomes.csv` | Spearman/Pearson/Kendall statistics, spatial-bootstrap intervals, naive and cluster-aware tests and BH-adjusted values |
| `statistics/correlation_rankings.csv` | Separate yearly ranks for the 50 m crime indicator, rank intervals and top-10 bootstrap frequencies |
| `statistics/parameter_pairs.csv` | Pairwise parameter correlations and complete-case counts |
| `statistics/outcome_rates_by_training_quartile.csv` | Crime rates by bins defined from training data, with block-bootstrap intervals |
| `statistics/model_metrics.csv` | Model metrics for each radius, threshold and predefined subset |
| `statistics/model_metric_intervals.csv` | Spatial-bootstrap intervals with 1/2/4 km blocks |
| `statistics/paired_model_differences.csv` | Paired environmental increment comparisons, including uncertainty |
| `statistics/tuning_*.csv` | All configurations and fold results, not only the winner |
| `explanations/` | Exact local SHAP values, global importance/rank uncertainty, permutation results and seed variability |
| `figures/` | Performance/correlation/SHAP/missingness graphics, plus a three-panel plot for each candidate |
| `models/` | Nine primary-seed XGBoost models (three families × three radii), six additional 50 m seed models, schemas and exact configurations |
| `qa/` | Input manifest, spatial split memberships, distances/purges and fold/final feature exclusions |
| `validation.json`, `status.json`, `output_manifest.csv` | Validation, completion status and output checksums |

## Interpretation

The primary target combines nearby robbery and burglary; it does not label confirmed ATM attacks. The seven original report-filtered crime fields are unavailable in Chicago. The benchmark uses separately labeled retrospective occurrence counts, with a persistent historical reporting limitation. The model split prevents direct test-set information from entering fitting, but cannot repair late source revisions, historical cohort selection, prior study decisions, approximate geocodes or incomplete ATM mapping.

Correlation strength, predictive contribution and causal effect are different concepts. SHAP values are in log-odds; their absolute mean is an importance measure. Cluster bootstrap rank ranges expose rank instability. Individual permutation importance can underestimate shared information among correlated features. Values shown as missing or unrankable must not be read as zero association. Confidence intervals condition on the sample/model/grid; scientific review remains pending.
