"""Phase 5 step-by-step documentation, summaries, figures and release manifests."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/atm_restart_p5_matplotlib')
import collections,csv,json,hashlib,gzip
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/phase5'
CITIES=['New York City','Buffalo','Rochester'];MODELS=['M0','M1','M2']
def read(name):
 with (OUT/name).open() as f:return list(csv.DictReader(f))
def write(name,rows):
 rows=list(rows)
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table(rows,fields,numeric=()):
 return '| '+' | '.join(fields)+' |\n|'+'|'.join('---' for _ in fields)+'|\n'+''.join('| '+' | '.join(f'{float(r[k]):.4f}' if k in numeric and r[k] not in ['',None] else str(r.get(k,'')) for k in fields)+' |\n' for r in rows)
def main():
 validation=json.loads((OUT/'qa/validation.json').read_text());assert validation['status']=='PASS'
 status=json.loads((OUT/'qa/status.json').read_text());metrics=read('data/metrics.csv');benefits=read('data/benefit_summary.csv');gaps=read('data/transfer_gaps.csv');extra=read('data/extrapolation.csv');warnings=read('qa/warnings.csv')
 groups=collections.defaultdict(list)
 for r in metrics:groups[tuple(r[k] for k in ['city','condition','source','fraction','model'])].append(r)
 summaries=[]
 for key,rows in groups.items():
  r=dict(zip(['city','condition','source','fraction','model'],key));r.update(seeds=len(rows),test_n=int(rows[0]['n']),positives=int(rows[0]['positives']))
  for field in ['average_precision','roc_auc','brier_score','ece_10bins','calibration_mean_error','top_decile_precision','top_decile_recall','top_decile_lift']:
   values=[float(row[field]) for row in rows if row[field]!=''];r['mean_'+field]=float(np.mean(values)) if values else None
  values=[float(row['average_precision']) for row in rows];r.update(ap_seed_sd=float(np.std(values,ddof=1)) if len(values)>1 else 0.,ap_seed_min=min(values),ap_seed_max=max(values))
  summaries.append(r)
 write('data/condition_summary.csv',summaries)
 overview=[]
 for city in CITIES:
  rows=[r for r in benefits if r['city']==city]
  overview.append({'city':city,'positive_mean_conditions':sum(float(r['mean_benefit'])>0 for r in rows),'negative_mean_conditions':sum(float(r['mean_benefit'])<0 for r in rows),'conditions':len(rows)})
 prediction_groups=collections.defaultdict(list)
 with gzip.open(OUT/'data/predictions.csv.gz','rt',newline='') as f:
  for r in csv.DictReader(f):prediction_groups[tuple(r[k] for k in ['city','condition','source','fraction','seed','model'])].append((float(r['p_raw']),int(r['y'])))
 calibration=[]
 for key,values in prediction_groups.items():
  values=np.array(values);bins=np.minimum((values[:,0]*10).astype(int),9)
  for b in range(10):
   selected=values[bins==b]
   if len(selected):calibration.append(dict(zip(['city','condition','source','fraction','seed','model'],key))|{'bin':b,'n':len(selected),'mean_probability':float(selected[:,0].mean()),'observed_rate':float(selected[:,1].mean())})
 assert sum(r['n'] for r in calibration)==status['prediction_rows']
 write('data/calibration_bins.csv',calibration)
 baseline=[r for r in metrics if r['condition'] in ['local_full','source_only']]
 pooled=[r for r in benefits if r['source']=='pooled']
 extrap=[]
 for r in extra:
  observed=int(r['target_observed'])
  if observed and r['target_outside_range']!='' and int(r['target_outside_range'])/observed>.2:
   extrap.append({**r,'outside_fraction':int(r['target_outside_range'])/observed})
 extrap.sort(key=lambda r:(r['city'],r['source'],r['feature']))
 conclusion='Transfer effects are mixed across cities, model families, source cities and adaptation fractions. Adding source data sometimes helps and sometimes harms the exactly matched local-only model; there is no demonstrated universal transfer benefit.'
 docs={
 '01_step_by_step.md':f'''# Phase 5 — complete step-by-step procedure

Computational status: **validated PASS**. The study remains retrospective and scientifically provisional. The phase 4 primary improvement criterion failed; phase 5 is an explicitly requested descriptive extension.

1. **Verify prior releases.** Check phase 4 validation and every phase 4 output checksum; its input loader also verifies phase 3. Reuse the same 1,201 training site-years from 2024, 1,241 test site-years from 2025, primary 50 m labels, 9-feature allowlist and fixed spatial groups. Do not alter earlier results.
2. **Freeze the transfer protocol.** Save `protocol/phase5_transfer_spec.md`, its hash and `qa/experiment_registry.json` before fitting. Predeclare conditions, fixed model capacities, seeds, sample fractions and evaluation formulas. Earlier model results are already known; no preregistration is claimed.
3. **Construct the common target tests.** For each of three target cities and its five frozen 2025 folds, identify the identical held-out sites for every experimental condition.
4. **Construct eligible earlier-year pools.** The local pool contains 2024 target-city rows; each source pool contains one other city's 2024 rows. Purge every pool within 1,500 m of the held-out target centers. The two source pools' union is the pooled-source condition. Preserve exact IDs, counts and separation audits.
5. **Build baseline conditions.** Fit local-full, each-source zero-shot and pooled-source zero-shot on their eligible pools. These deterministic conditions use seed 0 and are run once per model/fold, not copied across the 20 sampling seeds.
6. **Draw adaptation samples.** For each seed 20261001–20261020, uniformly permute the sorted local pool. Take ceil(10% × n) and ceil(25% × n), with the smaller sample nested in the larger. Do not stratify, redraw or change samples based on outcomes. Freeze all sampled IDs before fitting.
7. **Create matched comparisons.** For each sample, fit target-only and each individual/pooled source plus exactly that same sample. The only membership difference between an augmented model and its paired control is the source pool.
8. **Fit fixed models with local preprocessing.** M0 uses background-only unpenalized logistic; M1 uses all 9 primary features and logistic C=1; M2 uses those features and XGBoost depth 2/lambda 10. Fit imputation and any scaling only on each condition's own training rows. Do not tune, recalibrate or select predictors from 2025 labels.
9. **Handle small samples honestly.** Single-class training produces a flagged constant equal to its training prevalence. Empty training sets would be unsupported. This run has {status['single_class_fits']} single-class unique fits and {status['unsupported']} unsupported evaluations. Cache only identical model/sorted-membership fits; save every unique pipeline or constant artifact.
10. **Predict the common held-out cohort.** Aggregate each target/condition/model/seed's five folds into one complete 2025 prediction vector. This run has {status['model_evaluations']:,} model evaluations, {status['unique_fits']:,} unique fits, 1,476 complete target-year vectors and {status['prediction_rows']:,} prediction rows. The repeated rows across conditions are not new independent observations.
11. **Calculate transfer quantities.** Transfer gap is local-full AP minus source-only AP. Matched benefit is augmented AP minus the exactly matched target-only AP. Improvement over zero-shot is reported separately. Compute full ranking, probability and top-decile metrics, retaining all conditions rather than selecting a winner.
12. **Summarize sampling variability and coverage.** For each city/source/fraction/model, report all 20 seed benefits and their mean, sample SD, empirical 2.5/97.5 percentiles and positive/negative counts. These are sampling summaries, not confidence intervals. Report source-range extrapolation and missingness without using target labels to modify training.
13. **Validate and document.** Reconstruct every pool and sample, verify exact matched controls and temporal/spatial separation, reload all unique artifacts, independently check their preprocessing and reproduce every held-out probability. Refit representative conditions and reconcile every metric, gap, seed summary and extrapolation value. Publish plots, step-by-step methods, results, reproduction instructions and checksums.

Continue with [methods](02_methods.md), [results](03_results.md), [reproduction](04_reproduce.md) and [artifact guide](05_artifacts.md).
''',
 '02_methods.md':'''# Methods and limitations

## Population, timing and comparison design

The phase 2 address-continuity-supported cohort and phase 3 environmental features are unchanged. Training uses 2024 occurrences reported before January 1, 2025. Testing uses archived 2025 nearby robbery/burglary occurrences. Prior-year backgrounds remain report-filtered, with Buffalo creation timestamps only a proxy. Exposure uses retrospective monthly membership, not verified operation. Both outcome years were examined earlier.

For each target city and its five phase 4 spatial groups, keep the same 2025 test sites across all conditions. Retain only 2024 training centers at least 1,500 m WGS84 from those tests. This prevents previous-year labels from the held-out neighborhood from entering training. Unlike phase 4's simultaneous all-city fold holdouts, phase 5 purges against one target-city fold at a time; its local/source pools should not be mistaken for the original phase 4 fitted memberships.

Local-full is the all-available-local-label reference. Each-source and pooled-source zero-shot use no target labels. For seeds 20261001–20261020, uniformly permute the row-ID-sorted eligible local pool, then choose ceil(10% × pool size) and ceil(25% × pool size). Fractions are applied separately within each fold's eligible pool, not the entire city's cohort. The samples overlap and the 10% subset is nested in the 25% subset. No class balancing or outcome-dependent redraws occur. Target-only controls and all augmented conditions use precisely the same selected earlier-year target rows.

## Models, capacity and preprocessing

Model capacities are fixed from the original transfer plan, not optimized against the restart's test performance. M0 is unpenalized logistic on log1p background crime. M1 is L2 logistic C=1 with all 9 primary predictors. Logistic settings are lbfgs, max_iter=3000, tol=1e-8. M2 is CPU XGBoost with 150 trees, depth 2, lambda 10, learning rate .05, min_child_weight=5, subsample=colsample_bytree=1, histogram trees, seed 20261001 and one thread. No class weights or oversampling.

Each training membership learns its own median imputer, preserving entirely missing columns with a recorded zero fallback. Logistic models then learn a StandardScaler on that imputed training set. No phase 5 sigmoid calibration is fitted; native probabilities are assessed as produced. Metadata, city, coordinates, exposure and labels are not predictors. A single-class fit predicts its empirical prevalence, possibly exactly zero or one, and is flagged. It is never rescued with test labels. An empty pool would be recorded unsupported.

Identical sorted training memberships and model families share a cached fit. Distinct memberships never share learned preprocessing. All unique pipelines and constant predictors are saved with hashes and exact membership. Predictions may be computed for all 2025 rows for cache efficiency, but only each condition's own held-out test rows enter its metrics. Test features and labels never determine fitted statistics or parameters.

## Metrics and interpretation

AUPRC is non-interpolated average precision. Also report ROC-AUC, Brier score, ten equal-width-bin calibration error, mean predicted probability minus prevalence and top-decile precision/recall/lift. The top decile is exactly ceil(0.1*n), with row-ID tie-breaking. Undefined metrics remain missing. No post-test threshold selection or probability recalibration is performed.

Transfer gap = local-full AP − source-only AP; positive means local-full ranks better. Matched transfer benefit = source-plus-target AP − exactly matched target-only AP; positive means adding source labels improves ranking for that sample. Improvement over zero-shot only demonstrates a benefit from adding target labels, and cannot by itself establish a benefit from source data. A negative benefit is a substantive result, not a sample to discard.

For each source/target/model/fraction, summarize 20 paired seed differences using mean, sample SD, empirical 2.5/97.5 percentiles and positive/negative counts. Percentiles describe randomness in choosing earlier target labels; they are not population confidence intervals, and the 20 seeds are not independent test cohorts. Models, fractions and source choices are multiple descriptive comparisons, not separately confirmed effects. Positive average ranking benefit does not establish calibrated probabilities or a causal effect.

The feature-range table compares all observed 2025 target values with observed 2024 other-city ranges, separately for every feature/source. Missing values are counted separately. This city-level diagnostic uses no target outcomes, does not choose models and is not a fold-specific preprocessing step. The figures show mean paired AP benefits and native Brier scores; they do not imply statistical significance.

## Remaining research gates

The primary numerical comparison is reported in the phase 4 results. Transfer experiments do not provide automatic scientific approval. Independent offense, linkage, facility/continuity, Buffalo precision, boundary and feature-schema reviews remain pending. City sample sizes are highly unequal, and small adaptation samples often have one class. Coordinate revisions and up-to-50-m identity drift can change neighborhood assignments. Missing ACS attributes require training-only imputation, which cannot recover their true values. Monthly membership implies survival selection, municipal clipping can truncate backgrounds, and later-retrieved archived data do not reconstruct historical database vintages. These nearby-crime outcomes are not verified ATM attacks, and no deployment or location-optimization claim is made.
''',
 '03_results.md':f'''# Phase 5 results

**Computational validation: PASS.** Completed {status['model_evaluations']:,} model evaluations using {status['unique_fits']:,} unique saved models, {status['prediction_rows']:,} predictions and 1,476 complete target-year evaluation vectors. All training is from 2024 and all testing from 2025. There are {status['single_class_fits']} constant single-class fits, {status['unsupported']} unsupported evaluations and {len(warnings)} captured estimator-warning rows.

{conclusion}

## Direction of mean matched benefits

{table(overview,['city','positive_mean_conditions','negative_mean_conditions','conditions'])}

These counts describe the 18 source/fraction/model combinations per city. They are not independent significance tests, and a positive mean does not imply that every seed benefits.

## Pooled-source matched benefits

{table(pooled,['city','fraction','model','mean_benefit','sd','seed_p025','seed_p975','negative_seeds'],['mean_benefit','sd','seed_p025','seed_p975'])}

The paired target-only control always uses exactly the same earlier target rows. `seed_p025` and `seed_p975` are empirical percentiles across the same 20 sampling seeds, **not confidence intervals**. The full individual-source and pooled-source table follows below.

## Local-full and zero-shot performance

{table(baseline,['city','condition','source','model','n','positives','average_precision','brier_score','ece_10bins','top_decile_recall'],['average_precision','brier_score','ece_10bins','top_decile_recall'])}

{table(gaps,['city','source','model','local_ap','source_ap','transfer_gap'],['local_ap','source_ap','transfer_gap'])}

A positive gap means the source-only model is worse than local-full. These models use fixed phase 5 capacities and target-specific purging; their scores need not equal phase 4's tuned models.

## Every matched source/fraction/model comparison

{table(benefits,['city','source','fraction','model','mean_benefit','seed_p025','seed_p975','positive_seeds','negative_seeds'],['mean_benefit','seed_p025','seed_p975'])}

## Probability accuracy and sampling variation

All 1,476 evaluations include native Brier, ECE, mean calibration error and top-decile metrics in `data/metrics.csv`. `data/condition_summary.csv` summarizes these across seeds while preserving the target sample size and AP seed range. The pooled-source probability figure compares mean Brier for augmented and matched local-only conditions, with local-full as a reference; lower is better. Calibration bins for every complete test vector are saved in `data/calibration_bins.csv`; the calibration figure shows local-full and pooled zero-shot references without averaging seed predictions into a new ensemble. The curves are descriptive, with no independent-sample inference. No recalibration or post-test choice between models was made. Negative seed counts and constant fits should be considered when interpreting seemingly large benefits in small cities.

## Feature extrapolation

{len(extrap)} source/target/feature rows have more than 20% of observed target values outside the observed source range. All 81 source/target/feature rows, including missingness, are preserved in `data/extrapolation.csv`. A range mismatch indicates limited source coverage; it is not proof of failure, and it was not used to select sources or features.

## Validation and scientific status

Validation reconstructed every local/source pool and deterministic sample, verified the exactly matched controls, reproduced every saved model's held-out probabilities and training-only preprocessing, independently refit representative local/augmented models, and reconciled all metrics, gaps, benefits, seed summaries and extrapolation calculations. Checksums and model artifacts are retained.

The experiments remain descriptive. Independent research review is pending, and both outcome years were inspected previously. No universal transfer, calibrated operational risk or confirmatory scientific success is claimed.
''',
 '04_reproduce.md':'''# Reproduction

## 1. Verify prerequisites

Phases 1–4 must be present in this restart. Phase 4 validation must be PASS and its output hashes unchanged. The phase 5 loader also invokes the phase 4 input checks against the phase 3 release. It reuses saved spatial groups and does not rerun phase 4 fitting.

## 2. Use the recorded Python environment

The repository `.venv` has the required packages. For a standalone copy, create an environment and install `requirements-phase5.txt`, which includes the phase 4 dependencies. Actual versions and timestamps are recorded in `qa/run_environment.json`. All required data are local; no API keys, new downloads or parent-project data are needed. Do not run Python with `-O`, which disables assertions.

## 3. Freeze plans without fitting

From the repository root:

```bash
.venv/bin/python restart_3_0/scripts/run_phase5.py --prepare-only
```

This verifies the protocol and input releases, constructs the target-specific test and training pools, freezes 20-seed samples, writes the registry and prepares 2,460 plans / 7,380 model evaluations. It invalidates any prior phase 5 validation; continue through the remaining steps before using the release as complete.

## 4. Run the full transfer ladder

```bash
.venv/bin/python restart_3_0/scripts/run_phase5.py
```

The command verifies the same frozen splits and fits all registered conditions. Each model uses one thread; progress prints after each target-fold group of 164 plans. The cache reuses identical memberships within the run. It is not an interrupted-run disk-resume mechanism: rerunning rebuilds the full experiment. Do not change the specification or frozen samples silently; create a documented version amendment for a changed design.

## 5. Validate all outputs

```bash
.venv/bin/python restart_3_0/scripts/validate_phase5.py
```

Validation checks all exact memberships and samples, every model artifact and held-out prediction, training-only medians/scalers, constant fallbacks, all metric vectors and every transfer summary. It also independently refits representative local and augmented models. It does not refit every unique model from scratch. See `qa/validation.json` and `qa/verified_pool_separation.csv`.

## 6. Generate documentation and figures

```bash
.venv/bin/python restart_3_0/scripts/report_phase5.py
```

Reporting requires validation PASS and generates the step-by-step guide, methods, complete results, condition summaries, PNG/PDF figures, manifests and overall restart phase status. The plotting cache is under `/tmp`. In a standalone folder, replace the repository-prefixed commands with `python scripts/...`.

## 7. Review results without changing the test

Read baseline gaps separately from exactly matched benefits. Inspect each source, fraction and model; report negative outcomes and single-class fallbacks. Seed percentiles are not confidence intervals. Do not select a favorable source/model and call it confirmed on these already-inspected data.

Input and implementation manifests use paths relative to the restart root; output manifests use paths relative to `results/phase5`. Recompute SHA-256 of every referenced file to verify integrity. Only load trusted joblib artifacts generated by this workflow. Scientific acceptance remains separate from computational PASS.
''',
 '05_artifacts.md':'''# Artifact guide

| File or folder | Purpose |
|---|---|
| data/modeling_cohort.csv | Reused annual labels, feature keys, city and frozen spatial assignments |
| data/splits.csv | Exact test, local and source pools for every target/fold |
| data/target_samples.csv | Every 10%/25% earlier-target subset for all 20 seeds |
| data/predictions.csv.gz | Every held-out 2025 probability, outcome and experimental key |
| data/metrics.csv | 1,476 full target-year metric vectors |
| data/calibration_bins.csv | Native observed rates, mean probabilities and bin counts for every test vector |
| data/condition_summary.csv | Per-condition seed-mean metrics and AP sampling ranges |
| data/transfer_gaps.csv | Local-full minus source-only AP |
| data/transfer_benefits.csv | Per-seed augmented minus exactly matched target-only AP, plus improvement over zero-shot |
| data/benefit_summary.csv | All 54 city/source/fraction/model benefit summaries across 20 seeds |
| data/extrapolation.csv | All 81 source/target/feature observed-range and missingness diagnostics |
| models/ | Every unique fitted pipeline or explicit constant model |
| qa/training_members.csv.gz | Exact training membership of each unique fit |
| qa/model_fits.csv | Fixed parameters, membership hashes, class counts, fallback flags and artifact hashes |
| qa/preprocessing.csv | Training medians/scalers and all-empty-column flags for nonconstant fits |
| qa/evaluations.csv | 7,380 condition/fold/model evaluations, cached fit references and separation |
| qa/verified_pool_separation.csv | Independently reconstructed candidate/retained/purged counts and minimum distances |
| qa/warnings.csv | Captured estimator warnings; header-only if none |
| qa/protocol_freeze.json, qa/split_freeze.json | Before-fitting protocol and sample fingerprints |
| qa/experiment_registry.json | Fixed seeds, model settings, fractions and previous primary-gate status |
| qa/run_environment.json | Actual packages, timestamps and thread count |
| qa/validation.json, qa/status.json | Computational validation, run totals and distinct scientific-review status |
| qa/input_manifest.csv, qa/implementation_manifest.csv, qa/output_manifest.csv | Input, final code and output SHA-256 manifests |
| figures/ | Mean matched-benefit, pooled-source Brier and reference calibration figures in PNG/PDF |

The `site_id` in prediction files is the site-year **row_id** used in phase 4; it is not a permanent machine identifier. Join to phase 2 using row_id. `physical_site_id` in the modeling cohort is the coordinate-based phase 2 identity and may change at the same address between years. Repeated predictions across conditions/seeds are evaluations of the same held-out sites, not independent new samples. `fraction=1, seed=0` denotes local-full; `fraction=0, seed=0` denotes deterministic zero-shot; adaptation/control rows use the registered fractions and seeds.
'''}
 for name,text in docs.items():(OUT/'docs'/name).write_text(text)
 # All source/model combinations are shown on one common signed color scale.
 limit=max(abs(float(r['mean_benefit'])) for r in benefits);fig,axes=plt.subplots(1,3,figsize=(15,7),layout='constrained')
 for ax,city in zip(axes,CITIES):
  sources=[c for c in CITIES if c!=city]+['pooled'];labels=[(s,m) for s in sources for m in MODELS]
  values=np.array([[float(next(r['mean_benefit'] for r in benefits if r['city']==city and r['source']==s and r['model']==m and float(r['fraction'])==f)) for f in [.1,.25]] for s,m in labels])
  im=ax.imshow(values,cmap='RdBu',vmin=-limit,vmax=limit,aspect='auto');ax.set_xticks([0,1],['10% local','25% local']);ax.set_yticks(range(len(labels)),[s+' · '+m for s,m in labels]);ax.set_title(city)
  for i in range(len(labels)):
   for j in range(2):ax.text(j,i,f'{values[i,j]:+.3f}',ha='center',va='center',color='white' if abs(values[i,j])>.65*limit else 'black',fontsize=9)
 fig.colorbar(im,ax=axes,label='Mean paired AP benefit: augmented − matched local-only',shrink=.7)
 fig.suptitle('2024 labels → 2025 tests · 20 fixed sampling seeds · descriptive means')
 for ext in ['png','pdf']:fig.savefig(OUT/f'figures/matched_transfer_benefits.{ext}',dpi=160)
 plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained');colors={'M0':'#657786','M1':'#167d9a','M2':'#df7b36'}
 for ax,city in zip(axes,CITIES):
  for model in MODELS:
   for condition,style,source in [('target_only','--','target'),('source_plus_target','-','pooled')]:
    values=[next(r['mean_brier_score'] for r in summaries if r['city']==city and r['model']==model and r['condition']==condition and r['source']==source and float(r['fraction'])==f) for f in [.1,.25]]
    ax.plot([10,25],values,style,marker='o',color=colors[model],label=model+(' local only' if condition=='target_only' else ' pooled + local'))
   local=next(float(r['brier_score']) for r in metrics if r['city']==city and r['model']==model and r['condition']=='local_full');ax.axhline(local,ls=':',color=colors[model],alpha=.7)
  ax.set(title=city,xlabel='Earlier local-label fraction (%)',ylabel='Mean native Brier score (lower is better)');ax.set_xticks([10,25]);ax.grid(alpha=.2)
 axes[0].legend(fontsize=7);fig.suptitle('Probability accuracy · solid: pooled + local; dashed: matched local; dotted: local-full')
 for ext in ['png','pdf']:fig.savefig(OUT/f'figures/pooled_source_brier.{ext}',dpi=160)
 plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
 for ax,city in zip(axes,CITIES):
  for model in MODELS:
   for condition,source,style in [('local_full','target','-'),('source_only','pooled','--')]:
    rows=sorted([r for r in calibration if r['city']==city and r['model']==model and r['condition']==condition and r['source']==source],key=lambda r:r['bin'])
    ax.plot([r['mean_probability'] for r in rows],[r['observed_rate'] for r in rows],style,marker='o',color=colors[model],label=model+(' local-full' if condition=='local_full' else ' pooled zero-shot'))
  ax.plot([0,1],[0,1],':',color='black',alpha=.5);ax.set(title=city,xlim=(0,1),ylim=(0,1),xlabel='Mean predicted probability',ylabel='Observed positive fraction')
 axes[0].legend(fontsize=7);fig.suptitle('Held-out native calibration · solid: local-full; dashed: pooled zero-shot')
 for ext in ['png','pdf']:fig.savefig(OUT/f'figures/reference_calibration.{ext}',dpi=160)
 plt.close(fig)
 (OUT/'README.md').write_text(f'''# Phase 5 — city-transfer experiments, 2024 → 2025

Computationally complete and validated: **{status['model_evaluations']:,} model evaluations**, **{status['unique_fits']:,} unique saved fits**, **{status['prediction_rows']:,} held-out predictions**, **20 sampling seeds**. Independent scientific review remains pending.

{conclusion}

- [Complete step-by-step procedure](docs/01_step_by_step.md)
- [Methods and limitations](docs/02_methods.md)
- [Full results and interpretation](docs/03_results.md)
- [Reproduction commands](docs/04_reproduce.md)
- [Artifact guide](docs/05_artifacts.md)
- [Transfer benefits](data/benefit_summary.csv), [transfer gaps](data/transfer_gaps.csv), [all metrics](data/metrics.csv), [validation](qa/validation.json)

![Mean matched transfer benefits](figures/matched_transfer_benefits.png)

![Native probability accuracy](figures/pooled_source_brier.png)

![Reference native calibration](figures/reference_calibration.png)

The 20-seed percentiles are sampling summaries, not confidence intervals. Phase 4's primary improvement criterion failed; these are descriptive follow-on experiments, not confirmation or deployment approval.
''')
 paths=[ROOT/'scripts'/n for n in ['run_phase5.py','phase5_common.py','validate_phase5.py','report_phase5.py','run_phase4.py','phase4_common.py']]+[ROOT/'protocol/phase5_transfer_spec.md',ROOT/'requirements-phase5.txt',ROOT/'requirements-phase4.txt',ROOT/'requirements.txt']
 write('qa/implementation_manifest.csv',[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths])
 paths=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='output_manifest.csv')
 write('qa/output_manifest.csv',[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths])
 p=ROOT/'reports/phase_status.json';overall=json.loads(p.read_text());overall.update(phase_5='computationally_complete',phase_5_validation='PASS',phase_5_model_evaluations=status['model_evaluations'],phase_5_unique_fits=status['unique_fits'],phase_5_prediction_rows=status['prediction_rows'],phase_5_confirmatory_complete=False);p.write_text(json.dumps(overall,indent=2)+'\n')
 print(conclusion);print('Reports, figures and final manifests generated.',flush=True)
if __name__=='__main__':main()
