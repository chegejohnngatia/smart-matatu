
import sqlite3
import os

DATABASE = os.path.abspath(
    os.environ.get(
        "SMART_MATATU_DB",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "smart_matatu.db")
    )
)


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row

    # Enforce foreign-key constraints on every connection.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def init_db():
    connection = get_db_connection()

    try:
        # Matatus
        connection.execute("""
            CREATE TABLE IF NOT EXISTS matatus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registration_number TEXT NOT NULL,
                route_name TEXT NOT NULL
            )
        """)

        # Conductor accounts
        connection.execute("""
            CREATE TABLE IF NOT EXISTS conductors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK (is_active IN (0, 1)),
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                passport_photo TEXT
            )
        """)

        # Safely migrate conductor accounts.
        # Preserve existing conductor records and historical references.
        columns = connection.execute(
            "PRAGMA table_info(conductors)"
        ).fetchall()

        column_names = {column["name"] for column in columns}

        if "deleted_at" not in column_names:
            connection.execute("""
                ALTER TABLE conductors
                ADD COLUMN deleted_at TEXT
            """)

        # Conductor-to-matatu assignments
        connection.execute("""
            CREATE TABLE IF NOT EXISTS matatu_assignments (
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
            )
        """)

        # A conductor can have only one active matatu assignment.
        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                one_active_assignment_per_conductor
            ON matatu_assignments (conductor_id)
            WHERE ended_at IS NULL
        """)

        # Route stages
        connection.execute("""
            CREATE TABLE IF NOT EXISTS stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                route_name TEXT NOT NULL,
                name TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                sequence_number INTEGER NOT NULL
            )
        """)

        # Permanent passenger identities
        connection.execute("""
            CREATE TABLE IF NOT EXISTS passengers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                passenger_code TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Passenger destination records (journeys)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS passenger_destinations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_token TEXT NOT NULL,
                destination_stage_id INTEGER NOT NULL,
                status TEXT DEFAULT 'waiting'
            )
        """)

        # Safely migrate existing databases.
        # Never recreate or delete the existing destination table.
        columns = connection.execute(
            "PRAGMA table_info(passenger_destinations)"
        ).fetchall()

        column_names = {column["name"] for column in columns}

        if "passenger_id" not in column_names:
            connection.execute("""
                ALTER TABLE passenger_destinations
                ADD COLUMN passenger_id INTEGER
                REFERENCES passengers(id)
            """)

        # Passenger destination-change requests.
        # Requests do not change the active journey destination
        # until the conductor approves them.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS destination_change_requests (
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
                resolved_at TEXT,
                FOREIGN KEY (matatu_id)
                    REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id),
                FOREIGN KEY (current_destination_stage_id)
                    REFERENCES stages(id),
                FOREIGN KEY (requested_destination_stage_id)
                    REFERENCES stages(id)
            )
        """)

        # A journey may have only one pending request at a time.
        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                one_pending_destination_request_per_journey
            ON destination_change_requests (passenger_destination_id)
            WHERE status = 'pending'
        """)

        # Matatu GPS locations.
        # Keep this definition unchanged for now.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS matatu_locations (
                matatu_id INTEGER PRIMARY KEY,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                current_stage_sequence INTEGER DEFAULT 0
            )
        """)

        # Passenger balances owed by the conductor.
        # Paid records are retained for history.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS passenger_balances (
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
                paid_by_conductor_id INTEGER,
                FOREIGN KEY (matatu_id)
                    REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id),
                FOREIGN KEY (paid_by_conductor_id)
                    REFERENCES conductors(id)
            )
        """)

        # Speed up queries for active balances belonging to a matatu.
        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_passenger_balances_matatu_status
            ON passenger_balances (matatu_id, status)
        """)

        # Emergency alerts for passenger issues and proximity warnings.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS emergency_alerts (
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
                acknowledged_by_conductor_id INTEGER,
                FOREIGN KEY (matatu_id)
                    REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id),
                FOREIGN KEY (acknowledged_by_conductor_id)
                    REFERENCES conductors(id)
            )
        """)

        # Prevent duplicate proximity alerts for the same journey.
        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                one_proximity_alert_per_journey
            ON emergency_alerts (passenger_destination_id)
            WHERE alert_type = 'proximity'
        """)

        # Speed up retrieval of alerts for a matatu.
        connection.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_emergency_alerts_matatu_status
            ON emergency_alerts (matatu_id, status)
        """)

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
