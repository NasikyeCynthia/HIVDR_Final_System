import hashlib
from pathlib import Path
import tempfile
import unittest
try:
    import numpy as np
    from sklearn.naive_bayes import GaussianNB
    from ml.compare_models import NUMERIC,preprocessing,disjoint,choose_cutoff,metrics,score,cohort,candidates
    RESEARCH_DEPS=True
except ModuleNotFoundError:
    RESEARCH_DEPS=False

@unittest.skipUnless(RESEARCH_DEPS,'Install ml/requirements-comparison.txt in the research environment')
class ModelComparisonTests(unittest.TestCase):
    def test_preprocessing_excludes_holdout(self):
        features=[]
        for i in range(21):
            f={k:float(i) for k in NUMERIC};f.update(sex='F',regimen='TRAIN' if i<20 else 'UNSEEN')
            features.append(f)
        spec=preprocessing(features,np.arange(20))
        self.assertEqual(spec['numeric']['age']['median'],9.5)
        self.assertNotIn('UNSEEN',spec['categorical']['regimen'])

    def test_facility_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError,'Facility leakage'):
            disjoint(np.array(['A','B','A']),np.array([0,1]),np.array([2]))

    def test_operating_point_and_metrics(self):
        y=np.array([0,0,1,1]);p=np.array([.1,.2,.7,.8]);t=choose_cutoff(y,p)
        m=metrics(y,p,t)
        self.assertEqual(m['f1'],1.);self.assertEqual(m['sensitivity'],1.)

    def test_naive_bayes_margin_keeps_extreme_probability_ranking(self):
        model=GaussianNB(var_smoothing=.01).fit(np.array([[-2.],[-1.],[1.],[2.]]),np.array([0,0,1,1]))
        values=score(model,np.array([[10.],[100.]]))
        self.assertTrue(np.all(np.isfinite(values)))
        self.assertGreater(values[1],values[0])

    def test_wrong_data_hash_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'input.csv';p.write_text('not the training data')
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                cohort(p,{'data_sha256':'wrong'})

    def test_no_hidden_patient_level_validation(self):
        models,missing,_=candidates()
        self.assertFalse(models['SVM (RBF)'].probability)
        self.assertFalse(models['Neural network (MLP)'].early_stopping)
        self.assertFalse(models['Histogram gradient boosting'].early_stopping)
        if 'CatBoost' in models:self.assertFalse(models['CatBoost'].get_params()['allow_writing_files'])

if __name__=='__main__':unittest.main()
