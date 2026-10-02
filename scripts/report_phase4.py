"""Render phase 4 research figures, Markdown reports and release checksums."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/atm-phase4-matplotlib')
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve
from run_phase4 import OUT,ROOT,read,sha,save,write

COLORS={'M0':'#555555','M1':'#0072B2','M2':'#D55E00'}
LABELS={'M0':'M0: crime only','M1':'M1: logistic + environment','M2':'M2: XGBoost + environment'}
SCHEMES={'spatial':'Buffered spatial holdouts','leave_city_out':'Leave one city out'}
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str,r))+' |' for r in rows])
def fmt(v):return 'NA' if v in ('',None) else f'{float(v):.3f}'
def md(name,text):(OUT/name).write_text(text.strip()+'\n')
def figure(name,fig):
    fig.savefig(OUT/'figures'/f'{name}.png',dpi=180,bbox_inches='tight')
    fig.savefig(OUT/'figures'/f'{name}.pdf',bbox_inches='tight')
    plt.close(fig)

def plots(predictions,metrics,comparisons,calibration,cohort):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    for ax,scheme in zip(axes,SCHEMES):
        for model in COLORS:
            rows=[r for r in predictions if r['variant']=='primary_50m' and r['scheme']==scheme and r['model']==model]
            y=np.array([int(r['y']) for r in rows]);p=np.array([float(r['p_raw']) for r in rows])
            precision,recall,_=precision_recall_curve(y,p)
            ap=next(r['average_precision'] for r in metrics if r['variant']=='primary_50m' and r['scheme']==scheme and r['model']==model and r['city']=='ALL' and r['probabilities']=='raw')
            ax.step(recall,precision,where='post',color=COLORS[model],label=f'{model}, AP={float(ap):.3f}')
        ax.axhline(y.mean(),linestyle=':',color='#999999',label=f'Prevalence={y.mean():.3f}')
        ax.set(xlabel='Recall',ylabel='Precision',title=SCHEMES[scheme],xlim=(0,1),ylim=(0,1.02));ax.legend(loc='lower left',fontsize=9)
    fig.suptitle('Exploratory 2025 holdouts: primary 50 m endpoint (pooled cities)')
    figure('precision_recall',fig)
    fig,axes=plt.subplots(1,2,figsize=(13,5.8),layout='constrained')
    for ax,scheme in zip(axes,SCHEMES):
        selected=[r for r in comparisons if r['scheme']==scheme]
        labels=[]
        for i,r in enumerate(selected):
            point=float(r['ap_difference']);low=float(r['ci_low']);high=float(r['ci_high']);color=COLORS[r['comparison'].split('-')[0]]
            ax.plot([low,high],[i,i],color=color,linewidth=2);ax.plot(point,i,'o',color=color)
            labels.append(r['city'].replace('New York City','NYC')+' · '+r['comparison'])
        ax.axvline(0,color='#444444',linewidth=1);ax.axvline(.01,color='#999999',linestyle=':',label='Working gain threshold 0.01')
        ax.set(yticks=range(len(labels)),yticklabels=labels,xlabel='Average precision difference vs M0',title=SCHEMES[scheme]);ax.invert_yaxis()
    fig.suptitle('Exploratory paired differences: 95% spatial-block bootstrap intervals\n2,000 draws; conditional on fitted predictions, without model refits',fontsize=12)
    figure('paired_ap_intervals',fig)
    fig,axes=plt.subplots(2,2,figsize=(10,8),layout='constrained')
    for row,scheme in enumerate(SCHEMES):
        for col,prob in enumerate(['raw','sigmoid']):
            ax=axes[row,col]
            for model in COLORS:
                points=[r for r in calibration if r['variant']=='primary_50m' and r['scheme']==scheme and r['city']=='ALL' and r['model']==model and r['probabilities']==prob]
                points.sort(key=lambda r:int(r['bin']))
                ax.plot([float(r['mean_probability']) for r in points],[float(r['observed_rate']) for r in points],'-o',ms=4,color=COLORS[model],label=model)
            ax.plot([0,1],[0,1],'--',color='#999999');ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean predicted probability',ylabel='Observed event fraction',title=SCHEMES[scheme]+' · '+prob);ax.legend()
    fig.suptitle('Exploratory calibration: 10 fixed-width bins, pooled cities\nSigmoid learned only from inner training-set holdouts',fontsize=12)
    figure('calibration',fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),layout='constrained')
    for ax,city in zip(axes,['New York City','Buffalo','Rochester']):
        rows=[r for r in cohort if r['city']==city]
        ax.scatter([float(r['easting_m'])/1000 for r in rows],[float(r['northing_m'])/1000 for r in rows],c=[int(r['spatial_fold']) for r in rows],cmap='tab10',vmin=0,vmax=9,s=12)
        ax.set(title=f'{city} (n={len(rows)})',xlabel='UTM easting (km)',ylabel='UTM northing (km)');ax.set_aspect('equal',adjustable='datalim')
    fig.suptitle('Outcome-independent spatial groups; 1,500 m training purge applied per holdout')
    figure('spatial_groups',fig)
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    cities=['ALL','New York City','Buffalo','Rochester'];positions=np.arange(4)
    for ax,scheme in zip(axes,SCHEMES):
        for m,model in enumerate(COLORS):
            values=[float(next(r['average_precision'] for r in metrics if r['variant']=='primary_50m' and r['scheme']==scheme and r['city']==city and r['model']==model and r['probabilities']=='raw')) for city in cities]
            ax.bar(positions+(m-1)*.24,values,width=.24,label=model,color=COLORS[model])
        ax.set(xticks=positions,xticklabels=['Pooled','NYC','Buffalo','Rochester'],ylim=(0,1),ylabel='Average precision',title=SCHEMES[scheme]);ax.legend()
    fig.suptitle('Exploratory city-specific performance; AP depends on prevalence')
    figure('city_average_precision',fig)

def main():
    status=json.loads((OUT/'qa/phase4_status.json').read_text());validation=json.loads((OUT/'qa/validation.json').read_text())
    assert status['validation_status']==validation['status']=='PASS'
    metrics=read(OUT/'data/metrics.csv');comparisons=read(OUT/'data/paired_ap_comparisons.csv')
    predictions=read(OUT/'data/predictions.csv');calibration=read(OUT/'data/calibration_bins.csv');cohort=read(OUT/'data/modeling_cohort.csv')
    fits=read(OUT/'qa/model_fit_audit.csv');warnings_rows=read(OUT/'qa/fit_warnings.csv')
    split_rows=read(OUT/'qa/split_separation.csv');env=json.loads((OUT/'qa/run_environment.json').read_text())
    plots(predictions,metrics,comparisons,calibration,cohort)
    primary=[r for r in metrics if r['variant']=='primary_50m' and r['city']=='ALL' and r['probabilities']=='raw']
    main_table=table(['Evaluation','Model','AP / AUPRC','ROC-AUC','Brier','Top-decile precision','Top-decile lift'],
        [[SCHEMES[r['scheme']],r['model'],fmt(r['average_precision']),fmt(r['roc_auc']),fmt(r['brier_score']),fmt(r['top_decile_precision']),fmt(r['top_decile_lift'])] for r in primary])
    ci_table=table(['Evaluation','Comparison','AP gain','95% interval','Exploratory numerical gate'],
        [[SCHEMES[r['scheme']],r['comparison'],fmt(r['ap_difference']),f"[{fmt(r['ci_low'])}, {fmt(r['ci_high'])}]",r['exploratory_numerical_gate']] for r in comparisons if r['city']=='ALL'])
    city_table=table(['City','Sites','Positive at 50 m','Prevalence'],
        [[city,len([r for r in cohort if r['city']==city]),sum(int(r['y_primary_50m']) for r in cohort if r['city']==city),
          f"{np.mean([int(r['y_primary_50m']) for r in cohort if r['city']==city]):.3f}"] for city in ['New York City','Buffalo','Rochester']])
    signal=[r for r in comparisons if r['city']=='ALL' and r['exploratory_numerical_gate']=='True']
    signal_text=('No pooled model comparison met the working AP-gain criterion in either evaluation.' if not signal else
        'The working numerical criterion was met by '+', '.join(SCHEMES[r['scheme']]+' '+r['comparison'] for r in signal)+'. This is an exploratory signal, not a confirmatory pass.')
    save(OUT/'qa/decision.json',{'exploratory_pooled_numerical_gate':'met_for_at_least_one_comparison' if signal else 'not_met',
        'confirmatory_go':False,'full_phase4_complete':False,
        'reason':'Forward temporal validation and phase 2/3 research review are incomplete.',
        'interpretation':signal_text,'criterion':{'minimum_ap_gain':0.01,'lower_95pct_bound_must_exceed':0},
        'no_effect_claim_supported':False})
    md('README.md',f'''# Phase 4 exploratory results

The supported exploratory modeling workflow is complete and validated. **Full blueprint phase 4 is not complete:** the data contain only 2025 outcomes, so forward temporal validation cannot be performed, and earlier research-review gates remain open.

- [What was completed](docs/01_work_completed.md)
- [Methods](docs/02_methods.md)
- [Results and interpretation](docs/03_results.md)
- [Reproduction and files](docs/04_reproduce.md)

## Main result

{main_table}

{signal_text} None of the comparisons authorizes confirmatory claims or operational ATM risk scores.

The run covers 1,192 full-year sites, three model families, two evaluation schemes and six predefined analysis variants. It produced {status['fitted_outer_models']} outer-fold model artifacts across {status['outer_evaluations']} evaluations. M0 uses lagged crime alone; M1 and M2 add the 13 phase 3 environmental predictors. All preprocessing and hyperparameter tuning occur within the training side of each split.

See the [paired AP comparisons](data/paired_ap_comparisons.csv), [all metrics](data/metrics.csv), [held-out predictions](data/predictions.csv), [validation](qa/validation.json) and [phase status](qa/phase4_status.json). Figures are saved as PNG and PDF in [figures](figures/).

![Paired exploratory AP differences](figures/paired_ap_intervals.png)
''')
    md('docs/01_work_completed.md',f'''# What was completed

Phase 4 asks whether environmental information improves held-out near-ATM crime prediction beyond prior surrounding crime. This delivery runs the comparisons supported by the available single-year panel and documents the missing temporal component.

1. Froze the [analysis specification](../../../protocol/phase4_analysis_spec_v1.0.md) before model fitting and recorded its hash.
2. Joined the full-year phase 3 feature matrix to the phase 2 binary outcomes using exact site IDs. Retained all 1,192 sites, including missing features.
3. Created outcome-independent spatial groups and froze outer/inner split membership before fitting. Applied a 1,500 m center-to-center exclusion to each training/validation boundary.
4. Fit M0 crime-only logistic regression, M1 regularized logistic regression and M2 CPU XGBoost. Tuned only inside outer training sets.
5. Evaluated five spatial holdouts and three leave-one-city-out tests. Performed five predeclared sensitivity analyses with their corresponding splits.
6. Saved native and training-only sigmoid-calibrated predictions. Computed AP, ROC-AUC, Brier, calibration and top-decile metrics by city and pooled.
7. Computed 2,000 paired, city-stratified spatial-block bootstrap draws for each primary comparison scope.
8. Preserved {status['fitted_outer_models']} model artifacts, preprocessing values, parameter searches, warnings, split manifests, prediction files and source checksums.
9. Ran focused metric/preprocessing tests and {len(validation['checks'])} artifact-validation checks. Generated five research figures in both PNG and PDF and this documentation.

## What remains incomplete

The existing sources provide only one exposure-supported outcome year. Spatial and leave-one-city-out tests use 2025 labels on both sides of geographically separated splits; they are not forecasts of a later year. A true forward temporal experiment requires additional annual cohorts and features available before each prediction period.

Phase 2's independent offense/linkage/identity reviews, Buffalo coordinate assessment, exposure assumptions and phase 3 feature acceptance remain open. This package keeps `full_blueprint_phase4_complete=false` and `confirmatory_modeling_ready=false` even if an exploratory numerical threshold passes. Phase 5 target adaptation and substantive feature attribution are not part of this delivery.
''')
    md('docs/02_methods.md','''# Methods

## Cohort and outcome

Use the 1,192 sites in the existing 2025 full-year historical panel. Each has 365 days supported by the phase 2 adjacent-snapshot continuity assumption, not directly observed uninterrupted operation. The main outcome is any police-recorded robbery/burglary within 50 m during 2025. Counts are converted to binary for the nearest-site-only sensitivity. No label or coordinate was invented.

The data remain observational and retrospectively assembled. Full-year membership itself uses future snapshots relative to January 2025; this selection may affect transportability. Police extracts may include later revisions. These limitations prevent a claim of exact prospective deployment simulation.

## Spatial and city holdouts

Each city uses 2 km square blocks in its designated UTM coordinate system, anchored at zero easting/northing. Five compact groups are created from occupied block centers using KMeans, fixed seed 20261001 and n_init=20, weighted by site counts. Group numbers are canonicalized by center coordinates. Neither outcomes nor model performance influence these partitions.

For each of five spatial folds, hold out one group from every city. Remove potential training sites within 1,500 m WGS84 distance of any held-out center. Thus two 500 m context circles remain at least 500 m apart. Leave-one-city-out tests train on the other cities' sites, with the same distance rule. Outer test rows and excluded rows never enter inner tuning.

Inner folds use the existing group IDs within the outer training set and repeat the purge. Inner validation must contain both classes; training must have at least ten rows and both classes. Invalid folds are logged and skipped. With fewer than two valid inner folds, the fixed first candidate is used and no sigmoid is fitted. This prevents test-set tuning but can weaken model selection in the smallest source-city samples.

These are same-year spatial evaluation schemes. They do not meet the blueprint's future-period requirement. Spatial folds are not forced to have equal size; preserve and inspect their coverage instead of changing partitions to obtain better metrics.

## Model fitting and tuning

M0 receives only log1p(2024 primary background incidents at >200–500 m). M1 and M2 use all 14 frozen phase 3 predictors: that baseline plus 13 environmental/context variables. City, coordinates, geography IDs, exposure duration, future membership and quality flags are excluded from inputs.

Within every training split, missing values are imputed with training medians; features entirely missing in training receive the explicit zero fallback. Logistic models also fit scaling within that split. No rows are dropped for feature missingness, no oversampling is used, and no held-out prevalence adjustment is applied.

| Model | Fixed settings | Inner search |
|---|---|---|
| M0 | Unpenalized logistic regression, lbfgs, max_iter 3000, tolerance 1e-8 | None |
| M1 | L2 logistic regression, same solver/convergence settings | C = 0.1, 1, 10 |
| M2 | CPU XGBoost, 150 trees, learning rate 0.05, min_child_weight 5, all rows/features per tree, histogram method | depth 2/3 × lambda 10/1 |

Candidate selection maximizes mean inner-fold average precision; ties retain the first candidate. The selected pipeline is refitted on outer training rows, then scored once on the held-out rows. Relevant implementation references are [scikit-learn logistic regression](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html) and the [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html). Exact installed versions are recorded separately.

## Calibration

Primary results use the native probabilities. A secondary sigmoid maps the selected model's inner out-of-fold logits to probabilities using only outer-training labels. Its slope is constrained nonnegative, with a small 1e-6 slope penalty. Failed or unsupported fits fall back to native probabilities and are recorded. Raw and sigmoid results are both reported; no choice between them is made based on test performance. Evaluation reliability bins use ten fixed probability intervals. The [calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) motivates using predictions from data excluded from base-model fitting to train the probability mapping.

## Metrics

AUPRC is represented by non-interpolated [average precision](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html), not trapezoidal area. AP depends on prevalence, so city sample sizes and positive fractions accompany it. ROC-AUC measures ranking; Brier measures squared probability error. Calibration diagnostics include mean predicted probability minus observed prevalence, ten-bin expected calibration error, and reliability tables. Binwise Wilson intervals are descriptive and do not adjust for spatial clustering.

For top-decile capture, select exactly ceil(0.10 × number of test sites), sorting equal probabilities by site ID. Precision is the positive fraction among selected sites; recall is their share of all positives; lift divides precision by overall prevalence. Single-class tests have undefined ROC-AUC, and no-positive tests have undefined AP. Pooled scores combine untouched predictions from the respective outer folds and are dominated by NYC, not city-balanced.

## Paired uncertainty and decision

For the primary endpoint, resample occupied 2 km blocks with replacement within each city, retain all rows in each sampled block, and apply the same replicate weights to M0/M1/M2. Use 2,000 replicates and fixed seed 20261001. Compute percentile 95% intervals for AP(M1)−AP(M0) and AP(M2)−AP(M0), pooled and by city. The implementation handles ties and zero sample weights and is checked against the library AP calculation.

These intervals condition on the saved out-of-fold predictions. They do not refit or retune models, do not fully represent algorithm-training uncertainty, and depend on the chosen block size. Small numbers of city blocks limit inference. No multiplicity correction is applied; city and sensitivity results remain exploratory.

The working numerical flag requires AP gain at least 0.01 and a lower interval bound above zero. It is not a confirmatory approval gate because the data validity and temporal requirements remain unmet. A failed flag is not proof of no environmental effect. Calibration is reported independently; passing a ranking threshold alone does not justify operational probability estimates.

## Sensitivities

The five fixed sensitivities are 25 m, 100 m, nearest-site-only 50 m, report-date-cutoff background, and excluding Buffalo. Each reruns the same nested process using the original spatial groups; the Buffalo-exclusion variant removes that city from both source and test sets. Sensitivities are not used to replace the main 50 m result, and no additional bootstrap decision flags are calculated for them. Report-date filtering still does not recreate an as-of-2025 police database.
''')
    per_city=table(['Evaluation','City','Model','AP','Brier'],[[SCHEMES[r['scheme']],r['city'],r['model'],fmt(r['average_precision']),fmt(r['brier_score'])]
        for r in metrics if r['variant']=='primary_50m' and r['city']!='ALL' and r['probabilities']=='raw'])
    sens=table(['Variant','Evaluation','M0 AP','M1 AP','M2 AP'],[[variant,SCHEMES[scheme]]+
        [fmt(next(r['average_precision'] for r in metrics if r['variant']==variant and r['scheme']==scheme and r['model']==model and r['city']=='ALL' and r['probabilities']=='raw')) for model in COLORS]
        for variant in ['radius_25m','radius_100m','nearest_only_50m','report_cutoff_background','exclude_buffalo'] for scheme in SCHEMES])
    calibration_table=table(['Evaluation','Model','Raw Brier','Sigmoid Brier','Raw ECE','Sigmoid ECE'],[[SCHEMES[scheme],model]+[
        fmt(next(r[field] for r in metrics if r['variant']=='primary_50m' and r['scheme']==scheme and r['model']==model and r['city']=='ALL' and r['probabilities']==prob))
        for field,prob in [('brier_score','raw'),('brier_score','sigmoid'),('ece_10bins','raw'),('ece_10bins','sigmoid')]] for scheme in SCHEMES for model in COLORS])
    fallback=sum(int(r['valid_inner_folds'])<2 for r in fits)
    model_warnings=[r for r in warnings_rows if r['model']!='ALL']
    skipped=[r for r in warnings_rows if r['model']=='ALL']
    min_distance=min(float(r['minimum_train_test_distance_m']) for r in split_rows if r['minimum_train_test_distance_m'])
    primary_lo=[r for r in fits if r['variant']=='primary_50m' and r['scheme']=='leave_city_out' and r['model']=='M0']
    train_table=table(['Held-out city','Training sites','Training positives','Test sites'],[[r['fold'],r['train_n'],r['train_positive'],r['test_n']] for r in primary_lo])
    spatial_gains={r['comparison']:r for r in comparisons if r['city']=='ALL' and r['scheme']=='spatial'}
    loco_gains={r['comparison']:r for r in comparisons if r['city']=='ALL' and r['scheme']=='leave_city_out'}
    interpretation=f'''Adding environmental predictors changed pooled spatial AP by {float(spatial_gains['M1-M0']['ap_difference']):+.3f} for logistic regression and {float(spatial_gains['M2-M0']['ap_difference']):+.3f} for XGBoost. Both spatial intervals include zero, so these point improvements do not establish reliable incremental value under the working criterion.

In leave-one-city-out evaluation, the pooled AP changes were {float(loco_gains['M1-M0']['ap_difference']):+.3f} and {float(loco_gains['M2-M0']['ap_difference']):+.3f}, respectively. Pooled comparisons also rank predictions from different fitted models against each other, so probability comparability across cities affects the result. City-specific estimates are essential for interpretation. The saved comparisons show lower AP for both environmental models when NYC is held out; this result comes from training on only 75 Buffalo/Rochester sites and should not be generalized to all source/target designs.

The conclusion is inconclusive incremental value under the predefined pooled test, not proof that environmental context has no association with crime.'''
    md('docs/03_results.md',f'''# Results and interpretation

The supported exploratory comparisons have finished and their saved artifacts passed validation. **This does not complete the blueprint's forward temporal or confirmatory evaluation.**

## Cohort

{city_table}

## Primary 50 m results

{main_table}

Paired comparisons:

{ci_table}

{signal_text} The numerical flag does not override unresolved phase 2/3 review or the missing future-year test. Report the observed estimates and uncertainty rather than selecting a more favorable radius, city or calibration variant.

{interpretation}

![Primary paired differences](../figures/paired_ap_intervals.png)

## City-specific results

{per_city}

Leave-one-city-out training sizes:

{train_table}

The cities differ sharply in cohort size and prevalence. In particular, predicting NYC from the other two cities trains on only 75 sites, whereas predicting either smaller city trains largely on NYC. The small Buffalo/Rochester test samples produce unstable precision and top-decile estimates. Pooled metrics primarily reflect NYC and are not evidence of uniform cross-city benefit.

![Precision–recall curves](../figures/precision_recall.png)

## Calibration

{calibration_table}

Lower Brier and ECE are better, but finite-bin ECE depends on the binning and sample size. Sigmoid calibration is a predefined secondary analysis and was learned without outer test labels. These results do not validate absolute risks for deployment.

![Calibration plots](../figures/calibration.png)

## Sensitivity analyses

{sens}

All sensitivities retain their original labels and model-selection procedure. They do not substitute for the primary result. The nearest-only definition changes incident attribution; excluding Buffalo changes both the training mixture and evaluation population. Neither comparison isolates a causal mechanism.

## Quality and execution

- Completed {status['outer_evaluations']} outer evaluations and saved {status['fitted_outer_models']} fitted fold models.
- Verified {status['prediction_rows']} held-out model prediction rows.
- Minimum verified inner/outer train–test center separation: {min_distance:.2f} m, above the 1,500 m requirement.
- Inner folds skipped for insufficient rows/classes: {len(skipped)} logged fold instances.
- Model fits with fewer than two usable inner folds: {fallback}; these use the predetermined first candidate and no sigmoid.
- Model-library warning records: {len(model_warnings)}. See the warning CSV; skipped-inner-fold notices are counted separately.
- Artifact validation: PASS ({len(validation['checks'])} checks), including preprocessing reconciliation, exact prediction reproduction and paired-interval checks.

Execution started {env['started_utc']} and finished {env['finished_utc']}. Package versions and environment details are in `qa/run_environment.json`.

## What remains before a full phase 4 acceptance

1. Acquire additional exposure-supported annual cohorts, reconstruct their ex-ante features, and run the planned forward-time test.
2. Complete phase 2 independent crime/linkage/identity review and assess Buffalo's location precision.
3. Resolve or approve phase 3 feature definitions, spatial ambiguities and the missing-data treatment within the final modeling design.
4. Rebuild and rerun if those reviews change sites, labels, features or exposure eligibility.
5. Obtain researcher sign-off on the practical-effect criterion and evaluate calibration before any confirmatory or operational claim.

No causal feature explanation, optimized ATM placement or target-adaptation benefit is established here. The phase status remains **exploratory computational work complete; full blueprint phase 4 incomplete**.
''')
    md('docs/04_reproduce.md','''# Reproduction and files

Run from the project root:

```bash
.venv/bin/python -m pip install -r requirements-phase4.txt
.venv/bin/python scripts/test_phase4.py
.venv/bin/python scripts/run_phase4.py --prepare-only
.venv/bin/python scripts/run_phase4.py
.venv/bin/python scripts/validate_phase4.py
.venv/bin/python scripts/report_phase4.py
```

The installation step needs network access only if dependencies are missing. The complete analysis reads local phase 2/3 data and uses no API key or external data requests. Models use one CPU thread; numerical libraries are also constrained during fitting. Splits, random seeds, hyperparameter grids and package versions are preserved.

The pre-fitting split freeze is checked on every run. Existing result files are regenerated by these commands; preserve a separate copy if starting a new analysis version. A changed phase 3 release or protocol will cause checksum/freeze checks to fail and requires a documented amendment, not bypassing the checks.

## File guide

| File/folder | Meaning |
|---|---|
| `data/modeling_cohort.csv` | IDs, spatial blocks/folds and endpoint labels; not a predictor allowlist |
| `data/outer_split_membership.csv` | Train/test/purged rows for each analysis |
| `data/inner_split_membership.csv` | Nested training/validation/purged rows |
| `data/predictions.csv` | Untouched outer-test native and sigmoid predictions |
| `data/metrics.csv` | City and pooled results for all variants |
| `data/calibration_bins.csv` | Reliability values and descriptive binwise intervals |
| `data/inner_search_scores.csv` | Every candidate's inner-fold and mean AP |
| `data/paired_ap_comparisons.csv` | Main paired differences, intervals and exploratory flags |
| `data/paired_bootstrap_replicates.csv` | All 2,000 draws for each scheme/scope |
| `models/` | Fitted outer pipelines, predictor lists and sigmoid parameters |
| `qa/fitted_preprocessing.csv` | Training medians/scaling values and all-missing flags |
| `qa/model_fit_audit.csv` | Selected parameters, set hashes and model checksums |
| `qa/calibration_training_oof.csv` | Training-only predictions used for sigmoid fitting |
| `qa/fit_warnings.csv` | Skipped inner folds and model warnings |
| `qa/split_separation.csv` | Membership sizes and minimum WGS84 separation |
| `qa/protocol_freeze.json`, `qa/split_freeze.json` | Pre-fitting specification and split hashes |
| `qa/experiment_registry.json` | Fixed model/split/variant definitions |
| `qa/run_environment.json` | Runtime and package versions |
| `qa/input_manifest.csv` | Consumed input and training-implementation hashes |
| `qa/validation.json`, `qa/phase4_status.json` | Verification and explicit incomplete temporal gate |
| `qa/decision.json` | Exploratory numerical decision and blocked confirmatory gate |
| `qa/implementation_manifest.csv` | Hashes of training, validation, testing and report code |
| `figures/` | Five figures, each as PNG and PDF |
| `release_manifest.sha256` | Hashes of all other output artifacts |

Models are local exploratory fold artifacts, not a single approved deployment model. Joblib files should only be loaded from this trusted generated package. For model M0, the saved predictor list contains only the background variable; M1/M2 use the complete phase 3 allowlist. For the report-cutoff sensitivity, replace the baseline with the phase 3 cutoff version before applying a stored pipeline.

From `results/phase4`, verify the release with:

```bash
sha256sum --check release_manifest.sha256
```

The training code is in `scripts/run_phase4.py`, focused tests in `scripts/test_phase4.py`, independent artifact checks in `scripts/validate_phase4.py`, and report generation in `scripts/report_phase4.py`. All are provided alongside the data package. No phase 2/3 artifact is overwritten by this workflow.
''')
    implementation=[ROOT/'scripts'/n for n in ['run_phase4.py','test_phase4.py','validate_phase4.py','report_phase4.py']]
    implementation += [ROOT/'requirements-phase4.txt',ROOT/'protocol/phase4_analysis_spec_v1.0.md']
    write(OUT/'qa/implementation_manifest.csv',[{'file':str(p.relative_to(ROOT)),'sha256':sha(p)} for p in implementation])
    paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='release_manifest.sha256')
    (OUT/'release_manifest.sha256').write_text(''.join(f'{sha(p)}  {p.relative_to(OUT)}\n' for p in paths))
    print(f'Wrote five Markdown files, ten figure files and checksums for {len(paths)} artifacts.')

if __name__=='__main__':main()
