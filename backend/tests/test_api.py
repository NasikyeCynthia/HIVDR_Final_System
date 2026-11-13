"""HTTP integration checks. Install requirements-dev.txt to run these checks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HAS_HTTP_TEST_DEPS = all(importlib.util.find_spec(module) for module in ('fastapi', 'httpx'))

@unittest.skipUnless(HAS_HTTP_TEST_DEPS, 'Install backend/requirements-dev.txt for FastAPI HTTP integration tests')
class ApiTests(unittest.TestCase):
    def setUp(self):
        with self.database.connect() as con:con.execute('DELETE FROM interpretation_jobs')
    @classmethod
    def setUpClass(cls):
        from unittest.mock import patch
        cls.worker=patch('app.services.auto_interpretation.schedule');cls.worker.start();cls.addClassCleanup(cls.worker.stop)
        from app.routers.auth import attempts
        attempts.clear()
        from fastapi.testclient import TestClient
        from app.core import bootstrap, database
        from app.main import app
        cls.bootstrap, cls.database = bootstrap, database
        cls.old = (bootstrap.ROOT, bootstrap.DB, database.DB)
        cls.temp = tempfile.TemporaryDirectory()
        bootstrap.ROOT = Path(cls.temp.name)
        (bootstrap.ROOT / 'data').mkdir()
        bootstrap.DB = database.DB = bootstrap.ROOT / 'data' / 'api.sqlite3'
        cls.client = TestClient(app)
        cls.client.__enter__()
        cls.password = (bootstrap.ROOT / 'data' / 'local_login.txt').read_text().split('Password: ')[1].strip()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        cls.bootstrap.ROOT, cls.bootstrap.DB, cls.database.DB = cls.old
        cls.temp.cleanup()

    def login(self, role):
        self.client.cookies.clear()
        result = self.client.post('/api/auth/login', json={'username': role, 'password': self.password})
        self.assertEqual(result.status_code, 200, result.text)

    def test_unauthenticated_access(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/patients').status_code, 401)

    def test_role_permissions_and_input_validation(self):
        self.login('lab')
        self.assertEqual(self.client.patch('/api/patients/1/profile', json={'adherence': 99}).status_code, 403)
        self.login('nurse')
        self.assertEqual(self.client.patch('/api/patients/1/profile', json={'adherence': 101}).status_code, 422)
        self.assertEqual(self.client.get('/api/settings/audit').status_code, 403)
        self.assertEqual(self.client.get('/api/patients').status_code, 200)

    def test_cookie_and_documented_routes(self):
        self.login('admin')
        self.assertIn('session', self.client.cookies)
        for route in ['/api/risk/rules', '/api/integrations/status', '/api/settings/users', '/api/notifications', '/api/health']:
            self.assertEqual(self.client.get(route).status_code, 200, route)
        paths = self.client.get('/openapi.json').json()['paths']
        self.assertIn('/api/lab/{patient_id}/result', paths)
        self.assertIn('/api/decisions/{patient_id}/approve', paths)

    def test_foreign_origin_rejected(self):
        result = self.client.post('/api/auth/login', json={'username': 'admin', 'password': self.password}, headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(result.status_code, 403)

    def test_complete_dataset_columns_and_record_fields_preserve_source_order(self):
        from app.services.record_service import COLUMNS
        self.login('lab')
        self.assertEqual(self.client.get('/api/patients/columns').json()['columns'],COLUMNS)
        detail=self.client.get('/api/patients/1').json()
        fields=[field for section in detail['record_sections'].values() for field in section]
        ordered=sorted(fields,key=lambda field:field['order'])
        self.assertEqual([field['key'] for field in ordered[:len(COLUMNS)]],COLUMNS)
        response=self.client.get('/api/patients/table',params=[('ids',1)]+[('fields',field) for field in COLUMNS])
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(list(response.json()[0]['fields']),COLUMNS)

    def test_result_correction_accepts_original_pi_column_and_frequencies(self):
        import json
        self.login('lab')
        with self.database.connect() as con:
            patient=dict(con.execute('SELECT * FROM patients WHERE id=1').fetchone())
            episode=dict(con.execute('SELECT * FROM episodes WHERE patient_id=1').fetchone())
            raw=json.loads(patient['source_overrides_json'] or '{}')
            raw['Resistance to EFV']='Susceptible'
            con.execute('UPDATE patients SET source_overrides_json=? WHERE id=1',(json.dumps(raw),))
            con.execute("UPDATE episodes SET status='Usable result',reviewed_at=NULL,decision=NULL,received_at='2026-10-01',suggestion_json='{}' WHERE patient_id=1")
        try:
            body={'outcome':'Usable result','tested_at':'2026-10-20','released_at':'2026-10-21',
                  'correction_reason':'Correct genotype transcription','pi':'M46I(99.9%)','insti':'R263K(100.0%)',
                  'nrti':'M184V','nnrti':'K103N','drug_levels':{'3TC':'High-Level Resistance','EFV':''}}
            response=self.client.put('/api/lab/1/result',json=body)
            self.assertEqual(response.status_code,200,response.text)
            detail=self.client.get('/api/patients/1').json()
            self.assertEqual(detail['current_record']['PI'],'M46I(99.9%)')
            self.assertEqual(detail['current_record']['INSTI'],'R263K(100.0%)')
            self.assertEqual(set(detail['patient']['suggested_mutations'].split()),{'PR:M46I','IN:R263K','RT:M184V','RT:K103N'})
            self.assertEqual(detail['current_record']['Resistance to EFV'],'')
            self.assertEqual(detail['current_record']['Resistance to 3TC'],'High-Level Resistance')
            self.assertIsNone(detail['patient']['interpretation'])
            with self.database.connect() as con:
                self.assertIsNone(con.execute('SELECT suggestion_json FROM episodes WHERE patient_id=1').fetchone()[0])
        finally:
            with self.database.connect() as con:
                con.execute('UPDATE patients SET source_overrides_json=?,data_version=? WHERE id=1',(patient['source_overrides_json'],patient['data_version']))
                keys=['status','reviewed_at','decision','received_at','suggestion_json','mutations','sequence','subtype','interpretation_json','interpreted_at','report_at','tested_at','amplified','failure_reason','discussion_status','repeat_requested_at','version']
                con.execute('UPDATE episodes SET '+','.join(key+'=?' for key in keys)+' WHERE patient_id=1',[episode[key] for key in keys])

    def test_resistance_table_keeps_exposure_and_api_results_separate(self):
        import json
        self.login('lab')
        saved={'provider':'Stanford HIVdb Sierra','version':{'text':'fixture'},'submitted_mutations':['RT:M184V'],
               'analysis':{'drugResistance':[{'gene':{'name':'RT'},'drugScores':[{'drug':{'displayAbbr':'3TC'},'score':60,'level':5,'text':'High-Level Resistance'}]}]}}
        with self.database.connect() as con:
            old=dict(con.execute('SELECT source_overrides_json FROM patients WHERE id=1').fetchone())
            original=con.execute('SELECT interpretation_json FROM episodes WHERE patient_id=1').fetchone()[0]
            con.execute('UPDATE patients SET source_overrides_json=? WHERE id=1',(json.dumps({'exposure_to_AZT':'0','exposure_to_DTG':'','Resistance to 3TC':'Susceptible'}),))
            con.execute('UPDATE episodes SET interpretation_json=? WHERE patient_id=1',(json.dumps(saved),))
        try:
            r=self.client.get('/api/patients/table',params=[('ids',1),('fields','exposure_to_AZT'),('fields','exposure_to_DTG'),('fields','Resistance to 3TC'),('include_resistance','true')])
            self.assertEqual(r.status_code,200,r.text)
            row=r.json()[0]
            self.assertEqual(row['fields']['exposure_to_AZT'],'0')
            self.assertEqual(row['fields']['exposure_to_DTG'],'')
            self.assertEqual(row['fields']['Resistance to 3TC'],'Susceptible')
            self.assertEqual(row['interpretation']['analysis']['drugResistance'][0]['drugScores'][0]['level'],5)
            self.assertNotIn('submitted_mutations',row['interpretation'])
            self.assertNotIn('interpretation',self.client.get('/api/patients/table?ids=1').json()[0])
        finally:
            with self.database.connect() as con:
                con.execute('UPDATE patients SET source_overrides_json=? WHERE id=1',(old['source_overrides_json'],))
                con.execute('UPDATE episodes SET interpretation_json=? WHERE patient_id=1',(original,))

    def test_connection_check_requires_login_and_calls_live_adapter(self):
        from unittest.mock import patch
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/integrations/stanford/check').status_code,401)
        self.login('lab')
        result={'connected':True,'version':{'text':'fixture'},'checked_at':'2026-11-13T08:00:00Z'}
        with patch('app.services.stanford_service.check_connection',return_value=result) as check:
            response=self.client.get('/api/integrations/stanford/check')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),result)
        check.assert_called_once()

    def test_saved_result_retry_is_available_to_clinician_without_editing_genotype(self):
        from unittest.mock import patch
        with self.database.connect() as con:
            before=dict(con.execute('SELECT * FROM episodes WHERE patient_id=1').fetchone())
            con.execute("UPDATE episodes SET status='Usable result',decision=NULL,mutations='RT:M184V IN:E157Q' WHERE patient_id=1")
        try:
            self.login('nurse')
            self.assertEqual(self.client.post('/api/workflow/patients/1/retry-interpretation').status_code,403)
            self.login('clinician')
            with patch('app.services.auto_interpretation.schedule') as schedule:
                response=self.client.post('/api/workflow/patients/1/retry-interpretation')
            self.assertEqual(response.status_code,200,response.text)
            schedule.assert_called_once_with(1)
            with self.database.connect() as con:
                self.assertEqual(con.execute('SELECT status FROM interpretation_jobs').fetchone()[0],'pending')
                self.assertEqual(con.execute('SELECT mutations FROM episodes WHERE patient_id=1').fetchone()[0],'RT:M184V IN:E157Q')
        finally:
            with self.database.connect() as con:
                con.execute('UPDATE episodes SET status=?,decision=?,mutations=?,interpretation_json=? WHERE patient_id=1',
                            (before['status'],before['decision'],before['mutations'],before.get('interpretation_json')))

    def test_notification_read_state_is_persistent_and_scoped_to_account(self):
        self.login('lab')
        response=self.client.get('/api/notifications/inbox?source=synthetic')
        self.assertEqual(response.status_code,200,response.text)
        inbox=response.json();self.assertTrue(inbox['items'])
        self.assertGreaterEqual(inbox['total'],inbox['unread_count'])
        unread_inbox=self.client.get('/api/notifications/inbox?source=synthetic&status=unread').json()
        self.assertEqual(unread_inbox['total'],unread_inbox['unread_count'])
        key=inbox['items'][0]['id']
        self.assertEqual(self.client.patch('/api/notifications/read',json={'ids':[key],'read':True}).status_code,200)
        again=self.client.get('/api/notifications/inbox?source=synthetic').json()
        self.assertTrue(next(i for i in again['items'] if i['id']==key)['read'])
        self.assertEqual(again['unread_count'],inbox['unread_count']-1)
        with self.database.connect() as con:
            lab_id=con.execute("SELECT id FROM users WHERE username='lab'").fetchone()[0]
            other=con.execute("SELECT id FROM users WHERE username='clinician'").fetchone()[0]
            self.assertEqual(con.execute('SELECT count(*) FROM notification_reads WHERE user_id=? AND notification_key=?',(lab_id,key)).fetchone()[0],1)
            self.assertEqual(con.execute('SELECT count(*) FROM notification_reads WHERE user_id=? AND notification_key=?',(other,key)).fetchone()[0],0)
        self.assertEqual(self.client.patch('/api/notifications/read',json={'ids':[key],'read':False}).status_code,200)
        self.assertFalse(next(i for i in self.client.get('/api/notifications/inbox?source=synthetic').json()['items'] if i['id']==key)['read'])
        self.assertEqual(self.client.patch('/api/notifications/read',json={'ids':['invalid']} ).status_code,400)

    def test_mutation_entry_saves_source_and_prefills_without_changing_lab_outcome(self):
        import json
        self.login('lab')
        with self.database.connect() as con:
            patient=dict(con.execute('SELECT * FROM patients WHERE id=1').fetchone())
            episode=dict(con.execute('SELECT * FROM episodes WHERE patient_id=1').fetchone())
            overlays=json.loads(patient['source_overrides_json'] or '{}')
            overlays['Resistance to 3TC']='Susceptible'
            con.execute('UPDATE patients SET source_overrides_json=? WHERE id=1',(json.dumps(overlays),))
            con.execute("UPDATE episodes SET status='Usable result',reviewed_at=NULL,decision=NULL,interpretation_json=?,sequence='ACGT',suggestion_json='{}' WHERE patient_id=1",(json.dumps({'version':{'text':'old'}}),))
        body={'pi':'M46I, I54V','insti':'E157Q(99.7%)','nrti':'M184V(99.2%)','nnrti':'K103N',
              'reason':'Entered from laboratory report','expected_version':patient['data_version'],'expected_lab_version':episode['version']}
        response=self.client.put('/api/lab/1/mutations',json=body)
        self.assertEqual(response.status_code,200,response.text)
        detail=self.client.get('/api/patients/1').json()
        updated=detail['patient']
        self.assertEqual(detail['current_record']['INSTI'],'E157Q(99.7%)')
        self.assertEqual(detail['current_record']['Resistance to 3TC'],'')
        self.assertEqual(set(updated['suggested_mutations'].split()),{'PR:M46I','PR:I54V','IN:E157Q','RT:M184V','RT:K103N'})
        self.assertIsNone(updated['interpretation'])
        self.assertEqual(updated['status'],'Usable result')
        self.assertEqual(updated['sequence'],'')
        self.assertEqual(updated['report_at'],episode['report_at'])
        self.assertEqual(self.client.put('/api/lab/1/mutations',json=body).status_code,409)
        with self.database.connect() as con:
            con.execute('UPDATE patients SET source_overrides_json=?,data_version=? WHERE id=1',(patient['source_overrides_json'],patient['data_version']))
            for key in ('status','reviewed_at','decision','interpretation_json','sequence','suggestion_json','mutations','version'):
                con.execute('UPDATE episodes SET '+key+'=? WHERE patient_id=1',(episode[key],))

    def test_mutation_entry_permissions_and_validation(self):
        self.login('lab')
        detail=self.client.get('/api/patients/2').json()['patient']
        body={'nrti':'RT:patient','reason':'Entered from laboratory report',
              'expected_version':detail['data_version'],'expected_lab_version':detail['version']}
        self.login('nurse')
        self.assertEqual(self.client.put('/api/lab/2/mutations',json=body).status_code,403)
        self.login('lab')
        with self.database.connect() as con:
            before=dict(con.execute('SELECT * FROM episodes WHERE patient_id=2').fetchone())
            con.execute("UPDATE episodes SET status='Pending',reviewed_at=NULL,decision=NULL WHERE patient_id=2")
        self.assertEqual(self.client.put('/api/lab/2/mutations',json=body).status_code,400)
        body['nrti']='M184V'
        self.assertEqual(self.client.put('/api/lab/2/mutations',json=body).status_code,200)
        self.assertEqual(self.client.get('/api/patients/2').json()['patient']['status'],'Pending')
        with self.database.connect() as con:
            con.execute("UPDATE episodes SET reviewed_at='2026-11-01' WHERE patient_id=2")
        detail=self.client.get('/api/patients/2').json()['patient']
        body.update(expected_version=detail['data_version'],expected_lab_version=detail['version'])
        self.assertEqual(self.client.put('/api/lab/2/mutations',json=body).status_code,409)
        with self.database.connect() as con:
            for key in ('status','reviewed_at','decision'):
                con.execute('UPDATE episodes SET '+key+'=? WHERE patient_id=2',(before[key],))
