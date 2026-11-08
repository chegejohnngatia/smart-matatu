import os
import sqlite3
import tempfile
import unittest

import migrate_matatu_lifecycle


class MatatuLifecycleMigrationTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.temp_dir.name,
            "test_matatu_lifecycle.db",
        )
        self.create_database()

    def tearDown(self):
        self.temp_dir.cleanup()

    def connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def run_migration(self):
        migrate_matatu_lifecycle.migrate(self.db_path)

    def create_database(self, registrations=None):
        if registrations is None:
            registrations = [
                (1, "KCA 123A", "Nairobi - Thika"),
                (2, "KDB 456B", "Nakuru - Nairobi"),
            ]

        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_number TEXT NOT NULL,
                    route_name TEXT NOT NULL
                )
            """)

            connection.executemany("""
                INSERT INTO matatus (
                    id, registration_number, route_name
                )
                VALUES (?, ?, ?)
            """, registrations)

            connection.commit()

        finally:
            connection.close()

    def create_history_table(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatu_registration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    matatu_id INTEGER NOT NULL,
                    registration_number TEXT NOT NULL,
                    normalized_registration_number TEXT NOT NULL,
                    effective_start TEXT NOT NULL,
                    effective_end TEXT,
                    CHECK (
                        effective_end IS NULL
                        OR effective_end >= effective_start
                    )
                )
            """)
            connection.commit()

        finally:
            connection.close()

    def insert_history(
        self,
        matatu_id,
        registration,
        normalized,
        start,
        end=None,
    ):
        connection = self.connect()

        try:
            connection.execute("""
                INSERT INTO matatu_registration_history (
                    matatu_id,
                    registration_number,
                    normalized_registration_number,
                    effective_start,
                    effective_end
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                matatu_id,
                registration,
                normalized,
                start,
                end,
            ))
            connection.commit()

        finally:
            connection.close()

    def test_fresh_migration_creates_lifecycle_schema(self):
        self.run_migration()

        connection = self.connect()

        try:
            tables = {
                row["name"]
                for row in connection.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                """)
            }

            expected = {
                "matatus",
                "matatu_registration_registry",
                "matatu_registration_history",
                "matatu_payment_audit_archive",
                "matatu_emergency_audit_archive",
                "matatu_assignment_audit_archive",
            }

            self.assertTrue(expected.issubset(tables))

            archive_schemas = {
                "matatu_payment_audit_archive": {
                    "columns": {
                        "id",
                        "registration_number",
                        "source_record_id",
                        "amount",
                        "status",
                        "created_at",
                        "paid_at",
                        "confirmed_at",
                        "conductor_attribution_present",
                        "archived_at",
                    },
                    "source_id": "source_record_id",
                },
                "matatu_emergency_audit_archive": {
                    "columns": {
                        "id",
                        "registration_number",
                        "source_record_id",
                        "alert_type",
                        "status",
                        "created_at",
                        "acknowledged_at",
                        "conductor_attribution_present",
                        "archived_at",
                    },
                    "source_id": "source_record_id",
                },
                "matatu_assignment_audit_archive": {
                    "columns": {
                        "id",
                        "source_assignment_id",
                        "conductor_id",
                        "conductor_name",
                        "registration_number",
                        "assigned_at",
                        "ended_at",
                        "archived_at",
                    },
                    "source_id": "source_assignment_id",
                },
            }

            for table_name, schema in archive_schemas.items():
                actual_columns = {
                    row["name"]
                    for row in connection.execute(
                        f'PRAGMA table_info("{table_name}")'
                    )
                }

                self.assertEqual(
                    actual_columns,
                    schema["columns"],
                    f"Unexpected columns in {table_name}",
                )

                unique_source_id = False

                for index in connection.execute(
                    f'PRAGMA index_list("{table_name}")'
                ):
                    if index["unique"]:
                        index_name = index["name"].replace('"', '""')
                        indexed_columns = [
                            row["name"]
                            for row in connection.execute(
                                f'PRAGMA index_info("{index_name}")'
                            )
                        ]

                        if indexed_columns == [schema["source_id"]]:
                            unique_source_id = True
                            break

                self.assertTrue(
                    unique_source_id,
                    f"{table_name} must have a unique source ID",
                )

                self.assertEqual(
                    connection.execute(
                        f'PRAGMA foreign_key_list("{table_name}")'
                    ).fetchall(),
                    [],
                    f"{table_name} must not have foreign keys",
                )
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(matatus)"
                )
            }

            self.assertIn("is_archived", columns)
            self.assertIn("archived_at", columns)

            self.assertEqual(
                connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()[0],
                "ok",
            )

            self.assertEqual(
                connection.execute(
                    "PRAGMA foreign_key_check"
                ).fetchall(),
                [],
            )

        finally:
            connection.close()

    def test_incompatible_payment_archive_rolls_back_migration(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatu_payment_audit_archive (
                    id INTEGER PRIMARY KEY,
                    source_record_id INTEGER,
                    legacy_private_data TEXT
                )
            """)

            connection.execute("""
                INSERT INTO matatu_payment_audit_archive (
                    id, source_record_id, legacy_private_data
                )
                VALUES (1, 101, 'preserve-this-record')
            """)

            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(
            RuntimeError,
            "Unexpected matatu_payment_audit_archive schema",
        ):
            self.run_migration()

        connection = self.connect()

        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(matatu_payment_audit_archive)"
                )
            }

            self.assertEqual(
                columns,
                {"id", "source_record_id", "legacy_private_data"},
            )

            record = connection.execute("""
                SELECT id, source_record_id, legacy_private_data
                FROM matatu_payment_audit_archive
                WHERE id = 1
            """).fetchone()

            self.assertIsNotNone(record)
            self.assertEqual(record["source_record_id"], 101)
            self.assertEqual(
                record["legacy_private_data"],
                "preserve-this-record",
            )

            self.assertNotIn(
                "matatu_registration_registry",
                {
                    row["name"]
                    for row in connection.execute("""
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                    """)
                },
            )
        finally:
            connection.close()

    def test_incompatible_emergency_archive_rolls_back_migration(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatu_emergency_audit_archive (
                    id INTEGER PRIMARY KEY,
                    source_record_id INTEGER,
                    legacy_private_data TEXT
                )
            """)

            connection.execute("""
                INSERT INTO matatu_emergency_audit_archive (
                    id, source_record_id, legacy_private_data
                )
                VALUES (1, 202, 'preserve-emergency-record')
            """)

            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(
            RuntimeError,
            "Unexpected matatu_emergency_audit_archive schema",
        ):
            self.run_migration()

        connection = self.connect()

        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(matatu_emergency_audit_archive)"
                )
            }

            self.assertEqual(
                columns,
                {"id", "source_record_id", "legacy_private_data"},
            )

            record = connection.execute("""
                SELECT id, source_record_id, legacy_private_data
                FROM matatu_emergency_audit_archive
                WHERE id = 1
            """).fetchone()

            self.assertIsNotNone(record)
            self.assertEqual(record["source_record_id"], 202)
            self.assertEqual(
                record["legacy_private_data"],
                "preserve-emergency-record",
            )

            self.assertNotIn(
                "matatu_registration_registry",
                {
                    row["name"]
                    for row in connection.execute("""
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                    """)
                },
            )
        finally:
            connection.close()
    def test_payment_archive_requires_unique_source_record_id(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatu_payment_audit_archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_number TEXT NOT NULL,
                    source_record_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT,
                    paid_at TEXT,
                    confirmed_at TEXT,
                    conductor_attribution_present INTEGER NOT NULL
                        CHECK (conductor_attribution_present IN (0, 1)),
                    archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(
            RuntimeError,
            "matatu_payment_audit_archive source IDs must be unique",
        ):
            self.run_migration()

        connection = self.connect()

        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(matatu_payment_audit_archive)"
                )
            }

            self.assertEqual(columns, {
                "id",
                "registration_number",
                "source_record_id",
                "amount",
                "status",
                "created_at",
                "paid_at",
                "confirmed_at",
                "conductor_attribution_present",
                "archived_at",
            })

            self.assertNotIn(
                "matatu_registration_registry",
                {
                    row["name"]
                    for row in connection.execute("""
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                    """)
                },
            )
        finally:
            connection.close()
    def test_emergency_archive_rejects_foreign_keys(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE archive_parent (
                    id INTEGER PRIMARY KEY
                )
            """)

            connection.execute("""
                CREATE TABLE matatu_emergency_audit_archive (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    registration_number TEXT NOT NULL,
                    source_record_id INTEGER NOT NULL UNIQUE,
                    alert_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT,
                    acknowledged_at TEXT,
                    conductor_attribution_present INTEGER NOT NULL
                        CHECK (conductor_attribution_present IN (0, 1)),
                    archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (source_record_id)
                        REFERENCES archive_parent(id)
                )
            """)

            connection.execute(
                "INSERT INTO archive_parent (id) VALUES (303)"
            )

            connection.execute("""
                INSERT INTO matatu_emergency_audit_archive (
                    registration_number,
                    source_record_id,
                    alert_type,
                    status,
                    conductor_attribution_present
                )
                VALUES ('KCA 123A', 303, 'emergency', 'open', 1)
            """)

            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(
            RuntimeError,
            "matatu_emergency_audit_archive must not reference operational tables",
        ):
            self.run_migration()

        connection = self.connect()

        try:
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_list(matatu_emergency_audit_archive)"
            ).fetchall()

            self.assertEqual(len(foreign_keys), 1)
            self.assertEqual(foreign_keys[0]["table"], "archive_parent")

            record = connection.execute("""
                SELECT source_record_id, alert_type, status
                FROM matatu_emergency_audit_archive
                WHERE source_record_id = 303
            """).fetchone()

            self.assertIsNotNone(record)
            self.assertEqual(record["alert_type"], "emergency")
            self.assertEqual(record["status"], "open")

            self.assertNotIn(
                "matatu_registration_registry",
                {
                    row["name"]
                    for row in connection.execute("""
                        SELECT name
                        FROM sqlite_master
                        WHERE type = 'table'
                    """)
                },
            )
        finally:
            connection.close()
    def test_initial_registry_and_history_are_backfilled(self):
        self.run_migration()

        connection = self.connect()

        try:
            registry = connection.execute("""
                SELECT *
                FROM matatu_registration_registry
                ORDER BY original_matatu_id
            """).fetchall()

            history = connection.execute("""
                SELECT *
                FROM matatu_registration_history
                ORDER BY matatu_id
            """).fetchall()

            self.assertEqual(len(registry), 2)
            self.assertEqual(len(history), 2)

            self.assertEqual(
                [row["normalized_registration_number"] for row in registry],
                ["KCA 123A", "KDB 456B"],
            )

            self.assertEqual(
                [row["normalized_registration_number"] for row in history],
                ["KCA 123A", "KDB 456B"],
            )

            self.assertTrue(
                all(row["effective_end"] is None for row in history)
            )

            self.assertTrue(
                all(row["registered_at"] for row in registry)
            )

            for row in history:
                self.assertEqual(
                    row["effective_start"],
                    connection.execute("""
                        SELECT registered_at
                        FROM matatu_registration_registry
                        WHERE original_matatu_id = ?
                          AND normalized_registration_number = ?
                    """, (
                        row["matatu_id"],
                        row["normalized_registration_number"],
                    )).fetchone()["registered_at"],
                )

        finally:
            connection.close()

    def test_migration_is_idempotent(self):
        self.run_migration()
        self.run_migration()

        connection = self.connect()

        try:
            self.assertEqual(
                connection.execute("""
                    SELECT COUNT(*)
                    FROM matatu_registration_registry
                """).fetchone()[0],
                2,
            )

            self.assertEqual(
                connection.execute("""
                    SELECT COUNT(*)
                    FROM matatu_registration_history
                """).fetchone()[0],
                2,
            )

        finally:
            connection.close()

    def test_unusual_whitespace_uses_consistent_normalization(self):
        connection = self.connect()

        try:
            connection.execute("""
                UPDATE matatus
                SET registration_number = ?
                WHERE id = 1
            """, ("\tKCA 123A\n",))
            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            registry = connection.execute("""
                SELECT normalized_registration_number
                FROM matatu_registration_registry
                WHERE original_matatu_id = 1
            """).fetchone()

            history = connection.execute("""
                SELECT normalized_registration_number
                FROM matatu_registration_history
                WHERE matatu_id = 1
            """).fetchone()

            self.assertEqual(
                registry["normalized_registration_number"],
                "KCA 123A",
            )
            self.assertEqual(
                history["normalized_registration_number"],
                "KCA 123A",
            )

        finally:
            connection.close()

    def test_duplicate_live_registrations_are_rejected(self):
        connection = self.connect()

        try:
            connection.execute("""
                UPDATE matatus
                SET registration_number = ?
                WHERE id = 2
            """, (" kca 123a ",))
            connection.commit()

        finally:
            connection.close()

        with self.assertRaises(RuntimeError):
            self.run_migration()

        connection = self.connect()

        try:
            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(matatus)"
                )
            }

            self.assertNotIn("is_archived", columns)

            self.assertIsNone(connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'matatu_registration_registry'
            """).fetchone())

        finally:
            connection.close()

    def test_valid_historical_gap_is_preserved(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA OLD",
            "KCA OLD",
            "2026-01-01 08:00:00",
            "2026-01-01 09:00:00",
        )

        self.insert_history(
            1,
            "KCA 123A",
            "KCA 123A",
            "2026-01-01 10:00:00",
            None,
        )

        self.run_migration()

        connection = self.connect()

        try:
            rows = connection.execute("""
                SELECT registration_number,
                       effective_start,
                       effective_end
                FROM matatu_registration_history
                WHERE matatu_id = 1
                ORDER BY effective_start
            """).fetchall()

            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["registration_number"], "KCA OLD")
            self.assertEqual(rows[0]["effective_end"], "2026-01-01 09:00:00")
            self.assertEqual(rows[1]["registration_number"], "KCA 123A")
            self.assertEqual(rows[1]["effective_start"], "2026-01-01 10:00:00")
            self.assertIsNone(rows[1]["effective_end"])

            historical_reservation = connection.execute("""
                SELECT original_matatu_id, registered_at
                FROM matatu_registration_registry
                WHERE normalized_registration_number = ?
            """, ("KCA OLD",)).fetchone()

            self.assertIsNotNone(historical_reservation)
            self.assertEqual(
                historical_reservation["original_matatu_id"], 1
            )
            self.assertEqual(
                historical_reservation["registered_at"],
                "2026-01-01 08:00:00",
            )

        finally:
            connection.close()

    def test_repeated_historical_registration_creates_one_reservation(self):
        self.create_history_table()

        self.insert_history(
            1, "KCA OLD", "KCA OLD",
            "2020-01-01 08:00:00", "2020-06-01 08:00:00",
        )
        self.insert_history(
            1, "KCA OLD", "KCA OLD",
            "2021-01-01 08:00:00", "2021-06-01 08:00:00",
        )
        self.insert_history(
            1, "KCA 123A", "KCA 123A",
            "2022-01-01 08:00:00", None,
        )

        self.run_migration()

        connection = self.connect()
        try:
            rows = connection.execute("""
                SELECT original_matatu_id, registered_at
                FROM matatu_registration_registry
                WHERE normalized_registration_number = ?
            """, ("KCA OLD",)).fetchall()

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["original_matatu_id"], 1)
            self.assertEqual(
                rows[0]["registered_at"], "2020-01-01 08:00:00"
            )
        finally:
            connection.close()

    def test_deleted_matatu_historical_registration_remains_reserved(self):
        self.create_history_table()

        self.insert_history(
            99, "KCA GONE", "KCA GONE",
            "2020-01-01 08:00:00", "2020-06-01 08:00:00",
        )

        self.run_migration()

        connection = self.connect()
        try:
            row = connection.execute("""
                SELECT original_matatu_id, registered_at
                FROM matatu_registration_registry
                WHERE normalized_registration_number = ?
            """, ("KCA GONE",)).fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row["original_matatu_id"], 99)
            self.assertEqual(row["registered_at"], "2020-01-01 08:00:00")
        finally:
            connection.close()

    def test_conflicting_historical_ownership_is_rejected(self):
        self.create_history_table()

        self.insert_history(
            1, "KCA OLD", "KCA OLD",
            "2020-01-01 08:00:00", "2020-06-01 08:00:00",
        )
        self.insert_history(
            99, "KCA OLD", "KCA OLD",
            "2021-01-01 08:00:00", "2021-06-01 08:00:00",
        )

        with self.assertRaisesRegex(RuntimeError, "conflicts"):
            self.run_migration()

        connection = self.connect()
        try:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(matatus)")
            }
            self.assertNotIn("is_archived", columns)

            registry = connection.execute("""
                SELECT name FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'matatu_registration_registry'
            """).fetchone()
            self.assertIsNone(registry)
        finally:
            connection.close()

    def test_existing_registry_owner_conflict_is_rejected(self):
        self.create_history_table()

        self.insert_history(
            1, "KCA OLD", "KCA OLD",
            "2020-01-01 08:00:00", "2020-06-01 08:00:00",
        )

        connection = self.connect()
        try:
            connection.execute("""
                CREATE TABLE matatu_registration_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_registration_number TEXT NOT NULL UNIQUE,
                    registration_number TEXT NOT NULL,
                    original_matatu_id INTEGER NOT NULL,
                    registered_at TEXT NOT NULL,
                    permanently_deleted_at TEXT
                )
            """)
            connection.execute("""
                INSERT INTO matatu_registration_registry (
                    normalized_registration_number,
                    registration_number,
                    original_matatu_id,
                    registered_at
                )
                VALUES (?, ?, ?, ?)
            """, ("KCA OLD", "KCA OLD", 99, "1999-01-01 00:00:00"))
            connection.commit()
        finally:
            connection.close()

        with self.assertRaisesRegex(RuntimeError, "existing registry owner"):
            self.run_migration()

    def test_existing_registry_timestamp_is_preserved(self):
        self.run_migration()

        connection = self.connect()
        try:
            self.insert_history(
                1, "KCA OLD", "KCA OLD",
                "2020-01-01 08:00:00", "2020-06-01 08:00:00",
            )

            connection.execute("""
                INSERT INTO matatu_registration_registry (
                    normalized_registration_number,
                    registration_number,
                    original_matatu_id,
                    registered_at
                )
                VALUES (?, ?, ?, ?)
            """, ("KCA OLD", "KCA OLD", 1, "1999-01-01 00:00:00"))
            connection.commit()
        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()
        try:
            row = connection.execute("""
                SELECT original_matatu_id, registered_at
                FROM matatu_registration_registry
                WHERE normalized_registration_number = ?
            """, ("KCA OLD",)).fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row["original_matatu_id"], 1)
            self.assertEqual(row["registered_at"], "1999-01-01 00:00:00")
        finally:
            connection.close()

    def test_adjacent_historical_intervals_are_valid(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA OLD",
            "KCA OLD",
            "2026-01-01 08:00:00",
            "2026-01-01 10:00:00",
        )

        self.insert_history(
            1,
            "KCA 123A",
            "KCA 123A",
            "2026-01-01 10:00:00",
            None,
        )

        self.run_migration()

        connection = self.connect()

        try:
            self.assertEqual(
                connection.execute("""
                    SELECT COUNT(*)
                    FROM matatu_registration_history
                    WHERE matatu_id = 1
                """).fetchone()[0],
                2,
            )

        finally:
            connection.close()

    def test_overlapping_historical_intervals_are_rejected(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA OLD",
            "KCA OLD",
            "2026-01-01 08:00:00",
            "2026-01-01 12:00:00",
        )

        self.insert_history(
            1,
            "KCA 123A",
            "KCA 123A",
            "2026-01-01 11:00:00",
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "overlapping"):
            self.run_migration()

        connection = self.connect()

        try:
            self.assertEqual(
                connection.execute("""
                    SELECT COUNT(*)
                    FROM matatu_registration_history
                """).fetchone()[0],
                2,
            )

            columns = {
                row["name"]
                for row in connection.execute(
                    "PRAGMA table_info(matatus)"
                )
            }

            self.assertNotIn("is_archived", columns)

            self.assertIsNone(connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'matatu_registration_registry'
            """).fetchone())

        finally:
            connection.close()

    def test_invalid_timestamp_is_rejected(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA 123A",
            "KCA 123A",
            "not-a-timestamp",
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "invalid timestamp"):
            self.run_migration()

    def test_timezone_aware_timestamp_is_rejected(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA 123A",
            "KCA 123A",
            "2026-01-01T08:00:00+03:00",
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "timezone-aware"):
            self.run_migration()

    def test_end_before_start_is_rejected(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatu_registration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    matatu_id INTEGER NOT NULL,
                    registration_number TEXT NOT NULL,
                    normalized_registration_number TEXT NOT NULL,
                    effective_start TEXT NOT NULL,
                    effective_end TEXT
                )
            """)

            connection.executemany("""
                INSERT INTO matatu_registration_history (
                    matatu_id,
                    registration_number,
                    normalized_registration_number,
                    effective_start,
                    effective_end
                )
                VALUES (?, ?, ?, ?, ?)
            """, [
                (
                    1,
                    "KCA OLD",
                    "KCA OLD",
                    "2026-01-01 12:00:00",
                    "2026-01-01 10:00:00",
                ),
                (
                    1,
                    "KCA 123A",
                    "KCA 123A",
                    "2026-01-01 13:00:00",
                    None,
                ),
            ])

            connection.commit()

        finally:
            connection.close()

        with self.assertRaisesRegex(RuntimeError, "earlier"):
            self.run_migration()

    def test_registration_normalization_mismatch_is_rejected(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA 123A",
            "WRONG VALUE",
            "2026-01-01 08:00:00",
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "normalized registration"):
            self.run_migration()

    def test_history_without_open_current_entry_is_rejected(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA OLD",
            "KCA OLD",
            "2026-01-01 08:00:00",
            "2026-01-01 09:00:00",
        )

        with self.assertRaisesRegex(RuntimeError, "no open current entry"):
            self.run_migration()

    def test_multiple_open_history_entries_are_rejected(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA OLD",
            "KCA OLD",
            "2026-01-01 08:00:00",
            None,
        )

        self.insert_history(
            1,
            "KCA 123A",
            "KCA 123A",
            "2026-01-01 09:00:00",
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "multiple open"):
            self.run_migration()

    def test_open_history_must_match_current_registration(self):
        self.create_history_table()

        self.insert_history(
            1,
            "KCA OLD",
            "KCA OLD",
            "2026-01-01 08:00:00",
            None,
        )

        with self.assertRaisesRegex(RuntimeError, "does not match"):
            self.run_migration()

    def test_registry_rebuild_removes_original_matatu_unique_constraint(self):
        connection = self.connect()

        try:
            connection.execute("""
                CREATE TABLE matatu_registration_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    normalized_registration_number TEXT NOT NULL,
                    registration_number TEXT NOT NULL,
                    original_matatu_id INTEGER NOT NULL UNIQUE,
                    registered_at TEXT NOT NULL,
                    permanently_deleted_at TEXT
                )
            """)

            connection.executemany("""
                INSERT INTO matatu_registration_registry (
                    id,
                    normalized_registration_number,
                    registration_number,
                    original_matatu_id,
                    registered_at,
                    permanently_deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (
                    2, "KCA 123A", "KCA 123A", 1,
                    "2026-01-01 08:00:00", None,
                ),
                (
                    9, "KDB 456B", "KDB 456B", 2,
                    "2026-01-02 08:00:00", None,
                ),

                (
                    45, "KXX 999X", "KXX 999X", 99,
                    "2026-01-03 08:00:00",
                    "2026-01-04 08:00:00",
                ),
            ])

            # Simulate a historical AUTOINCREMENT high-water mark
            # greater than the highest surviving registry ID.
            connection.execute("""
                UPDATE sqlite_sequence
                SET seq = 60
                WHERE name = 'matatu_registration_registry'
            """)

            connection.commit()

        finally:
            connection.close()

        self.run_migration()

        connection = self.connect()

        try:
            records = connection.execute("""
                SELECT id,
                       normalized_registration_number,
                       original_matatu_id,
                       permanently_deleted_at
                FROM matatu_registration_registry
                ORDER BY id
            """).fetchall()

            self.assertEqual(
                [
                    (row["id"], row["normalized_registration_number"],
                     row["original_matatu_id"])
                    for row in records
                ],
                [
                    (2, "KCA 123A", 1),
                    (9, "KDB 456B", 2),
                    (45, "KXX 999X", 99),
                ],
            )

            deleted = connection.execute("""
                SELECT permanently_deleted_at
                FROM matatu_registration_registry
                WHERE normalized_registration_number = 'KXX 999X'
            """).fetchone()

            self.assertIsNotNone(deleted)
            self.assertEqual(
                deleted["permanently_deleted_at"],
                "2026-01-04 08:00:00",
            )

            sequence = connection.execute("""
                SELECT seq
                FROM sqlite_sequence
                WHERE name = 'matatu_registration_registry'
            """).fetchone()

            self.assertIsNotNone(sequence)
            self.assertGreaterEqual(sequence["seq"], 60)

            indexes = connection.execute("""
                PRAGMA index_list(matatu_registration_registry)
            """).fetchall()

            unique_normalized_indexes = []
            unique_original_id_indexes = []

            for index in indexes:
                if not index["unique"]:
                    continue

                columns = [
                    row["name"]
                    for row in connection.execute(
                        f'PRAGMA index_info("{index["name"]}")'
                    )
                ]

                if columns == ["normalized_registration_number"]:
                    unique_normalized_indexes.append(index["name"])

                if columns == ["original_matatu_id"]:
                    unique_original_id_indexes.append(index["name"])

            self.assertTrue(unique_normalized_indexes)
            self.assertEqual(unique_original_id_indexes, [])

            # Confirm that a further historical registration can be
            # associated with Matatu 1.
            connection.execute("""
                INSERT INTO matatu_registration_registry (
                    normalized_registration_number,
                    registration_number,
                    original_matatu_id,
                    registered_at
                )
                VALUES (
                    'KCA OLD',
                    'KCA OLD',
                    1,
                    '2025-11-01 08:00:00'
                )
            """)

            connection.commit()

        finally:
            connection.close()
