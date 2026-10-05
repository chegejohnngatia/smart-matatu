import sqlite3

DATABASE = "smart_matatu.db"


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
            current_stage_sequence INTEGER DEFAULT 0
        )
    """)

    connection.commit()
    connection.close()