import os
import sqlite3
from pathlib import Path
from urllib.parse import quote


def inspect_database(database_path):
    database_path = Path(database_path).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found: {database_path}"
        )

    print(f"DATABASE PATH: {database_path}")

    # Open the database in read-only mode.
    connection = sqlite3.connect(
        database_path.as_uri() + "?mode=ro",
        uri=True
    )

    try:
        connection.row_factory = sqlite3.Row

        # 1. List all tables.
        print("\nDATABASE TABLES")
        print("================")

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """
        ).fetchall()

        table_names = [table["name"] for table in tables]

        for name in table_names:
            print(f"- {name}")

        # 2. Inspect conductor-related tables.
        for table_name in ("conductors", "matatu_assignments"):
            print(f"\n{table_name.upper()} COLUMNS")
            print("=" * (len(table_name) + 8))

            if table_name not in table_names:
                print("- Table not found")
                continue

            columns = connection.execute(
                f"PRAGMA table_info({table_name})"
            ).fetchall()

            for column in columns:
                print(
                    f"- {column['name']}: {column['type']} "
                    f"| NOT NULL: {column['notnull']} "
                    f"| PRIMARY KEY: {column['pk']}"
                )

        # 3. Inspect indexes on important tables.
        for table_name in ("conductors", "matatu_assignments"):
            print(f"\n{table_name.upper()} INDEXES")
            print("=" * (len(table_name) + 8))

            if table_name not in table_names:
                print("- Table not found")
                continue

            indexes = connection.execute(
                f"PRAGMA index_list({table_name})"
            ).fetchall()

            for index in indexes:
                print(f"\nIndex: {index['name']}")
                print(f"Unique: {bool(index['unique'])}")

                details = connection.execute(
                    f"PRAGMA index_info('{index['name']}')"
                ).fetchall()

                print(
                    "Columns:",
                    [column["name"] for column in details]
                )

        # 4. Inspect matatu assignment table SQL.
        print("\nASSIGNMENT TABLE SQL")
        print("====================")

        schema = connection.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'matatu_assignments'
            """
        ).fetchone()

        print(schema["sql"] if schema else "Table not found")

        # 5. Inspect notification table.
        print("\nNOTIFICATION TABLE COLUMNS")
        print("==========================")

        if "passenger_notifications" in table_names:
            for column in connection.execute(
                "PRAGMA table_info(passenger_notifications)"
            ):
                print(f"- {column['name']}: {column['type']}")
        else:
            print("- Table not found")

        # 6. Inspect payment status counts.
        print("\nEXISTING PAYMENT STATUS COUNTS")
        print("==============================")

        if "passenger_balances" in table_names:
            payment_columns = {
                column["name"]
                for column in connection.execute(
                    "PRAGMA table_info(passenger_balances)"
                )
            }

            if "status" in payment_columns:
                statuses = connection.execute(
                    """
                    SELECT status, COUNT(*) AS total
                    FROM passenger_balances
                    GROUP BY status
                    ORDER BY status
                    """
                ).fetchall()

                for row in statuses:
                    print(f"- {row['status']}: {row['total']}")
            else:
                print("- Status column not found")
        else:
            print("- passenger_balances table not found")

        # 7. Notification count.
        print("\nEXISTING NOTIFICATION COUNT")
        print("===========================")

        if "passenger_notifications" in table_names:
            count = connection.execute(
                "SELECT COUNT(*) FROM passenger_notifications"
            ).fetchone()[0]

            print(f"- {count}")
        else:
            print("- Table not found")

        # 8. Database integrity.
        print("\nDATABASE INTEGRITY")
        print("==================")

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print(integrity)

    finally:
        connection.close()


if __name__ == "__main__":
    database_path = os.path.abspath(
        os.environ.get(
            "SMART_MATATU_DB",
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "smart_matatu.db"
            )
        )
    )

    inspect_database(database_path)
