from flask import Flask, render_template, request, redirect, url_for
from database import init_db, get_db_connection
from gps import calculate_distance, calculate_route_distance
import socket
import qrcode
import io
import base64





app = Flask(__name__)


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

    # Get all stages on the matatu route
    route_stages = connection.execute(
        """
        SELECT *
        FROM stages
        WHERE route_name = ?
        ORDER BY sequence_number
        """,
        (matatu["route_name"],)
    ).fetchall()

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

            # Get only the stages between the current position
            # and the passenger's destination
            remaining_stages = [
                stage
                for stage in route_stages
                if current_stage_sequence < stage["sequence_number"]
                and stage["sequence_number"] <= passenger["destination_sequence"]
            ]

            # Calculate distance by following the route stages
            distance = calculate_route_distance(
                matatu_latitude,
                matatu_longitude,
                remaining_stages
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