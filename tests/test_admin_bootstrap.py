import os
import unittest
from unittest.mock import patch

from backend import server


class FakeUsers:
    def __init__(self):
        self.calls = []

    async def update_one(self, query, update, upsert=False):
        self.calls.append((query, update, upsert))


class FakeDb:
    def __init__(self):
        self.users = FakeUsers()


class SyncAdminUserTest(unittest.IsolatedAsyncioTestCase):
    async def test_does_nothing_without_admin_variables(self):
        fake_db = FakeDb()
        with patch.dict(os.environ, {}, clear=True), patch.object(server, 'db', fake_db):
            await server.sync_admin_user()
        self.assertEqual(fake_db.users.calls, [])

    async def test_rejects_incomplete_admin_configuration(self):
        fake_db = FakeDb()
        with patch.dict(os.environ, {'ADMIN_EMAIL': 'admin@example.com'}, clear=True), patch.object(server, 'db', fake_db):
            with self.assertRaisesRegex(RuntimeError, 'ADMIN_EMAIL e ADMIN_PASSWORD'):
                await server.sync_admin_user()
        self.assertEqual(fake_db.users.calls, [])

    async def test_upserts_admin_with_normalized_email_and_hashed_password(self):
        fake_db = FakeDb()
        variables = {
            'ADMIN_EMAIL': '  ADMIN@Example.COM ',
            'ADMIN_PASSWORD': 'senha-segura',
            'ADMIN_NAME': '  Administrador Railway  ',
        }
        with patch.dict(os.environ, variables, clear=True), patch.object(server, 'db', fake_db):
            await server.sync_admin_user()

        self.assertEqual(len(fake_db.users.calls), 1)
        query, update, upsert = fake_db.users.calls[0]
        self.assertEqual(query, {'email': 'admin@example.com'})
        self.assertTrue(upsert)
        self.assertEqual(update['$set']['nome'], 'Administrador Railway')
        self.assertEqual(update['$set']['role'], 'admin')
        self.assertTrue(server.verify_password('senha-segura', update['$set']['senha_hash']))
        self.assertNotEqual(update['$set']['senha_hash'], 'senha-segura')
        self.assertIn('id', update['$setOnInsert'])
        self.assertIn('created_at', update['$setOnInsert'])


if __name__ == '__main__':
    unittest.main()
