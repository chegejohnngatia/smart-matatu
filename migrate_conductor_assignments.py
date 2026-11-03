
import os
import sqlite3
from contextlib import closing

DATABASE = os.path.abspath(
    os.environ.get(
        "SMART_MATATU_DB",
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "smart_matatu.db"
        )
    )
)


def migrate():
    with closing(sqlite3.connect(DATABASE)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS conductors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1
                        CHECK (is_active IN (0, 1)),
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
            """)

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

            # Allow multiple active conductors on the same matatu.
            # Remove the previous restriction if it exists.
            connection.execute("""
                DROP INDEX IF EXISTS
                    one_active_assignment_per_matatu
            """)

            connection.commit()

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    migrate()
    print("Conductor assignment migration completed.")
