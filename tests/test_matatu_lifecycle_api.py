import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as smart_matatu_app
import migrate_matatu_lifecycle


class TestMatatuCreationAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(
            self.temp_dir.name,
            "test_matatus.db"
        )

        self._create_test_database()

        migrate_matatu_lifecycle.migrate(self.database_path)

        self.database_patch = patch.object(
            smart_matatu_app,
            "get_db_connection",
            self.get_test_connection
        )
        self.database_patch.start()

        self.client = smart_matatu_app.app.test_client()

        self.admin_email = "admin@test.com"
        self.admin_password = "TestAdmin123!"

        self._create_test_admin()

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
            CREATE TABLE admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT
            );

            CREATE TABLE matatus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_number TEXT NOT NULL,
                route_name TEXT NOT NULL,
                route_id INTEGER REFERENCES routes(id)
            );

            CREATE TABLE conductors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                passport_photo TEXT
            );

            CREATE TABLE matatu_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conductor_id INTEGER NOT NULL,
                matatu_id INTEGER NOT NULL,
                assigned_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                ended_at TEXT,

                FOREIGN KEY (conductor_id)
                    REFERENCES conductors(id),

                FOREIGN KEY (matatu_id)
                    REFERENCES matatus(id),

                CHECK (
                    ended_at IS NULL
                    OR ended_at >= assigned_at
                )
            );

            CREATE UNIQUE INDEX one_active_assignment_per_conductor
            ON matatu_assignments (conductor_id)
            WHERE ended_at IS NULL;


            CREATE TABLE stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_name TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                sequence_number INTEGER NOT NULL,
                route_id INTEGER REFERENCES routes(id),
                is_archived INTEGER NOT NULL DEFAULT 0
                    CHECK (is_archived IN (0, 1)),
                archived_at TEXT
            );

            CREATE UNIQUE INDEX unique_active_stage_sequence_per_route
            ON stages (route_id, sequence_number)
            WHERE is_archived = 0;

            CREATE TABLE passengers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_code TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE passenger_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_token TEXT NOT NULL,
                destination_stage_id INTEGER NOT NULL,
                status TEXT DEFAULT 'waiting',
                passenger_id INTEGER REFERENCES passengers(id),
                access_token_hash TEXT
            );

            CREATE TABLE destination_change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                current_destination_stage_id INTEGER NOT NULL,
                requested_destination_stage_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                FOREIGN KEY (matatu_id) REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id),
                FOREIGN KEY (current_destination_stage_id)
                    REFERENCES stages(id),
                FOREIGN KEY (requested_destination_stage_id)
                    REFERENCES stages(id)
            );

            CREATE TABLE passenger_balances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                amount REAL NOT NULL CHECK (amount > 0),
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN (
                            'pending',
                            'awaiting_confirmation',
                            'confirmed'
                        )
                    ),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                paid_at TEXT,
                confirmed_at TEXT,
                paid_by_conductor_id INTEGER REFERENCES conductors(id),
                FOREIGN KEY (matatu_id) REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id)
            );

            CREATE TABLE emergency_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL
                    CHECK (alert_type IN ('proximity', 'passenger_issue')),
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'acknowledged')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TEXT,
                acknowledged_by_conductor_id INTEGER
                    REFERENCES conductors(id),
                FOREIGN KEY (matatu_id) REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id)
            );

            CREATE TABLE passenger_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                balance_id INTEGER,
                notification_type TEXT NOT NULL
                    CHECK (
                        notification_type IN (
                            'payment_confirmation',
                            'payment_reminder'
                        )
                    ),
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
                    CHECK (is_read IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE matatu_locations (
                matatu_id INTEGER PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                current_stage_sequence INTEGER DEFAULT 0,
                speed REAL DEFAULT 20
            );

            INSERT INTO routes (id, name, description, is_active)
            VALUES
                (1, 'Nairobi - Thika', 'Test active route', 1),
                (2, 'Nakuru - Nairobi', 'Test inactive route', 0),
                (3, 'Nairobi - Muranga', 'Second active test route', 1);


            INSERT INTO stages (
                id, route_name, name, sequence_number, route_id
            )
            VALUES
                (1, 'Nairobi - Thika', 'Rosters', 1, 1),
                (2, 'Nairobi - Thika', 'Kasarani', 2, 1),
                (3, 'Nairobi - Thika', 'Thika', 3, 1),
                (4, 'Nairobi - Muranga', 'Rosters', 1, 3),
                (5, 'Nairobi - Muranga', 'Muranga', 2, 3);
        """)

        connection.commit()
        connection.close()

    def _create_test_admin(self):
        connection = self.get_test_connection()

        connection.execute("""
            INSERT INTO admins (
                full_name,
                email,
                password_hash,
                is_active
            )
            VALUES (?, ?, ?, 1)
        """, (
            "Test Administrator",
            self.admin_email,
            generate_password_hash(self.admin_password)
        ))

        connection.commit()
        connection.close()

    def login_as_admin(self):
        response = self.client.post(
            "/api/auth/login",
            json={
                "email": self.admin_email,
                "password": self.admin_password
            }
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertTrue(data["success"])
        self.assertIn("csrf_token", data)

        return data["csrf_token"]

    def create_matatu(self, registration_number="KXX 123X",
                      route_id=1, csrf_token=None):

        headers = {}

        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.post(
            "/api/admin/matatus",
            json={
                "registration_number": registration_number,
                "route_id": route_id
            },
            headers=headers
        )

    def update_matatu(self, matatu_id, payload, csrf_token=None):
        headers = {}

        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.put(
            f"/api/admin/matatus/{matatu_id}",
            json=payload,
            headers=headers
        )

    def test_admin_can_create_matatu(self):
        csrf_token = self.login_as_admin()

        response = self.create_matatu(
            registration_number="KXX 123X",
            route_id=1,
            csrf_token=csrf_token
        )

        self.assertEqual(response.status_code, 201)

        data = response.get_json()

        self.assertTrue(data["success"])
        self.assertEqual(
            data["matatu"]["registration_number"],
            "KXX 123X"
        )
        self.assertEqual(data["matatu"]["route_id"], 1)
        self.assertEqual(
            data["matatu"]["route_name"],
            "Nairobi - Thika"
        )
        self.assertFalse(data["matatu"]["is_archived"])
        self.assertIsNone(data["matatu"]["archived_at"])

        connection = self.get_test_connection()

        matatu = connection.execute("""
            SELECT *
            FROM matatus
            WHERE registration_number = ?
        """, ("KXX 123X",)).fetchone()

        registry = connection.execute("""
            SELECT *
            FROM matatu_registration_registry
            WHERE normalized_registration_number = ?
        """, ("KXX 123X",)).fetchone()

        connection.close()

        self.assertIsNotNone(matatu)
        self.assertIsNotNone(registry)
        self.assertEqual(matatu["route_id"], 1)
        self.assertEqual(registry["original_matatu_id"], matatu["id"])

    def test_registration_number_is_normalized(self):
        csrf_token = self.login_as_admin()

        response = self.create_matatu(
            registration_number="  kxx 123x  ",
            route_id=1,
            csrf_token=csrf_token
        )

        self.assertEqual(response.status_code, 201)

        connection = self.get_test_connection()

        registry = connection.execute("""
            SELECT normalized_registration_number,
                   registration_number
            FROM matatu_registration_registry
        """).fetchone()

        connection.close()

        self.assertEqual(
            registry["normalized_registration_number"],
            "KXX 123X"
        )
        self.assertEqual(
            registry["registration_number"],
            "kxx 123x"
        )

    def test_duplicate_registration_is_rejected(self):
        csrf_token = self.login_as_admin()

        first_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )

        self.assertEqual(first_response.status_code, 201)

        second_response = self.create_matatu(
            "kxx 123x", 1, csrf_token
        )

        self.assertEqual(second_response.status_code, 409)

        connection = self.get_test_connection()

        count = connection.execute("""
            SELECT COUNT(*)
            FROM matatus
        """).fetchone()[0]

        connection.close()

        self.assertEqual(count, 1)

    def test_permanently_deleted_registration_cannot_be_reused(self):
        csrf_token = self.login_as_admin()

        first_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )

        self.assertEqual(first_response.status_code, 201)

        connection = self.get_test_connection()

        matatu_id = first_response.get_json()["matatu"]["id"]

        connection.execute(
            "DELETE FROM matatus WHERE id = ?",
            (matatu_id,)
        )

        connection.execute("""
            UPDATE matatu_registration_registry
            SET permanently_deleted_at = CURRENT_TIMESTAMP
            WHERE normalized_registration_number = ?
        """, ("KXX 123X",))

        connection.commit()
        connection.close()

        response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )

        self.assertEqual(response.status_code, 409)

    def test_missing_registration_number_is_rejected(self):
        csrf_token = self.login_as_admin()

        response = self.client.post(
            "/api/admin/matatus",
            json={"route_id": 1},
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 400)

    def test_empty_registration_number_is_rejected(self):
        csrf_token = self.login_as_admin()

        response = self.create_matatu(
            "   ", 1, csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_invalid_route_ids_are_rejected(self):
        csrf_token = self.login_as_admin()

        invalid_route_ids = [
            0,
            -1,
            True,
            "1",
            None
        ]

        for route_id in invalid_route_ids:
            with self.subTest(route_id=route_id):
                response = self.create_matatu(
                    "KXX 123X",
                    route_id,
                    csrf_token
                )

                self.assertEqual(response.status_code, 400)

    def test_inactive_route_is_rejected(self):
        csrf_token = self.login_as_admin()

        response = self.create_matatu(
            "KXX 123X", 2, csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_nonexistent_route_is_rejected(self):
        csrf_token = self.login_as_admin()

        response = self.create_matatu(
            "KXX 123X", 999, csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_request_is_rejected(self):
        response = self.create_matatu(
            "KXX 123X", 1
        )

        self.assertEqual(response.status_code, 401)

    def test_conductor_cannot_create_matatu(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["csrf_token"] = "conductor-csrf-token"

        response = self.create_matatu(
            "KXX 123X",
            1,
            "conductor-csrf-token"
        )

        self.assertEqual(response.status_code, 403)

    def test_missing_csrf_token_is_rejected(self):
        self.login_as_admin()

        response = self.create_matatu(
            "KXX 123X", 1
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_csrf_token_is_rejected(self):
        self.login_as_admin()

        response = self.create_matatu(
            "KXX 123X",
            1,
            "incorrect-token"
        )

        self.assertEqual(response.status_code, 403)

    def test_invalid_json_body_is_rejected(self):
        csrf_token = self.login_as_admin()

        response = self.client.post(
            "/api/admin/matatus",
            data="invalid-json",
            content_type="application/json",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 400)

    def test_registry_failure_rolls_back_matatu_insert(self):
        csrf_token = self.login_as_admin()

        connection = self.get_test_connection()

        connection.execute("""
            CREATE TRIGGER reject_registry_insert
            BEFORE INSERT ON matatu_registration_registry
            BEGIN
                SELECT RAISE(ABORT, 'Simulated registry failure');
            END;
        """)

        connection.commit()
        connection.close()

        response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )

        self.assertEqual(response.status_code, 500)

        connection = self.get_test_connection()

        matatu_count = connection.execute("""
            SELECT COUNT(*)
            FROM matatus
            WHERE registration_number = ?
        """, ("KXX 123X",)).fetchone()[0]

        registry_count = connection.execute("""
            SELECT COUNT(*)
            FROM matatu_registration_registry
            WHERE normalized_registration_number = ?
        """, ("KXX 123X",)).fetchone()[0]

        connection.close()

        self.assertEqual(matatu_count, 0)
        self.assertEqual(registry_count, 0)


    def test_admin_can_edit_matatu_registration_and_history(self):
        csrf_token = self.login_as_admin()
        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        response = self.update_matatu(
            matatu_id,
            {"registration_number": "KCA 456B"},
            csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["matatu"]["registration_number"],
            "KCA 456B"
        )

        connection = self.get_test_connection()

        matatu = connection.execute(
            "SELECT registration_number FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        history = connection.execute(
            "SELECT registration_number, normalized_registration_number, "
            "effective_start, effective_end "
            "FROM matatu_registration_history "
            "WHERE matatu_id = ? ORDER BY id",
            (matatu_id,)
        ).fetchall()

        registry = connection.execute(
            "SELECT normalized_registration_number, original_matatu_id "
            "FROM matatu_registration_registry "
            "ORDER BY id"
        ).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KCA 456B")
        self.assertEqual(len(history), 2)

        self.assertEqual(history[0]["registration_number"], "KXX 123X")
        self.assertIsNotNone(history[0]["effective_end"])

        self.assertEqual(history[1]["registration_number"], "KCA 456B")
        self.assertEqual(
            history[1]["normalized_registration_number"],
            "KCA 456B"
        )
        self.assertIsNone(history[1]["effective_end"])

        self.assertEqual(len(registry), 2)
        self.assertEqual(
            {row["normalized_registration_number"] for row in registry},
            {"KXX 123X", "KCA 456B"}
        )
        self.assertTrue(
            all(row["original_matatu_id"] == matatu_id for row in registry)
        )

    def test_admin_can_edit_matatu_route_without_changing_history(self):
        csrf_token = self.login_as_admin()
        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()
        history_before = connection.execute(
            "SELECT id, registration_number, normalized_registration_number, "
            "effective_start, effective_end "
            "FROM matatu_registration_history WHERE matatu_id = ?",
            (matatu_id,)
        ).fetchall()
        connection.close()

        response = self.update_matatu(
            matatu_id,
            {"route_id": 3},
            csrf_token
        )

        self.assertEqual(response.status_code, 200)

        updated = response.get_json()["matatu"]
        self.assertEqual(updated["route_id"], 3)
        self.assertEqual(updated["route_name"], "Nairobi - Muranga")

        connection = self.get_test_connection()

        matatu = connection.execute(
            "SELECT registration_number, route_id, route_name "
            "FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        history_after = connection.execute(
            "SELECT id, registration_number, normalized_registration_number, "
            "effective_start, effective_end "
            "FROM matatu_registration_history WHERE matatu_id = ?",
            (matatu_id,)
        ).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KXX 123X")
        self.assertEqual(matatu["route_id"], 3)
        self.assertEqual(matatu["route_name"], "Nairobi - Muranga")
        self.assertEqual(len(history_before), 1)
        self.assertEqual(len(history_after), 1)
        self.assertEqual(dict(history_before[0]), dict(history_after[0]))


    def test_admin_can_edit_registration_and_route_together(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        response = self.update_matatu(
            matatu_id,
            {
                "registration_number": "KCA 456B",
                "route_id": 3
            },
            csrf_token
        )

        self.assertEqual(response.status_code, 200)

        updated = response.get_json()["matatu"]
        self.assertEqual(updated["registration_number"], "KCA 456B")
        self.assertEqual(updated["route_id"], 3)
        self.assertEqual(updated["route_name"], "Nairobi - Muranga")

        connection = self.get_test_connection()

        matatu = connection.execute(
            "SELECT registration_number, route_id, route_name "
            "FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        history = connection.execute(
            "SELECT registration_number, effective_end "
            "FROM matatu_registration_history "
            "WHERE matatu_id = ? ORDER BY id",
            (matatu_id,)
        ).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KCA 456B")
        self.assertEqual(matatu["route_id"], 3)
        self.assertEqual(matatu["route_name"], "Nairobi - Muranga")
        self.assertEqual(len(history), 2)
        self.assertIsNotNone(history[0]["effective_end"])
        self.assertEqual(history[1]["registration_number"], "KCA 456B")
        self.assertIsNone(history[1]["effective_end"])



    def test_admin_cannot_use_registration_reserved_by_another_matatu(self):
        csrf_token = self.login_as_admin()

        first_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(first_response.status_code, 201)
        first_id = first_response.get_json()["matatu"]["id"]

        second_response = self.create_matatu(
            "KCA 456B", 1, csrf_token
        )
        self.assertEqual(second_response.status_code, 201)
        second_id = second_response.get_json()["matatu"]["id"]

        response = self.update_matatu(
            second_id,
            {"registration_number": "KXX 123X"},
            csrf_token
        )

        self.assertEqual(response.status_code, 409)

        connection = self.get_test_connection()

        first_matatu = connection.execute(
            "SELECT registration_number FROM matatus WHERE id = ?",
            (first_id,)
        ).fetchone()

        second_matatu = connection.execute(
            "SELECT registration_number FROM matatus WHERE id = ?",
            (second_id,)
        ).fetchone()

        second_history = connection.execute(
            "SELECT registration_number, effective_end "
            "FROM matatu_registration_history "
            "WHERE matatu_id = ? ORDER BY id",
            (second_id,)
        ).fetchall()

        registry = connection.execute(
            "SELECT normalized_registration_number, original_matatu_id "
            "FROM matatu_registration_registry ORDER BY id"
        ).fetchall()

        connection.close()

        self.assertEqual(first_matatu["registration_number"], "KXX 123X")
        self.assertEqual(second_matatu["registration_number"], "KCA 456B")

        self.assertEqual(len(second_history), 1)
        self.assertEqual(second_history[0]["registration_number"], "KCA 456B")
        self.assertIsNone(second_history[0]["effective_end"])

        self.assertEqual(len(registry), 2)
        self.assertEqual(
            {
                row["normalized_registration_number"]
                for row in registry
            },
            {"KXX 123X", "KCA 456B"}
        )



    def test_matatu_cannot_reuse_its_own_historical_registration(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)
        matatu_id = create_response.get_json()["matatu"]["id"]

        change_response = self.update_matatu(
            matatu_id,
            {"registration_number": "KCA 456B"},
            csrf_token
        )
        self.assertEqual(change_response.status_code, 200)

        connection = self.get_test_connection()

        history_before = connection.execute(
            "SELECT registration_number, effective_start, effective_end "
            "FROM matatu_registration_history "
            "WHERE matatu_id = ? ORDER BY id",
            (matatu_id,)
        ).fetchall()

        registry_before = connection.execute(
            "SELECT normalized_registration_number, original_matatu_id "
            "FROM matatu_registration_registry ORDER BY id"
        ).fetchall()

        connection.close()

        response = self.update_matatu(
            matatu_id,
            {"registration_number": "KXX 123X"},
            csrf_token
        )

        self.assertEqual(response.status_code, 409)

        connection = self.get_test_connection()

        matatu = connection.execute(
            "SELECT registration_number FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        history_after = connection.execute(
            "SELECT registration_number, effective_start, effective_end "
            "FROM matatu_registration_history "
            "WHERE matatu_id = ? ORDER BY id",
            (matatu_id,)
        ).fetchall()

        registry_after = connection.execute(
            "SELECT normalized_registration_number, original_matatu_id "
            "FROM matatu_registration_registry ORDER BY id"
        ).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KCA 456B")
        self.assertEqual(len(history_after), 2)
        self.assertEqual(
            [dict(row) for row in history_before],
            [dict(row) for row in history_after]
        )
        self.assertEqual(
            [dict(row) for row in registry_before],
            [dict(row) for row in registry_after]
        )




    def test_matatu_edit_rejects_invalid_payloads_without_changes(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        invalid_payloads = [
            None,
            {},
            {"unknown_field": "value"},
            {"registration_number": 123},
            {"registration_number": "   "},
            {"route_id": True},
            {"route_id": 0},
            {"route_id": 2},
            {"route_id": 999}
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                response = self.update_matatu(
                    matatu_id, payload, csrf_token
                )
                self.assertEqual(response.status_code, 400)

        connection = self.get_test_connection()

        matatu = connection.execute(
            "SELECT registration_number, route_id, route_name "
            "FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        history = connection.execute(
            "SELECT registration_number, effective_start, effective_end "
            "FROM matatu_registration_history "
            "WHERE matatu_id = ? ORDER BY id",
            (matatu_id,)
        ).fetchall()

        registry = connection.execute(
            "SELECT normalized_registration_number, original_matatu_id "
            "FROM matatu_registration_registry ORDER BY id"
        ).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KXX 123X")
        self.assertEqual(matatu["route_id"], 1)
        self.assertEqual(matatu["route_name"], "Nairobi - Thika")

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["registration_number"], "KXX 123X")
        self.assertIsNone(history[0]["effective_end"])

        self.assertEqual(len(registry), 1)
        self.assertEqual(
            registry[0]["normalized_registration_number"], "KXX 123X"
        )
        self.assertEqual(registry[0]["original_matatu_id"], matatu_id)

    def test_archived_matatu_cannot_be_edited(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE matatus
            SET is_archived = 1,
                archived_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (matatu_id,))
        connection.commit()
        connection.close()

        response = self.update_matatu(
            matatu_id,
            {
                "registration_number": "KCA 456B",
                "route_id": 3
            },
            csrf_token
        )

        self.assertEqual(response.status_code, 409)

        connection = self.get_test_connection()

        matatu = connection.execute(
            "SELECT registration_number, route_id, route_name, "
            "is_archived FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        history = connection.execute(
            "SELECT registration_number, effective_end "
            "FROM matatu_registration_history WHERE matatu_id = ?",
            (matatu_id,)
        ).fetchall()

        registry = connection.execute(
            "SELECT normalized_registration_number "
            "FROM matatu_registration_registry ORDER BY id"
        ).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KXX 123X")
        self.assertEqual(matatu["route_id"], 1)
        self.assertEqual(matatu["route_name"], "Nairobi - Thika")
        self.assertEqual(matatu["is_archived"], 1)

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["registration_number"], "KXX 123X")
        self.assertIsNone(history[0]["effective_end"])

        self.assertEqual(len(registry), 1)
        self.assertEqual(
            registry[0]["normalized_registration_number"], "KXX 123X"
        )

    def test_editing_nonexistent_matatu_returns_404(self):
        csrf_token = self.login_as_admin()

        response = self.update_matatu(
            999999,
            {"registration_number": "KCA 456B"},
            csrf_token
        )

        self.assertEqual(response.status_code, 404)

        data = response.get_json()
        self.assertFalse(data["success"])

    def test_same_normalized_registration_does_not_create_history(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        response = self.update_matatu(
            matatu_id,
            {"registration_number": "  kxx 123x  "},
            csrf_token
        )

        self.assertEqual(response.status_code, 200)

        connection = self.get_test_connection()

        history = connection.execute(
            "SELECT registration_number, effective_end "
            "FROM matatu_registration_history WHERE matatu_id = ?",
            (matatu_id,)
        ).fetchall()

        registry = connection.execute(
            "SELECT normalized_registration_number "
            "FROM matatu_registration_registry"
        ).fetchall()

        connection.close()

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["registration_number"], "KXX 123X")
        self.assertIsNone(history[0]["effective_end"])

        self.assertEqual(len(registry), 1)
        self.assertEqual(
            registry[0]["normalized_registration_number"], "KXX 123X"
        )

    def test_history_insert_failure_rolls_back_matatu_edit(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        connection.execute("""
            CREATE TRIGGER reject_registration_history_insert
            BEFORE INSERT ON matatu_registration_history
            WHEN NEW.normalized_registration_number = 'KCA 456B'
            BEGIN
                SELECT RAISE(ABORT, 'Simulated history insertion failure');
            END;
        """)

        connection.commit()
        connection.close()

        response = self.update_matatu(
            matatu_id,
            {"registration_number": "KCA 456B"},
            csrf_token
        )

        self.assertEqual(response.status_code, 500)

        connection = self.get_test_connection()

        matatu = connection.execute("""
            SELECT registration_number
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()

        history = connection.execute("""
            SELECT registration_number, normalized_registration_number,
                   effective_end
            FROM matatu_registration_history
            WHERE matatu_id = ?
            ORDER BY id
        """, (matatu_id,)).fetchall()

        registry = connection.execute("""
            SELECT normalized_registration_number
            FROM matatu_registration_registry
            WHERE original_matatu_id = ?
            ORDER BY id
        """, (matatu_id,)).fetchall()

        connection.close()

        self.assertEqual(matatu["registration_number"], "KXX 123X")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["registration_number"], "KXX 123X")
        self.assertEqual(
            history[0]["normalized_registration_number"], "KXX 123X"
        )
        self.assertIsNone(history[0]["effective_end"])
        self.assertEqual(len(registry), 1)
        self.assertEqual(
            registry[0]["normalized_registration_number"], "KXX 123X"
        )

    def test_unauthenticated_edit_request_is_rejected(self):
        response = self.update_matatu(
            1, {"registration_number": "KCA 456B"}
        )

        self.assertEqual(response.status_code, 401)

    def test_conductor_cannot_edit_matatu(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["csrf_token"] = "conductor-csrf-token"

        response = self.update_matatu(
            1,
            {"registration_number": "KCA 456B"},
            "conductor-csrf-token"
        )

        self.assertEqual(response.status_code, 403)

    def test_edit_request_without_csrf_token_is_rejected(self):
        self.login_as_admin()

        response = self.update_matatu(
            1, {"registration_number": "KCA 456B"}
        )

        self.assertEqual(response.status_code, 403)

    def test_edit_request_with_invalid_csrf_token_is_rejected(self):
        self.login_as_admin()

        response = self.update_matatu(
            1,
            {"registration_number": "KCA 456B"},
            "incorrect-token"
        )

        self.assertEqual(response.status_code, 403)

    def test_route_change_preserves_active_conductor_assignment(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        conductor_cursor = connection.execute("""
            INSERT INTO conductors (
                full_name,
                email,
                password_hash,
                is_active
            )
            VALUES (?, ?, ?, 1)
        """, (
            "Test Conductor",
            "assignment-test@example.com",
            generate_password_hash("TestConductor123!")
        ))
        conductor_id = conductor_cursor.lastrowid

        connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id,
                matatu_id
            )
            VALUES (?, ?)
        """, (conductor_id, matatu_id))

        connection.commit()

        assignment_before = connection.execute("""
            SELECT id, conductor_id, matatu_id, assigned_at, ended_at
            FROM matatu_assignments
            WHERE conductor_id = ? AND ended_at IS NULL
        """, (conductor_id,)).fetchone()

        self.assertIsNotNone(assignment_before)
        connection.close()

        response = self.update_matatu(
            matatu_id,
            {"route_id": 3},
            csrf_token
        )

        self.assertEqual(response.status_code, 200)

        updated_matatu = response.get_json()["matatu"]
        self.assertEqual(updated_matatu["route_id"], 3)
        self.assertEqual(
            updated_matatu["route_name"],
            "Nairobi - Muranga"
        )

        connection = self.get_test_connection()

        assignment_after = connection.execute("""
            SELECT id, conductor_id, matatu_id, assigned_at, ended_at
            FROM matatu_assignments
            WHERE conductor_id = ?
        """, (conductor_id,)).fetchall()

        connection.close()

        self.assertEqual(len(assignment_after), 1)

        assignment_after = assignment_after[0]

        self.assertEqual(
            assignment_after["id"],
            assignment_before["id"]
        )
        self.assertEqual(
            assignment_after["conductor_id"],
            assignment_before["conductor_id"]
        )
        self.assertEqual(
            assignment_after["matatu_id"],
            assignment_before["matatu_id"]
        )
        self.assertEqual(
            assignment_after["assigned_at"],
            assignment_before["assigned_at"]
        )
        self.assertIsNone(assignment_after["ended_at"])

    def test_admin_can_archive_matatu_and_end_active_assignments(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        conductor_cursor = connection.execute("""
            INSERT INTO conductors (
                full_name, email, password_hash, is_active
            )
            VALUES (?, ?, ?, 1)
        """, (
            "Archive Test Conductor",
            "archive-test@example.com",
            generate_password_hash("TestConductor123!")
        ))
        conductor_id = conductor_cursor.lastrowid

        connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id, matatu_id, assigned_at, ended_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            conductor_id,
            matatu_id,
            "2024-01-01 08:00:00",
            "2024-01-01 09:00:00"
        ))

        connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id, matatu_id
            )
            VALUES (?, ?)
        """, (conductor_id, matatu_id))

        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertTrue(data["matatu"]["is_archived"])
        self.assertIsNotNone(data["matatu"]["archived_at"])
        self.assertEqual(data["matatu"]["id"], matatu_id)

        connection = self.get_test_connection()

        matatu = connection.execute("""
            SELECT is_archived, archived_at
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()

        assignments = connection.execute("""
            SELECT assigned_at, ended_at
            FROM matatu_assignments
            WHERE matatu_id = ?
            ORDER BY id
        """, (matatu_id,)).fetchall()

        connection.close()

        self.assertEqual(matatu["is_archived"], 1)
        self.assertIsNotNone(matatu["archived_at"])

        self.assertEqual(len(assignments), 2)

        # Existing historical assignment must remain unchanged.
        self.assertEqual(
            assignments[0]["assigned_at"],
            "2024-01-01 08:00:00"
        )
        self.assertEqual(
            assignments[0]["ended_at"],
            "2024-01-01 09:00:00"
        )

        # The active assignment must now be ended.
        self.assertIsNotNone(assignments[1]["ended_at"])

    def test_archiving_already_archived_matatu_returns_409(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        first_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(second_response.status_code, 409)
        self.assertFalse(second_response.get_json()["success"])

    def test_archiving_nonexistent_matatu_returns_404(self):
        csrf_token = self.login_as_admin()

        response = self.client.post(
            "/api/admin/matatus/999999/archive",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_unauthenticated_archive_request_is_rejected(self):
        response = self.client.post(
            "/api/admin/matatus/1/archive"
        )

        self.assertEqual(response.status_code, 401)

    def test_conductor_cannot_archive_matatu(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["csrf_token"] = "conductor-csrf-token"

        response = self.client.post(
            "/api/admin/matatus/1/archive",
            headers={"X-CSRF-Token": "conductor-csrf-token"}
        )

        self.assertEqual(response.status_code, 403)

    def test_archive_request_without_csrf_token_is_rejected(self):
        self.login_as_admin()

        response = self.client.post(
            "/api/admin/matatus/1/archive"
        )

        self.assertEqual(response.status_code, 403)

    def test_archive_failure_rolls_back_assignment_termination(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)

        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        conductor_cursor = connection.execute("""
            INSERT INTO conductors (
                full_name, email, password_hash, is_active
            )
            VALUES (?, ?, ?, 1)
        """, (
            "Rollback Test Conductor",
            "rollback-archive@example.com",
            generate_password_hash("TestConductor123!")
        ))
        conductor_id = conductor_cursor.lastrowid

        connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id, matatu_id
            )
            VALUES (?, ?)
        """, (conductor_id, matatu_id))

        connection.execute("""
            CREATE TRIGGER reject_matatu_archive
            BEFORE UPDATE OF is_archived ON matatus
            WHEN NEW.is_archived = 1
            BEGIN
                SELECT RAISE(ABORT, 'Simulated archive failure');
            END;
        """)

        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 500)

        connection = self.get_test_connection()

        matatu = connection.execute("""
            SELECT is_archived, archived_at
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()

        assignment = connection.execute("""
            SELECT ended_at
            FROM matatu_assignments
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchone()

        connection.close()

        self.assertEqual(matatu["is_archived"], 0)
        self.assertIsNone(matatu["archived_at"])
        self.assertIsNone(assignment["ended_at"])

    def test_admin_can_restore_matatu_without_recreating_assignments(self):
        csrf_token = self.login_as_admin()

        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)
        matatu_id = create_response.get_json()["matatu"]["id"]

        connection = self.get_test_connection()
        conductor_cursor = connection.execute("""
            INSERT INTO conductors (
                full_name, email, password_hash
            )
            VALUES (?, ?, ?)
        """, ("Test Conductor", "restore@test.com", "test-hash"))
        conductor_id = conductor_cursor.lastrowid

        connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id, matatu_id
            )
            VALUES (?, ?)
        """, (conductor_id, matatu_id))
        connection.commit()
        connection.close()

        archive_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        connection = self.get_test_connection()
        assignment_before = connection.execute("""
            SELECT *
            FROM matatu_assignments
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchone()
        self.assertIsNotNone(assignment_before)
        self.assertIsNotNone(assignment_before["ended_at"])
        assignment_before = dict(assignment_before)
        connection.close()

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/restore",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertFalse(data["matatu"]["is_archived"])
        self.assertIsNone(data["matatu"]["archived_at"])
        self.assertEqual(data["matatu"]["registration_number"], "KXX 123X")
        self.assertEqual(data["matatu"]["route_id"], 1)
        self.assertEqual(data["matatu"]["route_name"], "Nairobi - Thika")

        connection = self.get_test_connection()
        matatu = connection.execute("""
            SELECT *
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()
        assignments = connection.execute("""
            SELECT *
            FROM matatu_assignments
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchall()
        connection.close()

        self.assertFalse(matatu["is_archived"])
        self.assertIsNone(matatu["archived_at"])
        self.assertEqual(len(assignments), 1)
        self.assertEqual(dict(assignments[0]), assignment_before)

    def test_restoring_already_active_matatu_returns_409(self):
        csrf_token = self.login_as_admin()
        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        matatu_id = create_response.get_json()["matatu"]["id"]

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/restore",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 409)

    def test_restore_rejected_when_assigned_route_is_inactive(self):
        csrf_token = self.login_as_admin()
        create_response = self.create_matatu(
            "KXX 456X", 1, csrf_token
        )
        self.assertEqual(create_response.status_code, 201)
        matatu_id = create_response.get_json()["matatu"]["id"]

        archive_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        connection = self.get_test_connection()
        connection.execute(
            "UPDATE routes SET is_active = 0 WHERE id = 1"
        )
        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/restore",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["success"])

        connection = self.get_test_connection()
        matatu = connection.execute("""
            SELECT is_archived, archived_at
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()
        connection.close()

        self.assertEqual(matatu["is_archived"], 1)
        self.assertIsNotNone(matatu["archived_at"])

    def test_restoring_nonexistent_matatu_returns_404(self):
        csrf_token = self.login_as_admin()

        response = self.client.post(
            "/api/admin/matatus/999/restore",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_restore_request_is_rejected(self):
        response = self.client.post(
            "/api/admin/matatus/1/restore"
        )

        self.assertEqual(response.status_code, 401)

    def test_conductor_cannot_restore_matatu(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["csrf_token"] = "conductor-csrf-token"

        response = self.client.post(
            "/api/admin/matatus/1/restore",
            headers={"X-CSRF-Token": "conductor-csrf-token"}
        )

        self.assertEqual(response.status_code, 403)

    def test_restore_request_without_csrf_token_is_rejected(self):
        csrf_token = self.login_as_admin()
        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        matatu_id = create_response.get_json()["matatu"]["id"]

        archive_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/restore"
        )

        self.assertEqual(response.status_code, 403)

    def test_restore_failure_rolls_back_matatu_update(self):
        csrf_token = self.login_as_admin()
        create_response = self.create_matatu(
            "KXX 123X", 1, csrf_token
        )
        matatu_id = create_response.get_json()["matatu"]["id"]

        archive_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        connection = self.get_test_connection()
        archived_before = connection.execute("""
            SELECT is_archived, archived_at
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()
        self.assertTrue(archived_before["is_archived"])
        self.assertIsNotNone(archived_before["archived_at"])

        connection.executescript("""
            CREATE TRIGGER reject_matatu_restore
            BEFORE UPDATE OF is_archived ON matatus
            WHEN NEW.is_archived = 0
            BEGIN
                SELECT RAISE(ABORT, 'Simulated restore failure');
            END;
        """)
        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/restore",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 500)

        connection = self.get_test_connection()
        archived_after = connection.execute("""
            SELECT is_archived, archived_at
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()
        connection.close()

        self.assertTrue(archived_after["is_archived"])
        self.assertEqual(
            archived_after["archived_at"],
            archived_before["archived_at"]
        )


    def test_delete_requires_confirmation(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        matatu_id = created.get_json()["matatu"]["id"]

        response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 400)

    def test_delete_rejects_false_confirmation(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        matatu_id = created.get_json()["matatu"]["id"]

        response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            json={"confirm": False},
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 400)

    def test_delete_rejects_non_boolean_confirmation(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        matatu_id = created.get_json()["matatu"]["id"]

        response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            json={"confirm": 1},
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 400)

    def test_active_matatu_cannot_be_permanently_deleted(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        matatu_id = created.get_json()["matatu"]["id"]

        response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            json={"confirm": True},
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 409)

        connection = self.get_test_connection()
        matatu = connection.execute(
            "SELECT id, is_archived FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()
        connection.close()

        self.assertIsNotNone(matatu)
        self.assertEqual(matatu["is_archived"], 0)

    def test_deleting_nonexistent_matatu_returns_404(self):
        csrf_token = self.login_as_admin()

        response = self.client.delete(
            "/api/admin/matatus/99999",
            json={"confirm": True},
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 404)

    def test_invalid_delete_confirmation_preserves_matatu(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        matatu_id = created.get_json()["matatu"]["id"]

        response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            json={"confirm": "true"},
            headers={"X-CSRF-Token": csrf_token}
        )

        self.assertEqual(response.status_code, 400)

        connection = self.get_test_connection()
        matatu = connection.execute(
            "SELECT id, registration_number FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()
        connection.close()

        self.assertIsNotNone(matatu)
        self.assertEqual(matatu["registration_number"], "KXX 123X")


    def test_unauthenticated_delete_request_is_rejected(self):
        response = self.client.delete(
            "/api/admin/matatus/1",
            json={"confirm": True}
        )
        self.assertEqual(response.status_code, 401)

    def test_conductor_cannot_permanently_delete_matatu(self):
        with self.client.session_transaction() as session:
            session["user_id"] = 2
            session["full_name"] = "Test Conductor"
            session["email"] = "conductor@test.com"
            session["role"] = "conductor"
            session["csrf_token"] = "conductor-csrf-token"

        response = self.client.delete(
            "/api/admin/matatus/1",
            json={"confirm": True},
            headers={"X-CSRF-Token": "conductor-csrf-token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_delete_request_without_csrf_token_is_rejected(self):
        self.login_as_admin()
        response = self.client.delete(
            "/api/admin/matatus/1",
            json={"confirm": True}
        )
        self.assertEqual(response.status_code, 403)

    def test_permanent_delete_purges_data_and_preserves_anonymised_audits(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        self.assertEqual(created.status_code, 201)
        matatu_id = created.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        conductor_cursor = connection.execute("""
            INSERT INTO conductors (
                full_name, email, password_hash, is_active
            )
            VALUES (?, ?, ?, 1)
        """, (
            "Deletion Test Conductor",
            "delete-audit@test.com",
            generate_password_hash("TestConductor123!")
        ))
        conductor_id = conductor_cursor.lastrowid

        passenger_cursor = connection.execute("""
            INSERT INTO passengers (passenger_code)
            VALUES (?)
        """, ("DELETE-PASSENGER-001",))
        passenger_id = passenger_cursor.lastrowid

        journey_cursor = connection.execute("""
            INSERT INTO passenger_destinations (
                matatu_id, passenger_token, destination_stage_id,
                status, passenger_id, access_token_hash
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            matatu_id,
            "private-passenger-token",
            3,
            "waiting",
            passenger_id,
            "private-access-token-hash"
        ))
        journey_id = journey_cursor.lastrowid

        balance_cursor = connection.execute("""
            INSERT INTO passenger_balances (
                matatu_id, passenger_destination_id, amount,
                status, paid_at, confirmed_at, paid_by_conductor_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            matatu_id, journey_id, 250.0, "confirmed",
            "2026-11-08 07:00:00",
            "2026-11-08 07:05:00",
            conductor_id
        ))
        balance_id = balance_cursor.lastrowid

        alert_cursor = connection.execute("""
            INSERT INTO emergency_alerts (
                matatu_id, passenger_destination_id, alert_type,
                message, status, acknowledged_at,
                acknowledged_by_conductor_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            matatu_id, journey_id, "passenger_issue",
            "Private emergency message",
            "acknowledged",
            "2026-11-08 07:10:00",
            conductor_id
        ))
        alert_id = alert_cursor.lastrowid

        connection.execute("""
            INSERT INTO passenger_notifications (
                matatu_id, passenger_destination_id, balance_id,
                notification_type, message
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            matatu_id, journey_id, balance_id,
            "payment_confirmation",
            "Private passenger notification"
        ))

        connection.execute("""
            INSERT INTO destination_change_requests (
                matatu_id, passenger_destination_id,
                current_destination_stage_id,
                requested_destination_stage_id
            )
            VALUES (?, ?, ?, ?)
        """, (matatu_id, journey_id, 2, 3))

        assignment_cursor = connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id, matatu_id
            )
            VALUES (?, ?)
        """, (conductor_id, matatu_id))
        assignment_id = assignment_cursor.lastrowid

        assignment_timestamp = connection.execute("""
            SELECT assigned_at
            FROM matatu_assignments
            WHERE id = ?
        """, (assignment_id,)).fetchone()["assigned_at"]

        connection.execute("""
            INSERT INTO matatu_locations (
                matatu_id, latitude, longitude
            )
            VALUES (?, ?, ?)
        """, (matatu_id, -1.2864, 36.8172))

        connection.commit()
        connection.close()

        archive_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        delete_response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            json={"confirm": True},
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(delete_response.status_code, 200)

        connection = self.get_test_connection()

        self.assertIsNone(connection.execute("""
            SELECT id FROM matatus WHERE id = ?
        """, (matatu_id,)).fetchone())

        for table in (
            "matatu_assignments",
            "matatu_locations",
            "passenger_destinations",
            "destination_change_requests",
            "passenger_balances",
            "emergency_alerts",
            "passenger_notifications",
        ):
            count = connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE "
                + (
                    "passenger_destination_id = ?"
                    if table in (
                        "destination_change_requests",
                        "passenger_balances",
                        "emergency_alerts",
                        "passenger_notifications",
                    )
                    else "matatu_id = ?"
                ),
                (journey_id if table in (
                    "destination_change_requests",
                    "passenger_balances",
                    "emergency_alerts",
                    "passenger_notifications",
                ) else matatu_id,)
            ).fetchone()[0]
            self.assertEqual(count, 0, f"{table} should be purged")

        assignment_archive = connection.execute("""
            SELECT source_assignment_id, conductor_id, conductor_name,
                   registration_number, assigned_at, ended_at, archived_at
            FROM matatu_assignment_audit_archive
            WHERE source_assignment_id = ?
        """, (assignment_id,)).fetchone()

        self.assertIsNotNone(assignment_archive)
        self.assertEqual(assignment_archive["source_assignment_id"], assignment_id)
        self.assertEqual(assignment_archive["conductor_id"], conductor_id)
        self.assertEqual(assignment_archive["conductor_name"], "Deletion Test Conductor")
        self.assertEqual(assignment_archive["registration_number"], "KXX 123X")
        self.assertEqual(assignment_archive["assigned_at"], assignment_timestamp)
        self.assertIsNotNone(assignment_archive["ended_at"])
        self.assertIsNotNone(assignment_archive["archived_at"])

        self.assertIsNone(connection.execute("""
            SELECT id FROM passengers WHERE id = ?
        """, (passenger_id,)).fetchone())

        payment_archive = connection.execute("""
            SELECT registration_number, source_record_id, amount,
                   status, paid_at, confirmed_at,
                   conductor_attribution_present
            FROM matatu_payment_audit_archive
            WHERE source_record_id = ?
        """, (balance_id,)).fetchone()

        self.assertIsNotNone(payment_archive)
        self.assertEqual(payment_archive["registration_number"], "KXX 123X")
        self.assertEqual(payment_archive["amount"], 250.0)
        self.assertEqual(payment_archive["status"], "confirmed")
        self.assertEqual(payment_archive["conductor_attribution_present"], 1)

        emergency_archive = connection.execute("""
            SELECT registration_number, source_record_id, alert_type,
                   status, acknowledged_at,
                   conductor_attribution_present
            FROM matatu_emergency_audit_archive
            WHERE source_record_id = ?
        """, (alert_id,)).fetchone()

        self.assertIsNotNone(emergency_archive)
        self.assertEqual(emergency_archive["registration_number"], "KXX 123X")
        self.assertEqual(emergency_archive["alert_type"], "passenger_issue")
        self.assertEqual(emergency_archive["status"], "acknowledged")
        self.assertEqual(emergency_archive["conductor_attribution_present"], 1)

        payment_columns = {
            row["name"] for row in connection.execute(
                "PRAGMA table_info(matatu_payment_audit_archive)"
            ).fetchall()
        }
        emergency_columns = {
            row["name"] for row in connection.execute(
                "PRAGMA table_info(matatu_emergency_audit_archive)"
            ).fetchall()
        }

        for sensitive_column in (
            "passenger_id",
            "passenger_token",
            "access_token_hash",
            "paid_by_conductor_id",
            "acknowledged_by_conductor_id",
            "message",
        ):
            self.assertNotIn(sensitive_column, payment_columns)
            self.assertNotIn(sensitive_column, emergency_columns)

        registry_rows = connection.execute("""
            SELECT permanently_deleted_at
            FROM matatu_registration_registry
            WHERE original_matatu_id = ?
        """, (matatu_id,)).fetchall()

        self.assertTrue(registry_rows)
        self.assertTrue(all(
            row["permanently_deleted_at"] is not None
            for row in registry_rows
        ))

        history_count = connection.execute("""
            SELECT COUNT(*)
            FROM matatu_registration_history
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchone()[0]
        self.assertGreaterEqual(history_count, 1)

        connection.close()

    def test_permanent_delete_preserves_passenger_shared_with_another_matatu(self):
        csrf_token = self.login_as_admin()

        first = self.create_matatu("KXX 123X", 1, csrf_token)
        second = self.create_matatu("KYY 456Y", 3, csrf_token)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        first_id = first.get_json()["matatu"]["id"]
        second_id = second.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        passenger_cursor = connection.execute("""
            INSERT INTO passengers (passenger_code)
            VALUES (?)
        """, ("SHARED-PASSENGER-001",))
        passenger_id = passenger_cursor.lastrowid

        first_journey = connection.execute("""
            INSERT INTO passenger_destinations (
                matatu_id, passenger_token,
                destination_stage_id, passenger_id
            )
            VALUES (?, ?, ?, ?)
        """, (first_id, "first-private-token", 3, passenger_id))

        second_journey = connection.execute("""
            INSERT INTO passenger_destinations (
                matatu_id, passenger_token,
                destination_stage_id, passenger_id
            )
            VALUES (?, ?, ?, ?)
        """, (second_id, "second-private-token", 5, passenger_id))

        second_journey_id = second_journey.lastrowid

        connection.commit()
        connection.close()

        archive_response = self.client.post(
            f"/api/admin/matatus/{first_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        delete_response = self.client.delete(
            f"/api/admin/matatus/{first_id}",
            json={"confirm": True},
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(delete_response.status_code, 200)

        connection = self.get_test_connection()

        passenger = connection.execute("""
            SELECT id, passenger_code
            FROM passengers
            WHERE id = ?
        """, (passenger_id,)).fetchone()

        remaining_journey = connection.execute("""
            SELECT id, matatu_id, passenger_id
            FROM passenger_destinations
            WHERE id = ?
        """, (second_journey_id,)).fetchone()

        self.assertIsNotNone(passenger)
        self.assertEqual(passenger["passenger_code"], "SHARED-PASSENGER-001")
        self.assertIsNotNone(remaining_journey)
        self.assertEqual(remaining_journey["matatu_id"], second_id)
        self.assertEqual(remaining_journey["passenger_id"], passenger_id)

        self.assertIsNone(connection.execute("""
            SELECT id FROM matatus WHERE id = ?
        """, (first_id,)).fetchone())

        self.assertIsNotNone(connection.execute("""
            SELECT id FROM matatus WHERE id = ?
        """, (second_id,)).fetchone())

        connection.close()

    def test_permanent_delete_failure_rolls_back_all_changes(self):
        csrf_token = self.login_as_admin()
        created = self.create_matatu("KXX 123X", 1, csrf_token)
        self.assertEqual(created.status_code, 201)
        matatu_id = created.get_json()["matatu"]["id"]

        connection = self.get_test_connection()

        conductor_cursor = connection.execute("""
            INSERT INTO conductors (
                full_name, email, password_hash, is_active
            )
            VALUES (?, ?, ?, 1)
        """, (
            "Permanent Delete Rollback Conductor",
            "permanent-delete-rollback@test.com",
            generate_password_hash("TestConductor123!")
        ))
        conductor_id = conductor_cursor.lastrowid

        assignment_cursor = connection.execute("""
            INSERT INTO matatu_assignments (
                conductor_id, matatu_id
            )
            VALUES (?, ?)
        """, (conductor_id, matatu_id))
        assignment_id = assignment_cursor.lastrowid

        passenger_cursor = connection.execute("""
            INSERT INTO passengers (passenger_code)
            VALUES (?)
        """, ("ROLLBACK-PASSENGER-001",))
        passenger_id = passenger_cursor.lastrowid

        journey_cursor = connection.execute("""
            INSERT INTO passenger_destinations (
                matatu_id, passenger_token,
                destination_stage_id, passenger_id
            )
            VALUES (?, ?, ?, ?)
        """, (matatu_id, "rollback-private-token", 3, passenger_id))
        journey_id = journey_cursor.lastrowid

        balance_cursor = connection.execute("""
            INSERT INTO passenger_balances (
                matatu_id, passenger_destination_id, amount,
                status, paid_by_conductor_id
            )
            VALUES (?, ?, ?, ?, ?)
        """, (matatu_id, journey_id, 100.0, "confirmed", None))
        balance_id = balance_cursor.lastrowid

        connection.execute(f"""
            CREATE TRIGGER reject_permanent_matatu_delete
            BEFORE DELETE ON matatus
            WHEN OLD.id = {matatu_id}
            BEGIN
                SELECT RAISE(ABORT, 'Simulated permanent deletion failure');
            END;
        """)

        connection.commit()
        connection.close()

        archive_response = self.client.post(
            f"/api/admin/matatus/{matatu_id}/archive",
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(archive_response.status_code, 200)

        connection = self.get_test_connection()
        history_before = connection.execute("""
            SELECT id, registration_number, effective_start, effective_end
            FROM matatu_registration_history
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchall()
        connection.close()

        delete_response = self.client.delete(
            f"/api/admin/matatus/{matatu_id}",
            json={"confirm": True},
            headers={"X-CSRF-Token": csrf_token}
        )
        self.assertEqual(delete_response.status_code, 500)

        connection = self.get_test_connection()

        matatu = connection.execute("""
            SELECT id, is_archived, registration_number
            FROM matatus
            WHERE id = ?
        """, (matatu_id,)).fetchone()
        self.assertIsNotNone(matatu)
        self.assertEqual(matatu["is_archived"], 1)
        self.assertEqual(matatu["registration_number"], "KXX 123X")

        retained_assignment = connection.execute("""
            SELECT id, conductor_id, matatu_id, ended_at
            FROM matatu_assignments
            WHERE id = ?
        """, (assignment_id,)).fetchone()

        self.assertIsNotNone(retained_assignment)
        self.assertEqual(retained_assignment["conductor_id"], conductor_id)
        self.assertEqual(retained_assignment["matatu_id"], matatu_id)
        self.assertIsNotNone(retained_assignment["ended_at"])

        assignment_archive_count = connection.execute("""
            SELECT COUNT(*)
            FROM matatu_assignment_audit_archive
            WHERE source_assignment_id = ?
        """, (assignment_id,)).fetchone()[0]

        self.assertEqual(assignment_archive_count, 0)

        self.assertIsNotNone(connection.execute("""
            SELECT id FROM passengers WHERE id = ?
        """, (passenger_id,)).fetchone())

        self.assertIsNotNone(connection.execute("""
            SELECT id FROM passenger_destinations WHERE id = ?
        """, (journey_id,)).fetchone())

        self.assertIsNotNone(connection.execute("""
            SELECT id FROM passenger_balances WHERE id = ?
        """, (balance_id,)).fetchone())

        payment_archive_count = connection.execute("""
            SELECT COUNT(*)
            FROM matatu_payment_audit_archive
            WHERE source_record_id = ?
        """, (balance_id,)).fetchone()[0]
        self.assertEqual(payment_archive_count, 0)

        registry_rows = connection.execute("""
            SELECT permanently_deleted_at
            FROM matatu_registration_registry
            WHERE original_matatu_id = ?
        """, (matatu_id,)).fetchall()

        self.assertTrue(registry_rows)
        self.assertTrue(all(
            row["permanently_deleted_at"] is None
            for row in registry_rows
        ))

        history_after = connection.execute("""
            SELECT id, registration_number, effective_start, effective_end
            FROM matatu_registration_history
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchall()

        self.assertEqual(
            [tuple(row) for row in history_after],
            [tuple(row) for row in history_before]
        )

        connection.close()

if __name__ == "__main__":
    unittest.main()
