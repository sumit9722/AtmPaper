"""Produce phase 4 temporal / phase 5 Markdown reports and static figures."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/atm-phase45-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from temporal_common import *
def mdtable(rows,columns):
 def val(x):return f'{x:.4f}' if isinstance(x,float) else str(x)
 return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+'\n'.join('| '+' | '.join(val(r.get(c,'')) for c in columns)+' |' for r in rows)+'\n'
def doc(folder,name,text):
 p=folder/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.strip()+'\n')
def figure(folder,name):
 for ext in ['png','pdf']:plt.savefig(folder/'figures'/f'{name}.{ext}',bbox_inches='tight',dpi=170)
 plt.close()
def main():
 for f in [DATA,P4,P5]:(f/'figures').mkdir(exist_ok=True)
 s4=json.loads((P4/'qa/status.json').read_text());s5=json.loads((P5/'qa/status.json').read_text());summary=read(DATA/'qa/city_year_summary.csv');m4=read(P4/'data/metrics.csv');comp=read(P4/'data/paired_ap_comparisons.csv');m5=read(P5/'data/metrics.csv');benefits=read(P5/'data/benefit_summary.csv');gaps=read(P5/'data/transfer_gaps.csv')
 limitations='''These are retrospective research results, not confirmed ATM-attack predictions or operational risk scores. The 2025 outcomes were inspected in the earlier phase 4 analysis, so 2025 is not a pristine confirmatory holdout. Training uses report-date-filtered latest extracts, not a database frozen at the historical cutoff. Buffalo uses record creation as a report-availability proxy. Monthly listings support inferred operation; they do not establish exact opening or closing dates. The 2024 address links and up-to-50-m coordinate revisions require independent review. Crime harmonization/linkage, facility identity, Buffalo coordinate precision, continuity, and feature acceptance remain research gates. No independent human sign-off is claimed. Small Buffalo/Rochester samples and limited positives make their estimates unstable. Current municipal boundaries and retrospective archive availability are additional limitations.'''
 docs='''- [What was completed](docs/01_work_completed.md)
- [How it was done](docs/02_methods.md)
- [Results and interpretation](docs/03_results.md)
- [Reproduction and files](docs/04_reproduce.md)'''
 pooled=[{k:(float(r[k]) if k in ['average_precision','roc_auc','brier_score'] else r[k]) for k in ['model','average_precision','roc_auc','brier_score']} for r in m4 if r['city']=='ALL' and r['probabilities']=='raw']
 comparisons=[{'comparison':r['comparison'],'AP difference':float(r['ap_difference']),'95% lower':float(r['ci_low']),'95% upper':float(r['ci_high'])} for r in comp if r['city']=='ALL']
 doc(P4,'README.md',f'''# Phase 4 temporal supplement

The retrospective temporal computation and automated validation are complete. This extends the preserved [same-year phase 4 release](../README.md), resolving its missing earlier training year. Full confirmatory research acceptance is still pending.

{s4['train_cohort_rows']} eligible 2024 sites train the models; {s4['test_cohort_rows']} 2025 sites form the test cohort. Fifteen outer-fold models use nested spatial validation and training-only calibration. No comparison passed the prespecified numerical AP-gain gate.

{docs}

{mdtable(pooled,['model','average_precision','roc_auc','brier_score'])}

See [validation](qa/validation.json), [status](qa/status.json), [paired comparisons](data/paired_ap_comparisons.csv), and [the shared data](../../temporal_data/README.md).

![Temporal AP differences](figures/paired_ap_intervals.png)''')
 doc(P4,'docs/01_work_completed.md',f'''# Work completed

Acquired 12 additional monthly ATM snapshots, 2023 police records for all three cities, and pre-2024 Census context. Constructed the earlier cohort and reran M0/M1/M2 using 2024 training and 2025 testing with 1,500-m train/test separation. Saved all 15 models, training memberships, nested searches, preprocessing statistics, training-only calibration predictions, test predictions and metrics. Computed 2,000 city-stratified spatial-block bootstrap replicates per city/pooled evaluation. Automated validation is {s4['validation']}.

Two issues were resolved before fitting: inconsistent identifiers in the archived Census map service (replaced with matching official 2022 TIGER/Line polygons), and widespread 2024 ATM coordinate revisions (address continuity amendment). Both decisions are documented in the protocol folder. The exact-coordinate full-year 2024 cohort is empty; the temporal study relies on the explicitly amended continuity rule.

{limitations}''')
 doc(P4,'docs/02_methods.md','''# Methods

Predict nearby police-recorded robbery/burglary within 50 m over the full target year. Retain supported full-year exposure (366 days in 2024, 365 in 2025). For 2024 labels, retain only events with a report/creation date before 2025-01-01. The 2025 labels remain identical to the earlier phase 2 release.

Freeze ACS 2018–2022 estimates, released 2023-12-07, across both years. Use matching 2022 TIGER/Line polygons, EPA Smart Location Database 2021, previous-December statewide ATM competition, and previous-year robbery/burglary in the >200–500-m annulus reported before the prediction cutoff. Thus 2024 uses 2023 crime and December 2023 competition; 2025 uses 2024 crime and December 2024 competition. This changes the ACS vintage relative to phase 4 v1, so the v1/v2 difference is not an isolated time-split experiment.

Reuse frozen 2025 spatial folds. For each held-out fold, exclude 2024 locations within 1,500 m of every test site. Within the remaining 2024 training set, use spatial groups and the same purge for hyperparameter selection. M0 is unpenalized logistic regression on log1p prior crime; M1 is ridge logistic regression on all 14 predictors (C in 0.1, 1, 10); M2 is 150-tree XGBoost (depth 2/3, lambda 1/10, learning rate .05). Median imputation and logistic scaling fit only on each training subset. Sigmoid calibration uses inner out-of-fold 2024 predictions, never 2025 labels.

AP is non-interpolated average precision. Also report ROC-AUC, Brier, 10-bin expected calibration error, calibration mean error and top-decile precision/recall/lift. Compare M1/M2 against M0 on paired test rows. Resample 2-km blocks within city 2,000 times; omit replicates with no positive outcome and report the valid count. The numerical criterion is AP gain >= .01 with a positive 95% lower bound. Meeting a numerical criterion would not remove the independent review requirements.''')
 doc(P4,'docs/03_results.md',f'''# Results

{mdtable(pooled,['model','average_precision','roc_auc','brier_score'])}

{mdtable(comparisons,['comparison','AP difference','95% lower','95% upper'])}

M1's pooled AP improvement is uncertain; M2's pooled point estimate is below M0. Every pooled and city-specific AP-difference interval includes zero. The working numerical gate therefore fails everywhere. The results do not establish reliable added predictive value from the environmental feature set. This negative finding is retained; phase 5 is a descriptive transfer study, not evidence that the phase 4 scientific gate passed.

The 2025 cohort has 650 positives among 1,192 sites (prevalence 54.53%); pooled metrics are dominated by New York City. Buffalo has 14/46 positives and Rochester 7/29. All city-specific, native and sigmoid-calibrated metrics are in `data/metrics.csv`. Rochester has 1,999 valid bootstrap replicates; the other strata have 2,000.

{limitations}''')
 common_commands='''.venv/bin/python scripts/build_temporal_data.py
.venv/bin/python scripts/run_phase4_temporal.py
.venv/bin/python scripts/run_phase5.py
.venv/bin/python scripts/validate_phase45.py
.venv/bin/python scripts/report_phase45.py'''
 for folder in [P4,P5]:doc(folder,'docs/04_reproduce.md',f'''# Reproduction and files

From the repository root, install `requirements-phase5.txt` into the virtual environment. All acquired raw data are cached. Reproduction uses no Census requests or API key:

```bash
{common_commands}
```

The acquisition script has separate bounded, cached `history`, `crime`, `geography`, `tiger`, and `acs` stages. Do not refetch valid cached inputs. Only `acs` needs the user's key through hidden input or an environment variable; no key is stored in source, URLs, or sidecars. The incompatible archived `geography` response is preserved for audit, but models use `tiger`.

`data/` contains predictions, metrics and experiment/sampling tables. `qa/` contains splits, preprocessing, memberships, warnings, status, validation and release hashes. Large transfer prediction and membership tables use `.csv.gz`, readable with Python gzip/csv or pandas compression inference. `figures/` contains PNG and PDF figures. Temporal phase 4 saves joblib models under `models/`; phase 5 saves reproducible fit membership/parameter/preprocessing audits instead of thousands of model binaries. Never load untrusted joblib files.

`protocol/phase45_temporal_extension_v2.md` specifies the experiments. Boundary and continuity addenda document pre-fit corrections. `results/temporal_data/qa/` preserves source and protocol hashes. Frozen split hashes are checked before rerunning. All new files remain below GitHub's 100-MB per-file limit. No remote push is performed.

Validation is a separate computation checking source integrity, outcome reconciliation, historical membership, temporal/spatial separation, exact seeded adaptation subsets, training-only preprocessing, saved temporal-model predictions, metrics and matched benefits. It is not independent human scientific review.''')
 base=[{'city':r['city'],'source':r['source'],'model':r['model'],'local AP':float(r['local_ap']),'source AP':float(r['source_ap']),'transfer gap':float(r['transfer_gap'])} for r in gaps if r['source']=='pooled']
 brief=[{'city':r['city'],'fraction':r['fraction'],'model':r['model'],'mean benefit':float(r['mean_benefit']),'SD':float(r['sd']),'negative seeds':r['negative_seeds']} for r in benefits if r['source']=='pooled']
 doc(P5,'README.md',f'''# Phase 5 city-transfer results

The prespecified retrospective transfer experiment ladder and automated validation are complete. This is a descriptive analysis: the phase 4 numerical gate did not pass, and independent research review remains pending.

Completed {s5['model_evaluations']:,} model evaluations across {s5['plans']:,} city/fold/training conditions, using {s5['unique_fits']:,} unique fits and {s5['prediction_rows']:,} held-out predictions. Each city has local-full, both single-source zero-shot, pooled-source, and source-plus-10%/25% target experiments with exactly matched target-only controls across 20 fixed seeds.

{docs}

{mdtable(base,['city','source','model','local AP','source AP','transfer gap'])}

[Detailed benefit distributions](data/benefit_summary.csv), [all metrics](data/metrics.csv), [validation](qa/validation.json), [status](qa/status.json), [shared data](../temporal_data/README.md).

![Matched pooled-source benefits](figures/pooled_transfer_benefit.png)''')
 doc(P5,'docs/01_work_completed.md',f'''# Work completed

Implemented and executed the complete planned transfer ladder for New York City, Buffalo and Rochester. All model training/adaptation labels come from 2024; all evaluation labels come from the identical frozen 2025 target test sets. The experiments cover M0, M1 and M2, each source city separately, both sources pooled, 10% and 25% earlier-target samples, and exactly matched target-only controls. Twenty fixed seeds produce sampling distributions instead of a selected favorable draw.

Saved {s5['model_evaluations']:,} evaluations, {s5['unique_fits']:,} unique fit audits, {s5['prediction_rows']:,} predictions, all sampling memberships, training preprocessing, AP/ROC/calibration/top-decile metrics, transfer gaps, matched benefits, negative-seed counts, feature extrapolation diagnostics and figures. Validation is {s5['validation']}. Unsupported conditions: {s5['unsupported']}. Single-class unique fits requiring the prespecified constant-prevalence fallback: {s5['single_class_fits']}.

{limitations}''')
 doc(P5,'docs/02_methods.md','''# Methods

The shared temporal cohort uses the audited earlier-year construction described in `results/temporal_data/README.md`. For each target city and frozen 2025 test fold, the local pool contains 2024 target sites at least 1,500 m from test locations. Source pools contain only other cities' eligible 2024 sites. All conditions use the identical test locations and outcomes.

Local-full fits all eligible local training rows. Source-only fits either other city, or both pooled. For seeds 20261001–20261020, uniformly permute the sorted target pool and take ceil(10% * n) and ceil(25% * n), nesting the smaller sample in the larger. Sampling ignores class labels; do not redraw unfavorable samples. For each sampled subset, fit target-only and each source-plus-target condition using exactly that subset.

Models use fixed parameters, prespecified before fitting: M0 unpenalized logistic regression; M1 C=1 ridge logistic regression; M2 150-tree XGBoost, depth 2, lambda 10, learning rate .05. Fit median imputation and logistic scaling on the condition's own training rows. Single-class training uses a flagged constant empirical-prevalence probability; empty pools are unsupported. No target-test tuning, recalibration, feature selection or threshold fitting occurs. Identical sorted training memberships and model families share cached fits. Caching does not share learned preprocessing across different training sets.

Pool held-out folds once per target/condition/model/seed. Transfer gap = local-full AP minus source-only AP; positive means source-only is worse. Matched transfer benefit = source-plus-target AP minus AP from the identical target-only subset; positive means source data helps. Also report improvement over zero-shot separately: it cannot establish source-data benefit alone. Summarize 20 seed differences with mean, sample SD, empirical 2.5/97.5 percentiles and negative-seed count. These percentiles describe variation in sampled earlier labels, not population confidence intervals or independent test-set replications.

Assess native probabilities using Brier, ECE, mean calibration error and calibration plots. No phase 5 sigmoid fit is performed. Feature extrapolation compares observed 2025 target values with other-city 2024 observed ranges, reporting missing counts separately. This diagnostic uses no target outcomes and does not select models.''')
 doc(P5,'docs/03_results.md',f'''# Results and interpretation

## Pooled-source versus local-full

{mdtable(base,['city','source','model','local AP','source AP','transfer gap'])}

A negative transfer gap means pooled sources outperform this local-full model on the shared test data; local-full is a benchmark, not a mathematical upper bound. Compare each model and city separately. The full table also reports both individual source cities.

## Does source data help with limited local labels?

{mdtable(brief,['city','fraction','model','mean benefit','SD','negative seeds'])}

Pooled-source M2 has positive mean matched benefits in Buffalo at 10% (+0.0785 AP) and 25% (+0.0858), with no negative seeds in either condition. Rochester M2 also improves on average (+0.0720 and +0.0709), while Rochester M0/M1 have negative mean benefits at both fractions. In New York City, M1 at 10% loses AP in all 20 seeds (mean -0.0243); M2 at 25% improves on average (+0.0109), with one negative seed. These mixed results do not support a universal transfer claim.

Positive matched benefit supports descriptive usefulness of source data for that condition; negative values show negative transfer. The complete 54-row summary includes individual-source results, empirical seed percentiles and positive/negative counts. Never interpret improvement over zero-shot alone as proof of useful transfer. With small local pools, ceil rounding means nominal fractions differ slightly from realized percentages, and single-class controls can be common.

There are {s5['single_class_fits']} unique constant-prevalence fallback fits. Consult the fit/evaluation audits before interpreting gains over tiny target-only models. Calibration and AP can tell different stories; examine Brier and the calibration plots before considering probabilities useful. The phase 4 AP-gain gate failed, so these phase 5 results do not establish confirmatory transportability.

{limitations}''')
 doc(DATA,'README.md',f'''# Shared 2024–2025 temporal data

This separate result folder extends the original data without changing earlier phase releases.

{mdtable(summary,['year','city','full_year_sites','positive_50m'])}

The 2024 cohort has 1,201 sites and 684 positives; the 2025 cohort has 1,192 sites and 650 positives. All confirmatory-eligibility flags are false.

Sources: [NY DFS bank-owned ATM inventory](https://data.ny.gov/Government-Finance/Bank-Owned-ATM-Locations-in-New-York-State/ndex-ad5r), its archived monthly snapshots (December 2023–January 2025), [2022 ACS release information](https://www.census.gov/programs-surveys/acs/news/data-releases/2022/release.html), [official 2022 TIGER/Line block groups](https://www2.census.gov/geo/tiger/TIGER2022/BG/tl_2022_36_bg.zip), and the existing phase 3 EPA SLD2021 sources. Police acquisition endpoints and request provenance are preserved under `data/raw/temporal_extension/crime2023`; 2024/2025 police extracts remain from phase 2.

The ACS 2018–2022 estimates were released December 7, 2023, before both prediction years. Seven county attribute requests and three metadata requests were made, sequentially with pauses and caching; the credential was not saved. All remaining downloads were public and used no Census key.

`data/context_raw.csv` preserves raw feature components and ACS uncertainty/annotation fields; `data/features.csv` applies the frozen 14-feature schema; `data/cohort.csv` stores labels and historical cutoffs. The baseline competition inventories are statewide. Background crime uses the previous year, >200–500 m, and report availability before January 1 of the prediction year. `data/outcome_links_2024.csv` allows direct label reconciliation.

Two pre-fit amendments are essential. The archived ACS2022 map service's identifiers did not match the API; the official 2022 TIGER/Line archive does. The service response is retained but not used for fitting. Exact address-plus-coordinate identities produce zero full-year 2024 sites because of historical coordinate revisions. The amended cohort requires a unique normalized city/address in all 14 snapshots and all locations within 50 m of December 2023 coordinates. Use that baseline coordinate for context and labels. The original exact-identity exposure inventory remains in `qa/`; amended links are in `qa/continuity_links_2024.csv`.

The intervals support inferred 366-day continuity, not verified daily operation. The cohort conditions on later observed survival, which can limit prospective generalization. Compare against the old 2025 cohort with caution: its continuity method is unchanged, while 2024 uses the explicit amendment. No nearest-polygon or outcome-informed identity imputation is used. All raw inputs and protocol changes are checksummed under `qa/`.

{limitations}

Reproduce using the scripts in [phase 5 reproduction instructions](../phase5/docs/04_reproduce.md).''')
 # Paired phase 4 intervals.
 fig,ax=plt.subplots(figsize=(8,5));rows=comp
 for j,r in enumerate(rows):
  v=float(r['ap_difference']);ax.errorbar(v,j,xerr=[[v-float(r['ci_low'])],[float(r['ci_high'])-v]],fmt='o',color='#24577b')
 ax.set_yticks(range(len(rows)),[r['city']+' '+r['comparison'] for r in rows]);ax.axvline(0,color='gray',ls='--');ax.set_xlabel('Paired AP difference (95% spatial-block bootstrap interval)');ax.set_title('Retrospective 2024 → 2025 validation');figure(P4,'paired_ap_intervals')
 fig,axes=plt.subplots(1,3,figsize=(13,4),sharey=True)
 for ax,city in zip(axes,CITIES):
  rows=[r for r in benefits if r['city']==city and r['source']=='pooled'];positions=np.arange(len(rows));vals=[float(r['mean_benefit']) for r in rows]
  ax.bar(positions,vals,color=['#24577b' if v>=0 else '#b55244' for v in vals]);ax.errorbar(positions,vals,yerr=[float(r['sd']) for r in rows],fmt='none',color='black',capsize=3);ax.axhline(0,color='gray');ax.set_xticks(positions,[r['model']+'\n'+str(round(100*float(r['fraction'])))+'%' for r in rows]);ax.set_title(city)
 axes[0].set_ylabel('Matched AP benefit (mean ± seed SD)');fig.suptitle('Pooled sources + earlier target labels versus identical target-only labels');figure(P5,'pooled_transfer_benefit')
 import gzip,csv
 with gzip.open(P5/'data/predictions.csv.gz','rt') as f:pred=[r for r in csv.DictReader(f) if r['condition']=='source_only' and r['source']=='pooled']
 fig,axes=plt.subplots(1,3,figsize=(12,4),sharex=True,sharey=True)
 for ax,city in zip(axes,CITIES):
  ax.plot([0,1],[0,1],'--',color='gray')
  for model in MODELS:
   rows=[r for r in pred if r['city']==city and r['model']==model];p=np.array([float(r['p_raw']) for r in rows]);y=np.array([int(r['y']) for r in rows]);bins=np.minimum((p*10).astype(int),9);pts=[(p[bins==b].mean(),y[bins==b].mean()) for b in range(10) if np.any(bins==b)]
   ax.plot([x[0] for x in pts],[x[1] for x in pts],'o-',label=model)
  ax.set_title(city);ax.set_xlabel('Mean predicted probability');ax.legend()
 axes[0].set_ylabel('Observed fraction positive');fig.suptitle('Pooled-source native probability calibration (occupied fixed bins)');figure(P5,'pooled_calibration')
 for folder in [DATA,P4,P5]:
  files=[p for p in folder.rglob('*') if p.is_file() and p.name!='release_manifest.csv'];files += [ROOT/'scripts'/n for n in ['download_temporal_extension.py','build_temporal_data.py','temporal_common.py','run_phase4_temporal.py','run_phase5.py','validate_phase45.py','report_phase45.py']];files += [ROOT/'requirements-phase5.txt']
  files += [ROOT/p for p in ['scripts/run_phase4.py','scripts/build_phase3.py','scripts/download_census.py','requirements-phase4.txt','requirements.txt','protocol/phase45_temporal_extension_v2.md','protocol/phase45_boundary_correction.md','protocol/phase45_continuity_amendment.md']]
  write(folder/'qa/release_manifest.csv',[{'file':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(set(files))])
 print('Reports, figures and release manifests written.',flush=True)
if __name__=='__main__':main()
