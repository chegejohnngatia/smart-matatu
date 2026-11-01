
import sqlite3
import os

DATABASE = os.environ.get("SMART_MATATU_DB", "smart_matatu.db")


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
                    CHECK (status IN ('pending', 'paid')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                paid_at TEXT,
                FOREIGN KEY (matatu_id)
                    REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id)
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
                FOREIGN KEY (matatu_id)
                    REFERENCES matatus(id),
                FOREIGN KEY (passenger_destination_id)
                    REFERENCES passenger_destinations(id)
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
