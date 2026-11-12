
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
            "smart_matatu.db"
        )
    )
)

OLD_INDEX = "unique_stage_sequence_per_route"
NEW_INDEX = "unique_active_stage_sequence_per_route"

HISTORICAL_REFERENCES = {
    "passenger_destinations": (
        "destination_stage_id",
    ),
    "destination_change_requests": (
        "current_destination_stage_id",
        "requested_destination_stage_id",
    ),
}


def get_columns(connection, table):
    return {
        row["name"]: row
        for row in connection.execute(
            f"PRAGMA table_info({table})"
        ).fetchall()
    }


def get_index(connection, index_name):
    return connection.execute("""
        SELECT name, tbl_name, sql
        FROM sqlite_master
        WHERE type = 'index'
        AND name = ?
    """, (index_name,)).fetchone()


def validate_index(
    connection,
    index_name,
    expected_partial
):
    existing = get_index(connection, index_name)

    if existing is None:
        return False

    if existing["tbl_name"] != "stages":
        raise RuntimeError(
            f"{index_name} belongs to an unexpected table."
        )

    details = connection.execute(
        "PRAGMA index_list(stages)"
    ).fetchall()

    matching = next(
        (
            item for item in details
            if item["name"] == index_name
        ),
        None
    )

    if (
        matching is None
        or matching["unique"] != 1
        or matching["partial"] != int(expected_partial)
    ):
        raise RuntimeError(
            f"{index_name} has an unexpected uniqueness definition."
        )

    columns = [
        row["name"]
        for row in connection.execute(
            f"PRAGMA index_info('{index_name}')"
        ).fetchall()
    ]

    if columns != ["route_id", "sequence_number"]:
        raise RuntimeError(
            f"{index_name} has unexpected columns: {columns}"
        )

    if expected_partial:
        sql = (existing["sql"] or "").lower()
        normalized = re.sub(r"\s+", "", sql)
        normalized = normalized.replace('"', "").replace("`", "")

        if "whereis_archived=0" not in normalized:
            raise RuntimeError(
                f"{index_name} does not have the expected "
                "is_archived = 0 condition."
            )

    return True


def capture_historical_references(connection):
    references = {}

    for table, columns in HISTORICAL_REFERENCES.items():
        for column in columns:
            rows = connection.execute(
                f"""
                SELECT {column}, COUNT(*) AS reference_count
                FROM {table}
                WHERE {column} IS NOT NULL
                GROUP BY {column}
                ORDER BY {column}
                """
            ).fetchall()

            references[(table, column)] = [
                (row[column], row["reference_count"])
                for row in rows
            ]

    return references


def validate_reference_schema(connection):
    tables = {
        row["name"]
        for row in connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """).fetchall()
    }

    for table, required_columns in HISTORICAL_REFERENCES.items():
        if table not in tables:
            raise RuntimeError(
                f"Historical reference table is missing: {table}"
            )

        actual_columns = get_columns(connection, table)

        missing = set(required_columns) - set(actual_columns)

        if missing:
            raise RuntimeError(
                f"Missing historical reference columns "
                f"in {table}: {sorted(missing)}"
            )


def validate_stage_schema(connection):
    tables = {
        row["name"]
        for row in connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
        """).fetchall()
    }

    if "stages" not in tables:
        raise RuntimeError("Required stages table is missing.")

    columns = get_columns(connection, "stages")

    required = {
        "id",
        "name",
        "route_id",
        "route_name",
        "sequence_number",
        "latitude",
        "longitude",
    }

    missing = required - set(columns)

    if missing:
        raise RuntimeError(
            f"Unexpected stages schema. Missing: {sorted(missing)}"
        )


def validate_archive_columns(connection):
    columns = get_columns(connection, "stages")

    archived = columns["is_archived"]

    if (
        archived["type"].upper() != "INTEGER"
        or archived["notnull"] != 1
        or str(archived["dflt_value"]) != "0"
    ):
        raise RuntimeError(
            "Existing is_archived column has an unexpected definition."
        )

    archived_at = columns["archived_at"]

    if archived_at["type"].upper() != "TEXT":
        raise RuntimeError(
            "Existing archived_at column has an unexpected type."
        )

    table_sql = connection.execute("""
        SELECT sql
        FROM sqlite_master
        WHERE type = 'table'
        AND name = 'stages'
    """).fetchone()["sql"]

    normalized = re.sub(r"\s+", "", table_sql.lower())

    if (
        "check(is_archivedin(0,1))" not in normalized
        and "check(is_archivedin(0,1)" not in normalized
    ):
        raise RuntimeError(
            "Could not verify the is_archived CHECK constraint."
        )


