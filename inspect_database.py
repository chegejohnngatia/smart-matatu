
import sqlite3

connection = sqlite3.connect("smart_matatu.db")

try:
    print("NOTIFICATION TABLE COLUMNS")
    for column in connection.execute(
        "PRAGMA table_info(passenger_notifications)"
    ):
        print(f"- {column[1]}: {column[2]}")

    print("\nNOTIFICATION INDEXES")
    for index in connection.execute(
        "PRAGMA index_list(passenger_notifications)"
    ):
        print(f"- {index[1]}")

    print("\nEXISTING PAYMENT STATUS COUNTS")
    statuses = connection.execute(
        """
        SELECT status, COUNT(*)
        FROM passenger_balances
        GROUP BY status
        ORDER BY status
        """
    ).fetchall()

    for status, count in statuses:
        print(f"- {status}: {count}")

    print("\nEXISTING NOTIFICATION COUNT")
    count = connection.execute(
        "SELECT COUNT(*) FROM passenger_notifications"
    ).fetchone()[0]

    print(f"- {count}")

finally:
    connection.close()
