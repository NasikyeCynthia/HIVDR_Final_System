import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.core import bootstrap, database
from app.main import app
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
        self.login('counsellor')
        self.assertEqual(self.client.get('/api/patients/2').status_code,200)  # everyone can view
        with database.connect() as con:
            con.execute("UPDATE users SET can_access_all=1 WHERE username='counsellor'")
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
        response=self.client.put('/api/workflow/patients/1/psychosocial',json={'assessed':True,'factors':['Had 1 or no meal/day'],'notes':'Follow-up planned'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.client.get('/api/patients/1').json()['patient']['psychosocial']['factors'],['Had 1 or no meal/day'])
        self.login('lab')
        self.assertEqual(self.client.put('/api/workflow/patients/1/psychosocial',json={'assessed':True}).status_code,403)

    def test_stanford_result_storage_and_lab_invalidation(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET referred_at='2026-10-01' WHERE patient_id=1")
        self.login('lab')
        for stage,body in (('collection',{'sample_type':'Plasma','collected_at':'2026-10-02T08:00','centrifuged_at':'2026-10-02T09:00','tubes':2,'officer_phone':'+256772000111'}),
                           ('receipt',{'received_at':'2026-10-04','outcome':'Referred to DR lab','plasma_volume_ml':2}),
                           ('result',{'outcome':'Usable result','tested_at':'2026-10-20','released_at':'2026-10-21','mutations':'RT:M184V'})):
            r=self.client.put(f'/api/lab/1/{stage}',json=body)
            self.assertEqual(r.status_code,200,r.text)
        result={'provider':'Stanford HIVdb Sierra','version':{'text':'test-fixture'},'analysis':{'validationResults':[],'drugResistance':[]}}
        with patch('app.services.stanford_service.analyze',return_value=result):
            r=self.client.post('/api/workflow/patients/1/interpret',json={'kind':'mutations','text':'RT:M184V'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get('/api/patients/1').json()['patient']['interpretation']['version']['text'],'test-fixture')
        p=self.client.get('/api/patients/1').json()
        self.assertEqual(p['patient']['lab']['stage'],'Result released')
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

    def test_iac_sessions_drive_guideline_referral(self):
        self.login('admin')
        csv=('Patient No.,Facility,Age(yrs),Treatment Initiation Date,VL Leading to DR,VL Test Date,vl_1_Prior_To_DR,VL_1_Prior_To_DR_TestDate,Treatment Line at Sample collection,ART at sample collection(ART@VL@DR)\n'
             'ELIG-1,Demo Facility,40,01/01/2018,30000,15/08/2026,200000,01/05/2026,First Line,TDF-3TC-DTG\n')
        self.assertEqual(self.client.post('/api/settings/import',json={'source':'original','csv':csv}).status_code,200)
        pid=next(p['id'] for p in self.client.get('/api/patients').json() if p['external_id']=='ELIG-1')
        self.login('counsellor')
        self.assertEqual(self.client.get(f'/api/eligibility/{pid}').json()['status'],'needs_documentation')
        self.login('lab')
        self.assertEqual(self.client.post(f'/api/eligibility/{pid}/refer',json={}).status_code,400)  # not yet eligible
        self.login('counsellor')
        for day,pct in (('2026-05-20',96),('2026-06-20',99),('2026-07-20',100)):
            r=self.client.post(f'/api/eligibility/{pid}/iac',json={'session_date':day,'adherence_pct':pct})
            self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.get(f'/api/patients/{pid}').json()['patient']['eligibility']['status'],'eligible')
        self.assertEqual(self.client.post(f'/api/eligibility/{pid}/refer',json={}).status_code,403)  # counsellors cannot request
        self.login('lab')
        self.assertEqual(self.client.post(f'/api/eligibility/{pid}/refer',json={}).status_code,400)  # request form incomplete
        self.assertEqual(self.client.post(f'/api/eligibility/{pid}/refer',json={'weight_kg':60,'on_rifampicin':False,'biorepository_consent':'Accept'}).status_code,200)
        lab_id=self.client.get('/api/auth/me').json()['id']
        self.assertEqual(self.client.get(f'/api/patients/{pid}').json()['patient']['lab_owner'],lab_id)  # accountable officer
        self.assertEqual(self.client.get(f'/api/eligibility/{pid}').json()['status'],'in_process')

    def test_request_outside_criteria_is_lab_only_and_needs_reason(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET referred_at=NULL,sample_at=NULL,status='Not collected' WHERE patient_id=2")
            con.execute("UPDATE patients SET facility='Demo Facility' WHERE id=2")
        for role in ('nurse','clinician'):
            self.login(role)
            self.assertEqual(self.client.post('/api/eligibility/2/refer',json={'basis':'clinician_override','reason':'infant of failing mother'}).status_code,403)
        self.login('lab')
        self.assertEqual(self.client.post('/api/eligibility/2/refer',json={'basis':'clinician_override','reason':'short'}).status_code,400)
        r=self.client.post('/api/eligibility/2/refer',json={'basis':'clinician_override','reason':'HIV-positive infant born to a mother failing second line','weight_kg':60,'on_rifampicin':False,'biorepository_consent':'Accept'})
        self.assertEqual(r.status_code,200,r.text)

    def test_lab_stages_enforce_moh_sample_rules(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET referred_at=NULL WHERE patient_id=1")
        self.login('lab')
        plasma={'sample_type':'Plasma','collected_at':'2026-10-02T08:00','centrifuged_at':'2026-10-02T16:30','tubes':1,'storage_temp':'Room temperature','officer_phone':'0772000111'}
        self.assertEqual(self.client.put('/api/lab/1/collection',json=plasma).status_code,400)  # no indication yet
        with database.connect() as con:
            con.execute("UPDATE episodes SET referred_at='2026-10-01' WHERE patient_id=1")
        self.assertEqual(self.client.put('/api/lab/1/result',json={'outcome':'Usable result','tested_at':'2026-10-20','released_at':'2026-10-21'}).status_code,400)
        self.assertEqual(self.client.put('/api/lab/1/collection',json={**plasma,'centrifuged_at':None}).status_code,400)
        self.assertEqual(self.client.put('/api/lab/1/collection',json=plasma).status_code,200)
        flags=[f['text'] for f in self.client.get('/api/patients/1').json()['patient']['lab']['flags']]
        self.assertTrue(any('8.5 h' in f for f in flags), flags)
        self.assertTrue(any('two tubes' in f for f in flags), flags)
        self.assertEqual(self.client.put('/api/lab/1/receipt',json={'received_at':'2026-10-01','outcome':'Referred to DR lab'}).status_code,400)  # before collection
        self.assertEqual(self.client.put('/api/lab/1/receipt',json={'received_at':'2026-10-04','outcome':'Referred to DR lab','plasma_volume_ml':0.5}).status_code,400)
        self.assertEqual(self.client.put('/api/lab/1/receipt',json={'received_at':'2026-10-04','outcome':'Rejected','reason':'Not a listed reason'}).status_code,400)
        r=self.client.put('/api/lab/1/receipt',json={'received_at':'2026-10-04','outcome':'Rejected','reason':'Insufficient sample (less than 1 mL plasma)','plasma_volume_ml':0.5})
        self.assertEqual(r.status_code,200,r.text)
        p=self.client.get('/api/patients/1').json()['patient']
        self.assertEqual((p['status'],p['lab']['stage']),('Rejected','Returned to facility'))
        self.assertEqual(self.client.post('/api/lab/1/repeat-request').status_code,200)
        p=self.client.get('/api/patients/1').json()['patient']
        self.assertEqual((p['status'],p['attempt_no']),('Not collected',2))
        self.assertIn('Insufficient sample',p['repeat_reason'])
        self.login('nurse')
        notes=[r for item in self.client.get('/api/notifications').json() if item['patient_id']==1 for r in item['reasons']]
        self.assertTrue(any(r.startswith('Repeat sample requested') for r in notes), notes)

    def test_view_only_roles_and_implementation_follow_up(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET status='Usable result',decision='Switched',decision_at='2026-10-01',recommended_regimen='AZT-3TC-DTG',reviewed_at='2026-10-01',implemented_at=NULL WHERE patient_id=1")
            con.execute('UPDATE patients SET assigned_to=NULL WHERE id=1')
        self.login('clinician')
        self.assertEqual(self.client.patch('/api/patients/1/profile',json={'age':40}).status_code,403)
        self.assertEqual(self.client.post('/api/decisions/1/implement',json={'implementation_notes':'x'}).status_code,403)
        self.login('lab')
        self.assertEqual(self.client.post('/api/eligibility/1/iac',json={'session_date':'2026-10-01','adherence_pct':96}).status_code,403)
        self.login('nurse')
        me=self.client.get('/api/auth/me').json()
        self.assertIn('implement_decision',me['permissions'])
        detail=self.client.get('/api/patients/1').json()['patient']
        self.assertEqual(detail['recommended_regimen'],'AZT-3TC-DTG')   # approved decision is visible to the nurse
        self.assertEqual(self.client.post('/api/decisions/1/implement',json={'implementation_notes':'Started at clinic'}).status_code,400)
        r=self.client.post('/api/decisions/1/implement',json={'implementation_notes':'Started at clinic','start_date':'2026-10-05','started_regimen':'AZT-3TC-DTG','previous_stop_date':'2026-10-04'})
        self.assertEqual(r.status_code,200,r.text)
        follow=self.client.get('/api/patients/1').json()['follow_ups']
        self.assertEqual(follow[0]['due_date'],'2027-04-05')
        r=self.client.post('/api/decisions/1/follow-up',json={'care_status':'Alive and on treatment','vl_copies':40,'vl_date':'2026-11-01'})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(len(self.client.get('/api/patients/1').json()['follow_ups']),2)

    def test_cphl_receipt_checks_and_repeat_viral_load(self):
        with database.connect() as con:
            con.execute("UPDATE episodes SET referred_at='2026-10-01',status='Not collected',sample_at=NULL,sample_type=NULL,report_at=NULL,amplified=NULL,reviewed_at=NULL,decision=NULL,cphl_outcome=NULL,received_at=NULL WHERE patient_id=1")
        self.login('lab')
        self.assertEqual(self.client.put('/api/lab/1/collection',json={'sample_type':'Plasma','collected_at':'2026-10-02T08:00','centrifuged_at':'2026-10-02T09:00','tubes':2,'officer_phone':'0772000111'}).status_code,200)
        bad={'received_at':'2026-10-04','outcome':'Referred to DR lab','checks':{'id_matches':False}}
        self.assertEqual(self.client.put('/api/lab/1/receipt',json=bad).status_code,400)   # failed check must be rejected
        low={'received_at':'2026-10-04','outcome':'Referred to DR lab','repeat_vl':400,'repeat_vl_date':'2026-10-03'}
        self.assertEqual(self.client.put('/api/lab/1/receipt',json=low).status_code,400)   # VL below 1000 must be deferred
        ok={'received_at':'2026-10-04','outcome':'Referred to DR lab','plasma_volume_ml':2,'repeat_vl':25000,'repeat_vl_date':'2026-10-03'}
        r=self.client.put('/api/lab/1/receipt',json=ok); self.assertEqual(r.status_code,200,r.text)
        record=self.client.get('/api/patients/1').json()
        self.assertEqual(record['patient']['cphl_vl'],25000)
        self.assertEqual(record['patient']['lab']['stage'],'At DR laboratory')

if __name__=='__main__': unittest.main()
