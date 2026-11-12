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
from app.services.lab_service import record_collection, record_dispatch, record_receipt, record_result, request_repeat_sample
from app.services.decision_service import approve_decision, implement_decision
from app.services.referral_service import refer_for_drt
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

    def test_role_assignment_and_facility_permissions(self):
        with database.connect() as con:
            con.execute('UPDATE patients SET assigned_to=? WHERE id=2', (self.users['nurse']['id'],))
        with self.assertRaises(DomainError) as error:
            change_patient(2,self.users['lab'],{'adherence':99},update_profile)
        self.assertEqual(error.exception.status_code,403)
        change_patient(2,self.users['counsellor'],{'adherence':99},update_profile)
        with database.connect() as con:
            self.assertEqual(con.execute('SELECT assigned_to FROM patients WHERE id=2').fetchone()[0],self.users['nurse']['id'])
        with database.connect() as con:
            con.execute("UPDATE patients SET facility='Other Facility' WHERE id=2")
        with self.assertRaises(DomainError) as error:  # can view, cannot edit another facility
            change_patient(2,self.users['counsellor'],{},update_profile)
        self.assertEqual(error.exception.status_code,403)
        with self.assertRaises(DomainError) as error:  # nurses may view all facilities but edit only their own
            change_patient(2,self.users['nurse'],{},update_profile)
        self.assertEqual(error.exception.status_code,403)
        with database.connect() as con:
            self.assertIn(2,[p['id'] for p in records(con,self.users['counsellor'])])
            self.assertIn(2,[p['id'] for p in records(con,self.users['nurse'])])
            self.assertIn(2,[p['id'] for p in records(con,self.users['admin'])])

    def test_lab_review_and_implementation(self):
        pid=1
        lab=self.users['lab']
        with database.connect() as con:
            con.execute("UPDATE episodes SET referred_at='2026-10-01' WHERE patient_id=1")
            con.execute('UPDATE patients SET assigned_to=? WHERE id=1',(self.users['nurse']['id'],))
        with self.assertRaises(ValueError):
            change_patient(pid,lab,{'sample_type':'DBS','collected_at':'2026-10-02T09:00'},record_collection)
        change_patient(pid,lab,{'sample_type':'DBS','collected_at':'2026-10-02T09:00','officer_phone':'0772000111','dbs_reason':'Plasma processing or cold chain not available'},record_collection)
        change_patient(pid,lab,{'dispatched_at':'2026-10-03'},record_dispatch)
        change_patient(pid,lab,{'received_at':'2026-10-05','outcome':'Referred to DR lab'},record_receipt)
        change_patient(pid,lab,{'outcome':'Unamplified','tested_at':'2026-10-20','released_at':'2026-10-21','failure_reason':'No amplification'},record_result)
        change_patient(pid,lab,{},request_repeat_sample)
        decision={'decision':'Maintained','decision_notes':'Review rationale','recommended_regimen':'Test regimen'}
        with self.assertRaises(ValueError):
            change_patient(pid,self.users['clinician'],decision,approve_decision)
        change_patient(pid,lab,{'sample_type':'Plasma','collected_at':'2026-10-25T08:00','officer_phone':'0772000111','centrifuged_at':'2026-10-25T10:00','tubes':2},record_collection)
        change_patient(pid,lab,{'received_at':'2026-10-27','outcome':'Referred to DR lab','plasma_volume_ml':2},record_receipt)
        change_patient(pid,lab,{'outcome':'Usable result','tested_at':'2026-11-05','released_at':'2026-11-06','mutations':'RT:M184V'},record_result)
        with self.assertRaises(DomainError):
            change_patient(pid,self.users['nurse'],decision,approve_decision)
        with self.assertRaises(ValueError):  # psychosocial assessment missing
            change_patient(pid,self.users['clinician'],decision,approve_decision)
        with database.connect() as con:
            con.execute('UPDATE patients SET psychosocial_json=? WHERE id=1',(json.dumps({'assessed':True,'factors':[]}),))
        change_patient(pid,self.users['clinician'],decision,approve_decision)
        change_patient(pid,self.users['nurse'],{'implementation_notes':'Implementation confirmed'},implement_decision)
        with database.connect() as con:
            _,episode=load_patient(con,self.users['nurse'],pid)
            self.assertTrue(episode['implemented_at'])
            self.assertEqual(episode['attempt_no'],2)
            self.assertEqual(con.execute("SELECT count(*) FROM audit WHERE action='decision implemented'").fetchone()[0],1)
        with self.assertRaises(DomainError):
            change_patient(pid,lab,{},request_repeat_sample)

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
            change_patient(1,self.users['lab'],{},refer_for_drt)
        with self.assertRaises(DomainError):  # only laboratory staff request DR tests
            change_patient(1,self.users['clinician'],{},refer_for_drt)

if __name__=='__main__':
    unittest.main(verbosity=2)
