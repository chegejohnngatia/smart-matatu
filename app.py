from flask import Flask, jsonify, render_template, request, redirect, url_for, send_from_directory
from database import init_db, get_db_connection
from gps import calculate_distance
from location_service import LocationUpdateError, update_matatu_location
from datetime import datetime, timezone
import socket
import qrcode
import io
import base64
import os
import ipaddress
from urllib.parse import urlsplit, urlunsplit

FRONTEND_DIST = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "fronted",
    "dist"
)

app = Flask(
    __name__,
    static_folder=os.path.join(FRONTEND_DIST, "assets"),
    static_url_path="/assets"
)

init_db()

FRONTEND_ORIGINS = {
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173"
    ).split(",")
    if origin.strip()
}
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
LOCATION_SOURCE = os.getenv("LOCATION_SOURCE", "simulation").strip().lower()
CONDUCTOR_LOCATION_TOKEN = os.getenv("CONDUCTOR_LOCATION_TOKEN", "").strip()


@app.after_request
def add_api_cors_headers(response):
    origin = request.headers.get("Origin")
    if request.path.startswith("/api/") and is_allowed_frontend_origin(origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Vary"] = "Origin"
    return response


def is_loopback_host(host):
    if not host:
        return True
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def is_allowed_frontend_origin(origin):
    if not origin:
        return False
    if origin in FRONTEND_ORIGINS:
        return True
    origin_parts = urlsplit(origin)
    request_parts = urlsplit(f"//{request.host}")
    return (
        origin_parts.scheme == "http"
        and origin_parts.port == 5173
        and origin_parts.hostname
        and origin_parts.hostname == request_parts.hostname
    )


def passenger_frontend_url():
    configured_url = FRONTEND_URL
    if configured_url:
        configured_parts = urlsplit(configured_url)
        if not is_loopback_host(configured_parts.hostname):
            return configured_url

    origin = request.headers.get("Origin")
    if origin and is_allowed_frontend_origin(origin):
        origin_parts = urlsplit(origin)
        if not is_loopback_host(origin_parts.hostname):
            return origin.rstrip("/")
        if configured_url:
            configured_parts = urlsplit(configured_url)
            if configured_parts.port:
                netloc = f"{get_local_ip()}:{configured_parts.port}"
                return urlunsplit((configured_parts.scheme, netloc, "", "", ""))
        return f"{origin_parts.scheme}://{get_local_ip()}:{origin_parts.port or 5173}"

    if configured_url:
        configured_parts = urlsplit(configured_url)
        if configured_parts.port:
            netloc = f"{get_local_ip()}:{configured_parts.port}"
            return urlunsplit((configured_parts.scheme, netloc, "", "", ""))
    return f"http://{get_local_ip()}:5173"


@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith("/api/"):
        return jsonify({"error": {"message": "Resource not found"}}), 404
    return error


def row_to_dict(row):
    return dict(row) if row else None


def location_age_seconds(last_updated_at):
    if not last_updated_at:
        return None
    updated_at = datetime.fromisoformat(last_updated_at.replace("Z", "+00:00"))
    return max(0, (datetime.now(timezone.utc) - updated_at).total_seconds())


def location_payload(location):
    age_seconds = location_age_seconds(location["last_updated_at"])
    return {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "speed": location["speed"],
        "accuracy": location["accuracy"],
        "source": location["location_source"] or "simulation",
        "last_updated_at": location["last_updated_at"],
        "age_seconds": age_seconds,
        "stale": age_seconds is None or age_seconds > 60,
    }


def require_location_update_authorization(matatu_id):
    if not CONDUCTOR_LOCATION_TOKEN:
        return jsonify({"error": {"message": "Location update authorization is not configured"}}), 503
    if request.headers.get("X-Conductor-Token") != CONDUCTOR_LOCATION_TOKEN:
        return jsonify({"error": {"message": "Unauthorized location update"}}), 403
    assigned_matatu_header = request.headers.get("X-Conductor-Matatu-Id")
    try:
        assigned_matatu_id = int(assigned_matatu_header) if assigned_matatu_header else None
    except ValueError:
        return jsonify({"error": {"message": "Invalid assigned matatu"}}), 403
    if assigned_matatu_id is not None and assigned_matatu_id != matatu_id:
        return jsonify({"error": {"message": "Conductor is not assigned to this matatu"}}), 403
    return None


@app.route("/api/matatus", methods=["GET"])
def api_matatus():
    connection = get_db_connection()
    matatus = connection.execute(
        "SELECT id, registration_number, route_name FROM matatus ORDER BY id"
    ).fetchall()
    connection.close()
    return jsonify([row_to_dict(matatu) for matatu in matatus])


def admin_matatus_payload(connection):
    matatus = connection.execute(
        "SELECT id, registration_number, route_name FROM matatus ORDER BY id"
    ).fetchall()
    locations = {
        location["matatu_id"]: location
        for location in connection.execute("SELECT * FROM matatu_locations")
    }
    passenger_counts = {
        row["matatu_id"]: row["count"]
        for row in connection.execute(
            """
            SELECT matatu_id, COUNT(*) AS count
            FROM passenger_destinations
            GROUP BY matatu_id
            """
        )
    }
    return [
        {
            "id": matatu["id"],
            "registration": matatu["registration_number"],
            "route": matatu["route_name"],
            "passenger_count": passenger_counts.get(matatu["id"], 0),
            "status": (
                "On trip"
                if matatu["id"] in locations and locations[matatu["id"]]["speed"] > 0
                else "Stopped"
                if matatu["id"] in locations
                else "Not initialized"
            ),
            "location": location_payload(locations[matatu["id"]])
            if matatu["id"] in locations
            else None,
        }
        for matatu in matatus
    ]


def admin_routes_payload(connection):
    routes = connection.execute(
        """
        SELECT route_name, COUNT(*) AS stage_count
        FROM stages
        GROUP BY route_name
        ORDER BY route_name
        """
    ).fetchall()
    vehicle_counts = {
        row["route_name"]: row["count"]
        for row in connection.execute(
            """
            SELECT route_name, COUNT(*) AS count
            FROM matatus
            GROUP BY route_name
            """
        )
    }
    result = []
    for route in routes:
        stages = connection.execute(
            """
            SELECT id, name, latitude, longitude, sequence_number
            FROM stages
            WHERE route_name = ?
            ORDER BY sequence_number
            """,
            (route["route_name"],),
        ).fetchall()
        first_stage = stages[0] if stages else None
        last_stage = stages[-1] if stages else None
        distance_km = None
        if (
            first_stage
            and last_stage
            and first_stage["latitude"] is not None
            and first_stage["longitude"] is not None
            and last_stage["latitude"] is not None
            and last_stage["longitude"] is not None
        ):
            distance_km = round(
                calculate_distance(
                    first_stage["latitude"],
                    first_stage["longitude"],
                    last_stage["latitude"],
                    last_stage["longitude"],
                )
                / 1000,
                1,
            )
        result.append(
            {
                "name": route["route_name"],
                "origin": first_stage["name"] if first_stage else None,
                "destination": last_stage["name"] if last_stage else None,
                "distance_km": distance_km,
                "stage_count": route["stage_count"],
                "vehicle_count": vehicle_counts.get(route["route_name"], 0),
                "status": "Active",
                "stages": [row_to_dict(stage) for stage in stages],
            }
        )
    return result


def admin_trips_payload(connection):
    trips = []
    matatus = connection.execute(
        "SELECT id, registration_number, route_name FROM matatus ORDER BY id"
    ).fetchall()
    for matatu in matatus:
        location = connection.execute(
            "SELECT * FROM matatu_locations WHERE matatu_id = ?",
            (matatu["id"],),
        ).fetchone()
        passenger_count = connection.execute(
            "SELECT COUNT(*) AS count FROM passenger_destinations WHERE matatu_id = ?",
            (matatu["id"],),
        ).fetchone()["count"]
        status = "Scheduled"
        if location:
            status = "In progress" if location["speed"] > 0 else "Stopped"
        trips.append(
            {
                "id": f"MATATU-{matatu['id']:03d}",
                "matatu_id": matatu["id"],
                "registration": matatu["registration_number"],
                "route": matatu["route_name"],
                "passenger_count": passenger_count,
                "status": status,
                "location": location_payload(location) if location else None,
            }
        )
    return trips


@app.route("/api/admin/matatus", methods=["GET"])
def api_admin_matatus():
    connection = get_db_connection()
    payload = admin_matatus_payload(connection)
    connection.close()
    return jsonify(payload)


@app.route("/api/admin/routes", methods=["GET"])
def api_admin_routes():
    connection = get_db_connection()
    payload = admin_routes_payload(connection)
    connection.close()
    return jsonify(payload)


@app.route("/api/admin/trips", methods=["GET"])
def api_admin_trips():
    connection = get_db_connection()
    payload = admin_trips_payload(connection)
    connection.close()
    return jsonify(payload)


@app.route("/api/admin/dashboard", methods=["GET"])
def api_admin_dashboard():
    connection = get_db_connection()
    matatus = admin_matatus_payload(connection)
    routes = admin_routes_payload(connection)
    trips = admin_trips_payload(connection)
    connection.close()
    active_trips = sum(trip["status"] == "In progress" for trip in trips)
    return jsonify({
        "stats": {
            "matatus": len(matatus),
            "active_trips": active_trips,
            "available_vehicles": sum(item["status"] == "Not initialized" for item in matatus),
            "maintenance_vehicles": 0,
            "users": None,
        },
        "matatus": matatus,
        "routes": routes,
        "trips": trips,
        "alerts": [],
    })


@app.route("/api/admin/matatus/<int:matatu_id>/qr", methods=["GET"])
def api_admin_matatu_qr(matatu_id):
    connection = get_db_connection()
    matatu = connection.execute(
        "SELECT id, registration_number, route_name FROM matatus WHERE id = ?",
        (matatu_id,),
    ).fetchone()
    connection.close()
    if matatu is None:
        return jsonify({"error": {"message": "Matatu not found"}}), 404

    qr_url = f"{passenger_frontend_url()}/passenger/{matatu_id}"
    image_buffer = io.BytesIO()
    qrcode.make(qr_url).save(image_buffer, format="PNG")
    qr_data = base64.b64encode(image_buffer.getvalue()).decode("utf-8")
    return jsonify({
        "matatu_id": matatu_id,
        "registration": matatu["registration_number"],
        "route": matatu["route_name"],
        "qr_url": qr_url,
        "qr_data_url": f"data:image/png;base64,{qr_data}",
    })


@app.route("/api/passenger/trip-info", methods=["GET"])
def api_passenger_trip_info():
    matatu_id = request.args.get("matatu_id", type=int)
    if matatu_id is None:
        return jsonify({"error": {"message": "matatu_id is required"}}), 400

    connection = get_db_connection()
    matatu = connection.execute(
        "SELECT id, registration_number, route_name FROM matatus WHERE id = ?",
        (matatu_id,),
    ).fetchone()
    if matatu is None:
        connection.close()
        return jsonify({"error": {"message": "Matatu not found"}}), 404

    stages = connection.execute(
        """
        SELECT id, name, latitude, longitude, sequence_number
        FROM stages
        WHERE route_name = ?
        ORDER BY sequence_number
        """,
        (matatu["route_name"],),
    ).fetchall()
    connection.close()
    return jsonify({
        "id": matatu["id"],
        "plate": matatu["registration_number"],
        "route": matatu["route_name"],
        "code": f"MATATU-{matatu['id']:03d}",
        "stages": [row_to_dict(stage) for stage in stages],
    })


@app.route("/api/passenger/history", methods=["GET"])
def api_passenger_history():
    matatu_id = request.args.get("matatu_id", type=int)
    connection = get_db_connection()
    query = """
        SELECT passenger_destinations.id, passenger_destinations.passenger_token,
               passenger_destinations.status, stages.name AS destination
        FROM passenger_destinations
        JOIN stages ON stages.id = passenger_destinations.destination_stage_id
    """
    parameters = ()
    if matatu_id is not None:
        query += " WHERE passenger_destinations.matatu_id = ?"
        parameters = (matatu_id,)
    query += " ORDER BY passenger_destinations.id DESC"
    history = connection.execute(query, parameters).fetchall()
    connection.close()
    return jsonify([row_to_dict(item) for item in history])


@app.route("/api/passenger/register", methods=["POST"])
def api_passenger_register():
    payload = request.get_json(silent=True) or {}
    matatu_id = payload.get("matatu_id")
    destination_stage_id = payload.get("destination_stage_id")
    if not isinstance(matatu_id, int) or not isinstance(destination_stage_id, int):
        return jsonify({
            "error": {
                "message": "matatu_id and destination_stage_id are required",
                "fields": {
                    "matatu_id": "Enter a valid vehicle.",
                    "destination_stage_id": "Choose a valid destination.",
                },
            }
        }), 422

    connection = get_db_connection()
    matatu = connection.execute(
        "SELECT route_name FROM matatus WHERE id = ?", (matatu_id,)
    ).fetchone()
    stage = connection.execute(
        "SELECT id, name FROM stages WHERE id = ? AND route_name = ?",
        (destination_stage_id, matatu["route_name"] if matatu else ""),
    ).fetchone()
    if matatu is None or stage is None:
        connection.close()
        return jsonify({"error": {"message": "Destination is not on this route"}}), 422

    cursor = connection.execute(
        """
        INSERT INTO passenger_destinations
            (matatu_id, passenger_token, destination_stage_id)
        VALUES (?, ?, ?)
        """,
        (matatu_id, "TEMP", destination_stage_id),
    )
    passenger_id = cursor.lastrowid
    passenger_token = f"P{passenger_id:03d}"
    connection.execute(
        "UPDATE passenger_destinations SET passenger_token = ? WHERE id = ?",
        (passenger_token, passenger_id),
    )
    connection.commit()
    connection.close()
    return jsonify({
        "id": passenger_id,
        "passenger_token": passenger_token,
        "destination": stage["name"],
        "status": "waiting",
    }), 201


def get_local_ip():

    socket_connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        socket_connection.connect(("8.8.8.8", 80))
        local_ip = socket_connection.getsockname()[0]

    except Exception:
        local_ip = "127.0.0.1"

    finally:
        socket_connection.close()

    return local_ip

@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIST, "index.html")


