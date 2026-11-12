
import os
import sqlite3
import tempfile
import unittest

import migrate_routes


class RouteMigrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.temp_dir.name,
            "test_routes.db",
        )
        self.create_test_database()

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def run_migration(self):
        migrate_routes.migrate(self.db_path)

    def create_test_database(self):
        connection = self.connect()

        try:
            connection.executescript("""
                CREATE TABLE stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    sequence_number INTEGER NOT NULL
                );

                CREATE TABLE matatus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_number TEXT NOT NULL,
                    route_name TEXT NOT NULL
                );

                CREATE TABLE passenger_destinations (
                    id INTEGER PRIMARY KEY,
                    destination_stage_id INTEGER,
                    FOREIGN KEY (destination_stage_id)
                        REFERENCES stages(id)
                );

                CREATE TABLE destination_change_requests (
                    id INTEGER PRIMARY KEY,
                    current_destination_stage_id INTEGER NOT NULL,
                    requested_destination_stage_id INTEGER NOT NULL,
                    FOREIGN KEY (current_destination_stage_id)
                        REFERENCES stages(id),
                    FOREIGN KEY (requested_destination_stage_id)
                        REFERENCES stages(id)
                );
            """)

            stages = [
                (1, "Nairobi - Thika", "Pangani", 1),
                (2, "Nairobi- Thika", "Muthaiga", 2),
                (3, "Nairobi- Thika", "Rosters", 3),
                (4, "Nairobi- Thika", "Roysambu", 4),
                (5, "Nairobi- Thika", "Githurai", 5),
                (6, "Nairobi- Thika", "Ruiru", 6),
                (7, "Nairobi- Thika", "Juja", 7),
                (8, "Nairobi- Thika", "Thika", 8),
                (9, "Nairobi- Thika", "GPS test", 9),
                (10, "Nairobi - Nakuru", "Bahati", 1),
            ]

            connection.executemany("""
                INSERT INTO stages (
                    id, route_name, name, sequence_number
                )
                VALUES (?, ?, ?, ?)
            """, stages)

            connection.executemany("""
                INSERT INTO matatus (
                    id, registration_number, route_name
                )
                VALUES (?, ?, ?)
            """, [
                (1, "KCA 123A", "Nairobi- Thika"),
                (2, "KDB", "NAKURU -NAIROBI"),
            ])

            connection.executemany("""
                INSERT INTO passenger_destinations
                    (id, destination_stage_id)
                VALUES (?, ?)
            """, [
                (1, 1),
                (2, 4),
            ])

            connection.execute("""
                INSERT INTO destination_change_requests
                VALUES (1, 5, 6)
            """)

            connection.commit()

        finally:
            connection.close()

    def test_successful_migration_preserves_records(self):
        self.run_migration()

        connection = self.connect()

        try:
            routes = {
                row["name"]: row["id"]
                for row in connection.execute(
                    "SELECT id, name FROM routes"
                )
            }

            self.assertEqual(
                set(routes),
                {"Nairobi - Thika", "Nakuru - Nairobi"},
            )

            thika_id = routes["Nairobi - Thika"]
            nakuru_id = routes["Nakuru - Nairobi"]

            for stage_id in range(1, 9):
                row = connection.execute("""
                    SELECT route_id, sequence_number
                    FROM stages
                    WHERE id = ?
                """, (stage_id,)).fetchone()

                self.assertEqual(row["route_id"], thika_id)
                self.assertEqual(row["sequence_number"], stage_id)

            bahati = connection.execute("""
                SELECT route_id, sequence_number, route_name
                FROM stages
                WHERE id = 10
            """).fetchone()

            self.assertEqual(bahati["route_id"], nakuru_id)
            self.assertEqual(bahati["sequence_number"], 1)
            self.assertEqual(bahati["route_name"], "Nakuru - Nairobi")

            gps = connection.execute("""
                SELECT route_id, name
                FROM stages
                WHERE id = 9
            """).fetchone()

            self.assertIsNone(gps["route_id"])
            self.assertEqual(gps["name"], "GPS test")

            matatus = connection.execute("""
                SELECT id, route_id
                FROM matatus
                ORDER BY id
            """).fetchall()

            self.assertEqual(matatus[0]["route_id"], thika_id)
            self.assertEqual(matatus[1]["route_id"], nakuru_id)

            stage_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM stages ORDER BY id"
                )
            ]

            self.assertEqual(stage_ids, list(range(1, 11)))

            destinations = connection.execute("""
                SELECT id, destination_stage_id
                FROM passenger_destinations
                ORDER BY id
            """).fetchall()

            self.assertEqual(
                [(row[0], row[1]) for row in destinations],
                [(1, 1), (2, 4)],
            )

            request = connection.execute("""
                SELECT current_destination_stage_id,
                       requested_destination_stage_id
                FROM destination_change_requests
                WHERE id = 1
            """).fetchone()

            self.assertEqual(tuple(request), (5, 6))

            self.assertEqual(
                connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall(),
                [],
            )

            self.assertEqual(
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok",
            )

        finally:
            connection.close()

    def test_migration_can_run_twice(self):
        self.run_migration()
        self.run_migration()

        connection = self.connect()

        try:
            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM routes"
                ).fetchone()[0],
                2,
            )

            self.assertEqual(
                connection.execute("""
                    SELECT COUNT(*)
                    FROM stages
                    WHERE route_id IS NOT NULL
                """).fetchone()[0],
                9,
            )

        finally:
            connection.close()

    def test_additional_unrecognised_stage_is_preserved(self):
        connection = self.connect()

        try:
            connection.execute("""
                INSERT INTO stages (
                    id, route_name, name, sequence_number
                )
                VALUES (11, 'Unexpected Route', 'Unexpected Stage', 1)
            """)
            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            stage = connection.execute("""
                SELECT id, route_name, name, sequence_number, route_id
                FROM stages
                WHERE id = 11
            """).fetchone()

            self.assertIsNotNone(stage)
            self.assertEqual(stage["name"], "Unexpected Stage")
            self.assertEqual(stage["route_name"], "Unexpected Route")
            self.assertEqual(stage["sequence_number"], 1)
            self.assertIsNone(stage["route_id"])

        finally:
            connection.close()

    def test_additional_recognised_stage_with_arbitrary_id_is_assigned(self):
        connection = self.connect()

        try:
            connection.execute("""
                INSERT INTO stages (
                    id, route_name, name, sequence_number
                )
                VALUES (25, 'Nairobi - Thika', 'Parklands', 10)
            """)
            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            thika_id = connection.execute("""
                SELECT id
                FROM routes
                WHERE name = 'Nairobi - Thika'
            """).fetchone()["id"]

            stage = connection.execute("""
                SELECT route_id, sequence_number, name
                FROM stages
                WHERE id = 25
            """).fetchone()

            self.assertEqual(stage["route_id"], thika_id)
            self.assertEqual(stage["sequence_number"], 10)
            self.assertEqual(stage["name"], "Parklands")

        finally:
            connection.close()

    def test_additional_matatu_with_arbitrary_id_is_assigned(self):
        connection = self.connect()

        try:
            connection.execute("""
                INSERT INTO matatus (
                    id, registration_number, route_name
                )
                VALUES (35, 'KDA 456B', 'Nairobi - Thika')
            """)
            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            thika_id = connection.execute("""
                SELECT id
                FROM routes
                WHERE name = 'Nairobi - Thika'
            """).fetchone()["id"]

            matatu = connection.execute("""
                SELECT route_id, registration_number
                FROM matatus
                WHERE id = 35
            """).fetchone()

            self.assertEqual(matatu["route_id"], thika_id)
            self.assertEqual(matatu["registration_number"], "KDA 456B")

        finally:
            connection.close()

    def test_gps_stage_with_arbitrary_id_remains_unassigned(self):
        connection = self.connect()

        try:
            connection.execute("""
                DELETE FROM stages
                WHERE id = 9
            """)

            connection.execute("""
                INSERT INTO stages (
                    id, route_name, name, sequence_number
                )
                VALUES (45, 'Nairobi - Thika', 'GPS test', 99)
            """)

            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            gps = connection.execute("""
                SELECT route_id, sequence_number
                FROM stages
                WHERE id = 45
            """).fetchone()

            self.assertIsNotNone(gps)
            self.assertIsNone(gps["route_id"])
            self.assertEqual(gps["sequence_number"], 99)

        finally:
            connection.close()

    def test_existing_conflicting_route_assignment_causes_rollback(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE routes (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                )
            """)

            connection.execute("""
                INSERT INTO routes (id, name)
                VALUES (99, 'Unexpected Route')
            """)

            connection.execute("""
                ALTER TABLE stages
                ADD COLUMN route_id INTEGER REFERENCES routes(id)
            """)

            connection.execute("""
                UPDATE stages
                SET route_id = 99
                WHERE id = 1
            """)

            connection.commit()

        finally:
            connection.close()

        with self.assertRaises(RuntimeError):
            self.run_migration()

        connection = self.connect()

        try:
            stage = connection.execute("""
                SELECT route_id
                FROM stages
                WHERE id = 1
            """).fetchone()

            self.assertEqual(stage["route_id"], 99)

            self.assertEqual(
                connection.execute(
                    "SELECT COUNT(*) FROM routes"
                ).fetchone()[0],
                1,
            )

        finally:
            connection.close()

    def test_route_sequence_index_enforces_unique_sequences(self):
        self.run_migration()

        connection = self.connect()

        try:
            thika_id = connection.execute("""
                SELECT id
                FROM routes
                WHERE name = 'Nairobi - Thika'
            """).fetchone()[0]

            nakuru_id = connection.execute("""
                SELECT id
                FROM routes
                WHERE name = 'Nakuru - Nairobi'
            """).fetchone()[0]

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("""
                    INSERT INTO stages (
                        route_name, name, sequence_number, route_id
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    "Nairobi - Thika",
                    "Duplicate",
                    1,
                    thika_id,
                ))

            connection.execute("""
                INSERT INTO stages (
                    route_name, name, sequence_number, route_id
                )
                VALUES (?, ?, ?, ?)
            """, (
                "Nakuru - Nairobi",
                "New Stage",
                2,
                nakuru_id,
            ))

            connection.commit()

        finally:
            connection.close()

    def test_migration_succeeds_when_gps_stage_is_absent(self):
        connection = self.connect()

        try:
            connection.execute("DELETE FROM stages WHERE id = 9")
            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            routes = {
                row["name"]: row["id"]
                for row in connection.execute(
                    "SELECT id, name FROM routes"
                )
            }

            thika_id = routes["Nairobi - Thika"]
            nakuru_id = routes["Nakuru - Nairobi"]

            self.assertIsNone(
                connection.execute(
                    "SELECT id FROM stages WHERE id = 9"
                ).fetchone()
            )

            stage_ids = [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM stages ORDER BY id"
                )
            ]

            self.assertEqual(stage_ids, list(range(1, 9)) + [10])

            for stage_id in range(1, 9):
                stage = connection.execute("""
                    SELECT route_id, sequence_number
                    FROM stages
                    WHERE id = ?
                """, (stage_id,)).fetchone()

                self.assertEqual(stage["route_id"], thika_id)
                self.assertEqual(stage["sequence_number"], stage_id)

            bahati = connection.execute("""
                SELECT route_id, sequence_number
                FROM stages
                WHERE id = 10
            """).fetchone()

            self.assertEqual(bahati["route_id"], nakuru_id)
            self.assertEqual(bahati["sequence_number"], 1)

            matatus = connection.execute("""
                SELECT id, route_id
                FROM matatus
                ORDER BY id
            """).fetchall()

            self.assertEqual(
                [(row["id"], row["route_id"]) for row in matatus],
                [(1, thika_id), (2, nakuru_id)],
            )

            destinations = connection.execute("""
                SELECT id, destination_stage_id
                FROM passenger_destinations
                ORDER BY id
            """).fetchall()

            self.assertEqual(
                [(row[0], row[1]) for row in destinations],
                [(1, 1), (2, 4)],
            )

            request = connection.execute("""
                SELECT current_destination_stage_id,
                       requested_destination_stage_id
                FROM destination_change_requests
                WHERE id = 1
            """).fetchone()

            self.assertEqual(tuple(request), (5, 6))

            self.assertEqual(
                connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall(),
                [],
            )

        finally:
            connection.close()

    def test_existing_partial_index_is_preserved(self):
        self.run_migration()

        connection = self.connect()

        try:
            connection.execute(
                "DROP INDEX unique_stage_sequence_per_route"
            )

            connection.execute("""
                ALTER TABLE stages
                ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0
                CHECK (is_archived IN (0, 1))
            """)

            connection.execute("""
                ALTER TABLE stages
                ADD COLUMN archived_at TEXT
            """)

            connection.execute("""
                CREATE UNIQUE INDEX
                    unique_active_stage_sequence_per_route
                ON stages (route_id, sequence_number)
                WHERE is_archived = 0
            """)

            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            indexes = {
                row["name"]: row
                for row in connection.execute(
                    "PRAGMA index_list(stages)"
                )
            }

            self.assertIn(
                "unique_active_stage_sequence_per_route",
                indexes,
            )

            self.assertNotIn(
                "unique_stage_sequence_per_route",
                indexes,
            )

            self.assertEqual(
                indexes["unique_active_stage_sequence_per_route"]["unique"],
                1,
            )

            self.assertEqual(
                indexes["unique_active_stage_sequence_per_route"]["partial"],
                1,
            )

        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
