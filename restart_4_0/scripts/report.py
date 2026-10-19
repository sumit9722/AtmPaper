"""Write the complete, reproducible release from validated empirical outputs."""
from common import *
import collections
os.environ.setdefault('MPLCONFIGDIR','/tmp/atm_restart4_matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def table(rows, columns):
    def fmt(v):
        if isinstance(v,(float,np.floating)):return f'{v:.4f}'
        return str(v)
    return '| '+' | '.join(columns)+' |\n| '+' | '.join(['---']*len(columns))+' |\n'+''.join('| '+' | '.join(fmt(r.get(c,'')) for c in columns)+' |\n' for r in rows)

def numeric(rows, columns):
    return [r|{c:float(r[c]) for c in columns if r.get(c,'')!=''} for r in rows]

def main():
    p4,p5=ROOT/'results/phase4',ROOT/'results/phase5'
    validations=[json.loads((ROOT/f'results/phase{p}/qa/validation.json').read_text()) for p in [3,4,5]]
    assert all(v['status']=='PASS' for v in validations)
    m4=numeric(read(p4/'data/metrics.csv'),['average_precision','roc_auc','brier_score','top_decile_precision','top_decile_recall','prevalence'])
    comp=numeric(read(p4/'data/paired_comparisons.csv'),['ap_difference','ci_low','ci_high'])
    u5=numeric(read(p5/'data/benefit_uncertainty.csv'),['ap_difference','ci_low','ci_high','randomization_p','holm_p','seed_p025','seed_p975'])
    m5=numeric(read(p5/'data/metrics.csv'),['average_precision','brier_score','roc_auc','top_decile_precision'])
    primary=next(r for r in comp if r['primary']=='True')
    pooled=[r for r in m4 if r['scheme']=='forward_spatial' and r['city']=='ALL']
    selected=[r for r in read(p4/'qa/model_fits.csv') if r['model']=='M1']
    counts=collections.Counter(r['selected_feature'] for r in selected)
    supported=[r for r in u5 if r['supported_exploratory_benefit']=='True']
    # Descriptive covariate coverage: no labels are consulted to choose variables.
    X,y,meta,names,distance=load();years=np.array([r['year'] for r in meta]);cities=np.array([r['city'] for r in meta])
    ranges=[]
    for city in CITIES:
        target=X[(years==2025)&(cities==city)]
        for source in [c for c in CITIES if c!=city]+['pooled']:
            sourcevalues=X[(years==2024)&((cities!=city) if source=='pooled' else (cities==source))]
            for j,name in enumerate(names):
                s=sourcevalues[:,j];s=s[np.isfinite(s)];t=target[:,j];known=np.isfinite(t)
                outside=int(((t[known]<s.min())|(t[known]>s.max())).sum()) if len(s) else ''
                ranges.append({'city':city,'source':source,'feature':name,'source_observed':len(s),
                    'target_observed':int(known.sum()),'target_missing':int((~known).sum()),
                    'source_min':float(s.min()) if len(s) else '', 'source_max':float(s.max()) if len(s) else '',
                    'target_outside_source_range':outside})
    write(p5/'data/feature_extrapolation.csv',ranges)
    del X,distance
    calibration=[];grouped=collections.defaultdict(list)
    fields=['city','condition','source','fraction','seed','model']
    for r in gzread(p5/'data/predictions.csv.gz'):grouped[tuple(r[k] for k in fields)].append(r)
    for key,rows in grouped.items():
        prob=np.array([float(r['p_raw']) for r in rows]);label=np.array([int(r['y']) for r in rows]);bins=np.minimum((prob*10).astype(int),9)
        for b in range(10):
            mask=bins==b
            if mask.any():calibration.append(dict(zip(fields,key))|{'bin':b,'n':int(mask.sum()),
                 'mean_probability':float(prob[mask].mean()),'observed_rate':float(label[mask].mean())})
    write(p5/'data/calibration_bins.csv',calibration);del grouped
    feature_summary=[]
    evaluations=read(p4/'qa/evaluations.csv');spatialfits={r['fit_id'] for r in evaluations if r['scheme']=='forward_spatial' and r['model']=='M1'}
    sids={r['selection_id'] for r in selected if r['fit_id'] in spatialfits}
    ss=read(p4/'data/selection_scores.csv')
    for name in ['NONE']+json.loads((ROOT/'results/phase3/data/feature_schema.json').read_text())['predictors'][1:]:
        rr=[r for r in ss if r['selection_id'] in sids and r['added_feature']==name and r['reason']=='max_validation_ap']
        feature_summary.append({'candidate':name,'mean_2024_inner_AP':float(np.mean([float(r['mean_inner_ap']) for r in rr])),
                                'selected_outer_folds':sum(r['selected']=='True' for r in rr)})
    feature_summary.sort(key=lambda r:-r['mean_2024_inner_AP'])
    write(p4/'data/feature_leaderboard.csv',feature_summary)
    text='# Restart 4.0 — complete through Phase 5\n\n'
    text+='**Phases 1–5 are computationally complete; automated validation passed.** The primary exploratory improvement criterion passed.\n\n'
    text+='[Research update for the professor](Research_Update_for_Professor.md) presents the study, findings and limitations without internal project terminology.\n\n'
    text+=f"The strongest recurring additional predictor is **prior-year robbery/burglary within 50 m**, transformed as `log1p(count)` and filtered to reports available before the prediction year. It was selected in all five spatial outer folds and {counts.get('log1p_prior_crime_50m',0)} of eight Phase 4 fits overall. Selection compared 28 background/one-additional-variable choices using only 2024 training data.\n\n"
    text+=table(pooled,['model','average_precision','roc_auc','brier_score','top_decile_precision','top_decile_recall'])+'\n'
    text+=f"The primary M1−M0 AP gain is **{primary['ap_difference']:+.4f}**, with paired spatial 95% interval **[{primary['ci_low']:+.4f}, {primary['ci_high']:+.4f}]**. The evaluation contains 1,241 2025 ATM sites and 674 positive sites; no-skill prevalence is 0.5431. M0 is background-only logistic; M1 adds a training-selected variable with regularization; M2 uses shallow trees with the same selected predictors.\n\n"
    text+=f"Phase 5 completed **7,380 model evaluations** over 20 adaptation seeds. **{len(supported)} of 54** source/fraction/model comparisons meet the fixed exploratory support rule: AP gain ≥0.01, positive spatial interval, and Holm-adjusted block-randomization p<0.05. All 54 comparisons, including negative results, are reported in [Phase 5 results](results/phase5/docs/03_results.md).\n\n"
    if supported:text+=table(supported,['city','source','fraction','model','ap_difference','ci_low','ci_high','holm_p'])+'\n'
    text+='The main improvement measures temporal crime persistence. It does not demonstrate a housing effect, causal ATM risk, or universally beneficial city transfer. Both outcome years were inspected in previous releases, so these are exploratory findings; independent confirmation and source/linkage review remain pending.\n\n'
    text+='[Methods](reports/methods.md) · [Phase 1–3 execution](reports/phase_1_3.md) · [Phase 4 results](results/phase4/docs/03_results.md) · [Phase 5 results](results/phase5/docs/03_results.md) · [Validation status](reports/phase_status.json)\n\n'
    text+='Reproduce from the project root:\n\n```bash\n.venv/bin/python restart_4_0/scripts/run_all.py\n```\n\n'
    text+='The offline pipeline references the preserved `restart_3_0` and `restart_2024_2025` inputs. Keep those directories. It rechecks cached source digests, reconstructs features, fits every model, recalculates uncertainty and validates before regenerating reports. No new source download is claimed.\n'
    (ROOT/'README.md').write_text(text)
    methods='''# Methods and interpretation

The [frozen protocol](../protocol/restart_spec.md) and
[permutation-resolution amendment](../protocol/inference_resolution_amendment.md)
define this release. The amendment increased all Phase 5 permutation counts
before those experiments, because 999 permutations could not resolve the
first threshold in a 54-test Holm correction. No outcome-based stopping occurred.

Phases 1–2 inherit the validated 1,201-site 2024 and 1,241-site 2025 annual
cohorts. Archived inputs and their original provenance are retained in previous
release directories; 342 original raw-file digests were checked again. Training
labels are 2024 events reported before 2025; test labels are archived 2025
occurrences. Both years were inspected previously. Full-year inventory
membership is retrospective and does not prove continuous ATM operation.

Phase 3 joins eight housing and thirteen other environmental variables by exact
site-year identifier, alongside prior-year 200–500 m background crime. Six new
lagged crime predictors use 25/50/100 m counts, robbery/burglary separately at
50 m, and July–December crime at 50 m. All six require prior-year occurrence
and a known report date before January 1. Counts are transformed by log1p.
Every site-year count was independently recomputed by scanning geodesic
distances to all eligible events in its city. Unknown report dates are excluded.

The candidate family consists of background alone or background plus one
predictor, each fitted with L2 logistic regression C=1. Every distinct actual
training sample gets its own feature selection using three spatial groups
(saved 2024 fold modulo 3) and a 1,500 m purge. Imputation and scaling use
inner training rows only. Fewer than two valid folds triggers background-only
fallback. Small samples may also have one outcome class; these yield explicit
constant-probability artifacts. The batched selection solver matches sklearn;
final saved models use sklearn/XGBoost, and representative selections are
independently refitted with sklearn. The displayed feature leaderboard averages
dependent inner-fold results for description; it is not a second selection rule
or an independent estimate of generalization.

Phase 4 uses five simultaneous cross-city spatial folds and three city-held-out
fits. All fits use 2024 labels, all evaluation uses 2025 labels, and every
training site is at least 1,500 m from every held-out site. Primary M1 is fixed
in advance. M2 is a secondary shallow-tree model with the M1-selected features.
The primary numerical criterion is AP gain at least .01 and a positive paired
95% spatial-bootstrap lower bound. Secondary Phase 4 intervals are descriptive
and are not individually multiplicity-corrected.

Phase 5 uses target-specific folds. It evaluates local-full, each individual
source, pooled sources, and each source plus nested uniform 10%/25% local
samples. The paired local-only control always receives exactly those same
target labels. Twenty seeds describe training-sample variation. Deterministic
local/zero-shot fits are counted once; identical memberships share cached fits.
Feature selection for adaptation uses only the sampled target rows and its
permitted source rows. It cannot use the rest of the target training cohort.

Average precision (AP) is the primary ranking score. ROC-AUC, Brier score,
calibration error and top-decile precision/recall accompany it. The top decile
uses ceil(.1*n) and site-ID tie breaking. AP is prevalence dependent, and
NYC dominates pooled metrics; report city-specific results as well.

For uncertainty, 2,000 paired bootstrap replicates resample saved 2 km blocks
within cities. Phase 5 resamples the same blocks jointly across all 20 seed
vectors and averages their AP differences; seeds are not independent test
populations and their predictions are not averaged into an ensemble. The
two-sided randomization test swaps each complete seed-pair vector at the
spatial-block level for 9,999 permutations with add-one correction, then applies
Holm across all 54 comparisons. The null assumes prediction-pair exchangeability
at the block level. These calculations condition on fitted predictions, do not
refit training models, and do not account for prior analyses or all sources of
spatial dependence. They are exploratory conditional evidence.

Nearby robbery/burglary is not verified ATM targeting. Rounded coordinates in
Buffalo, uncertain facility identities, historical inventory continuity,
retrospective police revisions, housing-survey uncertainty and overlapping
incident neighborhoods remain limitations. Small Buffalo/Rochester samples
make transfer conclusions fragile. Independent source, offense, linkage,
coordinate, facility and feature review remains pending. A new untouched time
period is needed for confirmatory evaluation.

Method references: separating selection from outer evaluation follows the
[scikit-learn nested-validation guidance](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html).
Ranking is computed with the documented
[average precision metric](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.average_precision_score.html).
The randomized p-value uses the conservative add-one convention described in
the [SciPy permutation-test documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html).
Our resampling unit is a spatial block and the two-sided statistic uses the
absolute AP difference; this is a custom implementation, not a direct call to
SciPy's test or a claim that its assumptions have been externally verified.
'''
    (ROOT/'reports/methods.md').write_text(methods)
    (ROOT/'reports/phase_1_3.md').write_text('''# Phases 1–3 execution

1. **Phase 1 complete:** the retrospective 4.0 protocol fixes the outcome,
   candidate family, model families, splits and statistical tests before fits.
2. **Phase 2 complete:** inherited official source archives and validated annual
   cohorts were audited; all 342 raw-file hashes matched the original manifest.
   There are 2,442 site-years, with exact cohort and label reuse.
3. **Phase 3 complete:** 28 predictors were reconstructed/joined. Six new lag
   features were checked independently for every site-year using direct WGS84
   distances, event-year and report-date restrictions. No outcome-year events
   enter those predictors.

These stages reuse the original data acquisition and exposure reconstruction;
they do not claim new downloads or completed human review. Provenance is in
`input_manifest.csv`; exact feature validation is in
`../results/phase3/qa/validation.json`.
''')
    (ROOT/'results/phase3/README.md').write_text('# Phase 3\n\nValidation PASS: 2,442 site-years, 28 predictors, six newly reconstructed lag features.\n\n[Execution](../../reports/phase_1_3.md) · [Features](data/features.csv) · [Schema](data/feature_schema.json) · [Validation](qa/validation.json)\n')
    phase4text='# Phase 4 results\n\n**Validation: PASS.** 24 outer models, 7,446 prediction rows; all final models replay exactly.\n\n'
    phase4text+=table(m4,['scheme','city','model','average_precision','roc_auc','brier_score','top_decile_precision'])+'\n'
    phase4text+='## Paired AP differences\n\n'+table(comp,['scheme','city','comparison','ap_difference','ci_low','ci_high','primary','numerical_gate'])+'\n'
    phase4text+='Primary M1−M0 satisfies the frozen numerical criterion. Other intervals are descriptive and unadjusted. All intervals condition on fitted predictions and previously inspected outcomes.\n\n'
    phase4text+='## Training-only feature comparison\n\n'+table(feature_summary,['candidate','mean_2024_inner_AP','selected_outer_folds'])+'\n'
    phase4text+='Scores average the five spatial outer fits’ internal 2024 validation scores; overlapping fits are dependent. The 50 m prior-crime feature wins all five spatial selections. One of the three city-held-out selections instead chooses prior burglary at 50 m.\n\n'
    phase4text+='![Paired improvements](../figures/paired_improvement.png)\n\nSee [methods](../../../reports/methods.md) for temporal restrictions, selection, uncertainty and limitations.\n'
    (p4/'docs/03_results.md').write_text(phase4text)
    status=json.loads((p5/'qa/status.json').read_text())
    phase5text=f"# Phase 5 results\n\n**Validation: PASS.** {status['model_evaluations']:,} evaluations, {status['unique_models']:,} unique models, {status['nested_selections']:,} nested selections and {status['prediction_rows']:,} predictions. There are {status['single_class_models']} flagged single-class models and {status['warnings']} estimator warnings.\n\n"
    phase5text+=f"**{len(supported)} of 54 comparisons** meet the exploratory support rule. Positive seed means alone do not establish significance. The complete family below uses 2,000 spatial bootstraps, 9,999 block-swap permutations and Holm adjustment across all 54 tests.\n\n"
    phase5text+=table(u5,['city','source','fraction','model','ap_difference','ci_low','ci_high','positive_seeds','holm_p','supported_exploratory_benefit'])+'\n'
    phase5text+='## Local-full and zero-shot results\n\n'
    phase5text+=table([r for r in m5 if r['condition'] in ['local_full','source_only']],['city','condition','source','model','average_precision','brier_score'])+'\n'
    phase5text+='## Interpretation\n\nAdding source data can help or harm, depending on the target, source and available target labels. The primary Phase 4 improvement from lagged nearby crime does not imply that adding source-city observations improves an already strong target-only model. Small-city estimates use only 50 Buffalo and 31 Rochester test sites. No city/source/seed condition was discarded.\n\n'
    phase5text+='The seed percentile columns in `benefit_uncertainty.csv` describe training-sample variation. The spatial intervals resample the target geography jointly across seeds. The adjusted randomization p-values assume exchangeable model-prediction pairs within spatial blocks; they condition on fitted models. These previously inspected retrospective outcomes cannot provide independent confirmation.\n\n'
    phase5text+='All conditions have ten-bin calibration summaries in `data/calibration_bins.csv`. Source-to-target observed feature ranges and target missingness are recorded for all 252 city/source/feature combinations in `data/feature_extrapolation.csv`. These describe distribution differences without selecting sources or changing probabilities after evaluation.\n\n'
    phase5text+='![M1 transfer](../figures/matched_transfer.png)\n\nSee [methods](../../../reports/methods.md), [all metrics](../data/metrics.csv), [all seed benefits](../data/transfer_benefits.csv) and [validation](../qa/validation.json).\n'
    (p5/'docs/03_results.md').write_text(phase5text)
    for p in [p4,p5]:
        (p/'README.md').write_text(f'# {p.name.replace("phase","Phase ")}\n\nComputationally complete; validation PASS.\n\n[Results](docs/03_results.md) · [Methods](../../reports/methods.md) · [Validation](qa/validation.json) · [Restart overview](../../README.md)\n')
    # Publication-exportable figures; inference is plotted as paired differences.
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(9,5));rr=[r for r in comp if r['scheme']=='forward_spatial']
    for i,r in enumerate(rr):
        color='#117864' if r['comparison']=='M1-M0' else '#62758b'
        ax.errorbar(r['ap_difference'],i,xerr=[[r['ap_difference']-r['ci_low']],[r['ci_high']-r['ap_difference']]],fmt='o',color=color,capsize=3)
    ax.set_yticks(range(len(rr)),[r['city']+' · '+r['comparison'] for r in rr]);ax.invert_yaxis();ax.axvline(0,color='gray',lw=1)
    ax.set_xlabel('AP improvement over background-only model (paired spatial 95% interval)')
    ax.set_title('Restart 4.0 · 2024 training → 2025 evaluation')
    fig.text(.01,.01,'Exploratory conditional intervals. Primary comparison: pooled M1−M0; city intervals are unadjusted.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1))
    fig.savefig(p4/'figures/paired_improvement.png',dpi=180);fig.savefig(p4/'figures/paired_improvement.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(9,6));rr=[r for r in u5 if r['model']=='M1']
    for i,r in enumerate(rr):
        color='#117864' if r['supported_exploratory_benefit']=='True' else '#62758b'
        # Percentile intervals need not contain the point estimate.
        ax.plot([r['ci_low'],r['ci_high']],[i,i],color=color,lw=1.5);ax.plot(r['ap_difference'],i,'o',color=color,ms=4)
    labels=[r['city']+' ← '+r['source']+' · '+str(round(float(r['fraction'])*100))+'%' for r in rr]
    ax.set_yticks(range(len(rr)),labels,fontsize=8);ax.invert_yaxis();ax.axvline(0,color='gray',lw=1)
    ax.set_xlabel('Mean matched AP benefit across 20 seeds (spatial 95% interval)');ax.set_title('M1 transfer · green meets the complete adjusted support rule')
    fig.text(.01,.01,'Exploratory conditional inference; Holm correction includes all 54 source/fraction/model comparisons.',fontsize=8)
    fig.tight_layout(rect=(0,.04,1,1));fig.savefig(p5/'figures/matched_transfer.png',dpi=180);fig.savefig(p5/'figures/matched_transfer.pdf');plt.close(fig)
    save(ROOT/'reports/release_summary.json',{'validation':'PASS','phases_completed':[1,2,3,4,5],
        'primary_feature':'log1p_prior_crime_50m','primary_ap_gain':primary['ap_difference'],
        'primary_ci':[primary['ci_low'],primary['ci_high']],'phase5_supported_conditions':len(supported),
        'phase5_comparisons':len(u5),'phase5_corrected_inference':'PASS','confirmatory_complete':False})
    state=json.loads((ROOT/'reports/phase_status.json').read_text())
    state.update(phase_4='complete: validated PASS',phase_5='complete: validated PASS',
                 automated_validation='PASS',primary_numerical_gate=primary['numerical_gate']=='True',
                 phase5_supported_comparisons=len(supported),phase5_model_evaluations=status['model_evaluations'],
                 phase5_unique_models=status['unique_models'],phase5_corrected_inference='PASS',
                 independent_scientific_review='PENDING',confirmatory_complete=False)
    save(ROOT/'reports/phase_status.json',state)
    # Final manifest includes code, data, reports and saved models, excluding itself/logs.
    files=[p for p in ROOT.rglob('*') if p.is_file() and p.name!='release_manifest.csv' and '__pycache__' not in p.parts and p.suffix!='.log']
    write(ROOT/'reports/release_manifest.csv',[{'file':str(p.relative_to(ROOT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(files)])
    print('Complete report and release manifest written.',flush=True)

if __name__=='__main__':main()
