import argparse
import os
import re
import sqlite3
from contextlib import closing


DEFAULT_DATABASE = os.path.abspath(
    os.environ.get(
        "SMART_MATATU_DB",
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "smart_matatu.db",
        ),
    )
)

ROUTES = {
    "nairobithika": "Nairobi - Thika",
    "nairobinakuru": "Nakuru - Nairobi",
    "nakurunairobi": "Nakuru - Nairobi",
}

OLD_INDEX = "unique_stage_sequence_per_route"
NEW_INDEX = "unique_active_stage_sequence_per_route"

HISTORICAL_REFERENCES = {
    "passenger_destinations": ("destination_stage_id",),
    "destination_change_requests": (
        "current_destination_stage_id",
        "requested_destination_stage_id",
    ),
}


def normalize_route_name(value):
    """Normalise route aliases without depending on punctuation or spacing."""
    if value is None:
        return None

    return re.sub(r"[^a-z0-9]", "", value.casefold())


def canonical_route_name(value):
    """Return the canonical route name for a recognised legacy alias."""
    normalized = normalize_route_name(value)

    if normalized is None:
        return None

    return ROUTES.get(normalized)


def get_tables(connection):
    return {
        row["name"]
        for row in connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """)
    }


def get_columns(connection, table):
    return {
        row["name"]
        for row in connection.execute(
            f'PRAGMA table_info("{table}")'
        )
    }


def ensure_required_schema(connection):
    tables = get_tables(connection)

    for table in ("stages", "matatus"):
        if table not in tables:
            raise RuntimeError(f"Required table is missing: {table}")

    required_stage_columns = {
        "id",
        "name",
        "route_name",
        "sequence_number",
    }

    required_matatu_columns = {
        "id",
        "registration_number",
        "route_name",
    }

    if not required_stage_columns <= get_columns(connection, "stages"):
        raise RuntimeError("Unexpected stages table schema.")

    if not required_matatu_columns <= get_columns(connection, "matatus"):
        raise RuntimeError("Unexpected matatus table schema.")

    if "routes" in tables:
        route_columns = get_columns(connection, "routes")

        if not {"id", "name"} <= route_columns:
            raise RuntimeError("Unexpected routes table schema.")


def ensure_routes_table(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT
        )
    """)

    route_ids = {}

    for canonical_name in sorted(set(ROUTES.values())):
        rows = connection.execute("""
            SELECT id
            FROM routes
            WHERE name = ?
        """, (canonical_name,)).fetchall()

        if len(rows) > 1:
            raise RuntimeError(
                f"Multiple route records have the name "
                f"{canonical_name!r}."
            )

        if rows:
            route_ids[canonical_name] = rows[0]["id"]
        else:
            cursor = connection.execute("""
                INSERT INTO routes (name)
                VALUES (?)
            """, (canonical_name,))

            route_ids[canonical_name] = cursor.lastrowid

    return route_ids


def ensure_route_columns(connection):
    for table in ("stages", "matatus"):
        columns = get_columns(connection, table)

        if "route_id" not in columns:
            connection.execute(f"""
                ALTER TABLE "{table}"
                ADD COLUMN route_id INTEGER REFERENCES routes(id)
            """)

        foreign_keys = connection.execute(
            f'PRAGMA foreign_key_list("{table}")'
        ).fetchall()

        valid_route_fk = any(
            fk["table"] == "routes"
            and fk["from"] == "route_id"
            and fk["to"] == "id"
            for fk in foreign_keys
        )

        if not valid_route_fk:
            raise RuntimeError(
                f"{table}.route_id does not have the expected "
                "foreign key to routes(id). Migration stopped."
            )


def snapshot_historical_references(connection):
    """Capture existing passenger-to-stage references for verification."""
    snapshots = {}

    tables = get_tables(connection)

    for table, columns in HISTORICAL_REFERENCES.items():
        if table not in tables:
            continue

        actual_columns = get_columns(connection, table)

        missing = set(columns) - actual_columns

        if missing:
            raise RuntimeError(
                f"Historical table {table} is missing columns: "
                f"{sorted(missing)}."
            )

        selected_columns = ["id", *columns]

        rows = connection.execute(
            f"""
            SELECT {", ".join(f'"{column}"' for column in selected_columns)}
            FROM "{table}"
            ORDER BY id
            """
        ).fetchall()

        snapshots[table] = [
            tuple(row[column] for column in selected_columns)
            for row in rows
        ]

    return snapshots


