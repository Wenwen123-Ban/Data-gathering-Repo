from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app import create_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmp.name)
        fixtures = {
            'users.json': [
                {
                    'student_id': 'stu-001',
                    'name': 'Fixture User',
                    'notifications': [],
                }
            ],
            'registration_requests.json': [],
            'borrow_transactions.json': [
                {
                    'transaction_id': 'BTX-0001',
                    'student_id': 'stu-001',
                    'book_id': 'BK-101',
                    'reservation_date': '2026-04-28',
                    'status': 'reserved',
                }
            ],
            'date_restrictions.json': [],
        }
        for filename, payload in fixtures.items():
            (self.data_dir / filename).write_text(json.dumps(payload), encoding='utf-8')

        self.media_dir = self.data_dir / 'media'
        self.app = create_app(base_dir=self.data_dir, media_dir=self.media_dir)
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def test_health(self):
        resp = self.client.get('/api/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])

    def test_create_registration_request(self):
        payload = {
            'name': 'Test Student',
            'student_id': 'stu-test',
            'school_level': 'College',
            'year': '1',
            'course': 'BSIT',
            'contact': '123',
        }
        resp = self.client.post('/api/registration_requests', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['request']['student_id'], 'stu-test')

    def test_create_reservation_requires_fields(self):
        resp = self.client.post('/api/reservations', json={'student_id': 'x'})
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
