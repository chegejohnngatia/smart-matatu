
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app as smart_matatu_app


class TestRouteLifecycle(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(
            self.temp_dir.name,
            "test_routes.db"
        )

        self._create_test_database()

        self.database_patch = patch.object(
            smart_matatu_app,
            "get_db_connection",
            self.get_test_connection
        )
        self.database_patch.start()

        self.client = smart_matatu_app.app.test_client()
        self.csrf_token = "test-admin-csrf-token"

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def get_test_connection(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_test_database(self):
        connection = sqlite3.connect(self.database_path)

        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
            CREATE TABLE routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            );

            CREATE TABLE stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_name TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                sequence_number INTEGER NOT NULL,
                route_id INTEGER REFERENCES routes(id)
            );

            CREATE TABLE matatus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_number TEXT NOT NULL,
                route_name TEXT NOT NULL,
                route_id INTEGER REFERENCES routes(id)
            );

            INSERT INTO routes (id, name, description)
            VALUES (1, 'Test Route', 'Route lifecycle test');
        """)

        connection.commit()
        connection.close()

    def login_as_admin(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["full_name"] = "Test Admin"
            session["email"] = "admin@test.com"
            session["role"] = "admin"
            session["csrf_token"] = self.csrf_token

    def login_as_conductor(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["csrf_token"] = self.csrf_token

    def delete_route(self, route_id=1, csrf_token=None):
        headers = {}

        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.delete(
            f"/api/admin/routes/{route_id}",
            headers=headers
        )

    def test_admin_can_delete_route_without_dependencies(self):
        self.login_as_admin()

        response = self.delete_route(
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

        connection = self.get_test_connection()
        route = connection.execute(
            "SELECT id FROM routes WHERE id = 1"
        ).fetchone()
        connection.close()

        self.assertIsNone(route)

    def test_route_with_stages_cannot_be_deleted(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            INSERT INTO stages (
                route_name,
                name,
                sequence_number,
                route_id
            )
            VALUES (?, ?, ?, ?)
        """, ("Test Route", "Test Stage", 1, 1))
        connection.commit()
        connection.close()

        response = self.delete_route(
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["dependencies"]["stages"],
            1
        )

        connection = self.get_test_connection()
        route = connection.execute(
            "SELECT id FROM routes WHERE id = 1"
        ).fetchone()
        stage_count = connection.execute(
            "SELECT COUNT(*) FROM stages WHERE route_id = 1"
        ).fetchone()[0]
        connection.close()

        self.assertIsNotNone(route)
        self.assertEqual(stage_count, 1)

    def test_route_with_matatus_cannot_be_deleted(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            INSERT INTO matatus (
                registration_number,
                route_name,
                route_id
            )
            VALUES (?, ?, ?)
        """, ("KAA 123A", "Test Route", 1))
        connection.commit()
        connection.close()

        response = self.delete_route(
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json()["dependencies"]["matatus"],
            1
        )

        connection = self.get_test_connection()
        route = connection.execute(
            "SELECT id FROM routes WHERE id = 1"
        ).fetchone()
        matatu_count = connection.execute(
            "SELECT COUNT(*) FROM matatus WHERE route_id = 1"
        ).fetchone()[0]
        connection.close()

        self.assertIsNotNone(route)
        self.assertEqual(matatu_count, 1)

    def test_missing_route_returns_404(self):
        self.login_as_admin()

        response = self.delete_route(
            route_id=999,
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_request_returns_401(self):
        response = self.delete_route(
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 401)

    def test_conductor_cannot_delete_route(self):
        self.login_as_conductor()

        response = self.delete_route(
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 403)

    def test_missing_csrf_token_returns_403(self):
        self.login_as_admin()

        response = self.delete_route()

        self.assertEqual(response.status_code, 403)

    def test_invalid_csrf_token_returns_403(self):
        self.login_as_admin()

        response = self.delete_route(
            csrf_token="invalid-token"
        )

        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
