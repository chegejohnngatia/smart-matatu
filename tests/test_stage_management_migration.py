
import os
import sqlite3
import tempfile
import unittest

import migrate_stage_management


class StageManagementMigrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.temp_dir.name,
            "test_stage_management.db"
        )
        self.create_test_database()

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def create_test_database(self):
        connection = self.connect()

        try:
            connection.executescript("""
                CREATE TABLE routes (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE
                );

                INSERT INTO routes (id, name)
                VALUES
                    (1, 'Nairobi - Thika'),
                    (2, 'Nakuru - Nairobi');

                CREATE TABLE stages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    route_id INTEGER REFERENCES routes(id),
                    route_name TEXT NOT NULL,
                    name TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    sequence_number INTEGER NOT NULL
                );

                CREATE UNIQUE INDEX unique_stage_sequence_per_route
                ON stages (route_id, sequence_number);

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

            connection.executemany("""
                INSERT INTO stages (
                    id,
                    route_id,
                    route_name,
                    name,
                    latitude,
                    longitude,
                    sequence_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                (
                    1, 1, "Nairobi - Thika",
                    "Pangani", -1.2700, 36.8200, 1
                ),
                (
                    2, 1, "Nairobi - Thika",
                    "Muthaiga", -1.2500, 36.8200, 2
                ),
            ])

            connection.executemany("""
                INSERT INTO passenger_destinations (
                    id, destination_stage_id
                )
                VALUES (?, ?)
            """, [
                (1, 1),
                (2, 2),
            ])

            connection.execute("""
                INSERT INTO destination_change_requests (
                    id,
                    current_destination_stage_id,
                    requested_destination_stage_id
                )
                VALUES (1, 1, 2)
            """)

            connection.commit()

        finally:
            connection.close()

    def test_successful_migration_preserves_records(self):
        migrate_stage_management.migrate(self.db_path)

        connection = self.connect()

        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(stages)"
                )
            }

            self.assertIn("is_archived", columns)
            self.assertIn("archived_at", columns)

            stages = connection.execute("""
                SELECT id, name, route_id, sequence_number,
                       is_archived, archived_at
                FROM stages
                ORDER BY id
            """).fetchall()

            self.assertEqual(
                [row["id"] for row in stages],
                [1, 2]
            )

            self.assertEqual(
                [row["is_archived"] for row in stages],
                [0, 0]
            )

            # Existing route assignments and sequences survive.
            self.assertEqual(
                (stages[0]["route_id"], stages[0]["sequence_number"]),
                (1, 1)
            )

            self.assertEqual(
                (stages[1]["route_id"], stages[1]["sequence_number"]),
                (1, 2)
            )

            # Verify the old index is gone.
            old_index = connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'index'
                AND name = 'unique_stage_sequence_per_route'
            """).fetchone()

            self.assertIsNone(old_index)

            # Verify the new index exists.
            new_index = connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'index'
                AND name = 'unique_active_stage_sequence_per_route'
            """).fetchone()

            self.assertIsNotNone(new_index)

            # Verify historical passenger references.
            destinations = connection.execute("""
                SELECT id, destination_stage_id
                FROM passenger_destinations
                ORDER BY id
            """).fetchall()

            self.assertEqual(
                [tuple(row) for row in destinations],
                [(1, 1), (2, 2)]
            )

            request = connection.execute("""
                SELECT current_destination_stage_id,
                       requested_destination_stage_id
                FROM destination_change_requests
                WHERE id = 1
            """).fetchone()

            self.assertEqual(tuple(request), (1, 2))

            self.assertEqual(
                connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall(),
                []
            )

            self.assertEqual(
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok"
            )

        finally:
            connection.close()

    def test_migration_succeeds_when_gps_stage_id_9_exists(self):
        connection = self.connect()

        try:
            connection.execute("""
                INSERT INTO stages (
                    id, route_id, route_name, name,
                    latitude, longitude, sequence_number
                )
                VALUES (
                    9, NULL, 'Nairobi- Thika', 'GPS test',
                    -1.286389, 36.818223, 9
                )
            """)
            connection.commit()
        finally:
            connection.close()

        migrate_stage_management.migrate(self.db_path)

        connection = self.connect()
        try:
            gps = connection.execute("""
                SELECT id, route_id, route_name, name,
                       latitude, longitude, sequence_number
                FROM stages
                WHERE id = 9
            """).fetchone()

            self.assertIsNotNone(gps)
            self.assertEqual(
                tuple(gps),
                (
                    9, None, "Nairobi- Thika", "GPS test",
                    -1.286389, 36.818223, 9
                )
            )
        finally:
            connection.close()

    def test_migration_can_run_twice(self):
        migrate_stage_management.migrate(self.db_path)
        migrate_stage_management.migrate(self.db_path)

        connection = self.connect()

        try:
            columns = [
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(stages)"
                )
            ]

            self.assertEqual(columns.count("is_archived"), 1)
            self.assertEqual(columns.count("archived_at"), 1)

            indexes = [
                row["name"]
                for row in connection.execute(
                    "PRAGMA index_list(stages)"
                )
            ]

            self.assertEqual(
                indexes.count(
                    "unique_active_stage_sequence_per_route"
                ),
                1
            )

            self.assertNotIn(
                "unique_stage_sequence_per_route",
                indexes
            )

        finally:
            connection.close()

    def test_archived_stage_can_reuse_active_position(self):
        migrate_stage_management.migrate(self.db_path)

        connection = self.connect()

        try:
            connection.execute("""
                UPDATE stages
                SET is_archived = 1,
                    archived_at = CURRENT_TIMESTAMP,
                    sequence_number = 1
                WHERE id = 2
            """)

            connection.commit()

            archived = connection.execute("""
                SELECT is_archived, sequence_number
                FROM stages
                WHERE id = 2
            """).fetchone()

            self.assertEqual(archived["is_archived"], 1)
            self.assertEqual(archived["sequence_number"], 1)

        finally:
            connection.close()

    def test_duplicate_active_sequence_is_rejected(self):
        migrate_stage_management.migrate(self.db_path)

        connection = self.connect()

        try:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("""
                    INSERT INTO stages (
                        route_id,
                        route_name,
                        name,
                        sequence_number,
                        is_archived
                    )
                    VALUES (
                        1,
                        'Nairobi - Thika',
                        'Duplicate',
                        1,
                        0
                    )
                """)

        finally:
            connection.rollback()
            connection.close()

    def test_restoring_archived_stage_at_occupied_position_fails(self):
        migrate_stage_management.migrate(self.db_path)

        connection = self.connect()

        try:
            connection.execute("""
                UPDATE stages
                SET is_archived = 1,
                    archived_at = CURRENT_TIMESTAMP,
                    sequence_number = 1
                WHERE id = 2
            """)

            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute("""
                    UPDATE stages
                    SET is_archived = 0,
                        archived_at = NULL
                    WHERE id = 2
                """)

        finally:
            connection.rollback()
            connection.close()

    def test_unexpected_old_index_causes_rollback(self):
        connection = self.connect()

        try:
            connection.execute("""
                DROP INDEX unique_stage_sequence_per_route
            """)

            connection.execute("""
                CREATE UNIQUE INDEX unique_stage_sequence_per_route
                ON stages (name)
            """)

            connection.commit()

        finally:
            connection.close()

        with self.assertRaises(RuntimeError):
            migrate_stage_management.migrate(self.db_path)

        connection = self.connect()

        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(stages)"
                )
            }

            # ALTER TABLE changes must also roll back.
            self.assertNotIn("is_archived", columns)
            self.assertNotIn("archived_at", columns)

            # The unexpected original index must survive rollback.
            index = connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'index'
                AND name = 'unique_stage_sequence_per_route'
            """).fetchone()

            self.assertIsNotNone(index)

            index_columns = [
                row["name"]
                for row in connection.execute(
                    "PRAGMA index_info("
                    "'unique_stage_sequence_per_route')"
                )
            ]

            self.assertEqual(index_columns, ["name"])

        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
