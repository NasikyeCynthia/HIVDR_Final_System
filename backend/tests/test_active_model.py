import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.core import bootstrap, database
from app.services import ml_service
from app.services.ml_history_features import extract

def raw_record():
    return {'Age(yrs)':'35','sex':'F','Treatment Line at Sample collection':'Second Line',
            'ART at sample collection(ART@VL@DR)':'AZT-3TC-DTG','VL Leading to DR':'15000',
            'Sample collection Date':'01/06/2026','Treatment Initiation Date':'01/06/2015',
            'ART@VL@DR start date':'01/06/2024',
            'vl_1_Prior_To_DR':'25000','VL_1_Prior_To_DR_TestDate':'01/03/2026'}

class ActiveModelTests(unittest.TestCase):
    def tearDown(self):
        ml_service.model.cache_clear();ml_service.retraining_report.cache_clear()

    def test_active_history_model_and_correct_evaluation(self):
        ml_service.model.cache_clear();ml_service.retraining_report.cache_clear()
        status=ml_service.status()
        self.assertEqual(status['metadata']['version'],'hivdr-panel-v2-history')
        self.assertEqual(status['metadata']['threshold'],.62)
        self.assertAlmostEqual(status['metadata']['held_out_test']['roc_auc'],.7442658920884357)
        self.assertIsNone(status['validation'])
        self.assertEqual(status['retraining_evaluation']['legacy_test'],status['metadata']['held_out_test'])

    def test_prediction_uses_snapshot_not_later_followup(self):
        raw=raw_record()
        p={'source':'original','age':50,'regimen':'TDF-3TC-EFV','viral_load':20,'treatment_line':1,'sex':'M'}
        prediction=ml_service.predict(raw,p)
        expected=ml_service.predict_artifact(ml_service.model(),extract(raw))
        self.assertTrue(prediction['available'])
        self.assertAlmostEqual(prediction['probability'],expected)
        self.assertEqual(prediction['threshold'],.62)
        self.assertEqual(prediction['reference_sample_date'],'01/06/2026')

    def test_manual_record_in_synthetic_dataset_is_not_scored(self):
        result=ml_service.predict(raw_record(),{'source':'manual','dataset_source':'synthetic'})
        self.assertFalse(result['available']);self.assertIn('synthetic',result['reason'])
        self.assertEqual(result['version'],'hivdr-panel-v2-history')

    def test_missing_required_inputs_return_versioned_unavailable_state(self):
        result=ml_service.predict({}, {'source':'original'})
        self.assertFalse(result['available']);self.assertEqual(result['version'],'hivdr-panel-v2-history')
        self.assertIn('model_sha256',result)

    def test_wrong_weight_fingerprint_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(ml_service,'ARTIFACTS',Path(temp)):
            p=Path(temp);(p/'model.json').write_text('{}')
            (p/'active_model.json').write_text(json.dumps({'model':'v1','sha256':'wrong'}))
            ml_service.model.cache_clear()
            with self.assertRaisesRegex(ValueError,'fingerprint'):
                ml_service.model()

    def test_v1_rollback_selector_remains_supported(self):
        original=ml_service.ARTIFACTS/'model.json'
        with tempfile.TemporaryDirectory() as temp,patch.object(ml_service,'ARTIFACTS',Path(temp)):
            p=Path(temp);(p/'model.json').write_bytes(original.read_bytes())
            (p/'active_model.json').write_text('{"model":"v1"}')
            ml_service.model.cache_clear()
            self.assertEqual(ml_service.model()['metadata']['version'],'hivdr-panel-v1')

class ModelCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.old=bootstrap.ROOT,bootstrap.DB,database.DB
        bootstrap.ROOT=self.root;(self.root/'data').mkdir()
        bootstrap.DB=database.DB=self.root/'data/test.sqlite3'
        ml_service.model.cache_clear();bootstrap.initialize()
        with database.connect() as con:
            con.execute("UPDATE patients SET source='original',dataset_source='original',original_json=?,source_overrides_json='{}',data_version=4 WHERE id=1",(json.dumps(raw_record()),))
            self.risk={'category':'High','known_total':120,'factors':[{'name':'Existing factor','points':60}],
                       'ml':{'version':'hivdr-panel-v1','probability':.3}}
            con.execute("UPDATE episodes SET risk_json=?,risk_ml=.3,decision='Maintained',decision_notes='Existing clinical decision',recommended_regimen='AZT-3TC-DTG' WHERE patient_id=1",(json.dumps(self.risk),))

    def tearDown(self):
        bootstrap.ROOT,bootstrap.DB,database.DB=self.old
        self.temp.cleanup()

    def test_refresh_updates_only_ml_and_is_idempotent(self):
        with database.connect() as con:
            before=dict(con.execute('SELECT * FROM episodes WHERE patient_id=1').fetchone())
            p_before=dict(con.execute('SELECT * FROM patients WHERE id=1').fetchone())
        result=ml_service.refresh_cached_predictions(batch_size=3)
        self.assertEqual(result['updated'],1)
        with database.connect() as con:
            after=dict(con.execute('SELECT * FROM episodes WHERE patient_id=1').fetchone())
            self.assertEqual(dict(con.execute('SELECT * FROM patients WHERE id=1').fetchone()),p_before)
        for key in before:
            if key not in ('risk_json','risk_ml'):self.assertEqual(after[key],before[key],key)
        risk=json.loads(after['risk_json'])
        self.assertEqual({k:v for k,v in risk.items() if k!='ml'},{k:v for k,v in self.risk.items() if k!='ml'})
        self.assertEqual(risk['ml']['version'],'hivdr-panel-v2-history')
        self.assertEqual(ml_service.refresh_cached_predictions()['updated'],0)

    def test_concurrent_profile_edit_is_not_overwritten(self):
        actual=ml_service.predict
        def edited(raw,p):
            with database.connect() as con:con.execute('UPDATE patients SET data_version=data_version+1 WHERE id=?',(p['id'],))
            return actual(raw,p)
        with patch.object(ml_service,'predict',side_effect=edited):
            result=ml_service.refresh_cached_predictions()
        self.assertEqual(result['skipped'],1)
        with database.connect() as con:
            risk=json.loads(con.execute('SELECT risk_json FROM episodes WHERE patient_id=1').fetchone()[0])
        self.assertEqual(risk,self.risk)
