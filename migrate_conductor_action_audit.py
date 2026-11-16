
import os
import sqlite3


DATABASE = os.path.abspath(
    os.environ.get(
        "SMART_MATATU_DB",
        os.path.join(os.path.dirname(__file__), "smart_matatu.db")
    )
)


def migrate():
    print("Database:", DATABASE)

    if not os.path.exists(DATABASE):
        raise FileNotFoundError(
            f"Database does not exist: {DATABASE}"
        )

    connection = sqlite3.connect(DATABASE)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        connection.execute("BEGIN IMMEDIATE")

        required_tables = (
            "conductors",
            "passenger_balances",
            "emergency_alerts",
        )

        existing_tables = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            )
        }

        for table in required_tables:
            if table not in existing_tables:
                raise RuntimeError(
                    f"Required table is missing: {table}"
                )

        # Add the payment audit column if it does not exist.
        balance_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(passenger_balances)"
            )
        }

        if "paid_by_conductor_id" not in balance_columns:
            connection.execute(
                """
                ALTER TABLE passenger_balances
                ADD COLUMN paid_by_conductor_id INTEGER
                REFERENCES conductors(id)
                """
            )
            print("Added passenger_balances.paid_by_conductor_id")
        else:
            print("Payment audit column already exists.")

        # Add the emergency acknowledgement audit column.
        alert_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(emergency_alerts)"
            )
        }

        if "acknowledged_by_conductor_id" not in alert_columns:
            connection.execute(
                """
                ALTER TABLE emergency_alerts
                ADD COLUMN acknowledged_by_conductor_id INTEGER
                REFERENCES conductors(id)
                """
            )
            print(
                "Added emergency_alerts.acknowledged_by_conductor_id"
            )
        else:
            print("Emergency audit column already exists.")

        # Validate foreign-key integrity before committing.
        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(
                f"Foreign-key violations detected: {violations}"
            )

        connection.commit()
        print("Migration completed successfully.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
