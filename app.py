from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_from_directory,
    jsonify,
    session
)

import secrets
import hashlib
import re
import sqlite3
import uuid
from PIL import Image, UnidentifiedImageError
import warnings
from functools import wraps
from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from database import init_db, get_db_connection
from gps import calculate_distance

import socket
import qrcode
import io
import base64
import os

from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

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

# Conductor passport photo storage
CONDUCTOR_UPLOAD_FOLDER = os.path.join(
    app.instance_path,
    "conductor_uploads"
)

os.makedirs(CONDUCTOR_UPLOAD_FOLDER, exist_ok=True)

# Maximum upload size: 5 MB
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Flask session security configuration
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError(
        "FLASK_SECRET_KEY is missing. Check your .env file."
    )

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # Local development only

# =====================================================
# AUTHORIZATION: ADMINISTRATOR ACCESS
# =====================================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({
                "success": False,
                "message": "Authentication required."
            }), 401

        if session.get("role") != "admin":
            return jsonify({
                "success": False,
                "message": "Administrator access required."
            }), 403

        return f(*args, **kwargs)

    return decorated_function

# =====================================================
# AUTHENTICATION: LOGIN
# =====================================================

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password are required."
        }), 400

    connection = get_db_connection()

    try:
        # Check administrator accounts first.
        user = connection.execute(
            """
            SELECT id, full_name, email, password_hash
            FROM admins
            WHERE email = ? AND is_active = 1
            """,
            (email,)
        ).fetchone()

        role = "admin"

        # If no administrator was found, check conductors.
        if user is None:
            user = connection.execute(
                """
                SELECT id, full_name, email, password_hash
                FROM conductors
                WHERE email = ? AND is_active = 1
                """,
                (email,)
            ).fetchone()

            role = "conductor"

        # Verify account and password.
        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            return jsonify({
                "success": False,
                "message": "Invalid email or password."
            }), 401

        assigned_matatu = None

        # Every conductor must have an active matatu assignment.
        if role == "conductor":
            assigned_matatu = connection.execute(
                """
                SELECT
                    m.id AS matatu_id,
                    m.registration_number,
                    m.route_name
                FROM matatu_assignments ma
                JOIN matatus m ON m.id = ma.matatu_id
                WHERE ma.conductor_id = ?
                  AND ma.ended_at IS NULL
                """,
                (user["id"],)
            ).fetchone()

            if assigned_matatu is None:
                return jsonify({
                    "success": False,
                    "message": "You do not have an active matatu assignment."
                }), 403

        # Start a fresh authenticated session.
        session.clear()

        session["user_id"] = user["id"]
        session["full_name"] = user["full_name"]
        session["email"] = user["email"]
        session["role"] = role

        session["csrf_token"] = secrets.token_urlsafe(32)

        if assigned_matatu is not None:
            session["matatu_id"] = assigned_matatu["matatu_id"]

        response_user = {
            "id": user["id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": role
        }

        if assigned_matatu is not None:
            response_user["matatu"] = {
                "id": assigned_matatu["matatu_id"],
                "registration_number": assigned_matatu["registration_number"],
                "route_name": assigned_matatu["route_name"]
            }

        return jsonify({
                "success": True,
                "message": "Login successful.",
                "csrf_token": session["csrf_token"],
                "user": response_user
            }), 200

    finally:
        connection.close()

# =====================================================
# SECURITY: CSRF PROTECTION
# =====================================================

def csrf_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = session.get("csrf_token")
        request_token = request.headers.get("X-CSRF-Token")

        if (
            not session_token
            or not request_token
            or not secrets.compare_digest(
                session_token,
                request_token
            )
        ):
            return jsonify({
                "success": False,
                "message": "Invalid or missing CSRF token."
            }), 403

        return f(*args, **kwargs)

    return decorated_function

# =====================================================
# ADMIN: CREATE CONDUCTOR AND ASSIGN MATATU
# =====================================================

# =====================================================
# AUTHORIZATION: CONDUCTOR ACCESS
# =====================================================

def conductor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):

        # Confirm that a user is logged in.
        if "user_id" not in session:
            return jsonify({
                "success": False,
                "message": "Authentication required."
            }), 401

        # Only conductors may access conductor endpoints.
        if session.get("role") != "conductor":
            return jsonify({
                "success": False,
                "message": "Conductor access required."
            }), 403

        connection = get_db_connection()

        try:
            assignment = connection.execute(
                """
                SELECT matatu_id
                FROM matatu_assignments
                WHERE conductor_id = ?
                  AND ended_at IS NULL
                """,
                (session["user_id"],)
            ).fetchone()

        finally:
            connection.close()

        # A conductor must have an active assignment.
        if assignment is None:
            session.pop("matatu_id", None)

            return jsonify({
                "success": False,
                "message": "You do not have an active matatu assignment."
            }), 403

        assigned_matatu_id = assignment["matatu_id"]

        # If the URL contains a matatu ID, verify ownership.
        requested_matatu_id = kwargs.get("matatu_id")

        if requested_matatu_id is not None:
            if requested_matatu_id != assigned_matatu_id:
                return jsonify({
                    "success": False,
                    "message": "You are not authorized to access this matatu."
                }), 403

        # Keep the current assignment in the session.
        session["matatu_id"] = assigned_matatu_id

        return f(*args, **kwargs)

    return decorated_function

    # =====================================================
# AUTHORIZATION: PASSENGER ACCESS
# =====================================================

def get_authenticated_passenger(connection):
    auth_header = request.headers.get("Authorization", "")

    scheme, separator, token = auth_header.partition(" ")

    if (
        not separator
        or scheme.lower() != "bearer"
        or not token.strip()
    ):
        return None

    token = token.strip()

    token_hash = hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

    journey = connection.execute(
        """
        SELECT
            id,
            matatu_id,
            passenger_token,
            destination_stage_id,
            status
        FROM passenger_destinations
        WHERE access_token_hash = ?
        """,
        (token_hash,)
    ).fetchone()

    return journey

# =====================================================
# AUTH: GET CURRENT USER
# =====================================================

