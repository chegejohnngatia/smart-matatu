import argparse
import os
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


def get_columns(connection, table):
    return {
        row["name"]
        for row in connection.execute(
            f'PRAGMA table_info("{table}")'
        )
    }


def ensure_matatu_columns(connection):
    columns = get_columns(connection, "matatus")

    if "is_archived" not in columns:
        connection.execute("""
            ALTER TABLE matatus
            ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0
                CHECK (is_archived IN (0, 1))
        """)

    columns = get_columns(connection, "matatus")

    if "archived_at" not in columns:
        connection.execute("""
            ALTER TABLE matatus
            ADD COLUMN archived_at TEXT
        """)


def ensure_registry(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_registration_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_registration_number TEXT NOT NULL UNIQUE,
            registration_number TEXT NOT NULL,
            original_matatu_id INTEGER NOT NULL,
            registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            permanently_deleted_at TEXT
        )
    """)

    required = {
        "id",
        "normalized_registration_number",
        "registration_number",
        "original_matatu_id",
        "registered_at",
        "permanently_deleted_at",
    }

    actual = get_columns(
        connection,
        "matatu_registration_registry",
    )

    if not required.issubset(actual):
        raise RuntimeError(
            "Registration registry has an unexpected schema."
        )


def rebuild_registry_if_required(connection):
    """
    Enforce the registry uniqueness contract while preserving
    all existing records and the AUTOINCREMENT sequence.

    normalized_registration_number must be globally unique.
    original_matatu_id must not be unique.
    """

    table = "matatu_registration_registry"

    def has_single_column_unique_index(column_name):
        indexes = connection.execute(
            f'PRAGMA index_list("{table}")'
        ).fetchall()

        for index in indexes:
            if not index["unique"]:
                continue

            columns = [
                row["name"]
                for row in connection.execute(
                    f'PRAGMA index_info("{index["name"]}")'
                )
            ]

            if columns == [column_name]:
                return True

        return False

    normalized_is_unique = has_single_column_unique_index(
        "normalized_registration_number"
    )

    original_id_is_unique = has_single_column_unique_index(
        "original_matatu_id"
    )

    if normalized_is_unique and not original_id_is_unique:
        return

    old_sequence = connection.execute("""
        SELECT seq
        FROM sqlite_sequence
        WHERE name = 'matatu_registration_registry'
    """).fetchone()

    temporary_table = "matatu_registration_registry_rebuild"

    existing_temp = connection.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
    """, (temporary_table,)).fetchone()

    if existing_temp:
        raise RuntimeError(
            "Unexpected temporary registry table exists. "
            "Inspect the database before proceeding."
        )

    connection.execute(f"""
        CREATE TABLE {temporary_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_registration_number TEXT NOT NULL UNIQUE,
            registration_number TEXT NOT NULL,
            original_matatu_id INTEGER NOT NULL,
            registered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            permanently_deleted_at TEXT
        )
    """)

    connection.execute(f"""
        INSERT INTO {temporary_table} (
            id,
            normalized_registration_number,
            registration_number,
            original_matatu_id,
            registered_at,
            permanently_deleted_at
        )
        SELECT
            id,
            normalized_registration_number,
            registration_number,
            original_matatu_id,
            registered_at,
            permanently_deleted_at
        FROM matatu_registration_registry
        ORDER BY id
    """)

    connection.execute("""
        DROP TABLE matatu_registration_registry
    """)

    connection.execute(f"""
        ALTER TABLE {temporary_table}
        RENAME TO matatu_registration_registry
    """)

    if old_sequence is not None:
        current_sequence = connection.execute("""
            SELECT seq
            FROM sqlite_sequence
            WHERE name = 'matatu_registration_registry'
        """).fetchone()

        if current_sequence is None:
            connection.execute("""
                INSERT INTO sqlite_sequence (name, seq)
                VALUES ('matatu_registration_registry', ?)
            """, (old_sequence["seq"],))

        elif current_sequence["seq"] < old_sequence["seq"]:
            connection.execute("""
                UPDATE sqlite_sequence
                SET seq = ?
                WHERE name = 'matatu_registration_registry'
            """, (old_sequence["seq"],))

    if not has_single_column_unique_index(
        "normalized_registration_number"
    ):
        raise RuntimeError(
            "Registry normalized registration uniqueness "
            "could not be established."
        )

    if has_single_column_unique_index("original_matatu_id"):
        raise RuntimeError(
            "Registry original_matatu_id must not be unique."
        )