def verify_historical_references(connection, snapshots):
    for table, expected_rows in snapshots.items():
        columns = ["id", *HISTORICAL_REFERENCES[table]]

        actual_rows = connection.execute(
            f"""
            SELECT {", ".join(f'"{column}"' for column in columns)}
            FROM "{table}"
            ORDER BY id
            """
        ).fetchall()

        actual = [
            tuple(row[column] for column in columns)
            for row in actual_rows
        ]

        if actual != expected_rows:
            raise RuntimeError(
                f"Historical stage references changed in {table}."
            )


def validate_existing_route_assignment(
    connection,
    table,
    row,
    expected_route_id,
):
    existing_route_id = row["route_id"]

    if existing_route_id is None:
        return

    if existing_route_id != expected_route_id:
        raise RuntimeError(
            f"Conflicting route assignment in {table}, "
            f"record ID {row['id']}: existing route_id "
            f"{existing_route_id}, expected {expected_route_id}."
        )


def assign_recognised_routes(connection, route_ids):
    """Assign recognised aliases without changing existing conflicts."""

    gps_rows = connection.execute("""
        SELECT id, name, route_id
        FROM stages
    """).fetchall()

    gps_stage_ids = set()

    for row in gps_rows:
        if normalize_route_name(row["name"]) == "gpstest":
            gps_stage_ids.add(row["id"])

            if row["route_id"] is not None:
                raise RuntimeError(
                    f"GPS test stage ID {row['id']} already has a "
                    "route assignment. Resolve it explicitly before "
                    "running this migration."
                )

    # Process stages using their route names, not their IDs or counts.
    stage_rows = connection.execute("""
        SELECT id, name, route_name, route_id
        FROM stages
    """).fetchall()

    for row in stage_rows:
        if row["id"] in gps_stage_ids:
            continue

        canonical_name = canonical_route_name(row["route_name"])

        if canonical_name is None:
            continue

        expected_route_id = route_ids[canonical_name]

        validate_existing_route_assignment(
            connection,
            "stages",
            row,
            expected_route_id,
        )

        connection.execute("""
            UPDATE stages
            SET route_id = ?,
                route_name = ?
            WHERE id = ?
        """, (
            expected_route_id,
            canonical_name,
            row["id"],
        ))

    # Process matatus in the same way.
    matatu_rows = connection.execute("""
        SELECT id, route_name, route_id
        FROM matatus
    """).fetchall()

    for row in matatu_rows:
        canonical_name = canonical_route_name(row["route_name"])

        if canonical_name is None:
            continue

        expected_route_id = route_ids[canonical_name]

        validate_existing_route_assignment(
            connection,
            "matatus",
            row,
            expected_route_id,
        )

        connection.execute("""
            UPDATE matatus
            SET route_id = ?,
                route_name = ?
            WHERE id = ?
        """, (
            expected_route_id,
            canonical_name,
            row["id"],
        ))


def validate_existing_index(connection, index_name, expected_partial):
    index_row = connection.execute("""
        SELECT tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index'
        AND name = ?
    """, (index_name,)).fetchone()

    if index_row is None:
        return False

    if index_row["tbl_name"] != "stages":
        raise RuntimeError(
            f"Index {index_name} exists on an unexpected table."
        )

    details = connection.execute(
        "PRAGMA index_list(stages)"
    ).fetchall()

    matching = next(
        (item for item in details if item["name"] == index_name),
        None,
    )

    if (
        matching is None
        or matching["unique"] != 1
        or matching["partial"] != int(expected_partial)
    ):
        raise RuntimeError(
            f"Existing index {index_name} has an unexpected definition."
        )

    columns = [
        row["name"]
        for row in connection.execute(
            f'PRAGMA index_info("{index_name}")'
        )
    ]

    if columns != ["route_id", "sequence_number"]:
        raise RuntimeError(
            f"Index {index_name} has unexpected columns: {columns}."
        )

    if expected_partial:
        sql = (index_row["sql"] or "").casefold()
        compact_sql = re.sub(r"\s+", "", sql)

        if "whereis_archived=0" not in compact_sql:
            raise RuntimeError(
                f"Index {index_name} does not use the expected "
                "is_archived = 0 condition."
            )

    return True