@app.route("/admin")
def admin():
    return render_template("index.html")


@app.route("/add-matatu", methods=["GET", "POST"])
def add_matatu():

    if request.method == "POST":
        registration_number = request.form["registration_number"]
        route_name = request.form["route_name"]

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO matatus (registration_number, route_name)
            VALUES (?, ?)
            """,
            (registration_number, route_name)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("matatus"))

    return render_template("add_matatu.html")


@app.route("/generate-qr/<int:matatu_id>")
def generate_qr(matatu_id):

    connection = get_db_connection()

    # Get the selected matatu
    matatu = connection.execute(
        """
        SELECT * FROM matatus
        WHERE id = ?
        """,
        (matatu_id,)
    ).fetchone()

    # Get all registered matatus
    vehicles = connection.execute(
        """
        SELECT * FROM matatus
        ORDER BY id
        """
    ).fetchall()

    connection.close()

    if matatu is None:
        return "Matatu not found", 404

    # Get current laptop IP
    local_ip = get_local_ip()

    # Create passenger URL for this specific matatu
    qr_url = f"{passenger_frontend_url()}/passenger/{matatu_id}"

    # Generate QR code
    qr = qrcode.make(qr_url)

    # Store QR image in memory
    image_buffer = io.BytesIO()

    qr.save(image_buffer, format="PNG")

    image_buffer.seek(0)

    # Convert image to Base64
    qr_data = base64.b64encode(
        image_buffer.getvalue()
    ).decode("utf-8")

    return render_template(
        "matatus.html",
        vehicles=vehicles,
        qr_data=qr_data,
        qr_matatu=matatu,
        qr_url=qr_url
    )

@app.route("/matatus")
def matatus():

    connection = get_db_connection()

    vehicles = connection.execute(
        "SELECT * FROM matatus"
    ).fetchall()

    connection.close()

    return render_template(
        "matatus.html",
        vehicles=vehicles
    )

@app.route("/add-stage", methods=["GET", "POST"])
def add_stage():

    if request.method == "POST":

        route_name = request.form["route_name"]
        name = request.form["name"]
        sequence_number = request.form["sequence_number"]
        latitude = request.form["latitude"]
        longitude = request.form["longitude"]

        connection = get_db_connection()

        connection.execute(
            """
            INSERT INTO stages (
                route_name,
                name,
                latitude,
                longitude,
                sequence_number
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                route_name,
                name,
                latitude,
                longitude,
                sequence_number
            )
        )

        connection.commit()
        connection.close()

        return redirect(url_for("stages"))

    return render_template("add_stage.html")