def ensure_registration_history(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_registration_history (
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

    required = {
        "id",
        "matatu_id",
        "registration_number",
        "normalized_registration_number",
        "effective_start",
        "effective_end",
    }

    actual = get_columns(
        connection,
        "matatu_registration_history",
    )

    if not required.issubset(actual):
        raise RuntimeError(
            "Registration history has an unexpected schema."
        )


def backfill_registry(connection):
    """
    Reserve all current and historical Matatu registrations.

    Preserve existing registry ownership and timestamps.
    Reject conflicting historical ownership.
    """

    reservations = {}
    current_matatus = {}

    def add_reservation(matatu_id, registration, registered_at=None,
                        is_current=False):
        if not isinstance(registration, str) or not registration.strip():
            raise RuntimeError(
                f"Matatu {matatu_id} has an invalid registration."
            )

        normalized = registration.strip().upper()

        if not normalized:
            raise RuntimeError(
                f"Matatu {matatu_id} has an empty registration."
            )

        existing = reservations.get(normalized)

        if existing is not None:
            if existing["matatu_id"] != matatu_id:
                raise RuntimeError(
                    f"Registration {normalized} conflicts between "
                    f"matatus {existing['matatu_id']} and {matatu_id}."
                )

            if registered_at and (
                existing["registered_at"] is None
                or registered_at < existing["registered_at"]
            ):
                existing["registered_at"] = registered_at

            existing["is_current"] = (
                existing["is_current"] or is_current
            )
            return

        reservations[normalized] = {
            "matatu_id": matatu_id,
            "registration": registration.strip(),
            "registered_at": registered_at,
            "is_current": is_current,
        }

    # Load historical registrations first so their original dates
    # are retained when creating missing registry reservations.
    history_rows = connection.execute("""
        SELECT
            id,
            matatu_id,
            registration_number,
            normalized_registration_number,
            effective_start
        FROM matatu_registration_history
        ORDER BY effective_start, id
    """).fetchall()

    for row in history_rows:
        registration = row["registration_number"]

        if not isinstance(registration, str) or not registration.strip():
            raise RuntimeError(
                f"Matatu {row['matatu_id']} has an invalid "
                "historical registration."
            )

        normalized = registration.strip().upper()

        if normalized != row["normalized_registration_number"]:
            raise RuntimeError(
                f"Matatu {row['matatu_id']} has an invalid "
                "normalized registration."
            )

        add_reservation(
            row["matatu_id"],
            registration,
            row["effective_start"],
        )

    # Add current registrations and detect ownership conflicts.
    current_rows = connection.execute("""
        SELECT id, registration_number
        FROM matatus
        ORDER BY id
    """).fetchall()

    for row in current_rows:
        current_matatus[row["id"]] = True

        add_reservation(
            row["id"],
            row["registration_number"],
            is_current=True,
        )

    # Validate existing reservations before inserting missing ones.
    for normalized, reservation in reservations.items():
        existing = connection.execute("""
            SELECT
                original_matatu_id,
                permanently_deleted_at
            FROM matatu_registration_registry
            WHERE normalized_registration_number = ?
        """, (normalized,)).fetchone()

        if existing:
            if existing["original_matatu_id"] != reservation["matatu_id"]:
                raise RuntimeError(
                    f"Registration {normalized} conflicts "
                    "with an existing registry owner."
                )

            if (
                existing["permanently_deleted_at"] is not None
                and reservation["is_current"]
            ):
                raise RuntimeError(
                    f"Registration {normalized} is permanently deleted "
                    "but is still assigned to an existing Matatu."
                )

            # Never overwrite an existing reservation or its timestamp.
            continue

        if reservation["registered_at"] is not None:
            connection.execute("""
                INSERT INTO matatu_registration_registry (
                    normalized_registration_number,
                    registration_number,
                    original_matatu_id,
                    registered_at
                )
                VALUES (?, ?, ?, ?)
            """, (
                normalized,
                reservation["registration"],
                reservation["matatu_id"],
                reservation["registered_at"],
            ))
        else:
            connection.execute("""
                INSERT INTO matatu_registration_registry (
                    normalized_registration_number,
                    registration_number,
                    original_matatu_id
                )
                VALUES (?, ?, ?)
            """, (
                normalized,
                reservation["registration"],
                reservation["matatu_id"],
            ))


def backfill_registration_history(connection):
    """
    Backfill initial registration history and validate existing history.

    Existing Matatus use their registry registered_at timestamp because
    the Matatus table has no reliable creation timestamp.

    Existing history is never silently corrected or deleted.

    Registration intervals use half-open boundaries: an old entry may
    end at exactly the timestamp when the next entry starts.
    Gaps between entries are permitted.
    """

    from datetime import datetime

    def normalize_registration(value, context):
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"{context}: registration number is empty or invalid."
            )

        return value.strip().upper()

    def parse_timestamp(value, context):
        if not isinstance(value, str) or not value.strip():
            raise RuntimeError(
                f"{context}: timestamp is empty or invalid."
            )

        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise RuntimeError(
                f"{context}: invalid timestamp {value!r}."
            ) from exc

        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            raise RuntimeError(
                f"{context}: timezone-aware timestamps are not supported. "
                "Use SQLite-compatible timezone-naive timestamps."
            )

        canonical_seconds = parsed.isoformat(
            sep=" ",
            timespec="seconds"
        )
        canonical_microseconds = parsed.isoformat(
            sep=" ",
            timespec="microseconds"
        )

        if value not in (
            canonical_seconds,
            canonical_microseconds
        ):
            raise RuntimeError(
                f"{context}: timestamp {value!r} is not in the "
                "supported SQLite-compatible format "
                "YYYY-MM-DD HH:MM:SS[.ffffff]."
            )

        return parsed

    matatus = connection.execute("""
        SELECT id, registration_number
        FROM matatus
        ORDER BY id
    """).fetchall()

    for matatu in matatus:
        matatu_id = matatu["id"]
        registration_number = matatu["registration_number"]

        normalized = normalize_registration(
            registration_number,
            f"Matatu {matatu_id}"
        )

        registry = connection.execute("""
            SELECT
                normalized_registration_number,
                original_matatu_id,
                registered_at,
                permanently_deleted_at
            FROM matatu_registration_registry
            WHERE normalized_registration_number = ?
        """, (normalized,)).fetchone()

        if registry is None:
            raise RuntimeError(
                f"Matatu {matatu_id} has no registry reservation "
                f"for registration {normalized}."
            )

        if registry["original_matatu_id"] != matatu_id:
            raise RuntimeError(
                f"Registration {normalized} belongs to a different "
                f"Matatu than {matatu_id}."
            )

        if registry["permanently_deleted_at"] is not None:
            raise RuntimeError(
                f"Current registration {normalized} for Matatu "
                f"{matatu_id} is marked permanently deleted."
            )

        history_rows = connection.execute("""
            SELECT
                id,
                registration_number,
                normalized_registration_number,
                effective_start,
                effective_end
            FROM matatu_registration_history
            WHERE matatu_id = ?
        """, (matatu_id,)).fetchall()

        if not history_rows:
            registered_at = parse_timestamp(
                registry["registered_at"],
                f"Matatu {matatu_id} registry registered_at"
            )

            connection.execute("""
                INSERT INTO matatu_registration_history (
                    matatu_id,
                    registration_number,
                    normalized_registration_number,
                    effective_start,
                    effective_end
                )
                VALUES (?, ?, ?, ?, NULL)
            """, (
                matatu_id,
                registration_number,
                normalized,
                registered_at.isoformat(sep=" ")
            ))

            continue

        validated_history = []

        for history in history_rows:
            history_id = history["id"]
            context = (
                f"Matatu {matatu_id}, history entry {history_id}"
            )

            history_normalized = normalize_registration(
                history["registration_number"],
                context
            )

            if (
                history["normalized_registration_number"]
                != history_normalized
            ):
                raise RuntimeError(
                    f"{context}: stored normalized registration "
                    "does not match registration_number."
                )

            effective_start = parse_timestamp(
                history["effective_start"],
                f"{context} effective_start"
            )

            effective_end = None

            if history["effective_end"] is not None:
                effective_end = parse_timestamp(
                    history["effective_end"],
                    f"{context} effective_end"
                )

                if effective_end < effective_start:
                    raise RuntimeError(
                        f"{context}: effective_end is earlier "
                        "than effective_start."
                    )

            validated_history.append({
                "id": history_id,
                "registration_number": history["registration_number"],
                "normalized_registration_number": history_normalized,
                "effective_start": effective_start,
                "effective_end": effective_end,
            })

        validated_history.sort(
            key=lambda item: (
                item["effective_start"],
                item["id"]
            )
        )

        open_rows = [
            history
            for history in validated_history
            if history["effective_end"] is None
        ]

        if len(open_rows) == 0:
            raise RuntimeError(
                f"Matatu {matatu_id} has historical entries but "
                "no open current entry. Manual inspection is required."
            )

        if len(open_rows) > 1:
            raise RuntimeError(
                f"Matatu {matatu_id} has multiple open history "
                "entries. Manual inspection is required."
            )

        for index, current in enumerate(validated_history):
            if index == 0:
                continue

            previous = validated_history[index - 1]

            if previous["effective_end"] is None:
                raise RuntimeError(
                    f"Matatu {matatu_id} has an open history interval "
                    "before a later entry."
                )

            if (
                current["effective_start"]
                < previous["effective_end"]
            ):
                raise RuntimeError(
                    f"Matatu {matatu_id} has overlapping registration "
                    f"history entries {previous['id']} and "
                    f"{current['id']}. Manual inspection is required."
                )

        current_history = open_rows[0]

        if (
            current_history["registration_number"]
            != registration_number
            or current_history["normalized_registration_number"]
            != normalized
        ):
            raise RuntimeError(
                f"Matatu {matatu_id} has an open history entry "
                "that does not match its current registration. "
                "Manual inspection is required."
            )

def ensure_registration_history_indexes(connection):
    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_registration_history_matatu
        ON matatu_registration_history(matatu_id)
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_registration_history_normalized
        ON matatu_registration_history(
            normalized_registration_number
        )
    """)

    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_registration_history_unique_entry
        ON matatu_registration_history(
            matatu_id,
            normalized_registration_number,
            effective_start
        )
    """)

    connection.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_registration_history_one_current
        ON matatu_registration_history(matatu_id)
        WHERE effective_end IS NULL
    """)
def ensure_archive_tables(connection):
    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_payment_audit_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_number TEXT NOT NULL,
            source_record_id INTEGER NOT NULL UNIQUE,
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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_emergency_audit_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_number TEXT NOT NULL,
            source_record_id INTEGER NOT NULL UNIQUE,
            alert_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT,
            acknowledged_at TEXT,
            conductor_attribution_present INTEGER NOT NULL
                CHECK (conductor_attribution_present IN (0, 1)),
            archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_assignment_audit_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_assignment_id INTEGER NOT NULL UNIQUE,
            conductor_id INTEGER NOT NULL,
            conductor_name TEXT NOT NULL,
            registration_number TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            ended_at TEXT,
            archived_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    archive_schemas = {
        "matatu_payment_audit_archive": {
            "columns": {
                "id", "registration_number", "source_record_id",
                "amount", "status", "created_at", "paid_at",
                "confirmed_at", "conductor_attribution_present",
                "archived_at",
            },
            "source_id": "source_record_id",
        },
        "matatu_emergency_audit_archive": {
            "columns": {
                "id", "registration_number", "source_record_id",
                "alert_type", "status", "created_at",
                "acknowledged_at", "conductor_attribution_present",
                "archived_at",
            },
            "source_id": "source_record_id",
        },
        "matatu_assignment_audit_archive": {
            "columns": {
                "id", "source_assignment_id", "conductor_id",
                "conductor_name", "registration_number",
                "assigned_at", "ended_at", "archived_at",
            },
            "source_id": "source_assignment_id",
        },
    }

    for table_name, schema in archive_schemas.items():
        actual_columns = get_columns(connection, table_name)

        if actual_columns != schema["columns"]:
            raise RuntimeError(
                f"Unexpected {table_name} schema. "
                f"Expected: {sorted(schema['columns'])}. "
                f"Found: {sorted(actual_columns)}."
            )

        indexes = connection.execute(
            f'PRAGMA index_list("{table_name}")'
        ).fetchall()

        source_id = schema["source_id"]
        has_unique_source_id = False

        for index in indexes:
            if not index["unique"]:
                continue

            index_name = index["name"].replace('"', '""')
            indexed_columns = [
                row["name"]
                for row in connection.execute(
                    f'PRAGMA index_info("{index_name}")'
                )
            ]

            if indexed_columns == [source_id]:
                has_unique_source_id = True
                break

        if not has_unique_source_id:
            raise RuntimeError(
                f"{table_name} source IDs must be unique."
            )

        foreign_keys = connection.execute(
            f'PRAGMA foreign_key_list("{table_name}")'
        ).fetchall()

        if foreign_keys:
            raise RuntimeError(
                f"{table_name} must not reference operational tables."
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

    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            connection.execute("BEGIN IMMEDIATE")

            tables = {
                row["name"]
                for row in connection.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                """)
            }

            if "matatus" not in tables:
                raise RuntimeError(
                    "The matatus table does not exist."
                )

            ensure_matatu_columns(connection)
            ensure_registry(connection)

            rebuild_registry_if_required(connection)

            ensure_registration_history(connection)
            ensure_archive_tables(connection)

            backfill_registry(connection)
            backfill_registration_history(connection)

            ensure_registration_history_indexes(connection)

            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()

            if violations:
                raise RuntimeError(
                    f"Foreign-key violations: {len(violations)}"
                )

            integrity = connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            if integrity != "ok":
                raise RuntimeError(
                    f"Integrity check failed: {integrity}"
                )

            connection.commit()

            print("Matatu lifecycle migration completed.")
            print("Existing matatu IDs preserved.")
            print("Registration reservations preserved.")
            print("Registry uniqueness updated.")
            print("Registration history backfilled.")
            print("Audit archive tables verified.")
            print("Database integrity verified.")

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialize Matatu Lifecycle database support."
    )

    parser.add_argument(
        "--database",
        help="Explicit SQLite database path.",
    )

    args = parser.parse_args()
    migrate(args.database)
