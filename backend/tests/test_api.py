"""HTTP integration checks. Install requirements-dev.txt to run these checks."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

HAS_HTTP_TEST_DEPS = all(importlib.util.find_spec(module) for module in ('fastapi', 'httpx'))

@unittest.skipUnless(HAS_HTTP_TEST_DEPS, 'Install backend/requirements-dev.txt for FastAPI HTTP integration tests')
class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
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
