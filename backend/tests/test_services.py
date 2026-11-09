"""Dependency-free tests of the same services called by the FastAPI routers."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
from app.core import bootstrap, database
from app.core.errors import DomainError
from app.services.import_service import import_rows
from app.services.patient_service import records
from app.services.profile_service import update_profile
from app.services.lab_service import update_lab_result, request_repeat_sample
from app.services.decision_service import approve_decision, implement_decision
from app.services.referral_service import refer_for_drt
from app.services.risk_service import score
from app.services.workflow_service import load_patient, change_patient

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old=(bootstrap.ROOT,bootstrap.DB,database.DB)
        bootstrap.ROOT=Path(self.temp.name)
        (bootstrap.ROOT/'data').mkdir()
        bootstrap.DB=database.DB=bootstrap.ROOT/'data'/'test.sqlite3'
        bootstrap.initialize()
        with database.connect() as con:
            self.users={row['role']:dict(row) for row in con.execute('SELECT * FROM users')}

    def tearDown(self):
        bootstrap.ROOT,bootstrap.DB,database.DB=self.old
        self.temp.cleanup()

    def test_factor_boundaries_preserve_requested_weights(self):
        for vl,expected in [(199,0),(200,30),(999,30),(1000,60)]:
            self.assertEqual(score({'viral_load':vl,'adherence':100,'treatment_line':1})['factors'][0]['points'],expected)
        for adherence,expected in [(84.9,60),(85,30),(99.9,30),(100,0)]:
            self.assertEqual(score({'viral_load':0,'adherence':adherence,'treatment_line':1})['factors'][1]['points'],expected)
        for line,expected in [(1,0),(2,30),(3,60)]:
            self.assertEqual(score({'viral_load':0,'adherence':100,'treatment_line':line})['factors'][2]['points'],expected)
        self.assertEqual(score({'viral_load':1000,'adherence':82,'treatment_line':3})['total'],180)
        self.assertEqual(score({'viral_load':1000,'adherence':82,'treatment_line':3})['category'],'Rule unresolved')
        self.assertEqual(score({'viral_load':1000,'adherence':None,'treatment_line':3})['category'],'Incomplete')

    def test_role_assignment_and_facility_permissions(self):
        with database.connect() as con:
            con.execute('UPDATE patients SET assigned_to=? WHERE id=2', (self.users['nurse']['id'],))
        with self.assertRaises(DomainError) as error:
            change_patient(2,self.users['lab'],{'adherence':99},update_profile)
        self.assertEqual(error.exception.status_code,403)
        with self.assertRaises(DomainError):
            change_patient(2,self.users['counsellor'],{'adherence':99},update_profile)
        with database.connect() as con:
            con.execute("UPDATE patients SET facility='Other Facility' WHERE id=2")
        with self.assertRaises(DomainError) as error:
            change_patient(2,self.users['nurse'],{},update_profile)
        self.assertEqual(error.exception.status_code,404)
        with database.connect() as con:
            self.assertNotIn(2,[p['id'] for p in records(con,self.users['nurse'])])
            self.assertIn(2,[p['id'] for p in records(con,self.users['admin'])])

    def test_lab_review_and_implementation(self):
        pid=1
        change_patient(pid,self.users['nurse'],{'adherence':82},update_profile)
        with self.assertRaises(ValueError):
            change_patient(pid,self.users['lab'],{'sample_type':'DBS','status':'Unamplified','failure_reason':'Failed'},update_lab_result)
        change_patient(pid,self.users['lab'],{'sample_type':'DBS','dbs_reason':'Transport unavailable','status':'Unamplified','failure_reason':'No amplification'},update_lab_result)
        change_patient(pid,self.users['lab'],{},request_repeat_sample)
        decision={'decision':'Maintained','decision_notes':'Review rationale','recommended_regimen':'Test regimen'}
        with self.assertRaises(ValueError):
            change_patient(pid,self.users['clinician'],decision,approve_decision)
        change_patient(pid,self.users['lab'],{'sample_type':'Plasma','status':'Usable result','mutations':'Test evidence'},update_lab_result)
        with self.assertRaises(DomainError):
            change_patient(pid,self.users['nurse'],decision,approve_decision)
        change_patient(pid,self.users['clinician'],decision,approve_decision)
        change_patient(pid,self.users['nurse'],{'implementation_notes':'Implementation confirmed'},implement_decision)
        with database.connect() as con:
            _,episode=load_patient(con,self.users['nurse'],pid)
            self.assertTrue(episode['implemented_at'])
            self.assertEqual(con.execute("SELECT count(*) FROM audit WHERE action='decision implemented'").fetchone()[0],1)
        with self.assertRaises(ValueError):
            change_patient(pid,self.users['lab'],{'sample_type':'Plasma','status':'Pending'},update_lab_result)

    def test_csv_preservation_deduplication_and_rollback(self):
        text='Patient No.,Facility,VL Leading to DR,Extra column\nIMPORT-1,Demo Facility,"1,500 Copies / mL",retain me\n'
        parsed=list(csv.DictReader(io.StringIO(text)))
        with database.connect() as con:
            self.assertEqual(import_rows(con,parsed,'original',self.users['admin'])['added'],1)
            self.assertEqual(import_rows(con,parsed,'original',self.users['admin'])['skipped'],1)
            p=con.execute("SELECT * FROM patients WHERE external_id='IMPORT-1'").fetchone()
            self.assertEqual(json.loads(p['original_json'])['Extra column'],'retain me')
            self.assertIsNone(p['adherence'])
        bad=[{'Patient No.':'ROLLBACK-1'},{'Patient No.':'ROLLBACK-2','Adherence (%)':'101'}]
        with self.assertRaises(ValueError):
            with database.connect() as con:
                import_rows(con,bad,'original',self.users['admin'])
        with database.connect() as con:
            self.assertEqual(con.execute("SELECT count(*) FROM patients WHERE external_id='ROLLBACK-1'").fetchone()[0],0)

    def test_invalid_profile_values_and_blocked_referral(self):
        for data in [{'adherence':101},{'viral_load':-1},{'adherence':'NaN'},{'treatment_line':4}]:
            with self.assertRaises(ValueError):
                change_patient(1,self.users['nurse'],data,update_profile)
        with self.assertRaises(ValueError):
            change_patient(1,self.users['clinician'],{},refer_for_drt)

if __name__=='__main__':
    unittest.main(verbosity=2)
