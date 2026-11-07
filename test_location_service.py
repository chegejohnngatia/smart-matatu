from datetime import datetime, timezone
import sqlite3

import pytest

from database import init_db
from location_service import LocationUpdateError, update_matatu_location


@pytest.fixture
def connection(tmp_path, monkeypatch):
    database_path = tmp_path / "test.db"
    monkeypatch.setattr("database.DATABASE", str(database_path))
    init_db()
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        "INSERT INTO matatus (registration_number, route_name) VALUES (?, ?)",
        ("KDA 123A", "Test Route"),
    )
    connection.execute(
        """
        INSERT INTO stages (route_name, name, latitude, longitude, sequence_number)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("Test Route", "First Stage", -1.286389, 36.817223, 1),
    )
    connection.commit()
    yield connection
    connection.close()


def timestamp(second):
    return datetime(2026, 1, 1, 12, 0, second, tzinfo=timezone.utc)


def test_location_update_stores_latest_and_history(connection):
    result = update_matatu_location(
        connection, 1, -1.286389, 36.817223, 20, 5, timestamp(1), "gps"
    )
    connection.commit()

    location = connection.execute(
        "SELECT * FROM matatu_locations WHERE matatu_id = 1"
    ).fetchone()
    history = connection.execute(
        "SELECT * FROM matatu_location_history WHERE matatu_id = 1"
    ).fetchall()

    assert result["accepted"] is True
    assert location["location_source"] == "gps"
    assert location["current_stage_sequence"] == 1
    assert len(history) == 1


def test_invalid_coordinates_are_rejected(connection):
    with pytest.raises(LocationUpdateError):
        update_matatu_location(
            connection, 1, 91, 36.817223, 20, 5, timestamp(1), "gps"
        )


def test_older_updates_do_not_replace_latest_location(connection):
    update_matatu_location(
        connection, 1, -1.286389, 36.817223, 20, 5, timestamp(2), "gps"
    )
    result = update_matatu_location(
        connection, 1, -1.2, 36.8, 20, 5, timestamp(1), "gps"
    )
    connection.commit()

    location = connection.execute(
        "SELECT latitude FROM matatu_locations WHERE matatu_id = 1"
    ).fetchone()
    history_count = connection.execute(
        "SELECT COUNT(*) FROM matatu_location_history WHERE matatu_id = 1"
    ).fetchone()[0]

    assert result == {"accepted": False, "reason": "outdated"}
    assert location["latitude"] == pytest.approx(-1.286389)
    assert history_count == 1


def test_simulation_source_is_recorded(connection):
    result = update_matatu_location(
        connection, 1, -1.3, 36.8, 20, 0, timestamp(1), "simulation"
    )
    connection.commit()

    location = connection.execute(
        "SELECT location_source FROM matatu_locations WHERE matatu_id = 1"
    ).fetchone()

    assert result["source"] == "simulation"
    assert location["location_source"] == "simulation"
