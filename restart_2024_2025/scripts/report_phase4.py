"""Produce step-by-step phase 4 documentation, plots and release checksums."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/atm_restart_p4_matplotlib')
import csv,hashlib,json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/phase4'
def read(name):
    with (OUT/name).open() as f:return list(csv.DictReader(f))
def table(rows,fields):
    return '| '+' | '.join(fields)+' |\n|'+'|'.join('---' for _ in fields)+'|\n'+''.join('| '+' | '.join(str(r.get(k,'')) for k in fields)+' |\n' for r in rows)
def rounded(rows,fields):
    return [{k:(f'{float(r[k]):.4f}' if k in fields and r[k]!='' else r[k]) for k in r} for r in rows]
def main():
    validation=json.loads((OUT/'qa/validation.json').read_text());assert validation['status']=='PASS'
    status=json.loads((OUT/'qa/phase4_status.json').read_text());metrics=read('data/metrics.csv');comparisons=read('data/paired_ap_comparisons.csv');fits=read('qa/model_fit_audit.csv');warnings=read('qa/fit_warnings.csv')
    primary=[r for r in metrics if r['variant']=='primary_50m' and r['probabilities']=='raw']
    pooled=[r for r in primary if r['city']=='ALL'];gate=[r for r in comparisons if r['scheme']=='forward_spatial' and r['city']=='ALL']
    gate_text='; '.join(f"{r['comparison']}: AP difference {float(r['ap_difference']):+.4f}, 95% interval [{float(r['ci_low']):+.4f}, {float(r['ci_high']):+.4f}], numerical gate {'passed' if r['exploratory_numerical_gate']=='True' else 'not passed'}" for r in gate)
    spatial={r['model']:r for r in pooled if r['scheme']=='forward_spatial'}
    city_metrics={r['model']:r for r in pooled if r['scheme']=='forward_leave_city_out'}
    interpretation=(f"In the primary spatial evaluation, M1's Brier score is {float(spatial['M1']['brier_score']):.4f}, versus {float(spatial['M0']['brier_score']):.4f} for M0 (lower is better). Its ranking gain therefore does not establish better probability accuracy. In the pooled city-held-out evaluation, the native Brier scores are {float(city_metrics['M0']['brier_score']):.4f}, {float(city_metrics['M1']['brier_score']):.4f} and {float(city_metrics['M2']['brier_score']):.4f} for M0/M1/M2. Those larger ranking gains coexist with poor probability accuracy and severe source/target sample imbalance; they do not rescue the primary spatial gate or establish calibrated transfer.")
    passing=[r['comparison'] for r in gate if r['exploratory_numerical_gate']=='True']
    conclusion=('The primary pooled numerical improvement criterion was met by '+', '.join(passing)+'. This is a retrospective exploratory result, not scientific approval or proof of transportability.') if passing else 'Neither environmental model met the primary pooled numerical improvement criterion. This evaluation does not demonstrate reliable incremental improvement; it does not prove that environmental effects are absent.'
    fallbacks=sum(int(r['valid_inner_folds'])<2 for r in fits);calibration_fail=sum(not json.loads(r['calibration'])['applied'] for r in fits)
    docs={
    '01_step_by_step.md':f'''# Phase 4: complete step-by-step procedure

This release runs the 2024–2025 restart's retrospective predictive comparisons. Computational status: **PASS** after validation. Independent scientific acceptance remains pending.

1. **Verify prerequisites.** Use the phase 2 combined panel (1,201 rows in 2024, 1,241 in 2025) and phase 3's validated 14-column allowlist. Verify every phase 3 release hash. Keep all eligible rows, including the 49 site-years lacking unique EPA assignments.
2. **Freeze the analysis.** Record `protocol/phase4_analysis_spec.md`, its SHA-256 and the experiment registry before fitting. Predefine M0/M1/M2, candidate grids, metrics, five sensitivities and the AP improvement rule. Prior inspection of both years is explicitly recorded.
3. **Construct labels.** For 2024 training, use radius-specific occurrences with a report timestamp before January 1, 2025. For nearest-site training, use phase 2 links with nearest-cohort-site and report-cutoff flags. For 2025 testing, use archived annual occurrences. Preserve unfiltered labels and label-vintage metadata. Buffalo creation timestamps are only proxies.
4. **Assemble predictors.** Join by row_id. Use log1p prior-year report-filtered annulus crime for M0, and the same baseline plus 13 environmental predictors for M1/M2. No city, coordinates, identifiers, exposure days, outcomes or later-year membership flags enter a model. Coordinates are used only for split construction and distance purging.
5. **Freeze spatial assignments.** Independently for each year and city, project to its UTM zone, make 2 km blocks and cluster their centers into five site-count-weighted KMeans groups. Seed 20261001, n_init=20. Assign canonical group labels. Freeze the cohort and split files before fitting.
6. **Create outer tests.** Primary: each 2025 group is tested once, training on eligible 2024 rows. Secondary: hold out each 2025 city and train on other cities' 2024 rows. In both cases remove training centers within 1,500 m of test centers, providing at least 500 m between 500 m-radius contexts. Do not reuse held-out-neighborhood 2024 labels.
7. **Create inner splits.** Within each outer 2024 training set, validate on each preassigned 2024 group and purge inner training by the same 1,500 m rule. Require ten training rows and both classes in training/validation. Log skipped splits; fewer than two usable inner folds triggers the fixed first candidate and no sigmoid calibration.
8. **Fit preprocessing and tune models.** Every inner fit learns its own median imputer; all-missing training columns get a recorded zero fallback. Logistic models also learn a training-only StandardScaler. Fit M0 unpenalized logistic; tune M1's C over 0.1, 1, 10; tune M2 depth/lambda over (2,10), (2,1), (3,10), (3,1). Select mean inner average precision, retaining the first candidate on ties. Refit on outer training only.
9. **Calibrate without test labels.** As a separate diagnostic, fit a nonnegative-slope sigmoid to the selected candidate's inner out-of-fold logits/labels. Preserve native and calibrated probabilities; do not choose between them from test results. Primary comparisons always use native probabilities.
10. **Run every registered variant.** Primary 50 m, 25 m, 100 m, nearest-site-only 50 m, unfiltered-background replacement, and exclusion of Buffalo. Keep frozen spatial assignments and repeat the full nested procedure. There are {status['outer_evaluations']} outer evaluations and {status['fitted_outer_models']} final fold-model artifacts; inner tuning entails additional fits. No phase 5 adaptation is performed.
11. **Evaluate and quantify uncertainty.** Report average precision, ROC-AUC, Brier, ten-bin calibration error, mean calibration error and top-decile precision/recall/lift by city and pooled, for native and sigmoid probabilities. For the primary endpoint, use 2,000 paired, city-stratified spatial-block bootstrap replicates per scheme/city and compare M1−M0 and M2−M0. Save every replicate. Sensitivities do not replace the primary endpoint or receive extra improvement gates.
12. **Validate and release.** Independently reconstruct split distances, check years/membership, verify all fitted medians/scalers, reload every model and reproduce held-out probabilities, check tuning/calibration membership, recompute metrics and reconcile bootstrap intervals. Export models, audits, plots, methods, results, reproduction instructions and checksums. Automated passing checks never imply human approval.

See [methods](02_methods.md), [results](03_results.md), [reproduction](04_reproduce.md) and [artifact guide](05_artifacts.md).
''',
    '02_methods.md':'''# Methods and interpretation

## Population and temporal design

The cohort is the restart's address-continuity-supported DFS bank-owned/in-bank population, built independently for 2024 and 2025. The outcome measures police-recorded robbery/burglary near ATM coordinates, not verified attacks on machines. Training is exclusively 2024; testing exclusively 2025. Report-filtered 2024 labels reduce late-report leakage but cannot reconstruct a database frozen in January 2025. Exposure itself is retrospective and conditions on later snapshot membership. Both outcome years were examined in previous project analyses.

Primary forward-spatial evaluation tests future-year locations outside the training neighborhoods. It is more restrictive than predicting the next year at familiar sites. Secondary forward leave-city-out measures transport from earlier-year other-city data. It is not the phase 5 adaptation experiment. City cohorts are highly unequal: NYC dominates pooled metrics, while leave-NYC-out training has only 72 sites. Excluding Buffalo leaves only 24 Rochester training sites for the NYC city-held-out sensitivity. City-specific results and sample sizes must accompany pooled claims.

Five group assignments are made from 2 km UTM block centers using weighted KMeans, without labels. Train/test and inner train/validation pairs are separated by at least 1,500 m WGS84; two 500 m contexts therefore have at least a 500 m gap. A block cannot be split across outer groups within its annual cohort. Years are grouped independently, but the cross-year distance purge protects against neighborhood overlap despite changed coordinates. The grid origin and seed are fixed; groups are not regenerated to improve performance.

## Models, preprocessing and calibration

M0 is logistic regression on log1p report-filtered prior-year robbery/burglary in >200–500 m. M1 adds the 13 frozen environmental predictors and uses L2 regularization, C in [0.1, 1, 10]. Both use lbfgs, max_iter=3000, tol=1e-8. M0 uses C=infinity, equivalent to no regularization in the installed implementation. M2 uses CPU XGBoost: 150 trees, learning_rate=0.05, min_child_weight=5, subsample=colsample_bytree=1, histogram trees, seed 20261001, one thread; candidate (max_depth, reg_lambda) pairs are (2,10), (2,1), (3,10), (3,1). No class weights or oversampling are used.

Each fitting subset independently learns median imputation, retaining all-empty columns with zero fallback. Logistic fits then independently learn scaling; boosting is not scaled. No preprocessing is learned from outer tests or outer-purged rows. Candidate selection uses mean inner-fold average precision; test labels are untouched by tuning. Fewer than two valid inner splits invokes the first fixed candidate. All skipped inner splits, library warnings, selected parameters and fitted preprocessing are recorded.

The optional sigmoid uses only the chosen candidate's inner out-of-fold probabilities and labels, with slope >=0 and a 1e-6 slope penalty. This is training-internal calibration, not a second independent tuning set; its assessment is the outer test. Failed or unsupported calibration retains native probabilities. Both variants are reported, but all primary ranking comparisons and bootstrap gates use native probabilities.

The predictor definitions follow phase 3: a common pre-2024 ACS vintage, EPA neighborhood measures, prior-December ATM competition and prior-year crime. Missing EPA values are imputed within training, never assigned from a nearest polygon. Road/transit measures are neighborhood proxies. IDs and coordinates are excluded from predictors. Model artifacts are fold models, not a deployment model. Count regression is not used: daily machine operation is unverified and the registered primary estimand is binary annual nearby crime.

## Metrics and uncertainty

AUPRC means non-interpolated average precision. ROC-AUC is undefined in a single-class test; AP is undefined with zero positives. The top decile contains exactly ceil(0.1*n) rows, with row-ID tie-breaking. Brier, ten equal-width-bin expected calibration error and mean predicted probability minus prevalence describe probability quality. Calibration-bin Wilson intervals are descriptive binomial intervals and ignore spatial dependence; they are not the spatial bootstrap uncertainty interval.

For each primary scheme and city/pooled cohort, draw occupied 2 km blocks with replacement within cities, retaining all their rows. Use identical row weights for all models for 2,000 replicates, seed 20261001. Report percentile 95% intervals for paired AP differences. These intervals condition on the fitted prediction vectors; they do not include model-refit, tuning or cohort-selection uncertainty. City-stratified pooling is still dominated by NYC site counts and is not a city-balanced average.

The working numerical flag requires AP gain >=0.01 and lower paired 95% bound >0. It is exploratory and does not correct for all examined comparisons. Sensitivity results, nonlinear-only benefits or city heterogeneity must be reported as such. A wide interval is inconclusive, not evidence of no effect. Useful ranking does not imply calibrated absolute risk, a causal environmental effect or justified deployment.

## Continuing limitations

Independent offense, event linkage, facility/continuity, Buffalo coordinate-precision and feature-schema approval remain pending. Address identity and baseline coordinates can change across years; positional changes can change neighborhood context. Municipal clipping truncates some annuli. Archived sources are later revisions, not historical as-of databases. Small target cohorts and very small source cohorts limit transport estimates. No independent sign-off, untouched holdout or operational risk validity is claimed.
''',
    '03_results.md':f'''# Phase 4 results

**Computational status: validated PASS.** The run trained on the 1,201-site 2024 cohort and tested the 1,241-site 2025 cohort with spatial purging. It produced **{status['fitted_outer_models']} outer model artifacts** and **{status['prediction_rows']:,} held-out prediction rows** across six variants and two schemes. Each eligible 2025 row is predicted exactly once per model/variant/scheme. No phase 5 experiments were run.

## Primary pooled native-probability performance

{table(rounded(pooled,['average_precision','roc_auc','brier_score','ece_10bins','top_decile_recall']),['scheme','model','n','positives','average_precision','roc_auc','brier_score','ece_10bins','top_decile_recall'])}

## Primary paired environmental improvement

{gate_text}.

{conclusion}

{interpretation}

{table(rounded(comparisons,['ap_difference','ci_low','ci_high']),['scheme','city','comparison','ap_difference','ci_low','ci_high','valid_replicates','exploratory_numerical_gate'])}

## Primary results by city

{table(rounded([r for r in primary if r['city']!='ALL'],['average_precision','roc_auc','brier_score','top_decile_recall']),['scheme','city','model','n','positives','average_precision','roc_auc','brier_score','top_decile_recall'])}

## Sensitivity results

These analyses retain the same split assignments and do not replace the primary result. All test labels are 2025 outcomes; training labels remain report-filtered 2024 outcomes. The unfiltered-background variant changes only background predictors. Full native and sigmoid metrics, including all city-specific sensitivities, are in `data/metrics.csv`.

{table(rounded([r for r in metrics if r['variant']!='primary_50m' and r['city']=='ALL' and r['probabilities']=='raw'],['average_precision','brier_score','top_decile_recall']),['variant','scheme','model','n','average_precision','brier_score','top_decile_recall'])}

## Calibration and fit diagnostics

{table(rounded([r for r in metrics if r['variant']=='primary_50m' and r['city']=='ALL'],['average_precision','brier_score','ece_10bins','calibration_mean_error']),['scheme','model','probabilities','average_precision','brier_score','ece_10bins','calibration_mean_error'])}

There are {fallbacks} outer model fits with fewer than two valid inner folds and {calibration_fail} without an applied sigmoid calibrator. The warning audit has {len(warnings)} rows, including skipped-fold notices and any estimator warnings; these are retained for review. Figure files summarize pooled primary ranking and calibration. Raw probabilities remain the primary result regardless of secondary calibration performance.

Independent research acceptance remains pending. Neither a numerical gain nor automated PASS makes these previously inspected retrospective results confirmatory. See the methods for source, exposure, coordinate and sample-imbalance limitations.
''',
    '04_reproduce.md':'''# Reproduction and checks

## 1. Verify the input release

Start with completed phases 1–3 in this folder. Phase 3 validation must be PASS and its output hashes must match. Preserve `protocol/phase4_analysis_spec.md` and the phase 3 allowlist. No external downloads, API credentials or parent-project data are required.

## 2. Prepare the environment

The existing repository `.venv` contains the required packages. For a standalone copy, create an environment and install `requirements-phase4.txt`. Package versions and Python version from the actual run are recorded in `qa/run_environment.json`. Do not use Python `-O`, which disables validation assertions.

## 3. Freeze splits before fitting

From the repository root:

```bash
.venv/bin/python restart_2024_2025/scripts/run_phase4.py --prepare-only
```

This verifies phase 3, freezes the protocol, generates both annual block assignments, outer/inner membership, separation diagnostics and experiment registry. It does not fit models. The frozen split hashes must match on subsequent runs. It deliberately invalidates previous phase 4 validation; finish the remaining steps before treating the release as complete.

## 4. Run all registered experiments

```bash
.venv/bin/python restart_2024_2025/scripts/run_phase4.py
```

This also verifies/prepares the same frozen splits, then executes all 47 outer evaluations, nested tuning, 141 final fold fits, calibration, metric aggregation and paired block bootstrap. It uses one thread per model and prints progress for every completed outer evaluation. An interrupted run is incomplete; rerun the command to recompute the full registered set. It is not a model-cache resume command. A changed specification or split fails the freeze check and requires a documented version amendment; do not silently delete freezes to change the analysis.

## 5. Validate independently

```bash
.venv/bin/python restart_2024_2025/scripts/validate_phase4.py
```

The validator recomputes distances and checks all outer/inner memberships, temporal and city isolation, fitted preprocessing, all 141 model artifacts and predictions, selection/calibration records, metrics and bootstrap intervals. It does not rerun every inner model fit. Review `qa/validation.json` and `qa/fit_warnings.csv`.

## 6. Generate the report and figures

```bash
.venv/bin/python restart_2024_2025/scripts/report_phase4.py
```

Reporting requires validation PASS, creates the Markdown documents and PNG/PDF figures, updates restart phase status, and hashes the final outputs and implementation files. For a standalone folder use `python scripts/...` instead of the repository-prefixed commands. The plotting cache is placed in `/tmp`.

## 7. Review the scientific gate

Read the primary native-probability comparisons first, then city-specific and sensitivity results and calibration. The working improvement rule is AP gain >=0.01 with lower paired 95% bound >0. Independent research approval remains pending even if this flag passes. No phase 5 transfer/adaptation or deployment is authorized by running this workflow.

Input hashes are relative to the restart root. Output hashes are relative to `results/phase4`. Recompute SHA-256 and compare the manifest columns to detect changes. Only load the trusted joblib artifacts created by this workflow.
''',
    '05_artifacts.md':'''# Artifact guide

| Location | Contents / use |
|---|---|
| data/modeling_cohort.csv | Both annual site-year keys, coordinates, spatial groups, labels and label vintages; metadata only |
| data/outer_split_membership.csv | Training, held-out and distance-purged rows for each variant/scheme/fold |
| data/inner_split_membership.csv | Training, validation and purged rows inside each outer training set |
| data/predictions.csv | All held-out 2025 native and sigmoid probabilities, labels, model and split keys |
| data/inner_search_scores.csv | Every candidate's usable inner-fold AP, mean score and membership hashes |
| data/metrics.csv | Both probability types, all variants, both schemes, pooled and city-specific metrics |
| data/calibration_bins.csv | Bin counts, observed rates, average probabilities and descriptive Wilson intervals |
| data/paired_ap_comparisons.csv | Primary M1−M0 / M2−M0 AP differences, block intervals and numerical flags |
| data/paired_bootstrap_replicates.csv | All 2,000 paired draws per primary scheme/city grouping |
| models/ | 141 saved fold pipelines, predictor allowlists and training-only sigmoid parameters |
| qa/fitted_preprocessing.csv | Per-fit training medians, all-empty flags and logistic scaling values |
| qa/model_fit_audit.csv | Selected parameters, training/test hashes, sizes, artifact hashes, calibration settings |
| qa/calibration_training_oof.csv | Training-internal OOF predictions and labels used by sigmoid fits |
| qa/fit_warnings.csv | Skipped inner folds and captured library warnings |
| qa/split_separation.csv | Minimum outer/inner WGS84 separation, training/test/purged counts |
| qa/protocol_freeze.json, qa/split_freeze.json | Before-fitting specification and split fingerprints |
| qa/experiment_registry.json | Fixed variants, candidate grids, seeds and temporal parameters |
| qa/run_environment.json | Actual package versions, timestamps and thread count |
| qa/validation.json, qa/phase4_status.json | Computational validation and distinct research-acceptance status |
| qa/input_manifest.csv | Inputs and training implementation hashes frozen for the run |
| qa/implementation_manifest.csv | Final runner, common code, validator, reporter, protocol and requirements hashes |
| qa/output_manifest.csv | Final output hashes, including models, documentation and figures |
| figures/ | Pooled primary average-precision and calibration plots, PNG and PDF |

The prediction column named site_id is the **site-year row_id** (including the year suffix); physical_site_id in the modeling cohort is the phase 2 coordinate-based site identity. Join to phase 2 via row_id. Do not interpret those identities as permanent machine IDs. Each scheme provides its own complete test vector; never concatenate schemes or variants as if they were independent observations.
'''}
    for name,text in docs.items():(OUT/'docs'/name).write_text(text)
    fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,scheme in zip(axes,['forward_spatial','forward_leave_city_out']):
        rows=[r for r in pooled if r['scheme']==scheme];ax.bar([r['model'] for r in rows],[float(r['average_precision']) for r in rows],color=['#657786','#167d9a','#df7b36']);ax.axhline(float(rows[0]['prevalence']),color='gray',ls='--',label='Prevalence');ax.set_ylim(0,1);ax.set_title(scheme.replace('_',' '));ax.set_ylabel('Average precision');ax.legend()
    fig.suptitle('2024 training → 2025 testing · primary 50 m · native probabilities')
    for ext in ['png','pdf']:fig.savefig(OUT/f'figures/primary_average_precision.{ext}',dpi=160)
    plt.close(fig)
    bins=read('data/calibration_bins.csv');fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    for ax,scheme in zip(axes,['forward_spatial','forward_leave_city_out']):
        for model in ['M0','M1','M2']:
            rows=sorted([r for r in bins if r['variant']=='primary_50m' and r['city']=='ALL' and r['scheme']==scheme and r['model']==model and r['probabilities']=='raw'],key=lambda r:int(r['bin']))
            ax.plot([float(r['mean_probability']) for r in rows],[float(r['observed_rate']) for r in rows],'o-',label=model)
        ax.plot([0,1],[0,1],'--',color='gray');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted probability',ylabel='Observed fraction',title=scheme.replace('_',' '));ax.legend()
    fig.suptitle('Held-out calibration · primary 50 m · native probabilities')
    for ext in ['png','pdf']:fig.savefig(OUT/f'figures/primary_calibration.{ext}',dpi=160)
    plt.close(fig)
    (OUT/'README.md').write_text(f'''# Phase 4 — 2024-to-2025 model comparisons

Computationally complete and validated: **{status['fitted_outer_models']} fold models**, **{status['prediction_rows']:,} held-out prediction rows**, six variants and two forward evaluation schemes. Independent scientific approval remains pending.

{conclusion}

- [Complete step-by-step procedure](docs/01_step_by_step.md)
- [Methods and limitations](docs/02_methods.md)
- [Results, sensitivities and calibration](docs/03_results.md)
- [Exact reproduction commands](docs/04_reproduce.md)
- [Artifact guide](docs/05_artifacts.md)
- [Metrics](data/metrics.csv), [paired comparisons](data/paired_ap_comparisons.csv), [predictions](data/predictions.csv), [validation](qa/validation.json)

![Primary average precision](figures/primary_average_precision.png)

![Primary calibration](figures/primary_calibration.png)

No phase 5 adaptation or deployment was performed. These are nearby-crime outcomes in a retrospectively constructed cohort, not verified ATM-attack risks.
''')
    paths=[ROOT/'scripts'/n for n in ['run_phase4.py','phase4_common.py','validate_phase4.py','report_phase4.py']]+[ROOT/'protocol/phase4_analysis_spec.md',ROOT/'requirements-phase4.txt',ROOT/'requirements.txt']
    def manifest(path,rows):
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=['file','bytes','sha256']);w.writeheader();w.writerows(rows)
    manifest(OUT/'qa/implementation_manifest.csv',[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths])
    paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='output_manifest.csv')
    manifest(OUT/'qa/output_manifest.csv',[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths])
    path=ROOT/'reports/phase_status.json';overall=json.loads(path.read_text());overall.update(phase_4='computationally_complete',phase_4_validation='PASS',phase_4_models=status['fitted_outer_models'],phase_4_forward_temporal_validation=True,phase_4_primary_pooled_numerical_gate=bool(passing));path.write_text(json.dumps(overall,indent=2)+'\n')
    print(conclusion);print(gate_text)
if __name__=='__main__':main()
