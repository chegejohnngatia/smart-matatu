
import os
import sqlite3
from pathlib import Path


def inspect_database(database_path):
    database_path = Path(database_path).resolve()

    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found: {database_path}"
        )

    connection = sqlite3.connect(
        database_path.as_uri() + "?mode=ro",
        uri=True
    )

    try:
        print(f"Database: {database_path}")

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

                print(
                    "Columns:",
                    [column[2] for column in details]
                )

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

        print("\nDATABASE INTEGRITY")
        print("==================")
        print(connection.execute("PRAGMA integrity_check").fetchone()[0])

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
