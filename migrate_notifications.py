
import os
import sqlite3

DATABASE_PATH = os.path.abspath(
    os.environ.get(
        "SMART_MATATU_DB",
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "smart_matatu.db"
        )
    )
)


def migrate():
    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("BEGIN IMMEDIATE")

        existing_table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'passenger_notifications'
            """
        ).fetchone()

        if existing_table:
            raise RuntimeError(
                "passenger_notifications already exists. "
                "Inspect its schema before migrating."
            )

        connection.execute(
            """
            CREATE TABLE passenger_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                balance_id INTEGER,
                notification_type TEXT NOT NULL
                    CHECK (
                        notification_type IN (
                            'payment_confirmation',
                            'payment_reminder'
                        )
                    ),
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0
                    CHECK (is_read IN (0, 1)),
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX
            one_payment_confirmation_notification_per_balance
            ON passenger_notifications(balance_id)
            WHERE notification_type = 'payment_confirmation'
              AND balance_id IS NOT NULL
            """
        )

        connection.execute(
            """
            CREATE UNIQUE INDEX
            one_payment_reminder_notification_per_balance
            ON passenger_notifications(balance_id)
            WHERE notification_type = 'payment_reminder'
              AND balance_id IS NOT NULL
            """
        )

        connection.commit()
        print("Migration completed successfully.")
        print("Created passenger_notifications and its indexes.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate()