@app.route("/stages")
def stages():

    connection = get_db_connection()

    stage_list = connection.execute(
        """
        SELECT * FROM stages
        ORDER BY route_name, sequence_number
        """
    ).fetchall()

    connection.close()

    return render_template(
        "stages.html",
        stages=stage_list
    )


@app.route("/passenger/<int:matatu_id>", methods=["GET", "POST"])
def passenger(matatu_id):

    connection = get_db_connection()

    matatu = connection.execute(
        """
        SELECT * FROM matatus
        WHERE id = ?
        """,
        (matatu_id,)
    ).fetchone()

    if matatu is None:
        connection.close()
        return "Matatu not found", 404

    # Let the React SPA own passenger GET routes whenever its production build
    # is present. Keep the server-rendered form below as a development fallback.
    if request.method == "GET" and os.path.isfile(
        os.path.join(FRONTEND_DIST, "index.html")
    ):
        connection.close()
        return send_from_directory(FRONTEND_DIST, "index.html")

    stages = connection.execute(
        """
        SELECT * FROM stages
        WHERE route_name = ?
        ORDER BY sequence_number
        """,
        (matatu["route_name"],)
    ).fetchall()

    if request.method == "POST":

        destination_stage_id = request.form["destination_stage_id"]

        # Create the passenger journey first.
        cursor = connection.execute(
            """
            INSERT INTO passenger_destinations (
                matatu_id,
                passenger_token,
                destination_stage_id
            )
            VALUES (?, ?, ?)
            """,
            (
                matatu_id,
                "TEMP",
                destination_stage_id
            )
        )

        passenger_id = cursor.lastrowid

        # Create a simple human-readable Passenger ID.
        passenger_token = f"P{passenger_id:03d}"

        # Store the human-readable ID.
        connection.execute(
            """
            UPDATE passenger_destinations
            SET passenger_token = ?
            WHERE id = ?
            """,
            (
                passenger_token,
                passenger_id
            )
        )

        connection.commit()
        connection.close()

        return redirect(
            url_for(
                "passenger",
                matatu_id=matatu_id,
                passenger_id=passenger_id
            )
        )

    passenger_id = request.args.get("passenger_id")

    passenger_token = None

    if passenger_id:

        passenger = connection.execute(
            """
            SELECT passenger_token
            FROM passenger_destinations
            WHERE id = ?
            """,
            (passenger_id,)
        ).fetchone()

        if passenger:
            passenger_token = passenger["passenger_token"]

    connection.close()

    return render_template(
        "passenger.html",
        matatu=matatu,
        stages=stages,
        passenger_id=passenger_id,
        passenger_token=passenger_token
    )

