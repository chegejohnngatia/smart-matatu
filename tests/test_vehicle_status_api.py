import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import app as smart_matatu_app


class TestVehicleStatusAPI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(
            self.temp_dir.name,
            "test_vehicle_status.db"
        )
        self._create_test_database()

        self.database_patch = patch.object(
            smart_matatu_app,
            "get_db_connection",
            self.get_test_connection
        )
        self.database_patch.start()
        self.client = smart_matatu_app.app.test_client()

    def tearDown(self):
        self.database_patch.stop()
        self.temp_dir.cleanup()

    def get_test_connection(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _create_test_database(self):
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
            CREATE TABLE matatus (
                id INTEGER PRIMARY KEY,
                registration_number TEXT NOT NULL,
                route_name TEXT NOT NULL
            );

            CREATE TABLE matatu_locations (
                matatu_id INTEGER PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                current_stage_sequence INTEGER DEFAULT 0,
                speed REAL DEFAULT 20,
                accuracy REAL,
                last_updated_at TEXT,
                location_source TEXT DEFAULT 'simulation'
            );

            CREATE TABLE stages (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                route_name TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                latitude REAL,
                longitude REAL
            );

            CREATE TABLE passenger_destinations (
                id INTEGER PRIMARY KEY,
                matatu_id INTEGER NOT NULL,
                destination_stage_id INTEGER NOT NULL
            );

            INSERT INTO matatus (id, registration_number, route_name)
            VALUES (1, 'KDA 001X', 'Test Route');

            INSERT INTO matatu_locations (
                matatu_id, latitude, longitude, current_stage_sequence,
                speed, accuracy, last_updated_at, location_source
            )
            VALUES (1, -1.2864, 36.8172, 1, 20, 12, NULL, 'gps');

            INSERT INTO matatus (id, registration_number, route_name)
            VALUES (2, 'KDA 002Y', 'Test Route');

            INSERT INTO matatu_locations (
                matatu_id, latitude, longitude, current_stage_sequence,
                speed, accuracy, last_updated_at, location_source
            )
            VALUES (2, -1.2864, 36.8172, 0, 0, 10, NULL, 'simulation');

            INSERT INTO matatus (id, registration_number, route_name)
            VALUES (3, 'KDA 003Z', 'Test Route');

            INSERT INTO stages (id, name, route_name, sequence_number, latitude, longitude)
            VALUES
                (1, 'Stage A', 'Test Route', 1, -1.2800, 36.8100),
                (2, 'Stage B', 'Test Route', 2, -1.2900, 36.8200);

            INSERT INTO passenger_destinations (id, matatu_id, destination_stage_id)
            VALUES (1, 1, 2);
        """)
        connection.execute(
            "UPDATE matatu_locations SET last_updated_at = ?", (now,)
        )
        connection.commit()
        connection.close()

    def test_api_alias_returns_location_payload(self):
        response = self.client.get("/api/vehicle-status/1")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["matatu"], "KDA 001X")

        location = data["location"]
        self.assertIsNotNone(location)
        self.assertEqual(location["latitude"], -1.2864)
        self.assertEqual(location["longitude"], 36.8172)
        self.assertEqual(location["speed"], 20)
        self.assertEqual(location["accuracy"], 12)
        self.assertEqual(location["source"], "gps")
        self.assertIn("last_updated_at", location)
        self.assertIsInstance(location["age_seconds"], (int, float))
        self.assertFalse(location["stale"])

        self.assertEqual(len(data["passengers"]), 1)
        self.assertEqual(data["passengers"][0]["destination"], "Stage B")

    def test_legacy_route_includes_location(self):
        response = self.client.get("/vehicle-status/1")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["matatu"], "KDA 001X")
        self.assertIn("location", data)
        self.assertIn("passengers", data)

    def test_unknown_matatu_returns_json_404_for_api(self):
        response = self.client.get("/api/vehicle-status/99")

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"]["message"], "Matatu not found")

    def test_no_passengers_returns_empty_list_for_api(self):
        response = self.client.get("/api/vehicle-status/2")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["matatu"], "KDA 002Y")
        self.assertEqual(data["location"]["latitude"], -1.2864)
        self.assertEqual(data["passengers"], [])

    def test_no_passengers_keeps_legacy_string_for_template_path(self):
        response = self.client.get("/vehicle-status/2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_data(as_text=True),
            "No passenger destinations registered."
        )

    def test_missing_location_returns_json_404_for_api(self):
        response = self.client.get("/api/vehicle-status/3")

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertEqual(data["error"]["message"], "Matatu location not initialized.")


if __name__ == "__main__":
    unittest.main()
