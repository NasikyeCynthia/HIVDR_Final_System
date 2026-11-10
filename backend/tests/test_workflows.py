import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.core import bootstrap, database
from app.main import app
from app.services.risk_service import score
from app.services.stanford_service import analyze
from app.core.errors import DomainError

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        from app.routers.auth import attempts
        attempts.clear()
        self.temp=tempfile.TemporaryDirectory()
        self.old=(bootstrap.ROOT,bootstrap.DB,database.DB)
        bootstrap.ROOT=Path(self.temp.name)
        (bootstrap.ROOT/'data').mkdir()
        bootstrap.DB=database.DB=bootstrap.ROOT/'data'/'test.sqlite3'
        self.client=TestClient(app)
        self.client.__enter__()
        self.password=(bootstrap.ROOT/'data'/'local_login.txt').read_text().split('Password: ')[1].strip()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        bootstrap.ROOT,bootstrap.DB,database.DB=self.old
        self.temp.cleanup()

    def login(self,username):
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/auth/login',json={'username':username,'password':self.password}).status_code,200)

    def test_all_facilities_is_explicit_and_read_only(self):
        with database.connect() as con:
            con.execute("UPDATE patients SET facility='Other Hospital' WHERE id=2")
        self.login('nurse')
        self.assertEqual(self.client.get('/api/patients/2').status_code,404)
        with database.connect() as con:
            con.execute("UPDATE users SET can_access_all=1 WHERE username='nurse'")
        self.assertEqual(self.client.get('/api/patients/2').status_code,200)
        self.assertEqual(self.client.patch('/api/patients/2/profile',json={'adherence':100}).status_code,403)
        self.assertEqual(self.client.get('/api/auth/me').json()['can_access_all'],1)

    def test_decision_gate_and_independent_review(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET status='Usable result',reviewed_at=NULL,decision=NULL WHERE patient_id=1")
            con.execute('UPDATE patients SET adherence=NULL WHERE id=1')
        self.login('clinician')
        decision={'decision':'Maintained','decision_notes':'Test rationale','recommended_regimen':'Test regimen'}
        response=self.client.post('/api/decisions/1/approve',json=decision)
        self.assertEqual(response.status_code,400,response.text)
        response=self.client.post('/api/workflow/patients/1/review',json={'notes':'Awaiting profile completion'})
        self.assertEqual(response.status_code,200,response.text)
        p=self.client.get('/api/patients/1').json()['patient']
        self.assertTrue(p['reviewed_at'])
        self.assertIsNone(p['decision'])
        self.assertTrue(p['approval_blockers'])

    def test_psychosocial_permission_and_persistence(self):
        self.login('nurse')
        response=self.client.put('/api/workflow/patients/1/psychosocial',json={'assessed':True,'factors':['Food insecurity'],'notes':'Follow-up planned'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.client.get('/api/patients/1').json()['patient']['psychosocial']['factors'],['Food insecurity'])
        self.login('lab')
        self.assertEqual(self.client.put('/api/workflow/patients/1/psychosocial',json={'assessed':True}).status_code,403)

    def test_stanford_result_storage_and_lab_invalidation(self):
        self.login('lab')
        lab={'sample_type':'Plasma','status':'Usable result','mutations':'RT:M184V'}
        self.assertEqual(self.client.put('/api/lab/1',json=lab).status_code,200)
        result={'provider':'Stanford HIVdb Sierra','version':{'text':'test-fixture'},'analysis':{'validationResults':[],'drugResistance':[]}}
        with patch('app.services.stanford_service.analyze',return_value=result):
            r=self.client.post('/api/workflow/patients/1/interpret',json={'kind':'mutations','text':'RT:M184V'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/patients/1').json()['patient']['interpretation']['version']['text'],'test-fixture')
        self.client.put('/api/lab/1',json=lab)
        p=self.client.get('/api/patients/1').json()
        self.assertIsNone(p['patient']['interpretation'])
        self.assertEqual(len(p['lab_history']),2)

    def test_adapter_strips_fasta_identifiers_and_handles_failure(self):
        result={'data':{'currentVersion':{'text':'fixture'},'sequenceAnalysis':[{'validationResults':[],'drugResistance':[{'drugScores':[{'score':0}]}]}]}}
        def response(req,timeout):
            payload=json.loads(req.data)
            self.assertEqual(payload['variables']['sequences'][0]['header'],'analysis')
            self.assertNotIn('private-name',req.data.decode())
            return io.BytesIO(json.dumps(result).encode())
        with patch('urllib.request.urlopen',side_effect=response):
            self.assertEqual(analyze('sequence','>private-name\n'+'ACGT'*30)['version']['text'],'fixture')
        with patch('urllib.request.urlopen',side_effect=TimeoutError):
            with self.assertRaises(DomainError) as error: analyze('mutations','RT:M184V')
            self.assertEqual(error.exception.status_code,502)
        with self.assertRaises(DomainError): analyze('mutations','patient-name M184V')

    def test_historical_mapping_preserves_source_and_live_updates(self):
        self.login('admin')
        csv='Patient No.,Facility,Sample Type,Sample collection Date,DR_results_releaseDate,amplified,Resistance to 3TC,decision Category,Decision Date\nHIST-1,Demo Facility,P,01/10/2026,10/10/2026,1,High-Level Resistance,Maintained,15/10/2026\n'
        result=self.client.post('/api/settings/import',json={'source':'original','csv':csv})
        self.assertEqual(result.status_code,200,result.text)
        p=next(p for p in self.client.get('/api/patients').json() if p['external_id']=='HIST-1')
        self.assertEqual(p['status'],'Usable result')
        self.assertEqual(p['decision'],'Maintained')
        self.assertIsNone(p['adherence'])
        self.assertIsNone(p['assigned_to'])
        original=self.client.get('/api/patients/'+str(p['id'])).json()['original']
        self.assertEqual(original['Resistance to 3TC'],'High-Level Resistance')
        self.assertEqual(self.client.post('/api/workflow/map-original-history').json()['mapped'],0)

    def test_overall_risk_categories(self):
        for vl,adherence,line,total,category in [(100,100,1,0,'Low'),(200,100,1,30,'Intermediate'),(1000,100,1,60,'High'),(200,90,1,60,'High'),(1000,80,3,180,'High')]:
            result=score({'viral_load':vl,'adherence':adherence,'treatment_line':line})
            self.assertEqual((result['total'],result['category']),(total,category))


    def test_full_record_values_edit_clear_and_conflict(self):
        self.login('admin')
        csv='Patient No.,Facility,Age(yrs),VL Leading to DR,Treatment Line at Sample collection,ART at sample collection(ART@VL@DR),Weight\nREC-1,Demo Facility,38,1500,First Line,TDF-3TC-DTG,62\n'
        self.assertEqual(self.client.post('/api/settings/import',json={'source':'original','csv':csv}).status_code,200)
        pid=next(p['id'] for p in self.client.get('/api/patients').json() if p['external_id']=='REC-1')
        self.login('nurse')
        detail=self.client.get('/api/patients/'+str(pid)).json()
        self.assertEqual(detail['current_record']['Weight'],'62')
        self.assertIsNone(detail['patient']['adherence'])
        url=f'/api/operations/patients/{pid}/fields'
        result=self.client.patch(url,json={'expected_version':0,'fields':{'Weight':'65','VL Leading to DR':'200'}})
        self.assertEqual(result.status_code,200,result.text)
        result=self.client.patch(url,json={'expected_version':0,'fields':{'Weight':'66'}})
        self.assertEqual(result.status_code,409)
        result=self.client.patch(url,json={'expected_version':1,'fields':{'Weight':''}})
        self.assertEqual(result.status_code,200,result.text)
        detail=self.client.get('/api/patients/'+str(pid)).json()
        self.assertEqual(detail['original']['Weight'],'62')
        self.assertEqual(detail['current_record']['Weight'],'')
        self.assertEqual(detail['patient']['viral_load'],200)
        self.login('lab')
        self.assertEqual(self.client.patch(url,json={'expected_version':2,'fields':{'Age(yrs)':'99'}}).status_code,403)

    def test_archive_restore_and_account_creation(self):
        self.login('admin')
        account=self.client.post('/api/operations/accounts',json={'username':'new_nurse','name':'Test Nurse','role':'nurse','facility':'Demo Facility'})
        self.assertEqual(account.status_code,200,account.text)
        password=account.json()['password']
        self.assertGreaterEqual(len(password),16)
        self.client.cookies.clear()
        self.assertEqual(self.client.post('/api/auth/login',json={'username':'new_nurse','password':password}).status_code,200)
        result=self.client.post('/api/operations/patients/1/archive',json={'archived':True,'reason':'Duplicate registration'})
        self.assertEqual(result.status_code,200,result.text)
        self.assertFalse(any(p['id']==1 for p in self.client.get('/api/patients').json()))
        self.assertTrue(any(p['id']==1 for p in self.client.get('/api/patients?include_archived=true').json()))
        self.assertEqual(self.client.patch('/api/patients/1/profile',json={'age':40}).status_code,409)
        self.assertEqual(self.client.post('/api/operations/patients/1/archive',json={'archived':False,'reason':'Restore record'}).status_code,200)

    def test_model_api_and_missing_inputs(self):
        self.login('admin')
        report=self.client.get('/api/operations/model')
        self.assertEqual(report.status_code,200,report.text)
        self.assertTrue(report.json()['connected'])
        self.assertLess(report.json()['metadata']['held_out_test']['roc_auc'],1)
        self.assertFalse(self.client.get('/api/operations/patients/1/prediction').json()['available'])


    def test_partial_known_high_score_and_unknown_low(self):
        self.assertEqual(score({'viral_load':1000,'adherence':None,'treatment_line':1})['category'],'High')
        self.assertEqual(score({'viral_load':100,'adherence':None,'treatment_line':1})['category'],'Incomplete')

    def test_clinician_amendment_preserves_previous_decision(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET status='Usable result',reviewed_at='2026-10-01',decision='Maintained',decision_notes='Previous rationale' WHERE patient_id=1")
        self.login('nurse')
        url='/api/operations/patients/1/amend'
        self.assertEqual(self.client.post(url,json={'reason':'Correct laboratory report'}).status_code,403)
        self.login('clinician')
        self.assertEqual(self.client.post(url,json={'reason':'Correct laboratory report'}).status_code,200)
        detail=self.client.get('/api/patients/1').json()
        self.assertIsNone(detail['patient']['decision'])
        self.assertEqual(json.loads(detail['review_history'][0]['snapshot_json'])['decision'],'Maintained')
        self.assertEqual(detail['current_record']['decision Category'],'')


    def test_lab_field_entry_populates_results_and_requires_reasons(self):
        self.login('lab')
        url='/api/operations/patients/1/fields'
        data={'Sample Type':'D','Sample collection Date':'01/11/2026','amplified':'0'}
        response=self.client.patch(url,json={'expected_version':0,'fields':data})
        self.assertEqual(response.status_code,400,response.text)
        data.update({'DBS justification':'Plasma unavailable','Lab failure reason':'Amplification failed'})
        response=self.client.patch(url,json={'expected_version':0,'fields':data})
        self.assertEqual(response.status_code,200,response.text)
        result=self.client.get('/api/patients/1').json()
        self.assertEqual(result['patient']['status'],'Unamplified')
        self.assertEqual(result['patient']['failure_reason'],'Amplification failed')
        response=self.client.patch(url,json={'expected_version':1,'fields':{'Sample Type':'P','amplified':'1','Resistance to DTG':'Susceptible'}})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.client.get('/api/patients/1').json()['patient']['status'],'Usable result')


    def test_existing_mutations_are_usable_and_prefilled(self):
        self.login('admin')
        csv='Patient No.,Facility,amplified,NRTI,INSTI,Sample collection Date\nGEN-1,Demo Facility,1,M184V(99.7%),R263K(100.0%),01/11/2026\n'
        self.assertEqual(self.client.post('/api/settings/import',json={'source':'original','csv':csv}).status_code,200)
        patient=next(p for p in self.client.get('/api/patients').json() if p['external_id']=='GEN-1')
        self.assertEqual(patient['status'],'Usable result')
        details=self.client.get('/api/patients/'+str(patient['id'])).json()
        self.assertEqual(details['patient']['suggested_mutations'],'RT:M184V IN:R263K')

if __name__=='__main__': unittest.main()