@app.route("/conductor/<int:matatu_id>")
def conductor(matatu_id):

    connection = get_db_connection()

    # Get the matatu
    matatu = connection.execute(
        """
        SELECT * FROM matatus
        WHERE id = ?
        """,
        (matatu_id,)
    ).fetchone()

    if matatu is None:
        connection.close()
        return "Matatu not found", 404

    # Get passengers ordered by the stage
    # where they are going to alight.
    passengers = connection.execute(
        """
        SELECT
            passenger_destinations.id,
            passenger_destinations.passenger_token,
            passenger_destinations.status,
            stages.name AS destination,
            stages.sequence_number AS destination_sequence
        FROM passenger_destinations
        JOIN stages
            ON passenger_destinations.destination_stage_id = stages.id
        WHERE passenger_destinations.matatu_id = ?
        ORDER BY stages.sequence_number ASC,
                 passenger_destinations.id ASC
        """,
        (matatu_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "conductor.html",
        matatu=matatu,
        passengers=passengers
    )


@app.route("/notify-passenger/<int:passenger_id>", methods=["POST"])
def notify_passenger(passenger_id):

    connection = get_db_connection()

    connection.execute(
        """
        UPDATE passenger_destinations
        SET status = 'notified'
        WHERE id = ?
        """,
        (passenger_id,)
    )

    connection.commit()
    connection.close()

    return redirect(request.referrer)


@app.route("/api/vehicle-status/<int:matatu_id>")
@app.route("/vehicle-status/<int:matatu_id>")
def vehicle_status(matatu_id):

    connection = get_db_connection()

    # Get the matatu
    matatu = connection.execute(
        """
        SELECT * FROM matatus
        WHERE id = ?
        """,
        (matatu_id,)
    ).fetchone()

    if matatu is None:
        connection.close()
        return "Matatu not found", 404

    # Get current matatu location
    location = connection.execute(
        """
        SELECT * FROM matatu_locations
        WHERE matatu_id = ?
        """,
        (matatu_id,)
    ).fetchone()

    if location is None:
        connection.close()
        return "Matatu location not initialized.", 404

    matatu_latitude = location["latitude"]
    matatu_longitude = location["longitude"]
    current_stage_sequence = location["current_stage_sequence"]

    # Get current matatu speed
    current_speed = location["speed"]

    # Get passengers and their destinations
    passengers = connection.execute(
        """
        SELECT
            passenger_destinations.id,
            stages.name AS destination,
            stages.latitude,
            stages.longitude,
            stages.sequence_number AS destination_sequence
        FROM passenger_destinations
        JOIN stages
            ON passenger_destinations.destination_stage_id = stages.id
        WHERE passenger_destinations.matatu_id = ?
        """,
        (matatu_id,)
    ).fetchall()

    connection.close()

    if not passengers:
        return jsonify({
            "matatu": matatu["registration_number"],
            "location": location_payload(location),
            "passengers": [],
        })

    results = []

    for passenger in passengers:

        # Check whether the matatu has reached or passed
        # the passenger's destination
        if current_stage_sequence >= passenger["destination_sequence"]:

            status = "Arrived"
            remaining_distance_km = 0
            eta = None

        else:

            distance = calculate_distance(
                matatu_latitude,
                matatu_longitude,
                passenger["latitude"],
                passenger["longitude"]
            )

            remaining_distance_km = distance / 1000

            # Matatu is stopped
            if current_speed <= 0:

                status = "Stopped"
                eta = None

            # Matatu is moving
            else:

                status = "Moving"

                remaining_time_hours = (
                    remaining_distance_km / current_speed
                )

                eta = remaining_time_hours * 60

        results.append({
            "id": passenger["id"],
            "destination": passenger["destination"],
            "distance": remaining_distance_km,
            "speed": current_speed,
            "status": status,
            "eta": eta
        })

    return {
        "matatu": matatu["registration_number"],
        "location": location_payload(location),
        "passengers": results
    }


@app.route("/api/matatus/<int:matatu_id>/location", methods=["POST", "OPTIONS"])
def api_update_matatu_location(matatu_id):
    if request.method == "OPTIONS":
        return "", 204

    authorization_error = require_location_update_authorization(matatu_id)
    if authorization_error:
        return authorization_error
    if LOCATION_SOURCE != "gps":
        return jsonify({
            "error": {"message": "GPS location updates are disabled by configuration"}
        }), 409

    payload = request.get_json(silent=True) or {}
    try:
        connection = get_db_connection()
        result = update_matatu_location(
            connection,
            matatu_id,
            payload.get("latitude"),
            payload.get("longitude"),
            payload.get("speed"),
            payload.get("accuracy"),
            payload.get("recorded_at"),
            "gps",
        )
        connection.commit()
        connection.close()
    except LocationUpdateError as error:
        if "connection" in locals():
            connection.rollback()
            connection.close()
        return jsonify({"error": {"message": str(error)}}), error.status_code

    return jsonify(result), 200

@app.route("/move-matatu/<int:matatu_id>", methods=["GET", "POST"])
def move_matatu(matatu_id):

    connection = get_db_connection()

    # Get the matatu
    matatu = connection.execute(
        """
        SELECT * FROM matatus
        WHERE id = ?
        """,
        (matatu_id,)
    ).fetchone()

    if matatu is None:
        connection.close()
        return "Matatu not found", 404

    # Get current matatu location
    location = connection.execute(
        """
        SELECT * FROM matatu_locations
        WHERE matatu_id = ?
        """,
        (matatu_id,)
    ).fetchone()

    if location is None:
        connection.close()
        return "Matatu location not initialized", 404

    # Handle Move button
    if request.method == "POST":

        action = request.form["action"]

        # Move to the next stage
        if action == "move":

            next_stage = connection.execute(
                """
                SELECT * FROM stages
                WHERE route_name = ?
                AND sequence_number > ?
                ORDER BY sequence_number
                LIMIT 1
                """,
                (
                    matatu["route_name"],
                    location["current_stage_sequence"]
                )
            ).fetchone()

            if next_stage is not None:
                update_matatu_location(
                    connection,
                    matatu_id,
                    next_stage["latitude"],
                    next_stage["longitude"],
                    20,
                    0,
                    datetime.now(timezone.utc),
                    "simulation",
                )

        # Stop the matatu
        elif action == "stop":

            connection.execute(
                """
                UPDATE matatu_locations
                SET speed = 0
                WHERE matatu_id = ?
                """,
                (matatu_id,)
            )

        # Start moving again
        elif action == "start":

            connection.execute(
                """
                UPDATE matatu_locations
                SET speed = 20
                WHERE matatu_id = ?
                """,
                (matatu_id,)
            )

        connection.commit()

        # Redirect after POST
        return redirect(
            url_for(
                "move_matatu",
                matatu_id=matatu_id
            )
        )

    # Get updated location
    location = connection.execute(
        """
        SELECT * FROM matatu_locations
        WHERE matatu_id = ?
        """,
        (matatu_id,)
    ).fetchone()

    # Get current stage
    current_stage = connection.execute(
        """
        SELECT * FROM stages
        WHERE route_name = ?
        AND sequence_number = ?
        """,
        (
            matatu["route_name"],
            location["current_stage_sequence"]
        )
    ).fetchone()

    connection.close()

    # Display current location
    if current_stage is None:

        current_stage_name = "Starting Point"

        latitude = -1.286389
        longitude = 36.817223

    else:

        current_stage_name = current_stage["name"]

        latitude = current_stage["latitude"]
        longitude = current_stage["longitude"]

    speed = location["speed"]

    if speed == 0:
        movement_status = "Stopped"
    else:
        movement_status = "Moving"

    return f"""
        <!DOCTYPE html>

        <html>

        <head>

            <title>Matatu Simulation</title>

            <style>

                body {{
                    font-family: Arial, sans-serif;
                    max-width: 700px;
                    margin: 50px auto;
                    padding: 20px;
                }}

                .card {{
                    border: 1px solid #ddd;
                    border-radius: 10px;
                    padding: 25px;
                }}

                button {{
                    padding: 12px 20px;
                    margin: 10px 5px 10px 0;
                    font-size: 16px;
                    cursor: pointer;
                }}

                .reset {{
                    background-color: #ddd;
                }}

                .move {{
                    background-color: #333;
                    color: white;
                }}

                .stop {{
                    background-color: #b00020;
                    color: white;
                }}

                .start {{
                    background-color: #16803c;
                    color: white;
                }}

            </style>

        </head>

        <body>

            <div class="card">

                <h1>MATATU SIMULATION</h1>

                <p>
                    Matatu:
                    <strong>{matatu["registration_number"]}</strong>
                </p>

                <hr>

                <h2>Current Location</h2>

                <p>
                    Current Stage:
                    <strong>{current_stage_name}</strong>
                </p>

                <p>
                    Latitude:
                    <strong>{latitude}</strong>
                </p>

                <p>
                    Longitude:
                    <strong>{longitude}</strong>
                </p>

                <p>
                    Speed:
                    <strong>{speed} km/h</strong>
                </p>

                <p>
                    Status:
                    <strong>{movement_status}</strong>
                </p>

                <hr>

                <h2>Trip Controls</h2>

                <!-- Move one stage -->

                <form action="/move-matatu/{matatu_id}" method="POST" style="display:inline;">

                    <input type="hidden" name="action" value="move">

                    <button type="submit" class="move">
                        Move Matatu
                    </button>

                </form>


                <!-- Stop -->

                <form action="/move-matatu/{matatu_id}" method="POST" style="display:inline;">

                    <input type="hidden" name="action" value="stop">

                    <button type="submit" class="stop">
                        Stop Matatu
                    </button>

                </form>


                <!-- Start -->

                <form action="/move-matatu/{matatu_id}" method="POST" style="display:inline;">

                    <input type="hidden" name="action" value="start">

                    <button type="submit" class="start">
                        Start Moving
                    </button>

                </form>


                <!-- Reset -->

                <form action="/reset-matatu/{matatu_id}" method="GET">

                    <button type="submit" class="reset">
                        Reset Trip
                    </button>

                </form>

                <br>

                <a href="/passenger/{matatu_id}">
                    Open Passenger Dashboard
                </a>

            </div>

        </body>

        </html>
    """


@app.route("/reset-matatu/<int:matatu_id>")
def reset_matatu(matatu_id):

    connection = get_db_connection()

    update_matatu_location(
        connection,
        matatu_id,
        -1.286389,
        36.817223,
        20,
        0,
        datetime.now(timezone.utc),
        "simulation",
        reset_stage=True,
    )

    connection.commit()
    connection.close()

    return redirect(url_for("move_matatu", matatu_id=matatu_id))

@app.route("/gps-test")
def gps_test():

    connection = get_db_connection()

    stage = connection.execute(
        """
        SELECT * FROM stages
        WHERE name = 'GPS test'
        """
    ).fetchone()

    connection.close()

    if stage is None:
        return "GPS test stage not found in the database."

    # Simulated matatu location
    matatu_latitude = -1.286389
    matatu_longitude = 36.817223

    # Destination stage location from database
    stage_latitude = stage["latitude"]
    stage_longitude = stage["longitude"]

    distance = calculate_distance(
        matatu_latitude,
        matatu_longitude,
        stage_latitude,
        stage_longitude
    )

    return f"""
        <h1>GPS DATABASE TEST</h1>

        <p>
            Destination Stage:
            <strong>{stage["name"]}</strong>
        </p>

        <p>
            Stage Latitude:
            <strong>{stage_latitude}</strong>
        </p>

        <p>
            Stage Longitude:
            <strong>{stage_longitude}</strong>
        </p>

        <p>
            Distance from Matatu:
            <strong>{distance:.2f} metres</strong>
        </p>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
