import sqlite3
from pathlib import Path

database_path = Path(__file__).resolve().parent / "smart_matatu.db"
connection = sqlite3.connect(database_path)

try:
    for table in ("conductors", "matatu_assignments"):
        print(f"\n{table.upper()} INDEXES")
        print("=" * (len(table) + 8))

        indexes = connection.execute(
            f"PRAGMA index_list({table})"
        ).fetchall()

        for index in indexes:
            print(f"\nIndex: {index[1]}")
            print(f"Unique: {bool(index[2])}")

            details = connection.execute(
                f"PRAGMA index_info({index[1]})"
            ).fetchall()

            print("Columns:", [column[2] for column in details])

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

    print(schema[0] if schema else "Table not found")

finally:
    connection.close()
