
import os
import sqlite3
from datetime import datetime

source_path = os.path.abspath("smart_matatu.db")

if not os.path.isfile(source_path):
    raise FileNotFoundError(
        f"Database not found: {source_path}"
    )

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"{source_path}.{timestamp}.bak"

source = sqlite3.connect(source_path)
backup = sqlite3.connect(backup_path)

try:
    source.backup(backup)
    print("Database backup created successfully.")
    print(f"Backup location: {backup_path}")
finally:
    backup.close()
    source.close()
