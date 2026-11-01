import os
import sqlite3

DATABASE = os.environ.get(
    "SMART_MATATU_DB",
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "smart_matatu.db"
    )
)


def migrate():
    connection = sqlite3.connect(DATABASE)

    try:
        connection.execute("BEGIN IMMEDIATE")

        columns = connection.execute(
            "PRAGMA table_info(passenger_destinations)"
        ).fetchall()

        if not columns:
            raise RuntimeError(
                "passenger_destinations table does not exist."
            )

        existing_columns = {
            column[1] for column in columns
        }

        if "access_token_hash" not in existing_columns:
            connection.execute("""
                ALTER TABLE passenger_destinations
                ADD COLUMN access_token_hash TEXT
            """)

        connection.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                one_unique_passenger_access_token
            ON passenger_destinations(access_token_hash)
            WHERE access_token_hash IS NOT NULL
        """)

        connection.commit()
        print("Passenger access-token migration completed.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
