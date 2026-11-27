"""Read-only post-build checks, independent of the report generation path."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score
import xgboost as xgb
import pipeline as p


def validate(out):
    manifest=pd.read_csv(out/'output_manifest.csv')
    assert manifest.file.is_unique
    for r in manifest.to_dict('records'):
        path=out/r['file'];assert path.stat().st_size==r['bytes'] and p.digest(path)==r['sha256'],path
    p.verify_sources()
    frozen,env,_=p.load_data();prepared=pd.read_csv(out/'data/chicago_prepared.csv',dtype={'acs_geoid_2022':str,'sld_geoid_2019':str})
    assert list(prepared.row_id)==list(frozen.row_id)
    for f in env+p.CRIME:
        np.testing.assert_allclose(prepared[f],frozen[f],equal_nan=True,rtol=1e-12)
    test=frozen[frozen.outcome_year.eq(2025)].reset_index(drop=True)
    train=frozen[frozen.outcome_year.eq(2024)].reset_index(drop=True)
    preds=pd.read_csv(out/'data/predictions_2025.csv');metrics=pd.read_csv(out/'statistics/model_metrics.csv')
    count=0
    for radius in (25,50,100):
        for family in ('crime_only','environment_only','crime_plus_environment'):
            stem=out/'models'/f'{radius}m_{family}'
            spec=json.loads(stem.with_suffix('.schema.json').read_text());features=spec['features']
            keep,excluded=p.training_columns(train,spec['candidate_features'])
            assert keep==features and excluded==spec['excluded']
            model=xgb.XGBClassifier();model.load_model(stem.with_suffix('.json'))
            got=model.predict_proba(test[features])[:,1]
            saved=preds[preds.radius_m.eq(radius)&preds.model.eq(family)]
            assert list(saved.row_id)==list(test.row_id)
            np.testing.assert_allclose(got,saved.probability,rtol=1e-7)
            y=test[f'primary_any_{radius}m'].to_numpy(dtype=int);np.testing.assert_array_equal(y,saved.y)
            m=metrics[metrics.radius_m.eq(radius)&metrics.model.eq(family)&metrics.threshold_type.eq('fixed_0.5')&metrics.subset.eq('all')].iloc[0]
            assert abs(m.average_precision-average_precision_score(y,got))<1e-10
            assert abs(m.roc_auc-roc_auc_score(y,got))<1e-10
            if radius==50:
                sh=pd.read_csv(out/f'explanations/{family}_shap_values_2025.csv')
                margin=sh[spec['candidate_features']].sum(axis=1)+sh.bias_log_odds
                np.testing.assert_allclose(1/(1+np.exp(-margin)),got,atol=1e-6)
                ranking=pd.read_csv(out/f'explanations/{family}_shap_ranking.csv').set_index('parameter')
                for f in spec['candidate_features']:
                    assert abs(ranking.loc[f,'mean_abs_shap']-sh[f].abs().mean())<1e-10
            count+=1
    a=pd.read_csv(out/'statistics/associations_all_outcomes.csv');checked=0
    for year in (2024,2025):
        part=frozen[frozen.outcome_year.eq(year)]
        for r in a[a.year.eq(year)].to_dict('records'):
            complete=part[[r['parameter'],r['outcome']]].dropna()
            assert len(complete)==r['n_complete']
            if complete.iloc[:,0].nunique()>1:
                rho=spearmanr(complete.iloc[:,0],complete.iloc[:,1]).statistic
                assert abs(rho-r['spearman_rho'])<1e-10
            else:assert pd.isna(r['spearman_rho'])
            checked+=1
    candidate_set=set(env+p.CRIME)
    for file in ['statistics/distributions_all_parameters.csv','statistics/correlation_rankings.csv']:
        t=pd.read_csv(out/file)
        for year,part in t.groupby('year'):
            assert set(part.parameter)==candidate_set and part.parameter.is_unique
    assert all((out/'figures/parameters'/f'{f}.png').exists() for f in candidate_set)
    html=(out/'report.html').read_text()
    assert html.count('class="parameter"')==len(candidate_set)
    return {'status':'PASS','manifest_files_verified':len(manifest),'saved_models_replayed':count,
        'associations_recomputed':checked,'parameter_sections_and_plots':len(candidate_set),
        'source_values_preserved':True,'scientific_review':'PENDING'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=p.DEFAULT_OUT)
    args=parser.parse_args();print(json.dumps(validate(args.output),indent=2))
