
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app as smart_matatu_app


class DestinationChangeSecurityTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.temp_dir.name,
            "test_destination_changes.db"
        )

        self.create_test_database()

        self.database_patch = patch.object(
            smart_matatu_app,
            "get_db_connection",
            self.get_test_connection
        )
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.client = smart_matatu_app.app.test_client()
        self.csrf_token = "test-conductor-csrf-token"

        self.login_as_conductor()

    def get_test_connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_test_database(self):
        connection = sqlite3.connect(self.db_path)

        connection.executescript("""
            CREATE TABLE matatus (
                id INTEGER PRIMARY KEY,
                registration_number TEXT,
                route_name TEXT
            );

            CREATE TABLE conductors (
                id INTEGER PRIMARY KEY,
                full_name TEXT,
                email TEXT,
                password_hash TEXT,
                is_active INTEGER DEFAULT 1
            );

            CREATE TABLE matatu_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conductor_id INTEGER NOT NULL,
                matatu_id INTEGER NOT NULL,
                assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT
            );

            CREATE TABLE passengers (
                id INTEGER PRIMARY KEY,
                passenger_code TEXT
            );

            CREATE TABLE stages (
                id INTEGER PRIMARY KEY,
                route_name TEXT,
                name TEXT,
                latitude REAL,
                longitude REAL,
                sequence_number INTEGER
            );

            CREATE TABLE passenger_destinations (
                id INTEGER PRIMARY KEY,
                matatu_id INTEGER,
                passenger_id INTEGER,
                passenger_token TEXT,
                destination_stage_id INTEGER,
                status TEXT DEFAULT 'waiting'
            );

            CREATE TABLE destination_change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                current_destination_stage_id INTEGER NOT NULL,
                requested_destination_stage_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN ('pending', 'approved', 'rejected')
                    ),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            );

            INSERT INTO matatus VALUES
                (1, 'KAA123A', 'Kisii-Nairobi'),
                (2, 'KBB456B', 'Kisii-Keroka');

            INSERT INTO conductors (
                id, full_name, email, password_hash, is_active
            )
            VALUES (
                1, 'Test Conductor', 'conductor@test.com',
                'test-password', 1
            );

            INSERT INTO matatu_assignments (
                conductor_id, matatu_id
            )
            VALUES (1, 1);

            INSERT INTO passengers VALUES (1, 'P001');

            INSERT INTO stages VALUES
                (1, 'Kisii-Nairobi', 'Stage One', NULL, NULL, 1),
                (2, 'Kisii-Nairobi', 'Stage Two', NULL, NULL, 2),
                (3, 'Kisii-Keroka', 'Stage Three', NULL, NULL, 1);

            INSERT INTO passenger_destinations (
                id, matatu_id, passenger_id,
                passenger_token, destination_stage_id, status
            )
            VALUES
                (1, 1, 1, 'P001', 1, 'waiting'),
                (2, 2, 1, 'P002', 3, 'waiting');
        """)

        connection.commit()
        connection.close()

    def login_as_conductor(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 1
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["matatu_id"] = 1
            session["csrf_token"] = self.csrf_token

    def add_request(
        self,
        request_id=1,
        journey_id=1,
        matatu_id=1,
        current_stage=1,
        requested_stage=2
    ):
        connection = self.get_test_connection()

        connection.execute(
            """
            INSERT INTO destination_change_requests (
                id, matatu_id, passenger_destination_id,
                current_destination_stage_id,
                requested_destination_stage_id,
                status
            )
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (
                request_id,
                matatu_id,
                journey_id,
                current_stage,
                requested_stage
            )
        )

        connection.commit()
        connection.close()

    def get_request(self, request_id):
        connection = self.get_test_connection()

        row = connection.execute(
            """
            SELECT status
            FROM destination_change_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()

        connection.close()
        return row["status"] if row else None

    def get_journey_destination(self, journey_id):
        connection = self.get_test_connection()

        row = connection.execute(
            """
            SELECT destination_stage_id
            FROM passenger_destinations
            WHERE id = ?
            """,
            (journey_id,)
        ).fetchone()

        connection.close()
        return row["destination_stage_id"]

    def get_journey_status(self, journey_id):
            connection = self.get_test_connection()

            row = connection.execute(
                """
                SELECT status
                FROM passenger_destinations
                WHERE id = ?
                """,
                (journey_id,)
            ).fetchone()

            connection.close()
            return row["status"] if row else None

    def decision_headers(self):
        return {
            "X-CSRF-Token": self.csrf_token,
            "Content-Type": "application/json"
        }

    def test_unauthenticated_listing_is_rejected(self):
        with self.client.session_transaction() as session:
            session.clear()

        response = self.client.get(
            "/api/conductor/destination-change-requests/1"
        )

        self.assertEqual(response.status_code, 401)

    def test_wrong_role_cannot_list_requests(self):
        with self.client.session_transaction() as session:
            session["role"] = "admin"

        response = self.client.get(
            "/api/conductor/destination-change-requests/1"
        )

        self.assertEqual(response.status_code, 403)

    def test_conductor_cannot_list_another_matatus_requests(self):
        response = self.client.get(
            "/api/conductor/destination-change-requests/2"
        )

        self.assertEqual(response.status_code, 403)

    def test_conductor_cannot_resolve_another_matatus_request(self):
        self.add_request(
            request_id=2,
            journey_id=2,
            matatu_id=2,
            current_stage=3,
            requested_stage=3
        )

        response = self.client.post(
            "/api/conductor/destination-change-requests/2/decision",
            json={"action": "approve"},
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_request(2), "pending")

    def test_decision_without_csrf_token_is_rejected(self):
        self.add_request()

        response = self.client.post(
            "/api/conductor/destination-change-requests/1/decision",
            json={"action": "approve"}
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_request(1), "pending")

    def test_approval_updates_journey_and_request(self):
        self.add_request()

        response = self.client.post(
            "/api/conductor/destination-change-requests/1/decision",
            json={"action": "approve"},
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_request(1), "approved")
        self.assertEqual(self.get_journey_destination(1), 2)

    def test_rejection_preserves_existing_destination(self):
        self.add_request()

        response = self.client.post(
            "/api/conductor/destination-change-requests/1/decision",
            json={"action": "reject"},
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.get_request(1), "rejected")
        self.assertEqual(self.get_journey_destination(1), 1)



    def test_unauthenticated_user_cannot_access_conductor_page(self):
        with self.client.session_transaction() as session:
            session.clear()
        response = self.client.get("/conductor/1")
        self.assertEqual(response.status_code, 401)

    def test_admin_cannot_access_conductor_page(self):
        with self.client.session_transaction() as session:
            session["role"] = "admin"
        response = self.client.get("/conductor/1")
        self.assertEqual(response.status_code, 403)

    def test_conductor_cannot_access_unassigned_matatu_page(self):
        response = self.client.get("/conductor/2")
        self.assertEqual(response.status_code, 403)

    def test_conductor_can_access_assigned_matatu_page(self):
        response = self.client.get("/conductor/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CONDUCTOR DASHBOARD", response.data)
        self.assertIn(b"KAA123A", response.data)
        self.assertIn(b"P001", response.data)

        def test_unauthenticated_user_cannot_notify_passenger(self):
            with self.client.session_transaction() as session:
                session.clear()

            response = self.client.post("/notify-passenger/1")

            self.assertEqual(response.status_code, 401)
            self.assertEqual(self.get_journey_status(1), "waiting")

    def test_admin_cannot_notify_passenger(self):
        with self.client.session_transaction() as session:
            session["role"] = "admin"

        response = self.client.post(
            "/notify-passenger/1",
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_journey_status(1), "waiting")

    def test_notification_without_csrf_is_rejected(self):
        response = self.client.post("/notify-passenger/1")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_journey_status(1), "waiting")

    def test_conductor_cannot_notify_another_matatus_passenger(self):
        response = self.client.post(
            "/notify-passenger/2",
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.get_journey_status(2), "waiting")

    def test_conductor_can_notify_own_passenger(self):
        response = self.client.post(
            "/notify-passenger/1",
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.get_journey_status(1), "notified")

    def test_notification_rejects_nonexistent_journey(self):
        response = self.client.post(
            "/notify-passenger/999",
            headers=self.decision_headers()
        )

        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()

