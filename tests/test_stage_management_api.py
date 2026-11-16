import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app as smart_matatu_app
from migrate_stage_management import migrate


class TestStageManagementAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(
            self.temp_dir.name,
            "test_stage_management.db"
        )

        self._create_test_database()
        migrate(self.database_path)

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
            CREATE TABLE admins (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            INSERT INTO admins (
                id, full_name, email, password_hash, is_active
            )
            VALUES (
                1, 'Test Admin', 'admin@test.com', 'test-hash', 1
            );

            CREATE TABLE routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
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

            CREATE UNIQUE INDEX unique_stage_sequence_per_route
            ON stages(route_id, sequence_number);

            CREATE TABLE passenger_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_token TEXT NOT NULL,
                destination_stage_id INTEGER NOT NULL,
                status TEXT DEFAULT 'waiting',
                passenger_id INTEGER,
                access_token_hash TEXT
            );

            CREATE TABLE destination_change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                current_destination_stage_id INTEGER NOT NULL
                    REFERENCES stages(id),
                requested_destination_stage_id INTEGER NOT NULL
                    REFERENCES stages(id),
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT
            );

            INSERT INTO routes (id, name, description)
            VALUES
                (1, 'Nairobi - Thika', 'Test route one'),
                (2, 'Nakuru - Nairobi', 'Test route two');

            INSERT INTO stages (
                id, route_name, name, latitude,
                longitude, sequence_number, route_id
            )
            VALUES
                (1, 'Nairobi - Thika', 'Pangani',
                 -1.2700, 36.8300, 1, 1),
                (2, 'Nairobi - Thika', 'Muthaiga',
                 -1.2500, 36.8300, 2, 1);

            INSERT INTO passenger_destinations (
                id, matatu_id, passenger_token,
                destination_stage_id
            )
            VALUES
                (1, 1, 'TEST-PASSENGER-1', 1),
                (2, 1, 'TEST-PASSENGER-2', 2);

            INSERT INTO destination_change_requests (
                id, matatu_id, passenger_destination_id,
                current_destination_stage_id,
                requested_destination_stage_id
            )
            VALUES
                (1, 1, 1, 1, 2);
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


    def test_get_route_stages_returns_active_and_archived_stages(self):
        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1, archived_at = '2026-11-05 10:00:00'
            WHERE id = 2
        """)
        connection.commit()
        connection.close()

        self.login_as_admin()

        response = self.client.get("/api/admin/routes/1/stages")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertTrue(data["success"])
        self.assertEqual(data["route"]["id"], 1)
        self.assertEqual(
            [stage["id"] for stage in data["stages"]],
            [1, 2]
        )
        self.assertFalse(data["stages"][0]["is_archived"])
        self.assertTrue(data["stages"][1]["is_archived"])
        self.assertEqual(
            data["stages"][1]["archived_at"],
            "2026-11-05 10:00:00"
        )

    def test_get_route_stages_returns_404_for_missing_route(self):
        self.login_as_admin()

        response = self.client.get("/api/admin/routes/999/stages")

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_get_route_stages_requires_admin(self):
        response = self.client.get("/api/admin/routes/1/stages")

        self.assertIn(response.status_code, (401, 403, 302))


    def create_stage(self, payload, route_id=1, csrf_token=None):
        headers = {}
        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.post(
            f"/api/admin/routes/{route_id}/stages",
            json=payload,
            headers=headers
        )

    def test_create_stage_at_middle_position(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "Rosters",
            "latitude": -1.2000,
            "longitude": 36.9000,
            "position": 2
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertTrue(data["success"])

        connection = self.get_test_connection()
        stages = connection.execute("""
            SELECT id, name, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()
        connection.close()

        self.assertEqual(
            [(row["name"], row["sequence_number"]) for row in stages],
            [("Pangani", 1), ("Rosters", 2), ("Muthaiga", 3)]
        )

        self.assertEqual(
            [row["id"] for row in stages if row["name"] != "Rosters"],
            [1, 2]
        )

    def test_create_stage_rejects_invalid_position(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "Invalid Stage",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 4
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_create_stage_rejects_invalid_coordinates(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "Invalid Stage",
            "latitude": 95,
            "longitude": 36.9,
            "position": 2
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_create_stage_rejects_missing_route(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "New Stage",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 1
        }, route_id=999, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_create_stage_requires_csrf_token(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "New Stage",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 1
        })

        self.assertEqual(response.status_code, 403)



    def test_create_stage_at_beginning(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "New Beginning",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 1
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 201)

        connection = self.get_test_connection()
        stages = connection.execute("""
            SELECT id, name, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()
        connection.close()

        self.assertEqual(
            [(row["name"], row["sequence_number"]) for row in stages],
            [
                ("New Beginning", 1),
                ("Pangani", 2),
                ("Muthaiga", 3)
            ]
        )
        self.assertEqual(
            [row["id"] for row in stages if row["name"] != "New Beginning"],
            [1, 2]
        )

    def test_create_stage_at_end(self):
        self.login_as_admin()

        response = self.create_stage({
            "name": "Final Stage",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 3
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 201)

        connection = self.get_test_connection()
        stages = connection.execute("""
            SELECT name, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()
        connection.close()

        self.assertEqual(
            [(row["name"], row["sequence_number"]) for row in stages],
            [
                ("Pangani", 1),
                ("Muthaiga", 2),
                ("Final Stage", 3)
            ]
        )

    def test_create_stage_ignores_archived_stage_positions(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05T10:00:00'
            WHERE id = 2
        """)
        connection.commit()
        connection.close()

        response = self.create_stage({
            "name": "New Active Stage",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 2
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 201)

        connection = self.get_test_connection()

        active_stages = connection.execute("""
            SELECT name, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()

        archived_stage = connection.execute("""
            SELECT id, is_archived
            FROM stages
            WHERE id = 2
        """).fetchone()

        connection.close()

        self.assertEqual(
            [(row["name"], row["sequence_number"]) for row in active_stages],
            [
                ("Pangani", 1),
                ("New Active Stage", 2)
            ]
        )
        self.assertEqual(archived_stage["id"], 2)
        self.assertEqual(archived_stage["is_archived"], 1)

    def test_create_stage_rolls_back_on_insert_failure(self):
        self.login_as_admin()

        connection = self.get_test_connection()

        original_stages = [
            tuple(row)
            for row in connection.execute("""
                SELECT id, name, sequence_number
                FROM stages
                WHERE route_id = 1 AND is_archived = 0
                ORDER BY sequence_number
            """).fetchall()
        ]

        connection.execute("""
            CREATE TRIGGER force_stage_insert_failure
            BEFORE INSERT ON stages
            WHEN NEW.name = 'Force Failure'
            BEGIN
                SELECT RAISE(ABORT, 'Simulated insertion failure');
            END;
        """)

        connection.commit()
        connection.close()

        response = self.create_stage({
            "name": "Force Failure",
            "latitude": -1.2,
            "longitude": 36.9,
            "position": 2
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 409)

        connection = self.get_test_connection()

        final_stages = [
            tuple(row)
            for row in connection.execute("""
                SELECT id, name, sequence_number
                FROM stages
                WHERE route_id = 1 AND is_archived = 0
                ORDER BY sequence_number
            """).fetchall()
        ]

        connection.close()

        self.assertEqual(final_stages, original_stages)



    def update_stage(self, stage_id, payload, csrf_token=None):
        headers = {}
        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.put(
            f"/api/admin/stages/{stage_id}",
            json=payload,
            headers=headers
        )

    def test_update_stage_details_preserves_identity_and_order(self):
        self.login_as_admin()

        response = self.update_stage(1, {
            "name": "Updated Pangani",
            "latitude": -1.2500,
            "longitude": 36.8500
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

        connection = self.get_test_connection()
        stage = connection.execute("""
            SELECT id, route_id, name, latitude, longitude,
                   sequence_number, is_archived
            FROM stages
            WHERE id = 1
        """).fetchone()
        connection.close()

        self.assertEqual(stage["id"], 1)
        self.assertEqual(stage["route_id"], 1)
        self.assertEqual(stage["name"], "Updated Pangani")
        self.assertAlmostEqual(stage["latitude"], -1.2500)
        self.assertAlmostEqual(stage["longitude"], 36.8500)
        self.assertEqual(stage["sequence_number"], 1)
        self.assertEqual(stage["is_archived"], 0)

    def test_update_archived_stage_details(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05T10:00:00'
            WHERE id = 2
        """)
        connection.commit()
        connection.close()

        response = self.update_stage(2, {
            "name": "Updated Archived Stage",
            "latitude": -1.3000,
            "longitude": 36.9000
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 200)

        connection = self.get_test_connection()
        stage = connection.execute("""
            SELECT id, name, latitude, longitude,
                   sequence_number, is_archived, archived_at
            FROM stages
            WHERE id = 2
        """).fetchone()
        connection.close()

        self.assertEqual(stage["id"], 2)
        self.assertEqual(stage["name"], "Updated Archived Stage")
        self.assertEqual(stage["is_archived"], 1)
        self.assertIsNotNone(stage["archived_at"])

    def test_update_stage_rejects_invalid_coordinates(self):
        self.login_as_admin()

        response = self.update_stage(1, {
            "name": "Invalid Coordinates",
            "latitude": 95,
            "longitude": 36.9
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()["success"])

    def test_update_stage_returns_404_for_missing_stage(self):
        self.login_as_admin()

        response = self.update_stage(999, {
            "name": "Missing Stage",
            "latitude": -1.2,
            "longitude": 36.9
        }, csrf_token=self.csrf_token)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_update_stage_requires_csrf_token(self):
        self.login_as_admin()

        response = self.update_stage(1, {
            "name": "Updated Pangani",
            "latitude": -1.2,
            "longitude": 36.9
        })

        self.assertEqual(response.status_code, 403)


    def archive_stage(self, stage_id, csrf_token=None):
        headers = {}
        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.post(
            f"/api/admin/stages/{stage_id}/archive",
            headers=headers
        )

    def test_archive_stage_preserves_record_and_renumbers_active_stages(self):
        self.login_as_admin()

        response = self.archive_stage(1, self.csrf_token)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

        connection = self.get_test_connection()

        archived_stage = connection.execute("""
            SELECT id, is_archived, archived_at, sequence_number
            FROM stages
            WHERE id = 1
        """).fetchone()

        active_stages = connection.execute("""
            SELECT id, name, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()

        connection.close()

        self.assertEqual(archived_stage["id"], 1)
        self.assertEqual(archived_stage["is_archived"], 1)
        self.assertIsNotNone(archived_stage["archived_at"])

        self.assertEqual(
            [(row["name"], row["sequence_number"]) for row in active_stages],
            [("Muthaiga", 1)]
        )

    def test_archive_stage_preserves_historical_references(self):
        self.login_as_admin()

        connection = self.get_test_connection()

        references_before = connection.execute("""
            SELECT COUNT(*)
            FROM passenger_destinations
            WHERE destination_stage_id = 1
        """).fetchone()[0]

        connection.close()

        response = self.archive_stage(1, self.csrf_token)

        self.assertEqual(response.status_code, 200)

        connection = self.get_test_connection()

        references_after = connection.execute("""
            SELECT COUNT(*)
            FROM passenger_destinations
            WHERE destination_stage_id = 1
        """).fetchone()[0]

        connection.close()

        self.assertEqual(references_after, references_before)

    def test_archive_stage_rejects_already_archived_stage(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05T10:00:00'
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.archive_stage(1, self.csrf_token)

        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["success"])

    def test_archive_stage_returns_404_for_missing_stage(self):
        self.login_as_admin()

        response = self.archive_stage(999, self.csrf_token)

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_archive_stage_requires_csrf_token(self):
        self.login_as_admin()

        response = self.archive_stage(1)

        self.assertEqual(response.status_code, 403)

    def test_archive_stage_requires_admin(self):
        response = self.archive_stage(1)

        self.assertIn(response.status_code, (401, 403, 302))



    def restore_stage(self, stage_id, payload, csrf_token=None):
        headers = {}
        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.post(
            f"/api/admin/stages/{stage_id}/restore",
            json=payload,
            headers=headers
        )

    def test_restore_stage_at_beginning(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05 10:00:00'
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.restore_stage(1, {"position": 1}, self.csrf_token)

        self.assertEqual(response.status_code, 200)

        connection = self.get_test_connection()
        stages = connection.execute("""
            SELECT id, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()
        connection.close()

        self.assertEqual(
            [(row["id"], row["sequence_number"]) for row in stages],
            [(1, 1), (2, 2)]
        )

    def test_restore_stage_at_end(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05 10:00:00'
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.restore_stage(1, {"position": 2}, self.csrf_token)

        self.assertEqual(response.status_code, 200)

        connection = self.get_test_connection()
        stages = connection.execute("""
            SELECT id, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()
        connection.close()

        self.assertEqual(
            [(row["id"], row["sequence_number"]) for row in stages],
            [(2, 1), (1, 2)]
        )

    def test_restore_stage_rejects_invalid_position(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05 10:00:00'
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.restore_stage(
            1, {"position": 3}, self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_restore_stage_rejects_non_integer_position(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05 10:00:00'
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.restore_stage(
            1, {"position": 1.5}, self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_restore_stage_rejects_already_active_stage(self):
        self.login_as_admin()

        response = self.restore_stage(
            1, {"position": 1}, self.csrf_token
        )

        self.assertEqual(response.status_code, 409)

    def test_restore_stage_returns_404_for_missing_stage(self):
        self.login_as_admin()

        response = self.restore_stage(
            999, {"position": 1}, self.csrf_token
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])

    def test_restore_stage_requires_csrf_token(self):
        self.login_as_admin()

        response = self.restore_stage(1, {"position": 1})

        self.assertEqual(response.status_code, 403)

    def test_restore_stage_requires_admin(self):
        response = self.restore_stage(1, {"position": 1})

        self.assertIn(response.status_code, (401, 403, 302))


    def delete_stage(self, stage_id, payload=None, csrf_token=None):
        headers = {}

        if csrf_token:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.delete(
            f"/api/admin/stages/{stage_id}",
            json=payload,
            headers=headers
        )

    def test_delete_archived_stage_without_references(self):
        self.login_as_admin()

        # Create a stage specifically for this deletion test.
        connection = self.get_test_connection()
        cursor = connection.execute("""
            INSERT INTO stages (
                route_name,
                name,
                latitude,
                longitude,
                sequence_number,
                route_id,
                is_archived,
                archived_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            "Nairobi - Thika",
            "Test Deletion Stage",
            -1.2400,
            36.8300,
            3,
            1
        ))

        stage_id = cursor.lastrowid
        connection.commit()
        connection.close()

        self.archive_stage(stage_id, csrf_token=self.csrf_token)

        response = self.delete_stage(
            stage_id,
            {"confirm": True},
            csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

        connection = self.get_test_connection()
        stage = connection.execute(
            "SELECT id FROM stages WHERE id = ?",
            (stage_id,)
        ).fetchone()
        connection.close()

        self.assertIsNone(stage)

    def test_delete_active_stage_is_rejected(self):
        self.login_as_admin()

        response = self.delete_stage(
            2, {"confirm": True}, csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 409)


    def test_delete_stage_with_passenger_destination_reference(self):
        self.login_as_admin()
        self.archive_stage(2, csrf_token=self.csrf_token)

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE passenger_destinations
            SET destination_stage_id = 2
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.delete_stage(
            2, {"confirm": True}, csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 409)


    def test_delete_stage_with_current_destination_reference(self):
        self.login_as_admin()
        self.archive_stage(2, csrf_token=self.csrf_token)

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE destination_change_requests
            SET current_destination_stage_id = 2
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.delete_stage(
            2, {"confirm": True}, csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 409)


    def test_delete_stage_with_requested_destination_reference(self):
        self.login_as_admin()
        self.archive_stage(2, csrf_token=self.csrf_token)

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE destination_change_requests
            SET requested_destination_stage_id = 2
            WHERE id = 1
        """)
        connection.commit()
        connection.close()

        response = self.delete_stage(
            2, {"confirm": True}, csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 409)


    def test_delete_stage_requires_explicit_confirmation(self):
        self.login_as_admin()

        response = self.delete_stage(
            2, {"confirm": False}, csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 400)


    def test_delete_stage_returns_404_for_missing_stage(self):
        self.login_as_admin()

        response = self.delete_stage(
            999, {"confirm": True}, csrf_token=self.csrf_token
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(response.get_json()["success"])


    def test_delete_stage_requires_admin(self):
        self.login_as_conductor()

        response = self.delete_stage(
            2, {"confirm": True}, csrf_token=self.csrf_token
        )

        self.assertIn(response.status_code, (401, 403))


    def test_delete_stage_requires_csrf_token(self):
        self.login_as_admin()

        response = self.delete_stage(
            2, {"confirm": True}
        )

        self.assertEqual(response.status_code, 403)




    def reorder_stages(self, route_id, stage_ids, csrf_token=None):
        headers = {}
        if csrf_token is not None:
            headers["X-CSRF-Token"] = csrf_token

        return self.client.put(
            f"/api/admin/routes/{route_id}/stages/reorder",
            json={"stage_ids": stage_ids},
            headers=headers
        )

    def test_reorder_stages_successfully(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        cursor = connection.execute("""
            INSERT INTO stages (
                route_name, name, latitude, longitude,
                sequence_number, route_id, is_archived, archived_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            "Nairobi - Thika", "Rosters",
            -1.2, 36.9, 3, 1
        ))
        new_stage_id = cursor.lastrowid
        connection.commit()
        connection.close()

        response = self.reorder_stages(
            1, [new_stage_id, 1, 2], self.csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])

        connection = self.get_test_connection()
        stages = connection.execute("""
            SELECT id, sequence_number
            FROM stages
            WHERE route_id = 1 AND is_archived = 0
            ORDER BY sequence_number
        """).fetchall()
        connection.close()

        self.assertEqual(
            [(row["id"], row["sequence_number"]) for row in stages],
            [(new_stage_id, 1), (1, 2), (2, 3)]
        )

    def test_reorder_stages_rejects_missing_stage_id(self):
        self.login_as_admin()

        response = self.reorder_stages(
            1, [1], self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_reorder_stages_rejects_duplicate_ids(self):
        self.login_as_admin()

        response = self.reorder_stages(
            1, [1, 1, 2], self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_reorder_stages_rejects_unknown_stage_id(self):
        self.login_as_admin()

        response = self.reorder_stages(
            1, [1, 2, 999], self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_reorder_stages_rejects_stage_from_another_route(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        cursor = connection.execute("""
            INSERT INTO stages (
                route_name, name, latitude, longitude,
                sequence_number, route_id, is_archived, archived_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            "Nakuru - Nairobi", "Bahati",
            -1.2, 36.4, 1, 2
        ))
        other_route_stage_id = cursor.lastrowid
        connection.commit()
        connection.close()

        response = self.reorder_stages(
            1, [1, 2, other_route_stage_id], self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_reorder_stages_rejects_archived_stage_id(self):
        self.login_as_admin()

        connection = self.get_test_connection()
        connection.execute("""
            UPDATE stages
            SET is_archived = 1,
                archived_at = '2026-11-05 10:00:00'
            WHERE id = 2
        """)
        connection.commit()
        connection.close()

        response = self.reorder_stages(
            1, [1, 2], self.csrf_token
        )

        self.assertEqual(response.status_code, 400)

    def test_reorder_stages_rejects_missing_route(self):
        self.login_as_admin()

        response = self.reorder_stages(
            999, [1, 2], self.csrf_token
        )

        self.assertEqual(response.status_code, 404)

    def test_reorder_stages_requires_csrf_token(self):
        self.login_as_admin()

        response = self.reorder_stages(1, [2, 1])

        self.assertEqual(response.status_code, 403)

    def test_reorder_stages_requires_admin(self):
        self.login_as_conductor()

        response = self.reorder_stages(
            1, [2, 1], self.csrf_token
        )

        self.assertIn(response.status_code, (401, 403))

if __name__ == "__main__":
    unittest.main()
