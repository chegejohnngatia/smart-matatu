
import getpass
import sqlite3

from database import get_db_connection
from werkzeug.security import generate_password_hash


def create_admin():
    print("\n=== Smart Matatu: Create Administrator ===\n")

    full_name = input("Full name: ").strip()
    email = input("Email address: ").strip().lower()

    if not full_name or not email:
        print("Name and email are required.")
        return

    password = getpass.getpass("Password: ")
    confirm_password = getpass.getpass("Confirm password: ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    if password != confirm_password:
        print("Passwords do not match.")
        return

    password_hash = generate_password_hash(password)

    connection = get_db_connection()

    try:
        connection.execute(
            """
            INSERT INTO admins (
                full_name,
                email,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (full_name, email, password_hash)
        )

        connection.commit()
        print("\nAdministrator account created successfully.")

    except sqlite3.IntegrityError:
        connection.rollback()
        print("\nAn administrator with that email already exists.")

    finally:
        connection.close()


if __name__ == "__main__":
    create_admin()