@app.route("/api/auth/me", methods=["GET"])
def api_current_user():
    if "user_id" not in session:
        return jsonify({
            "success": False,
            "message": "Not authenticated."
        }), 401

    user = {
        "id": session["user_id"],
        "full_name": session["full_name"],
        "email": session["email"],
        "role": session["role"]
    }

    if session["role"] == "conductor":
        connection = get_db_connection()

        try:
            assigned_matatu = connection.execute(
                """
                SELECT
                    m.id AS matatu_id,
                    m.registration_number,
                    m.route_name
                FROM matatu_assignments ma
                JOIN matatus m ON m.id = ma.matatu_id
                WHERE ma.conductor_id = ?
                  AND ma.ended_at IS NULL
                """,
                (session["user_id"],)
            ).fetchone()

            if assigned_matatu is None:
                session.clear()

                return jsonify({
                    "success": False,
                    "message": "No active matatu assignment found."
                }), 403

            user["matatu"] = {
                "id": assigned_matatu["matatu_id"],
                "registration_number": assigned_matatu["registration_number"],
                "route_name": assigned_matatu["route_name"]
            }

        finally:
            connection.close()

    return jsonify({
        "success": True,
        "user": user,
        "csrf_token": session.get("csrf_token")
    }), 200

# =====================================================
# AUTH: LOGOUT
# =====================================================

@app.route("/api/auth/logout", methods=["POST"])
@csrf_required
def api_logout():
    session.clear()

    return jsonify({
        "success": True,
        "message": "Logout successful."
    }), 200

