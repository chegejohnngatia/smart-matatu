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

            columns = connection.execute(
                "PRAGMA table_info(conductors)"
            ).fetchall()

            existing_columns = {
                column[1] for column in columns
            }

            if "passport_photo" not in existing_columns:
                connection.execute("""
                    ALTER TABLE conductors
                    ADD COLUMN passport_photo TEXT
                """)

            connection.commit()

        except Exception:
            connection.rollback()
            raise


if __name__ == "__main__":
    migrate()
    print("Conductor passport photo migration completed.")