def ensure_stage_sequence_index(connection):
    columns = get_columns(connection, "stages")
    has_archive_column = "is_archived" in columns

    old_exists = validate_existing_index(
        connection,
        OLD_INDEX,
        expected_partial=False,
    )

    new_exists = validate_existing_index(
        connection,
        NEW_INDEX,
        expected_partial=True,
    )

    if old_exists and new_exists:
        raise RuntimeError(
            "Both old and new stage sequence indexes exist. "
            "Resolve the conflicting indexes before migration."
        )

    if has_archive_column:
        if old_exists:
            # The stage-management migration owns the transition
            # from the old full index to the new partial index.
            return

        if not new_exists:
            connection.execute(f"""
                CREATE UNIQUE INDEX {NEW_INDEX}
                ON stages (route_id, sequence_number)
                WHERE is_archived = 0
            """)

        return

    if new_exists:
        raise RuntimeError(
            "The partial stage index exists, but stages.is_archived "
            "is missing."
        )

    if not old_exists:
        connection.execute(f"""
            CREATE UNIQUE INDEX {OLD_INDEX}
            ON stages (route_id, sequence_number)
        """)


def verify_route_assignments(connection):
    # Every recognised, non-GPS route name must point to its
    # canonical route record.
    rows = connection.execute("""
        SELECT s.id, s.name, s.route_name, s.route_id, r.name AS actual_route
        FROM stages AS s
        LEFT JOIN routes AS r ON r.id = s.route_id
    """).fetchall()

    for row in rows:
        if normalize_route_name(row["name"]) == "gpstest":
            if row["route_id"] is not None:
                raise RuntimeError(
                    f"GPS test stage ID {row['id']} has a route assignment."
                )
            continue

        canonical_name = canonical_route_name(row["route_name"])

        if canonical_name is not None:
            if row["actual_route"] != canonical_name:
                raise RuntimeError(
                    f"Stage ID {row['id']} has an invalid route assignment."
                )

    matatu_rows = connection.execute("""
        SELECT m.id, m.route_name, m.route_id, r.name AS actual_route
        FROM matatus AS m
        LEFT JOIN routes AS r ON r.id = m.route_id
    """).fetchall()

    for row in matatu_rows:
        canonical_name = canonical_route_name(row["route_name"])

        if canonical_name is not None:
            if row["actual_route"] != canonical_name:
                raise RuntimeError(
                    f"Matatu ID {row['id']} has an invalid route assignment."
                )


def migrate(database_path=None):
    database = os.path.abspath(database_path or DEFAULT_DATABASE)

    print("Database:", database)

    if not os.path.isfile(database):
        raise FileNotFoundError(
            f"Database does not exist: {database}"
        )

    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            connection.execute("BEGIN IMMEDIATE")

            ensure_required_schema(connection)

            historical_snapshot = snapshot_historical_references(
                connection
            )

            route_ids = ensure_routes_table(connection)

            ensure_route_columns(connection)

            assign_recognised_routes(connection, route_ids)

            ensure_stage_sequence_index(connection)

            verify_route_assignments(connection)

            verify_historical_references(
                connection,
                historical_snapshot,
            )

            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if violations:
                raise RuntimeError(
                    "Foreign-key violations detected: "
                    f"{[tuple(row) for row in violations]}."
                )

            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            if integrity != "ok":
                raise RuntimeError(
                    f"SQLite integrity check failed: {integrity}"
                )

            connection.commit()

            print("Route migration completed successfully.")
            print("Routes:", route_ids)
            print("Existing stage IDs and sequence numbers preserved.")
            print("Existing matatu IDs preserved.")
            print("Historical stage references preserved.")

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate legacy route records safely."
    )

    parser.add_argument(
        "--database",
        help="Explicit SQLite database path for migration.",
    )

    args = parser.parse_args()

    migrate(args.database)