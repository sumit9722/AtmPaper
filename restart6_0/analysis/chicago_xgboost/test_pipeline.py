import unittest
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
import pipeline as p


class AnalysisTests(unittest.TestCase):
    def test_weighted_spearman_equals_expanded_sample_with_ties_and_missing(self):
        x=np.array([1.,1.,3.,4.,np.nan,2.]); y=np.array([0.,1.,1.,0.,1.,1.])
        weights=np.array([[2,1,0,3,2,1],[0,1,4,1,0,2],[0,0,0,0,1,0]],dtype=float)
        got=p.spearman_boot(x,y,weights)
        for i in range(2):
            ids=np.repeat(np.arange(len(x)),weights[i].astype(int));mask=np.isfinite(x[ids])
            expected=spearmanr(x[ids][mask],y[ids][mask]).statistic
            self.assertAlmostEqual(got[i],expected,places=12)
        self.assertTrue(np.isnan(got[2]))

    def test_training_only_exclusions_preserve_missing_values(self):
        train=pd.DataFrame({'constant':[2,2,np.nan],'empty':[np.nan]*3,'a':[0,1,np.nan],'duplicate':[0,1,np.nan]})
        keep,why=p.training_columns(train,list(train))
        self.assertEqual(keep,['a']);self.assertIn('duplicate',why)
        self.assertTrue(np.isnan(train.a.iloc[2]));self.assertEqual(train.a.iloc[0],0)
        # Test variation cannot make an unlearnable training feature eligible.
        test=train.copy();test['constant']=[3,4,5]
        self.assertEqual(p.training_columns(train,list(train))[0],['a'])

    def test_bh_known_result_and_missing(self):
        got=p.bh([.01,.04,.03,np.nan]);np.testing.assert_allclose(got[:3],[.03,.04,.04])
        self.assertTrue(np.isnan(got[3]))

    def test_tied_top_decile_does_not_depend_on_row_order(self):
        y=np.array([1]*4+[0]*6);probs=np.full(10,.4)
        a=p.metric_values(y,probs);b=p.metric_values(y[::-1],probs)
        self.assertAlmostEqual(a['top10_precision'],.4);self.assertEqual(a['top10_precision'],b['top10_precision'])
        self.assertTrue(np.isnan(a['precision']))

    def test_saved_sources_and_real_spatial_splits(self):
        self.assertEqual(len(p.verify_sources()),5)
        d,env,_=p.load_data();self.assertEqual(len(env),116)
        train=d[d.outcome_year.eq(2024)].reset_index(drop=True)
        for radius in (25,50,100):
            folds,audit=p.spatial_folds(train,train[f'primary_any_{radius}m'].to_numpy())
            seen=[]
            for a,b in folds:
                seen.extend(b.tolist());self.assertTrue(set(a).isdisjoint(b))
                for field in ('acs_geoid_2022','sld_geoid_2019'):
                    self.assertTrue(set(train.iloc[a][field]).isdisjoint(train.iloc[b][field]))
            self.assertEqual(sorted(seen),list(range(443)))
            self.assertTrue(all(row['minimum_train_validation_distance_m']>=1000 for row in audit))

    def test_xgboost_native_missing_and_shap_and_save_reload(self):
        import tempfile
        from pathlib import Path
        import xgboost as xgb
        x=pd.DataFrame({'a':[0,1,np.nan,3,4,5,6,np.nan]*5,'b':np.arange(40)%3})
        y=np.tile([0,0,1,0,1,1,1,0],5)
        model=p.estimator(dict(max_depth=2,n_estimators=12,min_child_weight=1,reg_lambda=1),17,1)
        model.fit(x,y);pred=model.predict_proba(x)[:,1]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'model.json';model.save_model(path)
            restored=xgb.XGBClassifier();restored.load_model(path)
            np.testing.assert_array_equal(pred,restored.predict_proba(x)[:,1])
        dm=xgb.DMatrix(x);b=model.get_booster()
        np.testing.assert_allclose(b.predict(dm,pred_contribs=True).sum(axis=1),b.predict(dm,output_margin=True),atol=1e-5)

    def test_transfer_uses_frozen_schema_without_requiring_outcomes(self):
        import tempfile
        from pathlib import Path
        from types import SimpleNamespace
        from unittest.mock import patch
        x=pd.DataFrame({'a':[0,1,np.nan,3,4,5,6,np.nan]*5,'b':np.arange(40)%3})
        y=np.tile([0,0,1,0,1,1,1,0],5)
        model=p.estimator(dict(max_depth=2,n_estimators=12,min_child_weight=1,reg_lambda=1),17,1)
        model.fit(x,y)
        target=x[['b','a']].copy();target['row_id']=['target_'+str(i) for i in range(len(x))];target['outcome_year']=2025
        # Deliberately no outcome columns. Inference must not need them.
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'source/models').mkdir(parents=True)
            for family in ('crime_only','environment_only','crime_plus_environment'):
                stem=root/'source/models'/f'50m_{family}'
                model.save_model(stem.with_suffix('.json'))
                p.dump(stem.with_suffix('.schema.json'),{'features':['a','b'],
                    'feature_training_ranges':{f:{'min':float(x[f].min()),'max':float(x[f].max()),'missing_fraction':float(x[f].isna().mean())} for f in x}})
            args=SimpleNamespace(model_dir=root/'source',output=root/'target',city='New York City',year=2025,radius=50,evaluate=False)
            with patch.object(p,'verify_sources'),patch.object(p,'load_data',return_value=(target,[],{})):
                p.transfer(args)
            saved=pd.read_csv(root/'target/predictions.csv')
            self.assertFalse((root/'target/evaluation.csv').exists())
            np.testing.assert_allclose(saved[saved.model.eq('crime_only')].probability,model.predict_proba(x)[:,1],rtol=1e-7)

if __name__=='__main__':unittest.main()
