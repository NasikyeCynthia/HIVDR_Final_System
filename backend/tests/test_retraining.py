"""Training isolation and portable candidate export regression checks."""
import unittest
import tempfile
from pathlib import Path
try:
    import numpy as np
    from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression
    from ml.retrain_model import preprocessing,disjoint,choose_cutoff,export_model,candidate_predict,logits,train
    from app.services.ml_features import transform
    RESEARCH_DEPS=True
except ModuleNotFoundError:
    RESEARCH_DEPS=False

@unittest.skipUnless(RESEARCH_DEPS,'Install ml/requirements-retraining.txt for research retraining tests')
class RetrainingTests(unittest.TestCase):
    def features(self):
        return [{'log_viral_load':float(i),'age':20+i,'treatment_line':1+i%3,'art_years_at_sample':float(i%5),
                 'log_prior_vl':None if i%3==0 else float(i),'prior_vl_count':i%4,'sex':'F' if i%2 else 'M',
                 'regimen':'TDF-3TC-DTG' if i%2 else 'AZT-3TC-DTG'} for i in range(40)]

    def test_preprocessing_does_not_learn_holdout(self):
        f=self.features();f[39]['age']=10000;f[39]['regimen']='UNSEEN'
        spec=preprocessing(f,np.arange(20))
        self.assertLess(spec['numeric']['age']['median'],50)
        self.assertNotIn('UNSEEN',spec['categorical']['regimen'])

    def test_facility_overlap_rejected(self):
        g=np.array(['A','B','A','C'])
        with self.assertRaisesRegex(ValueError,'Facility leakage'):
            disjoint(g,[np.array([0,1]),np.array([2,3])])
        disjoint(g,[np.array([0,2]),np.array([1,3])])

    def test_cutoff_uses_given_partition(self):
        t=choose_cutoff(np.array([0,0,1,1]),np.array([.1,.2,.7,.8]))
        self.assertGreater(t,.2)
        self.assertLessEqual(t,.7)

    def test_candidate_cannot_overwrite_deployed_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp);baseline=output/'model.json';baseline.write_text('protected')
            with self.assertRaisesRegex(ValueError,'must not overwrite'):
                train(output/'unused.csv',baseline,output)
            self.assertEqual(baseline.read_text(),'protected')

    def test_tree_comparisons_keep_double_precision_thresholds(self):
        value=float(np.nextafter(np.float32(1),np.float32(2)))
        artifact={'kind':'forest','preprocessing':{'numeric':{'age':{'median':0,'mean':0,'scale':1}},'categorical':{}},
                  'trees':[{'left':[1,-1,-1],'right':[2,-1,-1],'feature':[0,-2,-2],
                            'threshold':[value-1e-9,-2,-2],'positive_probability':[.5,.1,.9]}],
                  'calibration':{'coefficient':1,'intercept':0}}
        self.assertAlmostEqual(candidate_predict(artifact,{'age':value}),.9)

    def test_portable_exports_match_all_model_families(self):
        f=self.features();spec=preprocessing(f,np.arange(len(f)))
        x=np.array([transform(v,spec) for v in f]);y=np.array([int(i%7>=3) for i in range(40)])
        models=[LogisticRegression(max_iter=500),RandomForestClassifier(n_estimators=4,max_depth=3,random_state=1),
                ExtraTreesClassifier(n_estimators=4,max_depth=3,random_state=1),
                GradientBoostingClassifier(n_estimators=5,max_depth=2,learning_rate=.05,random_state=1)]
        for model in models:
            with self.subTest(model=type(model).__name__):
                model.fit(x,y);a=export_model(model,spec);a['calibration']={'coefficient':.9,'intercept':.1}
                expected=1/(1+np.exp(-(.1+.9*logits(model.predict_proba(x)[:,1]))))
                actual=np.array([candidate_predict(a,v) for v in f])
                self.assertLess(float(np.max(np.abs(expected-actual))),1e-8)

if __name__=='__main__':unittest.main()
