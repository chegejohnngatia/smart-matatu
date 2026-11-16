
import os
from pathlib import Path

from inspect_database import inspect_database
from backup_database import create_backup


def main():
    database_path = Path(
        os.path.abspath(
            os.environ.get(
                "SMART_MATATU_DB",
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "smart_matatu.db"
                )
            )
        )
    )

    print("=" * 50)
    print("SMART MATATU DATABASE MAINTENANCE")
    print("=" * 50)

    print("\nSTEP 1: DATABASE INSPECTION")
    inspect_database(database_path)

    print("\nSTEP 2: DATABASE BACKUP")
    backup_path = create_backup(database_path)

    print("\nMAINTENANCE COMPLETED")
    print(f"Database: {database_path}")
    print(f"Backup: {backup_path}")


if __name__ == "__main__":
    main()
