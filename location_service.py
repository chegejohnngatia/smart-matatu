from datetime import datetime, timezone
import math

from gps import calculate_distance


LOCATION_SOURCES = {"simulation", "gps"}
DEFAULT_STAGE_PROXIMITY_METERS = 100


class LocationUpdateError(ValueError):
    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


def _validate_number(name, value, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LocationUpdateError(f"{name} must be a number")
    if not math.isfinite(value):
        raise LocationUpdateError(f"{name} must be finite")
    if minimum is not None and value < minimum:
        raise LocationUpdateError(f"{name} is out of range")
    if maximum is not None and value > maximum:
        raise LocationUpdateError(f"{name} is out of range")
    return float(value)


def parse_recorded_at(value):
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError as error:
            raise LocationUpdateError("recorded_at must be a valid ISO-8601 timestamp") from error
    else:
        raise LocationUpdateError("recorded_at is required")

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _timestamp_for_storage(value):
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _now_for_storage():
    return _timestamp_for_storage(datetime.now(timezone.utc))


def update_matatu_location(
    connection,
    matatu_id,
    latitude,
    longitude,
    speed,
    accuracy,
    recorded_at,
    source,
    stage_proximity_meters=DEFAULT_STAGE_PROXIMITY_METERS,
    reset_stage=False,
):
    if source not in LOCATION_SOURCES:
        raise LocationUpdateError("source must be simulation or gps")

    latitude = _validate_number("latitude", latitude, -90, 90)
    longitude = _validate_number("longitude", longitude, -180, 180)
    speed = _validate_number("speed", speed, 0)
    accuracy = _validate_number("accuracy", accuracy, 0)
    recorded_datetime = parse_recorded_at(recorded_at)
    recorded_value = _timestamp_for_storage(recorded_datetime)

    matatu = connection.execute(
        "SELECT id, route_name FROM matatus WHERE id = ?", (matatu_id,)
    ).fetchone()
    if matatu is None:
        raise LocationUpdateError("Matatu not found", 404)

    location = connection.execute(
        "SELECT * FROM matatu_locations WHERE matatu_id = ?", (matatu_id,)
    ).fetchone()
    if location is not None and location["last_updated_at"]:
        previous_datetime = parse_recorded_at(location["last_updated_at"])
        if recorded_datetime <= previous_datetime:
            return {"accepted": False, "reason": "outdated"}

    current_stage_sequence = 0 if reset_stage else (
        location["current_stage_sequence"] if location else 0
    )
    next_stage = connection.execute(
        """
        SELECT sequence_number, latitude, longitude
        FROM stages
        WHERE route_name = ? AND sequence_number > ?
        ORDER BY sequence_number
        LIMIT 1
        """,
        (matatu["route_name"], current_stage_sequence),
    ).fetchone()
    if not reset_stage and next_stage and next_stage["latitude"] is not None and next_stage["longitude"] is not None:
        distance_to_stage = calculate_distance(
            latitude,
            longitude,
            next_stage["latitude"],
            next_stage["longitude"],
        )
        if distance_to_stage <= stage_proximity_meters:
            current_stage_sequence = next_stage["sequence_number"]

    received_at = _now_for_storage()
    if location is None:
        connection.execute(
            """
            INSERT INTO matatu_locations
                (matatu_id, latitude, longitude, current_stage_sequence, speed,
                 accuracy, last_updated_at, location_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (matatu_id, latitude, longitude, current_stage_sequence, speed,
             accuracy, recorded_value, source),
        )
    else:
        connection.execute(
            """
            UPDATE matatu_locations
            SET latitude = ?, longitude = ?, current_stage_sequence = ?,
                speed = ?, accuracy = ?, last_updated_at = ?, location_source = ?
            WHERE matatu_id = ?
            """,
            (latitude, longitude, current_stage_sequence, speed, accuracy,
             recorded_value, source, matatu_id),
        )

    connection.execute(
        """
        INSERT INTO matatu_location_history
            (matatu_id, latitude, longitude, speed, accuracy, source,
             recorded_at, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (matatu_id, latitude, longitude, speed, accuracy, source,
         recorded_value, received_at),
    )
    return {
        "accepted": True,
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "accuracy": accuracy,
        "source": source,
        "recorded_at": recorded_value,
        "current_stage_sequence": current_stage_sequence,
    }