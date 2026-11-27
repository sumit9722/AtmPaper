"""Refresh presentation from frozen outputs without training or changing statistics."""
import argparse
import json
from pathlib import Path
import pandas as pd
import pipeline as p


def render(out):
    original=pd.read_csv(out/'output_manifest.csv')
    protected=original[original.file.str.startswith(('models/','data/','statistics/','explanations/'))]
    for r in protected.to_dict('records'):assert p.digest(out/r['file'])==r['sha256']
    d,env,dictionary=p.load_data();features=env+p.CRIME
    train=d[d.outcome_year.eq(2024)].reset_index(drop=True);test=d[d.outcome_year.eq(2025)].reset_index(drop=True)
    predictions={(int(radius),family):part.probability.to_numpy() for (radius,family),part in
        pd.read_csv(out/'data/predictions_2025.csv').groupby(['radius_m','model'],sort=False)}
    ranks=pd.read_csv(out/'statistics/correlation_rankings.csv')
    shap=pd.read_csv(out/'explanations/crime_plus_environment_shap_values_2025.csv')[features].to_numpy()
    p.figures(train,test,features,env,dictionary,predictions,shap,ranks,out,parameter_plots=False)
    config=json.loads((out/'run_config.json').read_text())
    p.report(out,d,features,env,dictionary,
        pd.read_csv(out/'statistics/distributions_all_parameters.csv'),
        pd.read_csv(out/'statistics/associations_all_outcomes.csv'),ranks,
        pd.read_csv(out/'explanations/crime_plus_environment_shap_ranking.csv'),
        pd.read_csv(out/'explanations/crime_plus_environment_permutation_ranking.csv'),
        pd.read_csv(out/'statistics/model_metrics.csv'),pd.read_csv(out/'statistics/paired_model_differences.csv'),
        json.loads((out/'validation.json').read_text()),config)
    for r in protected.to_dict('records'):assert p.digest(out/r['file'])==r['sha256']
    p.dump(out/'qa/presentation_refresh.json',{'statistics_models_predictions_unchanged':True,
        'current_pipeline_sha256':p.digest(p.HERE/'pipeline.py'),
        'training_pipeline_sha256':config['pipeline_sha256'],
        'changes':'Stepwise precision-recall curves consistent with AP; selected model settings included in HTML.'})
    p.csv(out/'output_manifest.csv',[{'file':str(f.relative_to(out)),'bytes':f.stat().st_size,'sha256':p.digest(f)}
        for f in sorted(out.rglob('*')) if f.is_file() and f.name!='output_manifest.csv'])
    print('Report refreshed; models, predictions and statistics preserved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=p.DEFAULT_OUT)
    args=parser.parse_args();render(args.output)
