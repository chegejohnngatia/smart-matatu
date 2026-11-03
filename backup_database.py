
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def create_backup(source_path):
    source_path = Path(source_path).resolve()

    if not source_path.is_file():
        raise FileNotFoundError(
            f"Database not found: {source_path}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(f"{source_path}.{timestamp}.bak")

    if backup_path.exists():
        raise FileExistsError(
            f"Backup already exists: {backup_path}"
        )

    source = sqlite3.connect(
        source_path.as_uri() + "?mode=ro",
        uri=True
    )

    try:
        backup = sqlite3.connect(backup_path)

        try:
            source.backup(backup)

            integrity = backup.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]

            if integrity != "ok":
                raise RuntimeError(
                    f"Backup integrity check failed: {integrity}"
                )

        finally:
            backup.close()

        print("Database backup created and verified.")
        print(f"Source: {source_path}")
        print(f"Backup: {backup_path}")

        return backup_path

    except Exception:
        if backup_path.exists():
            backup_path.unlink()
        raise

    finally:
        source.close()


if __name__ == "__main__":
    source_path = os.path.abspath(
        os.environ.get(
            "SMART_MATATU_DB",
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "smart_matatu.db"
            )
        )
    )

    create_backup(source_path)
