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
        self.assertIn('/api/lab/{patient_id}', paths)
        self.assertIn('/api/decisions/{patient_id}/approve', paths)

    def test_foreign_origin_rejected(self):
        result = self.client.post('/api/auth/login', json={'username': 'admin', 'password': self.password}, headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(result.status_code, 403)
