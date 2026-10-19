"""Publish the completed simulation results while fixed inference finishes."""
from common import *
from report import table,numeric
import collections

def main():
    p4,p5=ROOT/'results/phase4',ROOT/'results/phase5'
    assert json.loads((p4/'qa/validation.json').read_text())['status']=='PASS'
    status=json.loads((p5/'qa/status.json').read_text());assert status['computation']=='complete'
    m=numeric(read(p4/'data/metrics.csv'),['average_precision','roc_auc','brier_score','top_decile_precision'])
    comp=numeric(read(p4/'data/paired_comparisons.csv'),['ap_difference','ci_low','ci_high'])
    primary=next(r for r in comp if r['primary']=='True')
    benefits=read(p5/'data/transfer_benefits.csv');groups=collections.defaultdict(list)
    for r in benefits:groups[tuple(r[k] for k in ['city','source','fraction','model'])].append(float(r['transfer_benefit']))
    summary=[dict(zip(['city','source','fraction','model'],key))|{'mean_AP_benefit':float(np.mean(v)),
        'positive_seeds':sum(x>0 for x in v),'seed_p025':float(np.quantile(v,.025)),
        'seed_p975':float(np.quantile(v,.975))} for key,v in groups.items()]
    write(p5/'data/benefit_summary.csv',summary)
    text='''# Restart 4.0 — simulation complete through Phase 5

**All model runs through Phase 5 are complete. The primary Phase 4 improvement
is statistically supported under the declared exploratory spatial analysis.**
Phases 1–4 passed automated validation. Phase 5 model, membership, selection
and metric checks passed; its full inference validation is finishing.

The strongest additional predictor is **prior-year robbery/burglary within
50 m of the ATM**, using log1p(count) and reports available before January 1.
It won all five spatial outer-fold selections among 28 candidate choices.
Mean internal 2024 validation AP was 0.7586 versus 0.6735 for background alone.

| 2025 evaluation | Background-only logistic | Selected logistic |
| --- | --- | --- |
| Average precision | 0.7195 | **0.8254** |
| ROC-AUC | 0.7242 | **0.7919** |
| Brier score (lower is better) | 0.2112 | **0.1868** |
| Top-decile precision | 76.8% | **94.4%** |

The primary AP gain is **+0.1059**, with paired spatial 95% interval
**[+0.0652, +0.1336]**. This exceeds the fixed +0.01 improvement threshold.
Evaluation uses 1,241 2025 sites; training and feature selection use 2024 only,
with 1,500 m spatial separation.

Phase 5 completed **7,380 evaluations**, **7,155 unique models**, **2,385 nested
feature selections**, and **610,572 predictions**, using 20 adaptation seeds.
Every final model replayed its stored predictions, and the unchanged baseline
reproduced Restart 3.0. The 54 transfer comparisons are saved in the
[Phase 5 results](results/phase5/docs/03_results.md). Corrected transfer
significance remains pending while the fixed 9,999-permutation tests finish;
seed percentiles are not confidence intervals. The final report refreshes
automatically after inference validation passes.

These are **exploratory** findings because both outcome years were examined in
earlier work. The improvement reflects temporal crime persistence and does not
establish a housing effect, causal ATM risk, or universal transfer benefit.
Independent source/linkage review and confirmation on untouched data remain
pending.

[Phase 4 results](results/phase4/docs/03_results.md) ·
[Phase 5 results](results/phase5/docs/03_results.md) ·
[Protocol](protocol/restart_spec.md) ·
[Status](reports/phase_status.json)

Reproduce from the project root:

```bash
.venv/bin/python restart_4_0/scripts/run_all.py
```

Keep the preserved `restart_3_0` and `restart_2024_2025` directories: this
offline release references their audited inputs. Earlier releases are preserved.
'''
    (ROOT/'README.md').write_text(text)
    (p4/'docs/03_results.md').write_text('# Phase 4 results\n\n**Validation PASS.** The primary pooled M1−M0 numerical criterion passed.\n\n'+
        table(m,['scheme','city','model','average_precision','roc_auc','brier_score','top_decile_precision'])+'\n'+
        table(comp,['scheme','city','comparison','ap_difference','ci_low','ci_high','primary'])+
        '\nIntervals are conditional on fitted predictions. Secondary intervals are unadjusted. All findings remain exploratory.\n\n![Paired improvements](../figures/paired_improvement.png)\n')
    (p5/'docs/03_results.md').write_text('# Phase 5 results\n\n**All 7,380 model evaluations complete.** Model replay, training-membership, nested selection and metric checks passed. Full corrected transfer inference is still running.\n\n'+
        table(summary,['city','source','fraction','model','mean_AP_benefit','positive_seeds','seed_p025','seed_p975'])+
        '\nThese are descriptive results over 20 matched training-sample seeds. Seed percentiles are not confidence intervals. No transfer condition is declared significant before the complete spatial tests and Holm adjustment finish.\n\n[All metrics](../data/metrics.csv) · [All matched benefits](../data/transfer_benefits.csv) · [Frozen protocol](../../../protocol/restart_spec.md)\n')
    state=json.loads((ROOT/'reports/phase_status.json').read_text())
    state.update(phase_5='model computation and core checks complete; corrected inference validation running',
        primary_numerical_gate=True,phase5_model_evaluations=7380,phase5_unique_models=7155,
        independent_scientific_review='PENDING',confirmatory_complete=False)
    save(ROOT/'reports/phase_status.json',state)
    save(ROOT/'reports/release_summary.json',{'phases_model_computation_completed':[1,2,3,4,5],
        'primary_feature':'log1p_prior_crime_50m','primary_ap_gain':primary['ap_difference'],
        'primary_ci':[primary['ci_low'],primary['ci_high']],
        'phase5_corrected_inference':'RUNNING','confirmatory_complete':False})
    print('Wrap-up report saved; corrected transfer inference remains explicitly pending.',flush=True)

if __name__=='__main__':main()
