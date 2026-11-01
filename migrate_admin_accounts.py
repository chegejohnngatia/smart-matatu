
import os
import sqlite3
from contextlib import closing

DATABASE = os.environ.get(
    "SMART_MATATU_DB",
    "smart_matatu.db"
)


def migrate(database=DATABASE):
    with closing(sqlite3.connect(database)) as connection:
        try:
            connection.execute("BEGIN IMMEDIATE")

            connection.execute("""
                CREATE TABLE IF NOT EXISTS admins (
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

            connection.commit()

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    migrate()
    print("Administrator accounts migration completed.")