def migrate(database_path=None):
    database = os.path.abspath(
        database_path or DEFAULT_DATABASE
    )

    print("Database:", database)

    if not os.path.isfile(database):
        raise FileNotFoundError(
            f"Database does not exist: {database}"
        )

    with closing(
        sqlite3.connect(database, timeout=30)
    ) as connection:

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            connection.execute("BEGIN IMMEDIATE")

            validate_stage_schema(connection)
            validate_reference_schema(connection)

            references_before = (
                capture_historical_references(connection)
            )

            # Add archival columns only when missing.
            columns = get_columns(connection, "stages")

            if "is_archived" not in columns:
                connection.execute("""
                    ALTER TABLE stages
                    ADD COLUMN is_archived INTEGER NOT NULL
                    DEFAULT 0
                    CHECK (is_archived IN (0, 1))
                """)

            columns = get_columns(connection, "stages")

            if "archived_at" not in columns:
                connection.execute("""
                    ALTER TABLE stages
                    ADD COLUMN archived_at TEXT
                """)

            validate_archive_columns(connection)

            # Validate existing indexes before changing anything.
            old_exists = validate_index(
                connection,
                OLD_INDEX,
                expected_partial=False
            )

            new_exists = validate_index(
                connection,
                NEW_INDEX,
                expected_partial=True
            )

            # Archived values must be valid.
            invalid_archived = connection.execute("""
                SELECT id, is_archived
                FROM stages
                WHERE is_archived NOT IN (0, 1)
                OR is_archived IS NULL
            """).fetchall()

            if invalid_archived:
                raise RuntimeError(
                    "Invalid archival values detected: "
                    f"{[tuple(row) for row in invalid_archived]}"
                )

            # Verify active stages do not have duplicate positions.
            duplicates = connection.execute("""
                SELECT route_id, sequence_number, COUNT(*) AS total
                FROM stages
                WHERE is_archived = 0
                GROUP BY route_id, sequence_number
                HAVING COUNT(*) > 1
            """).fetchall()

            if duplicates:
                raise RuntimeError(
                    "Duplicate active stage positions detected: "
                    f"{[tuple(row) for row in duplicates]}"
                )

            # Replace the old index only after validating it.
            if old_exists:
                connection.execute(
                    f"DROP INDEX {OLD_INDEX}"
                )

            if not new_exists:
                connection.execute("""
                    CREATE UNIQUE INDEX
                    unique_active_stage_sequence_per_route
                    ON stages (route_id, sequence_number)
                    WHERE is_archived = 0
                """)

            # Verify the final index.
            if not validate_index(
                connection,
                NEW_INDEX,
                expected_partial=True
            ):
                raise RuntimeError(
                    "The new active-stage index could not be verified."
                )

            if get_index(connection, OLD_INDEX) is not None:
                raise RuntimeError(
                    "The old full unique index still exists."
                )

            # Verify historical passenger references are unchanged.
            references_after = (
                capture_historical_references(connection)
            )

            if references_before != references_after:
                raise RuntimeError(
                    "Historical passenger-stage references changed."
                )

            # Verify foreign-key integrity.
            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if violations:
                raise RuntimeError(
                    "Foreign-key violations detected: "
                    f"{[tuple(row) for row in violations]}"
                )

            # Verify SQLite database integrity.
            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            if integrity != "ok":
                raise RuntimeError(
                    f"SQLite integrity check failed: {integrity}"
                )

            connection.commit()

            print("Stage management migration completed successfully.")
            print("Archival columns verified.")
            print("Old full unique index replaced.")
            print("New active-stage partial unique index verified.")
            print("Historical references preserved.")
            print("Foreign-key check: passed.")
            print("Integrity check:", integrity)

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migrate Smart Matatu stage management."
    )

    parser.add_argument(
        "--database",
        help="Explicit SQLite database path."
    )

    args = parser.parse_args()

    migrate(args.database)
