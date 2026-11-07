import os
import sqlite3

DATABASE = os.getenv("DATABASE_PATH", "smart_matatu.db")


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatus (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_number TEXT NOT NULL,
            route_name TEXT NOT NULL
        )
    """)

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

    connection.execute("""
        CREATE TABLE IF NOT EXISTS passenger_destinations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matatu_id INTEGER NOT NULL,
            passenger_token TEXT NOT NULL,
            destination_stage_id INTEGER NOT NULL,
            status TEXT DEFAULT 'waiting'
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_locations (
            matatu_id INTEGER PRIMARY KEY,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            current_stage_sequence INTEGER DEFAULT 0,
            speed REAL DEFAULT 20,
            accuracy REAL,
            last_updated_at TEXT,
            location_source TEXT DEFAULT 'simulation'
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS matatu_location_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matatu_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            speed REAL,
            accuracy REAL,
            source TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            received_at TEXT NOT NULL
        )
    """)

    location_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(matatu_locations)")
    }
    if "speed" not in location_columns:
        connection.execute(
            "ALTER TABLE matatu_locations ADD COLUMN speed REAL DEFAULT 20"
        )
    for column, definition in (
        ("accuracy", "REAL"),
        ("last_updated_at", "TEXT"),
        ("location_source", "TEXT DEFAULT 'simulation'"),
    ):
        if column not in location_columns:
            connection.execute(
                f"ALTER TABLE matatu_locations ADD COLUMN {column} {definition}"
            )

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_matatu_location_history_matatu_recorded
        ON matatu_location_history (matatu_id, recorded_at)
    """)

    connection.commit()
    connection.close()