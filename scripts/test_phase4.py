"""Focused tests for metric ties, bootstrap weights, preprocessing and calibration."""
import unittest
import numpy as np
from sklearn.metrics import average_precision_score
from run_phase4 import weighted_ap_setup,metrics,estimator,sigmoid_fit,calibrate

class Phase4Tests(unittest.TestCase):
    def test_weighted_ap_matches_library_with_ties_and_zero_weights(self):
        y=np.array([0,1,1,0,1,0]);p=np.array([.5,.5,.1,.1,.9,.9])
        ap=weighted_ap_setup(y,p)
        for w in [np.ones(6),np.array([0,3,2,0,1,4]),np.array([1,0,1,0,0,0])]:
            self.assertAlmostEqual(ap(w),average_precision_score(y,p,sample_weight=w),places=12)
    def test_no_positive_bootstrap_is_undefined(self):
        f=weighted_ap_setup(np.array([0,1]),np.array([.9,.2]))
        self.assertTrue(np.isnan(f(np.array([1.,0.]))))
    def test_top_decile_ties_use_ids(self):
        result=metrics(np.array([0,1,0,0]),np.array([.5,.5,.5,.5]),['b','a','c','d'])
        self.assertEqual(result['top_decile_n'],1)
        self.assertEqual(result['top_decile_hits'],1)
    def test_imputation_learns_only_training_data_and_retains_empty_column(self):
        X=np.array([[1.,np.nan],[3.,np.nan],[np.nan,np.nan],[5.,np.nan]])
        e=estimator('M1',{'C':1.}).fit(X,np.array([0,0,1,1]))
        before=e.named_steps['imputer'].statistics_.copy()
        e.predict_proba(np.array([[9999999.,9999999.],[np.nan,np.nan]]))
        np.testing.assert_equal(before,[3.,0.])
        np.testing.assert_equal(e.named_steps['imputer'].statistics_,before)
    def test_sigmoid_is_monotone_and_valid(self):
        y=np.array([0,1,0,0,1,0,1,1,0,1])
        p=np.linspace(.1,.9,10)
        fit=sigmoid_fit(y,p)
        self.assertTrue(fit['applied'])
        out=calibrate(p,fit)
        self.assertTrue(np.all(np.diff(out)>=0))
        self.assertTrue(np.all((out>=0)&(out<=1)))

if __name__=='__main__':unittest.main()
