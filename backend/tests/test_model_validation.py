"""Research evaluation checks; run with ml/requirements-training.txt installed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
try:
    import numpy as np
    from ml.validate_model import measures, calibration_bins, cluster_bootstrap, subgroup_results, audit
    RESEARCH_DEPS = True
except ImportError:
    RESEARCH_DEPS = False
from app.services import ml_service

@unittest.skipUnless(RESEARCH_DEPS, "Install ml/requirements-training.txt for research audit tests")
class ModelValidationTests(unittest.TestCase):
    def test_known_confusion_and_undefined_rates(self):
        m=measures([1,1,0,0],[.9,.4,.7,.1],.5)
        self.assertEqual(m['confusion_matrix'],{'tp':1,'tn':1,'fp':1,'fn':1})
        self.assertEqual(m['sensitivity'],.5)
        self.assertEqual(m['negative_predictive_value'],.5)
        self.assertIsNone(measures([0,0],[.1,.2],.5)['sensitivity'])
        self.assertIsNone(measures([0,0],[.1,.2],.5)['roc_auc'])

    def test_probability_bin_edges_count_every_case_once(self):
        y=np.array([0,1,0,1]);p=np.array([0,.1,.9,1])
        bins=calibration_bins(y,p)
        self.assertEqual(sum(b['n'] for b in bins),4)
        self.assertEqual(bins[-1]['n'],2)

    def test_cluster_bootstrap_reproducible(self):
        y=np.array([0,1,0,1]);p=np.array([.1,.8,.3,.7]);g=np.array(['A','A','B','B'])
        a=cluster_bootstrap(y,p,g,.5,100)
        self.assertEqual(a,cluster_bootstrap(y,p,g,.5,100))
        self.assertEqual(a['intervals']['sensitivity'],[1.,1.])

    def test_small_subgroups_suppressed(self):
        f={'age':12,'sex':'F','treatment_line':1,'regimen':'TDF-3TC-DTG'}
        result=subgroup_results([f],np.array([1]),np.array([.8]),.64)
        self.assertTrue(all(r['suppressed'] and r['metrics'] is None for r in result))

    def test_wrong_dataset_rejected_before_scoring(self):
        with tempfile.TemporaryDirectory() as temp:
            csv=Path(temp)/'data.csv';csv.write_text('not the dataset')
            artifact=Path(temp)/'model.json';artifact.write_text(json.dumps({'metadata':{'data_sha256':'different'}}))
            with self.assertRaisesRegex(ValueError,'Dataset hash'):
                audit(csv,artifact)

    def test_stale_validation_not_served(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(ml_service,'ARTIFACTS',Path(temp)):
            artifact={'metadata':{'data_sha256':'data','version':'v'}}
            p=Path(temp)/'model.json';p.write_text(json.dumps(artifact))
            report={'schema_version':1,'model_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'data_sha256':'data','model_version':'v'}
            v=Path(temp)/'validation.json';v.write_text(json.dumps(report))
            self.assertEqual(ml_service.validation_report(artifact),report)
            p.write_text('{}')
            self.assertIsNone(ml_service.validation_report(artifact))