@app.route("/api/admin/conductors", methods=["POST"])
@admin_required
@csrf_required
def create_conductor():
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    matatu_id = request.form.get("matatu_id", "").strip()
    passport_photo = request.files.get("passport_photo")

    # Validate required fields.
    if not all([full_name, email, password, matatu_id, passport_photo]):
        return jsonify({
            "success": False,
            "message": "All fields, including the passport photo, are required."
        }), 400

    if len(full_name) < 3 or len(full_name) > 100:
        return jsonify({
        "success": False,
        "message": "Full name must be between 3 and 100 characters."
    }), 400

    if not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
        email
        ):
        return jsonify({
        "success": False,
        "message": "Enter a valid email address."
    }), 400

    if len(password) < 8 or len(password) > 128:
        return jsonify({
        "success": False,
        "message": "Password must be between 8 and 128 characters."
    }), 400
    try:
        matatu_id = int(matatu_id)

        if matatu_id <= 0:
            raise ValueError

    except ValueError:
        return jsonify({
            "success": False,
            "message": "Invalid matatu selection."
        }), 400

        # Validate and process the uploaded image.
    try:
        passport_photo.stream.seek(0)

        # Check the actual image format and dimensions.
        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning
            )

            with Image.open(passport_photo.stream) as uploaded_image:
                if uploaded_image.format not in ("JPEG", "PNG"):
                    return jsonify({
                        "success": False,
                        "message": "Only JPEG and PNG images are accepted."
                    }), 400

                if (
                    uploaded_image.width < 200
                    or uploaded_image.height < 200
                ):
                    return jsonify({
                        "success": False,
                        "message": "The passport photo must be at least 200 × 200 pixels."
                    }), 400

                if (
                    uploaded_image.width > 6000
                    or uploaded_image.height > 6000
                ):
                    return jsonify({
                        "success": False,
                        "message": "The passport photo dimensions are too large."
                    }), 400

                # Verify that the image data is valid.
                uploaded_image.verify()

        # Reopen the image after verification.
        passport_photo.stream.seek(0)

        with warnings.catch_warnings():
            warnings.simplefilter(
                "error",
                Image.DecompressionBombWarning
            )

            with Image.open(passport_photo.stream) as uploaded_image:
                processed_image = uploaded_image.convert("RGB")
                processed_image.thumbnail((1200, 1200))

    except (
        UnidentifiedImageError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
        OSError,
        ValueError
    ):
        return jsonify({
            "success": False,
            "message": "The uploaded passport photo is invalid or too large."
        }), 400

    # Generate a unique filename.
    photo_filename = f"{uuid.uuid4().hex}.jpg"

    photo_path = os.path.join(
        CONDUCTOR_UPLOAD_FOLDER,
        photo_filename
    )

    relative_photo_path = os.path.join(
        "conductor_uploads",
        photo_filename
    ).replace("\\", "/")

    connection = get_db_connection()

    try:
        # Save the processed image.
        processed_image.save(
            photo_path,
            format="JPEG",
            quality=90,
            optimize=True
        )

        # Begin an atomic database operation.
        connection.execute("BEGIN IMMEDIATE")

        # Confirm the selected matatu exists.
        matatu = connection.execute(
            """
            SELECT id
            FROM matatus
            WHERE id = ?
            """,
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            connection.rollback()
            os.remove(photo_path)

            return jsonify({
                "success": False,
                "message": "Selected matatu does not exist."
            }), 404

        # Create the conductor account.
        password_hash = generate_password_hash(password)

        cursor = connection.execute(
            """
            INSERT INTO conductors (
                full_name,
                email,
                password_hash,
                passport_photo
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                full_name,
                email,
                password_hash,
                relative_photo_path
            )
        )

        conductor_id = cursor.lastrowid

        # Assign the selected matatu.
        connection.execute(
            """
            INSERT INTO matatu_assignments (
                conductor_id,
                matatu_id
            )
            VALUES (?, ?)
            """,
            (conductor_id, matatu_id)
        )

        connection.commit()

        return jsonify({
            "success": True,
            "message": "Conductor account created and matatu assigned successfully.",
            "conductor": {
                "id": conductor_id,
                "full_name": full_name,
                "email": email,
                "matatu_id": matatu_id,
                "passport_photo_url": url_for("get_passenger_conductor_photo")
            }
        }), 201

    except sqlite3.IntegrityError:
        connection.rollback()

        if os.path.exists(photo_path):
            os.remove(photo_path)

        return jsonify({
            "success": False,
            "message": "A conductor with this email already exists, or the conductor already has an active matatu assignment."
        }), 409

    except Exception:
        connection.rollback()

        if os.path.exists(photo_path):
            os.remove(photo_path)

        raise

    finally:
        connection.close()

@app.route("/api/passenger/conductor-photo", methods=["GET"])
def get_passenger_conductor_photo():
    connection = get_db_connection()

    try:
        journey = get_authenticated_passenger(connection)

        if journey is None:
            return jsonify({
                "success": False,
                "message": "A valid passenger access token is required."
            }), 401

        if journey["status"] != "waiting":
            return jsonify({
                "success": False,
                "message": "This passenger journey is no longer active."
            }), 403

        conductor = connection.execute(
            """
            SELECT
                c.full_name,
                c.passport_photo
            FROM matatu_assignments ma
            JOIN conductors c
                ON c.id = ma.conductor_id
            WHERE ma.matatu_id = ?
              AND ma.ended_at IS NULL
              AND c.is_active = 1
            """,
            (journey["matatu_id"],)
        ).fetchone()

        if conductor is None or not conductor["passport_photo"]:
            return jsonify({
                "success": False,
                "message": "No active conductor photo is available."
            }), 404

        photo_filename = os.path.basename(
            conductor["passport_photo"].replace("\\", "/")
        )

        if not re.fullmatch(r"[0-9a-f]{32}\.jpg", photo_filename):
            return jsonify({
                "success": False,
                "message": "The conductor photo is unavailable."
            }), 404

        photo_path = os.path.join(
            CONDUCTOR_UPLOAD_FOLDER,
            photo_filename
        )

        if not os.path.isfile(photo_path):
            return jsonify({
                "success": False,
                "message": "The conductor photo is unavailable."
            }), 404

        response = send_from_directory(
            CONDUCTOR_UPLOAD_FOLDER,
            photo_filename,
            mimetype="image/jpeg"
        )

        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"

        return response

    finally:
        connection.close()

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")

    allowed_origins = {
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }

    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin

        # Allow browser requests to include Flask session cookies.
        response.headers["Access-Control-Allow-Credentials"] = "true"

        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization, X-CSRF-Token"
        )

        response.headers["Vary"] = "Origin"

    return response

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

def check_proximity_alerts(matatu_id):
    connection = get_db_connection()

    try:
        location = connection.execute(
            """
            SELECT latitude, longitude
            FROM matatu_locations
            WHERE matatu_id = ?
            """,
            (matatu_id,)
        ).fetchone()

        if location is None:
            return 0

        passengers = connection.execute(
            """
            SELECT
                pd.id AS passenger_destination_id,
                pd.passenger_token,
                s.name AS destination_name,
                s.latitude AS destination_latitude,
                s.longitude AS destination_longitude,
                pb.id AS balance_id,
                pb.status AS balance_status
            FROM passenger_destinations pd
            JOIN stages s
                ON s.id = pd.destination_stage_id
            JOIN passenger_balances pb
                ON pb.passenger_destination_id = pd.id
               AND pb.matatu_id = pd.matatu_id
            WHERE pd.matatu_id = ?
              AND pd.status = 'waiting'
              AND pb.status IN (
                  'pending',
                  'awaiting_confirmation'
              )
            """,
            (matatu_id,)
        ).fetchall()

        alerts_created = 0

        for passenger in passengers:
            # Skip destinations without coordinates.
            if (
                passenger["destination_latitude"] is None
                or passenger["destination_longitude"] is None
            ):
                continue

            distance = calculate_distance(
                location["latitude"],
                location["longitude"],
                passenger["destination_latitude"],
                passenger["destination_longitude"]
            )

            if distance > 500:
                continue

            # A recorded but unconfirmed payment needs a
            # passenger reminder, not a conductor alert.
            if passenger["balance_status"] == "awaiting_confirmation":
                existing_notification = connection.execute(
                    """
                    SELECT id
                    FROM passenger_notifications
                    WHERE balance_id = ?
                      AND notification_type = 'payment_reminder'
                    LIMIT 1
                    """,
                    (passenger["balance_id"],)
                ).fetchone()

                if existing_notification:
                    continue

                connection.execute(
                    """
                    INSERT INTO passenger_notifications (
                        matatu_id,
                        passenger_destination_id,
                        balance_id,
                        notification_type,
                        message
                    )
                    VALUES (?, ?, ?, 'payment_reminder', ?)
                    """,
                    (
                        matatu_id,
                        passenger["passenger_destination_id"],
                        passenger["balance_id"],
                        (
                            f"Passenger {passenger['passenger_token']}, "
                            f"your destination "
                            f"{passenger['destination_name']} is within "
                            f"500 metres. Please confirm receipt of "
                            f"your recorded payment."
                        )
                    )
                )

                continue

            # Pending balances retain the existing conductor
            # proximity-alert behaviour.
            existing_alert = connection.execute(
                """
                SELECT id
                FROM emergency_alerts
                WHERE passenger_destination_id = ?
                  AND alert_type = 'proximity'
                """,
                (passenger["passenger_destination_id"],)
            ).fetchone()

            if existing_alert:
                continue

            connection.execute(
                """
                INSERT INTO emergency_alerts (
                    matatu_id,
                    passenger_destination_id,
                    alert_type,
                    message
                )
                VALUES (?, ?, 'proximity', ?)
                """,
                (
                    matatu_id,
                    passenger["passenger_destination_id"],
                    (
                        f"Passenger {passenger['passenger_token']} "
                        f"has an unpaid balance and is within 500 "
                        f"metres of destination "
                        f"{passenger['destination_name']}."
                    )
                )
            )

            alerts_created += 1

        connection.commit()
        return alerts_created

    except Exception:
        connection.rollback()
        app.logger.exception(
            "Failed to check proximity alerts for matatu %s.",
            matatu_id
        )
        raise

    finally:
        connection.close()

@app.route("/")
@app.route("/admin")
@app.route("/admin/<path:frontend_path>")
@app.route("/conductor")
@app.route("/conductor/<path:frontend_path>")
@app.route("/passenger")
@app.route("/passenger/<path:frontend_path>")
@app.route("/login")
@app.route("/home")
@app.route("/admin-prototype")
def serve_react_app(frontend_path=None):
    return send_from_directory(FRONTEND_DIST, "index.html")

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

@app.route("/api/conductor/dashboard/<int:matatu_id>", methods=["GET"])
@conductor_required
def conductor_dashboard_api(matatu_id):
    connection = get_db_connection()

    try:
        # Get the actual vehicle and route.
        matatu = connection.execute(
            """
            SELECT id, registration_number, route_name
            FROM matatus
            WHERE id = ?
            """,
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            return jsonify({
                "error": "Vehicle not found."
            }), 404

        # Get actual passengers and their destinations.
        # Stage sequence determines the order, not alphabetical order.
        rows = connection.execute(
            """
            SELECT
                pd.id AS passenger_id,
                pd.passenger_token,
                pd.destination_stage_id,
                s.name AS destination_name,
                s.sequence_number
            FROM passenger_destinations AS pd
            LEFT JOIN stages AS s
                ON s.id = pd.destination_stage_id
            WHERE pd.matatu_id = ?
            ORDER BY
                CASE WHEN s.sequence_number IS NULL THEN 1 ELSE 0 END,
                s.sequence_number ASC,
                pd.id ASC
            """,
            (matatu_id,)
        ).fetchall()

        passengers = [
            {
                "id": row["passenger_id"],
                "passenger_id": row["passenger_token"],
                "destination_stage_id": row["destination_stage_id"],
                "destination": row["destination_name"] or "Unknown destination",
                "stage_sequence": row["sequence_number"]
            }
            for row in rows
        ]

        response = jsonify({
            "vehicle": {
                "id": matatu["id"],
                "registration_number": matatu["registration_number"],
                "route_name": matatu["route_name"]
            },
            "passenger_count": len(passengers),
            "passengers": passengers
        })

        # Permit requests from the local React development server.
        origin = request.headers.get("Origin")
        allowed_origins = {
            "http://localhost:5173",
            "http://127.0.0.1:5173"
        }

        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"

        return response

    finally:
        connection.close()

# ---------------- CONDUCTOR EMERGENCY ALERT API ----------------

@app.route("/api/conductor/emergency-alerts/<int:matatu_id>", methods=["GET"])
@conductor_required
def get_conductor_emergency_alerts(matatu_id):
    connection = get_db_connection()

    try:
        matatu = connection.execute(
            "SELECT id FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            return jsonify({"error": "Vehicle not found."}), 404

        rows = connection.execute(
            """
            SELECT
                ea.id AS alert_id,
                ea.passenger_destination_id AS journey_id,
                pd.passenger_token AS passenger_id,
                ea.alert_type,
                ea.message,
                ea.status,
                ea.created_at,
                ea.acknowledged_at,
                ea.acknowledged_by_conductor_id,
                c.full_name AS acknowledged_by_conductor_name
            FROM emergency_alerts AS ea
            JOIN passenger_destinations AS pd
                ON pd.id = ea.passenger_destination_id
            LEFT JOIN conductors AS c
                ON c.id = ea.acknowledged_by_conductor_id
            WHERE ea.matatu_id = ?
            ORDER BY
                CASE WHEN ea.status = 'active' THEN 0 ELSE 1 END,
                ea.created_at DESC,
                ea.id DESC
            """,
            (matatu_id,)
        ).fetchall()

        alerts = [dict(row) for row in rows]

        active_alerts = [
            alert for alert in alerts
            if alert["status"] == "active"
        ]

        history = [
            alert for alert in alerts
            if alert["status"] == "acknowledged"
        ]

        return jsonify({
            "unresolved_count": len(active_alerts),
            "active_alerts": active_alerts,
            "history": history
        }), 200

    except Exception:
        app.logger.exception(
            "Failed to retrieve conductor emergency alerts."
        )
        return jsonify({
            "error": "Could not retrieve emergency alerts."
        }), 500

    finally:
        connection.close()

# ---------------- END CONDUCTOR EMERGENCY ALERT API ----------------

@app.route(
    "/api/conductor/emergency-alerts/<int:alert_id>/acknowledge",
    methods=["POST"]
)
@conductor_required
@csrf_required
def acknowledge_emergency_alert(alert_id):
    matatu_id = session["matatu_id"]
    conductor_id = session["user_id"]

    try:
        matatu_id = int(matatu_id)
        conductor_id = int(conductor_id)
    except (TypeError, ValueError):
        return jsonify({
            "error": "Valid vehicle and conductor IDs are required."
        }), 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        alert = connection.execute(
            """
            SELECT id, status
            FROM emergency_alerts
            WHERE id = ? AND matatu_id = ?
            """,
            (alert_id, matatu_id)
        ).fetchone()

        if alert is None:
            connection.rollback()
            return jsonify({
                "error": "Alert not found for this vehicle."
            }), 404

        if alert["status"] != "active":
            connection.rollback()
            return jsonify({
                "error": "This alert has already been acknowledged."
            }), 409

        cursor = connection.execute(
            """
            UPDATE emergency_alerts
            SET status = 'acknowledged',
                acknowledged_at = CURRENT_TIMESTAMP,
                acknowledged_by_conductor_id = ?
            WHERE id = ?
              AND matatu_id = ?
              AND status = 'active'
            """,
            (conductor_id, alert_id, matatu_id)
        )

        if cursor.rowcount != 1:
            connection.rollback()
            return jsonify({
                "error": "Acknowledgement failed. Please refresh and retry."
            }), 409

        connection.commit()

        return jsonify({
            "message": "Alert acknowledged. It remains available in history.",
            "alert_id": alert_id,
            "status": "acknowledged",
            "acknowledged_by_conductor_id": conductor_id,
            "balance_changed": False,
            "issue_resolved": False
        }), 200

    except Exception:
        connection.rollback()
        app.logger.exception("Failed to acknowledge emergency alert.")
        return jsonify({
            "error": "Could not acknowledge the emergency alert."
        }), 500

    finally:
        connection.close()

# ---------------- PASSENGER EMERGENCY ISSUE API ----------------

@app.route(
    "/api/passenger/journeys/<int:journey_id>/emergency-issues",
    methods=["POST"]
)
def create_passenger_emergency_issue(journey_id):
    data = request.get_json(silent=True) or {}

    issue_description = data.get("issue_description")

    if (
        not isinstance(issue_description, str)
        or not issue_description.strip()
    ):
        return jsonify({
            "error": "Please provide a description of the issue."
        }), 400

    issue_description = issue_description.strip()

    if len(issue_description) > 1000:
        return jsonify({
            "error": "The issue description must not exceed 1000 characters."
        }), 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        # Authenticate passenger using their access token.
        journey = get_authenticated_passenger(connection)

        if journey is None or journey["id"] != journey_id:
            connection.rollback()
            return jsonify({
                "error": "Invalid passenger authentication or journey."
            }), 401

        # Only active passenger journeys can submit issues.
        if journey["status"] != "waiting":
            connection.rollback()
            return jsonify({
                "error": "This journey is no longer active."
            }), 403

        # Check for an existing proximity alert.
        proximity_alert = connection.execute(
            """
            SELECT id
            FROM emergency_alerts
            WHERE passenger_destination_id = ?
              AND alert_type = 'proximity'
            LIMIT 1
            """,
            (journey_id,)
        ).fetchone()

        if proximity_alert:
            connection.rollback()
            return jsonify({
                "error": (
                    "A proximity alert has already been raised "
                    "for this journey."
                ),
                "existing_alert_id": proximity_alert["id"]
            }), 409

        # Prevent duplicate passenger issue alerts.
        existing_issue = connection.execute(
            """
            SELECT id, status
            FROM emergency_alerts
            WHERE passenger_destination_id = ?
              AND alert_type = 'passenger_issue'
            LIMIT 1
            """,
            (journey_id,)
        ).fetchone()

        if existing_issue:
            connection.rollback()
            return jsonify({
                "error": (
                    "An issue alert has already been raised "
                    "for this journey."
                ),
                "existing_alert_id": existing_issue["id"],
                "status": existing_issue["status"]
            }), 409

        # Create the emergency issue alert.
        cursor = connection.execute(
            """
            INSERT INTO emergency_alerts (
                matatu_id,
                passenger_destination_id,
                alert_type,
                message
            )
            VALUES (?, ?, 'passenger_issue', ?)
            """,
            (
                journey["matatu_id"],
                journey_id,
                issue_description
            )
        )

        alert_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Your issue has been reported to the conductor.",
            "alert_id": alert_id,
            "journey_id": journey_id,
            "alert_type": "passenger_issue",
            "status": "active"
        }), 201

    except Exception:
        connection.rollback()

        app.logger.exception(
            "Failed to create passenger emergency issue."
        )

        return jsonify({
            "error": "Could not submit the issue. Please try again."
        }), 500

    finally:
        connection.close()

# ---------------- END PASSENGER EMERGENCY ISSUE API ----------------

# ---------------- PASSENGER BALANCE API ----------------

@app.route("/api/conductor/balances/<int:matatu_id>", methods=["GET"])
@conductor_required
def get_conductor_balances(matatu_id):
    connection = get_db_connection()

    try:
        matatu = connection.execute(
            "SELECT id FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            return jsonify({"error": "Vehicle not found."}), 404

        rows = connection.execute("""
            SELECT
                pb.id AS balance_id,
                pb.matatu_id,
                pb.passenger_destination_id AS journey_id,
                pd.passenger_token AS passenger_id,
                pb.amount,
                pb.status,
                pb.created_at,
                pb.paid_at,
                pb.confirmed_at,
                pb.paid_by_conductor_id,
                c.full_name AS paid_by_conductor_name
            FROM passenger_balances AS pb
            JOIN passenger_destinations AS pd
                ON pd.id = pb.passenger_destination_id
            LEFT JOIN conductors AS c
                ON c.id = pb.paid_by_conductor_id
            WHERE pb.matatu_id = ?
            ORDER BY pb.id DESC
        """, (matatu_id,)).fetchall()

        balances = [dict(row) for row in rows]

        return jsonify({
            "pending_balances": [
                balance for balance in balances
                if balance["status"] == "pending"
            ],
            "awaiting_confirmation": [
                balance for balance in balances
                if balance["status"] == "awaiting_confirmation"
            ],
            "history": [
                balance for balance in balances
                if balance["status"] == "confirmed"
            ]
        }), 200

    except Exception:
        app.logger.exception("Failed to retrieve passenger balances.")
        return jsonify({
            "error": "Could not retrieve balances."
        }), 500

    finally:
        connection.close()

# ---------------- END PASSENGER BALANCE API ----------------

@app.route("/api/conductor/balances/<int:matatu_id>", methods=["POST"])
@conductor_required
@csrf_required
def add_conductor_balance(matatu_id):
    data = request.get_json(silent=True) or {}

    passenger_id = data.get("passenger_id")
    amount_raw = data.get("amount")

    if not isinstance(passenger_id, str) or not passenger_id.strip():
        return jsonify({"error": "A passenger ID is required."}), 400

    passenger_id = passenger_id.strip().upper()

    if isinstance(amount_raw, bool):
        return jsonify({"error": "Enter a valid positive amount."}), 400

    try:
        amount = float(amount_raw)

        if not __import__("math").isfinite(amount) or amount <= 0:
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid positive amount."}), 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        matatu = connection.execute(
            "SELECT id FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            connection.rollback()
            return jsonify({"error": "Vehicle not found."}), 404

        journeys = connection.execute("""
            SELECT id, passenger_token
            FROM passenger_destinations
            WHERE matatu_id = ?
              AND UPPER(passenger_token) = ?
              AND status = 'waiting'
            ORDER BY id DESC
        """, (matatu_id, passenger_id)).fetchall()

        if not journeys:
            connection.rollback()
            return jsonify({
                "error": (
                    f"No active journey was found for passenger ID "
                    f"{passenger_id} on this matatu. Check the ID and "
                    "ensure the passenger has an active journey."
                )
            }), 404

        if len(journeys) > 1:
            connection.rollback()
            return jsonify({
                "error": (
                    "Multiple active journeys match this passenger ID. "
                    "Resolve the ambiguity before adding a balance."
                )
            }), 409

        journey_id = journeys[0]["id"]

        # Prevent another balance while the existing one is unresolved.
        existing = connection.execute("""
            SELECT id, status
            FROM passenger_balances
            WHERE passenger_destination_id = ?
              AND status IN ('pending', 'awaiting_confirmation')
            LIMIT 1
        """, (journey_id,)).fetchone()

        if existing:
            connection.rollback()
            return jsonify({
                "error": (
                    "This passenger already has an outstanding balance. "
                    "Resolve it before adding another."
                )
            }), 409

        cursor = connection.execute("""
            INSERT INTO passenger_balances (
                matatu_id,
                passenger_destination_id,
                amount
            )
            VALUES (?, ?, ?)
        """, (matatu_id, journey_id, amount))

        balance_id = cursor.lastrowid
        connection.commit()

        return jsonify({
            "message": "Passenger balance added successfully.",
            "balance_id": balance_id,
            "passenger_id": journeys[0]["passenger_token"],
            "amount": amount,
            "status": "pending"
        }), 201

    except Exception:
        connection.rollback()
        app.logger.exception("Failed to add passenger balance.")
        return jsonify({
            "error": "Could not add passenger balance."
        }), 500

    finally:
        connection.close()

@app.route(
    "/api/conductor/balances/<int:balance_id>/pay",
    methods=["POST"]
)
@conductor_required
@csrf_required
def mark_conductor_balance_paid(balance_id):
    matatu_id = session["matatu_id"]
    conductor_id = session["user_id"]

    if isinstance(matatu_id, bool) or isinstance(conductor_id, bool):
        return jsonify({
            "error": "Valid vehicle and conductor IDs are required."
        }), 400

    try:
        matatu_id = int(matatu_id)
        conductor_id = int(conductor_id)

        if matatu_id <= 0 or conductor_id <= 0:
            raise ValueError

    except (TypeError, ValueError):
        return jsonify({
            "error": "Valid vehicle and conductor IDs are required."
        }), 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        balance = connection.execute("""
            SELECT
                pb.id,
                pb.status,
                pb.passenger_destination_id,
                pb.matatu_id,
                pd.passenger_token
            FROM passenger_balances pb
            JOIN passenger_destinations pd
                ON pd.id = pb.passenger_destination_id
               AND pd.matatu_id = pb.matatu_id
            WHERE pb.id = ?
              AND pb.matatu_id = ?
        """, (balance_id, matatu_id)).fetchone()

        if balance is None:
            connection.rollback()
            return jsonify({
                "error": "Balance not found for this vehicle."
            }), 404

        if balance["status"] != "pending":
            connection.rollback()
            return jsonify({
                "error": "Only pending balances can be moved to "
                         "awaiting confirmation."
            }), 409

        cursor = connection.execute("""
            UPDATE passenger_balances
            SET status = 'awaiting_confirmation',
                paid_at = CURRENT_TIMESTAMP,
                paid_by_conductor_id = ?
            WHERE id = ?
              AND matatu_id = ?
              AND status = 'pending'
        """, (conductor_id, balance_id, matatu_id))

        if cursor.rowcount != 1:
            connection.rollback()
            return jsonify({
                "error": "The balance could not be updated. "
                         "Please refresh and try again."
            }), 409

        connection.execute("""
            INSERT INTO passenger_notifications (
                matatu_id,
                passenger_destination_id,
                balance_id,
                notification_type,
                message
            )
            VALUES (?, ?, ?, 'payment_confirmation', ?)
        """, (
            matatu_id,
            balance["passenger_destination_id"],
            balance_id,
            (
                f"Your payment has been recorded for journey "
                f"{balance['passenger_token']}. "
                f"Please confirm receipt of the payment."
            )
        ))

        connection.commit()

        return jsonify({
            "message": "Repayment recorded. Awaiting passenger confirmation.",
            "balance_id": balance_id,
            "status": "awaiting_confirmation",
            "paid_by_conductor_id": conductor_id
        }), 200

    except Exception:
        connection.rollback()
        app.logger.exception(
            "Failed to record balance repayment or notification."
        )
        return jsonify({
            "error": "Could not record repayment."
        }), 500

    finally:
        connection.close()

@app.route(
    "/api/passenger/balances/<int:balance_id>/confirm",
    methods=["POST"]
)
def confirm_passenger_balance(balance_id):
    data = request.get_json(silent=True) or {}
    passenger_id = data.get("passenger_id")

    if not isinstance(passenger_id, str) or not passenger_id.strip():
        return jsonify({
            "error": "A valid passenger ID is required."
        }), 400

    passenger_id = passenger_id.strip().upper()
    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        balance = connection.execute("""
            SELECT pb.id, pb.status
            FROM passenger_balances AS pb
            JOIN passenger_destinations AS pd
              ON pd.id = pb.passenger_destination_id
            WHERE pb.id = ?
              AND UPPER(pd.passenger_token) = ?
        """, (balance_id, passenger_id)).fetchone()

        if balance is None:
            connection.rollback()
            return jsonify({
                "error": "Balance not found for this passenger."
            }), 404

        if balance["status"] != "awaiting_confirmation":
            connection.rollback()
            return jsonify({
                "error": "Only balances awaiting confirmation can be confirmed."
            }), 409

        cursor = connection.execute("""
            UPDATE passenger_balances
            SET status = 'confirmed',
                confirmed_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'awaiting_confirmation'
        """, (balance_id,))

        if cursor.rowcount != 1:
            connection.rollback()
            return jsonify({
                "error": "Confirmation failed. Please refresh and retry."
            }), 409

        connection.commit()

        return jsonify({
            "message": "Payment receipt confirmed.",
            "balance_id": balance_id,
            "status": "confirmed"
        }), 200

    except Exception:
        connection.rollback()
        app.logger.exception("Failed to confirm passenger balance.")
        return jsonify({
            "error": "Could not confirm payment."
        }), 500

    finally:
        connection.close()

@app.route(
    "/api/passenger/notifications/<string:passenger_id>",
    methods=["GET"]
)
def get_passenger_notifications(passenger_id):
    passenger_id = passenger_id.strip().upper()

    if not passenger_id:
        return jsonify({
            "error": "A valid passenger ID is required."
        }), 400

    connection = get_db_connection()

    try:
        passenger = connection.execute(
            """
            SELECT id
            FROM passenger_destinations
            WHERE UPPER(passenger_token) = ?
            LIMIT 1
            """,
            (passenger_id,)
        ).fetchone()

        if passenger is None:
            return jsonify({
                "error": "Passenger not found."
            }), 404

        notifications = connection.execute(
            """
            SELECT
                pn.id,
                pn.passenger_destination_id AS journey_id,
                pn.balance_id,
                pn.notification_type,
                pn.message,
                pn.is_read,
                pn.created_at
            FROM passenger_notifications pn
            JOIN passenger_destinations pd
                ON pd.id = pn.passenger_destination_id
            WHERE UPPER(pd.passenger_token) = ?
            ORDER BY pn.created_at DESC, pn.id DESC
            """,
            (passenger_id,)
        ).fetchall()

        return jsonify({
            "passenger_id": passenger_id,
            "notification_count": len(notifications),
            "notifications": [
                {
                    "id": notification["id"],
                    "journey_id": notification["journey_id"],
                    "balance_id": notification["balance_id"],
                    "notification_type": notification["notification_type"],
                    "message": notification["message"],
                    "is_read": bool(notification["is_read"]),
                    "created_at": notification["created_at"]
                }
                for notification in notifications
            ]
        }), 200

    except Exception:
        app.logger.exception(
            "Failed to retrieve passenger notifications."
        )
        return jsonify({
            "error": "Could not retrieve notifications."
        }), 500

    finally:
        connection.close()

@app.route(
    "/api/passenger/notifications/<string:passenger_id>/<int:notification_id>/read",
    methods=["POST"]
)
def mark_passenger_notification_read(passenger_id, notification_id):
    passenger_id = passenger_id.strip().upper()

    if not passenger_id:
        return jsonify({
            "error": "A valid passenger ID is required."
        }), 400

    connection = get_db_connection()

    try:
        notification = connection.execute(
            """
            SELECT pn.id, pn.is_read
            FROM passenger_notifications pn
            JOIN passenger_destinations pd
                ON pd.id = pn.passenger_destination_id
            WHERE pn.id = ?
              AND UPPER(pd.passenger_token) = ?
            """,
            (notification_id, passenger_id)
        ).fetchone()

        if notification is None:
            return jsonify({
                "error": "Notification not found."
            }), 404

        if notification["is_read"]:
            return jsonify({
                "message": "Notification has already been read.",
                "notification_id": notification_id,
                "is_read": True
            }), 200

        connection.execute(
            """
            UPDATE passenger_notifications
            SET is_read = 1
            WHERE id = ?
            """,
            (notification_id,)
        )

        connection.commit()

        return jsonify({
            "message": "Notification marked as read.",
            "notification_id": notification_id,
            "is_read": True
        }), 200

    except Exception:
        connection.rollback()
        app.logger.exception(
            "Failed to mark passenger notification as read."
        )
        return jsonify({
            "error": "Could not update notification."
        }), 500

    finally:
        connection.close()

# ---------------- END PASSENGER BALANCE API ----------------

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
    qr_url = f"http://{local_ip}:5000/passenger/{matatu_id}"

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

@app.route("/legacy-passenger/<int:matatu_id>", methods=["GET", "POST"])
def passenger(matatu_id):

    connection = get_db_connection()

    try:
        matatu = connection.execute(
            """
            SELECT * FROM matatus
            WHERE id = ?
            """,
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            return "Matatu not found", 404

        stages = connection.execute(
            """
            SELECT * FROM stages
            WHERE route_name = ?
            ORDER BY sequence_number
            """,
            (matatu["route_name"],)
        ).fetchall()

        if request.method == "POST":

            destination_stage_id = request.form[
                "destination_stage_id"
            ]

            try:
                # 1. Create a permanent passenger identity.
                cursor = connection.execute(
                    """
                    INSERT INTO passengers (passenger_code)
                    VALUES (?)
                    """,
                    ("PENDING",)
                )

                permanent_passenger_id = cursor.lastrowid

                # 2. Generate the permanent passenger code.
                passenger_token = (
                    f"P{permanent_passenger_id:03d}"
                )

                connection.execute(
                    """
                    UPDATE passengers
                    SET passenger_code = ?
                    WHERE id = ?
                    """,
                    (
                        passenger_token,
                        permanent_passenger_id
                    )
                )

                # 3. Create a destination record linked to
                #    the permanent passenger identity.
                cursor = connection.execute(
                    """
                    INSERT INTO passenger_destinations (
                        matatu_id,
                        passenger_token,
                        destination_stage_id,
                        passenger_id
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        matatu_id,
                        passenger_token,
                        destination_stage_id,
                        permanent_passenger_id
                    )
                )

                # Preserve the numeric journey record ID.
                journey_id = cursor.lastrowid

                connection.commit()

            except Exception:
                connection.rollback()
                raise

            return redirect(
                url_for(
                    "passenger",
                    matatu_id=matatu_id,
                    passenger_id=journey_id
                )
            )

        # GET request: retrieve the existing journey ID.
        journey_id = request.args.get("passenger_id")

        passenger_token = None

        if journey_id:
            passenger = connection.execute(
                """
                SELECT
                    COALESCE(
                        p.passenger_code,
                        pd.passenger_token
                    ) AS passenger_token
                FROM passenger_destinations pd
                LEFT JOIN passengers p
                    ON p.id = pd.passenger_id
                WHERE pd.id = ?
                  AND pd.matatu_id = ?
                """,
                (journey_id, matatu_id)
            ).fetchone()

            if passenger:
                passenger_token = passenger["passenger_token"]

        return render_template(
            "passenger.html",
            matatu=matatu,
            stages=stages,
            passenger_id=journey_id,
            passenger_token=passenger_token
        )

    finally:
        connection.close()

@app.route(
    "/api/passenger/journeys/<int:journey_id>/destination-change-requests",
    methods=["POST"]
)
def create_destination_change_request(journey_id):
    data = request.get_json(silent=True) or {}
    requested_stage_id = data.get("requested_destination_stage_id")

    if requested_stage_id is None:
        return jsonify({
            "error": "A requested destination stage is required."
        }), 400

    try:
        requested_stage_id = int(requested_stage_id)
    except (TypeError, ValueError):
        return jsonify({
            "error": "The requested destination stage must be an integer."
        }), 400

    connection = get_db_connection()

    try:
        journey = connection.execute(
            """
            SELECT
                pd.id,
                pd.matatu_id,
                pd.destination_stage_id,
                m.route_name
            FROM passenger_destinations AS pd
            JOIN matatus AS m ON m.id = pd.matatu_id
            WHERE pd.id = ?
            """,
            (journey_id,)
        ).fetchone()

        if journey is None:
            return jsonify({"error": "Passenger journey not found."}), 404

        if journey["destination_stage_id"] == requested_stage_id:
            return jsonify({
                "error": "The requested destination is already active."
            }), 400

        requested_stage = connection.execute(
            """
            SELECT id, name
            FROM stages
            WHERE id = ? AND route_name = ?
            """,
            (requested_stage_id, journey["route_name"])
        ).fetchone()

        if requested_stage is None:
            return jsonify({
                "error": "The requested destination is not on this route."
            }), 400

        existing_request = connection.execute(
            """
            SELECT id
            FROM destination_change_requests
            WHERE passenger_destination_id = ?
              AND status = 'pending'
            """,
            (journey_id,)
        ).fetchone()

        if existing_request is not None:
            return jsonify({
                "error": "You already have a pending destination-change request."
            }), 409

        cursor = connection.execute(
            """
            INSERT INTO destination_change_requests (
                matatu_id,
                passenger_destination_id,
                current_destination_stage_id,
                requested_destination_stage_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                journey["matatu_id"],
                journey_id,
                journey["destination_stage_id"],
                requested_stage_id
            )
        )

        connection.commit()

        return jsonify({
            "message": (
                "Your destination-change request has been sent to the conductor."
            ),
            "request_id": cursor.lastrowid,
            "status": "pending"
        }), 201

    except Exception:
        connection.rollback()
        app.logger.exception("Failed to create destination-change request.")
        return jsonify({
            "error": "Could not submit the destination-change request."
        }), 500

    finally:
        connection.close()

@app.route(
    "/api/conductor/destination-change-requests/<int:matatu_id>",
    methods=["GET"]
)
@conductor_required
def get_destination_change_requests(matatu_id):
    connection = get_db_connection()

    try:
        matatu = connection.execute(
            "SELECT id FROM matatus WHERE id = ?",
            (matatu_id,)
        ).fetchone()

        if matatu is None:
            return jsonify({"error": "Vehicle not found."}), 404

        rows = connection.execute(
            """
            SELECT
                dcr.id AS request_id,
                dcr.passenger_destination_id AS journey_id,
                COALESCE(p.passenger_code, pd.passenger_token) AS passenger_id,
                current_stage.name AS current_destination,
                requested_stage.name AS requested_destination,
                dcr.status,
                dcr.created_at
            FROM destination_change_requests AS dcr
            JOIN passenger_destinations AS pd
                ON pd.id = dcr.passenger_destination_id
            LEFT JOIN passengers AS p
                ON p.id = pd.passenger_id
            LEFT JOIN stages AS current_stage
                ON current_stage.id = dcr.current_destination_stage_id
            LEFT JOIN stages AS requested_stage
                ON requested_stage.id = dcr.requested_destination_stage_id
            WHERE dcr.matatu_id = ?
              AND dcr.status = 'pending'
            ORDER BY dcr.created_at ASC, dcr.id ASC
            """,
            (matatu_id,)
        ).fetchall()

        return jsonify({
            "requests": [
                {
                    "request_id": row["request_id"],
                    "journey_id": row["journey_id"],
                    "passenger_id": row["passenger_id"],
                    "current_destination": row["current_destination"],
                    "requested_destination": row["requested_destination"],
                    "status": row["status"],
                    "created_at": row["created_at"]
                }
                for row in rows
            ]
        })

    except Exception:
        app.logger.exception("Failed to retrieve destination-change requests.")
        return jsonify({
            "error": "Could not load destination-change requests."
        }), 500

    finally:
        connection.close()

@app.route(
    "/api/conductor/destination-change-requests/<int:request_id>/decision",
    methods=["POST"]
)
@conductor_required
@csrf_required
def decide_destination_change_request(request_id):
    data = request.get_json(silent=True) or {}
    action = data.get("action")

    if action not in ("approve", "reject"):
        return jsonify({
            "error": "Action must be 'approve' or 'reject'."
        }), 400

    connection = get_db_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        change_request = connection.execute(
            """
            SELECT
                id,
                matatu_id,
                passenger_destination_id,
                requested_destination_stage_id,
                status
            FROM destination_change_requests
            WHERE id = ?
            """,
            (request_id,)
        ).fetchone()

        if change_request is None:
            connection.rollback()
            return jsonify({
                "error": "Destination-change request not found."
            }), 404

        if change_request["status"] != "pending":
            connection.rollback()
            return jsonify({
                "error": "This request has already been resolved."
            }), 409

        if change_request["matatu_id"] != session.get("matatu_id"):
            connection.rollback()
            return jsonify({
                "error": "You are not authorized to resolve this request."
            }), 403


        if action == "approve":
            update_result = connection.execute(
                """
                UPDATE passenger_destinations
                SET destination_stage_id = ?
                WHERE id = ? AND matatu_id = ?
                """,
                (
                    change_request["requested_destination_stage_id"],
                    change_request["passenger_destination_id"],
                    change_request["matatu_id"]
                )
            )

            if update_result.rowcount != 1:
                connection.rollback()
                return jsonify({
                    "error": "The passenger journey could not be updated."
                }), 409


        status_result = connection.execute(
            """
            UPDATE destination_change_requests
            SET status = ?,
                resolved_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status = 'pending'
            """,
            (
                "approved" if action == "approve" else "rejected",
                request_id
            )
        )

        if status_result.rowcount != 1:
            connection.rollback()
            return jsonify({
                "error": "The request could not be resolved. Please try again."
            }), 409

        connection.commit()

        return jsonify({
            "message": (
                "Destination change approved."
                if action == "approve"
                else "Destination change rejected. The existing destination remains unchanged."
            ),
            "request_id": request_id,
            "status": "approved" if action == "approve" else "rejected"
        })

    except Exception:
        connection.rollback()
        app.logger.exception("Failed to resolve destination-change request.")
        return jsonify({
            "error": "Could not resolve the destination-change request."
        }), 500

    finally:
        connection.close()

@app.route("/conductor/<int:matatu_id>")
@conductor_required
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
@conductor_required
@csrf_required
def notify_passenger(passenger_id):
    connection = get_db_connection()

    try:
        journey = connection.execute(
            """
            SELECT id, matatu_id, status
            FROM passenger_destinations
            WHERE id = ?
            """,
            (passenger_id,)
        ).fetchone()

        if journey is None:
            return "Passenger journey not found", 404

        if journey["matatu_id"] != session.get("matatu_id"):
            return "You are not authorized to notify this passenger", 403

        if journey["status"] != "waiting":
            return "Passenger journey is not awaiting notification", 409

        result = connection.execute(
            """
            UPDATE passenger_destinations
            SET status = 'notified'
            WHERE id = ?
              AND matatu_id = ?
              AND status = 'waiting'
            """,
            (passenger_id, session["matatu_id"])
        )

        if result.rowcount != 1:
            connection.rollback()
            return "Passenger notification could not be completed", 409

        connection.commit()

        return redirect(url_for(
            "conductor",
            matatu_id=session["matatu_id"]
        ))

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

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
        return "No passenger destinations registered."

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
        "passengers": results
    }

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

                connection.execute(
                    """
                    UPDATE matatu_locations
                    SET latitude = ?,
                        longitude = ?,
                        current_stage_sequence = ?,
                        speed = 20
                    WHERE matatu_id = ?
                    """,
                    (
                        next_stage["latitude"],
                        next_stage["longitude"],
                        next_stage["sequence_number"],
                        matatu_id
                    )
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
        connection.close()

        # Check for proximity alerts after movement is saved.
        check_proximity_alerts(matatu_id)

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

    connection.execute(
        """
        UPDATE matatu_locations
        SET latitude = ?,
            longitude = ?,
            current_stage_sequence = ?
        WHERE matatu_id = ?
        """,
        (
            -1.286389,
            36.817223,
            0,
            matatu_id
        )
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