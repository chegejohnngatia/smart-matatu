
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app as smart_matatu_app


class ProximityAlertTests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(
            self.temp_dir.name,
            "test_smart_matatu.db"
        )

        self.create_test_database()

        self.database_patch = patch.object(
            smart_matatu_app,
            "get_db_connection",
            self.get_test_connection
        )
        self.database_patch.start()
        self.addCleanup(self.database_patch.stop)
        self.addCleanup(self.temp_dir.cleanup)

        self.client = smart_matatu_app.app.test_client()

    def get_test_connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def create_test_database(self):
        connection = sqlite3.connect(self.db_path)

        connection.executescript("""
            CREATE TABLE matatus (
                id INTEGER PRIMARY KEY,
                registration_number TEXT,
                route_name TEXT
            );

            CREATE TABLE matatu_locations (
                matatu_id INTEGER PRIMARY KEY,
                latitude REAL,
                longitude REAL,
                current_stage_sequence INTEGER DEFAULT 0
            );

            CREATE TABLE stages (
                id INTEGER PRIMARY KEY,
                route_name TEXT,
                name TEXT,
                latitude REAL,
                longitude REAL,
                sequence_number INTEGER
            );

            CREATE TABLE passenger_destinations (
                id INTEGER PRIMARY KEY,
                matatu_id INTEGER,
                passenger_token TEXT,
                destination_stage_id INTEGER,
                status TEXT DEFAULT 'waiting'
            );

            CREATE TABLE passenger_balances (
                id INTEGER PRIMARY KEY,
                matatu_id INTEGER,
                passenger_destination_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                paid_at TEXT,
                confirmed_at TEXT
            );

            CREATE TABLE passenger_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                balance_id INTEGER,
                notification_type TEXT NOT NULL
                    CHECK (
                        notification_type IN (
                            'payment_confirmation',
                            'payment_reminder'
                        )
                    ),
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE emergency_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matatu_id INTEGER NOT NULL,
                passenger_destination_id INTEGER NOT NULL,
                alert_type TEXT NOT NULL
                    CHECK (
                        alert_type IN (
                            'proximity',
                            'passenger_issue'
                        )
                    ),
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
                    CHECK (
                        status IN ('active', 'acknowledged')
                    ),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TEXT
            );

            CREATE UNIQUE INDEX one_proximity_alert_per_journey
            ON emergency_alerts (passenger_destination_id)
            WHERE alert_type = 'proximity';

            INSERT INTO matatus (
                id, registration_number, route_name
            )
            VALUES (1, 'KAA123A', 'Kisii-Nairobi');

            INSERT INTO matatus (
                id, registration_number, route_name
            )
            VALUES (2, 'KBB456B', 'Kisii-Keroka');

            INSERT INTO matatu_locations (
                matatu_id, latitude, longitude
            )
            VALUES (1, -0.6810, 34.7660);

            INSERT INTO stages (
                id, route_name, name, latitude, longitude,
                sequence_number
            )
            VALUES (
                1, 'Kisii-Nairobi', 'Nearby Stage',
                -0.6810, 34.7660, 1
            );

            INSERT INTO stages (
                id, route_name, name, latitude, longitude,
                sequence_number
            )
            VALUES (
                2, 'Kisii-Nairobi', 'Unknown Location',
                NULL, NULL, 2
            );
        """)

        connection.commit()
        connection.close()

    def add_journey(
        self,
        journey_id=1,
        passenger_id="P001",
        stage_id=1,
        balance_status="pending",
        matatu_id=1
    ):
        connection = self.get_test_connection()

        connection.execute(
            """
            INSERT INTO passenger_destinations (
                id, matatu_id, passenger_token,
                destination_stage_id, status
            )
            VALUES (?, ?, ?, ?, 'waiting')
            """,
            (
                journey_id,
                matatu_id,
                passenger_id,
                stage_id
            )
        )

        if balance_status is not None:
            connection.execute(
                """
                INSERT INTO passenger_balances (
                    matatu_id, passenger_destination_id,
                    amount, status
                )
                VALUES (?, ?, 25, ?)
                """,
                (matatu_id, journey_id, balance_status)
            )

        connection.commit()
        connection.close()

    def count_alerts(self, journey_id=None):
        connection = self.get_test_connection()

        if journey_id is None:
            row = connection.execute(
                "SELECT COUNT(*) FROM emergency_alerts"
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT COUNT(*)
                FROM emergency_alerts
                WHERE passenger_destination_id = ?
                """,
                (journey_id,)
            ).fetchone()

        connection.close()
        return row[0]

    def count_notifications(
        self,
        journey_id=None,
        notification_type=None
    ):
        connection = self.get_test_connection()

        query = "SELECT COUNT(*) FROM passenger_notifications"
        conditions = []
        parameters = []

        if journey_id is not None:
            conditions.append(
                "passenger_destination_id = ?"
            )
            parameters.append(journey_id)

        if notification_type is not None:
            conditions.append("notification_type = ?")
            parameters.append(notification_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        row = connection.execute(
            query,
            parameters
        ).fetchone()

        connection.close()
        return row[0]

    def create_alert(
        self,
        journey_id=1,
        alert_type="passenger_issue",
        status="active",
        matatu_id=1,
        message="Passenger reported a payment issue."
    ):
        connection = self.get_test_connection()

        cursor = connection.execute(
            """
            INSERT INTO emergency_alerts (
                matatu_id, passenger_destination_id,
                alert_type, message, status
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                matatu_id,
                journey_id,
                alert_type,
                message,
                status
            )
        )

        alert_id = cursor.lastrowid
        connection.commit()
        connection.close()
        return alert_id

    def get_alert(self, alert_id):
        connection = self.get_test_connection()

        row = connection.execute(
            """
            SELECT *
            FROM emergency_alerts
            WHERE id = ?
            """,
            (alert_id,)
        ).fetchone()

        result = dict(row) if row else None
        connection.close()
        return result

    def create_manual_issue(
        self,
        journey_id=1,
        passenger_id="P001",
        description=(
            "I sent the money but the conductor "
            "has not received it."
        )
    ):
        return self.client.post(
            f"/api/passenger/journeys/{journey_id}/emergency-issues",
            json={
                "passenger_id": passenger_id,
                "issue_description": description
            }
        )

    def acknowledge(self, alert_id, matatu_id=1):
        return self.client.post(
            f"/api/conductor/emergency-alerts/{alert_id}/acknowledge",
            json={"matatu_id": matatu_id}
        )

    def test_passenger_can_mark_own_notification_as_read(self):
        self.add_journey(passenger_id="P001")

        connection = self.get_test_connection()
        cursor = connection.execute(
            """
            INSERT INTO passenger_notifications (
                matatu_id,
                passenger_destination_id,
                balance_id,
                notification_type,
                message
            )
            VALUES (1, 1, 1, 'payment_confirmation', ?)
            """,
            ("Payment recorded.",)
        )
        notification_id = cursor.lastrowid
        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/passenger/notifications/P001/{notification_id}/read"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["is_read"])

        connection = self.get_test_connection()
        notification = connection.execute(
            "SELECT is_read FROM passenger_notifications WHERE id = ?",
            (notification_id,)
        ).fetchone()
        connection.close()

        self.assertEqual(notification["is_read"], 1)


    def test_passenger_cannot_mark_another_passengers_notification_as_read(self):
        self.add_journey(
            journey_id=1,
            passenger_id="P001"
        )
        self.add_journey(
            journey_id=2,
            passenger_id="P002"
        )

        connection = self.get_test_connection()
        cursor = connection.execute(
            """
            INSERT INTO passenger_notifications (
                matatu_id,
                passenger_destination_id,
                balance_id,
                notification_type,
                message
            )
            VALUES (1, 2, 2, 'payment_reminder', ?)
            """,
            ("P002 reminder.",)
        )
        notification_id = cursor.lastrowid
        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/passenger/notifications/P001/{notification_id}/read"
        )

        self.assertEqual(response.status_code, 404)

        connection = self.get_test_connection()
        notification = connection.execute(
            "SELECT is_read FROM passenger_notifications WHERE id = ?",
            (notification_id,)
        ).fetchone()
        connection.close()

        self.assertEqual(notification["is_read"], 0)


    def test_marking_already_read_notification_again_is_safe(self):
        self.add_journey(passenger_id="P001")

        connection = self.get_test_connection()
        cursor = connection.execute(
            """
            INSERT INTO passenger_notifications (
                matatu_id,
                passenger_destination_id,
                balance_id,
                notification_type,
                message,
                is_read
            )
            VALUES (1, 1, 1, 'payment_confirmation', ?, 1)
            """,
            ("Payment recorded.",)
        )
        notification_id = cursor.lastrowid
        connection.commit()
        connection.close()

        response = self.client.post(
            f"/api/passenger/notifications/P001/{notification_id}/read"
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["is_read"])
        self.assertIn(
            "already been read",
            response.get_json()["message"]
        )


        
        def test_passenger_retrieves_only_own_notifications(self):
            self.add_journey(
                journey_id=1,
                passenger_id="P001"
            )
            self.add_journey(
                journey_id=2,
                passenger_id="P002"
            )

            connection = self.get_test_connection()

            connection.executemany(
                """
                INSERT INTO passenger_notifications (
                    matatu_id,
                    passenger_destination_id,
                    balance_id,
                    notification_type,
                    message
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (1, 1, 1, "payment_confirmation", "P001 message"),
                    (1, 2, 2, "payment_reminder", "P002 message")
                ]
            )

            connection.commit()
            connection.close()

            response = self.client.get(
                "/api/passenger/notifications/P001"
            )

            self.assertEqual(response.status_code, 200)

            data = response.get_json()

            self.assertEqual(data["passenger_id"], "P001")
            self.assertEqual(data["notification_count"], 1)
            self.assertEqual(
                data["notifications"][0]["message"],
                "P001 message"
            )

    def test_passenger_notifications_are_returned_newest_first(self):
        self.add_journey(passenger_id="P001")

        connection = self.get_test_connection()

        connection.executemany(
            """
            INSERT INTO passenger_notifications (
                matatu_id,
                passenger_destination_id,
                balance_id,
                notification_type,
                message
            )
            VALUES (1, 1, ?, 'payment_reminder', ?)
            """,
            [
                (1, "Older notification"),
                (2, "Newer notification")
            ]
        )

        connection.commit()
        connection.close()

        response = self.client.get(
            "/api/passenger/notifications/P001"
        )

        self.assertEqual(response.status_code, 200)

        messages = [
            item["message"]
            for item in response.get_json()["notifications"]
        ]

        self.assertEqual(
            messages,
            ["Newer notification", "Older notification"]
        )

    def test_passenger_with_no_notifications_gets_empty_list(self):
        self.add_journey(passenger_id="P001")

        response = self.client.get(
            "/api/passenger/notifications/P001"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()

        self.assertEqual(data["notification_count"], 0)
        self.assertEqual(data["notifications"], [])

    def test_unknown_passenger_cannot_retrieve_notifications(self):
        response = self.client.get(
            "/api/passenger/notifications/P999"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.get_json()["error"],
            "Passenger not found."
        )


    
    def test_recording_payment_creates_confirmation_notification(self):
        self.add_journey(balance_status="pending")

        response = self.client.post(
            "/api/conductor/balances/1/pay",
            json={"matatu_id": 1}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["status"],
            "awaiting_confirmation"
        )

        connection = self.get_test_connection()

        balance = connection.execute("""
            SELECT status
            FROM passenger_balances
            WHERE id = 1
        """).fetchone()

        notification = connection.execute("""
            SELECT
                matatu_id,
                passenger_destination_id,
                balance_id,
                notification_type,
                message
            FROM passenger_notifications
            WHERE balance_id = 1
        """).fetchone()

        connection.close()

        self.assertEqual(balance["status"], "awaiting_confirmation")
        self.assertIsNotNone(notification)
        self.assertEqual(notification["matatu_id"], 1)
        self.assertEqual(notification["passenger_destination_id"], 1)
        self.assertEqual(notification["notification_type"], "payment_confirmation")
        self.assertIn("P001", notification["message"])
        self.assertEqual(
            self.count_notifications(
                journey_id=1,
                notification_type="payment_confirmation"
            ),
            1
        )

    
    def test_awaiting_confirmation_near_destination_creates_reminder(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )

        created = smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(created, 0)
        self.assertEqual(self.count_alerts(1), 0)
        self.assertEqual(
            self.count_notifications(
                journey_id=1,
                notification_type="payment_reminder"
            ),
            1
        )

    def test_repeated_check_does_not_duplicate_payment_reminder(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )

        smart_matatu_app.check_proximity_alerts(1)
        smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(
            self.count_notifications(
                journey_id=1,
                notification_type="payment_reminder"
            ),
            1
        )

    # Proximity alert tests

    def test_pending_balance_near_destination_creates_alert(self):
        self.add_journey(balance_status="pending")

        created = smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(created, 1)
        self.assertEqual(self.count_alerts(1), 1)

    def test_awaiting_confirmation_does_not_create_conductor_alert(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )

        created = smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(created, 0)
        self.assertEqual(self.count_alerts(), 0)

    def test_confirmed_balance_does_not_create_alert(self):
        self.add_journey(balance_status="confirmed")

        created = smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(created, 0)
        self.assertEqual(self.count_alerts(), 0)

    def test_missing_destination_coordinates_are_skipped(self):
        self.add_journey(
            stage_id=2,
            balance_status="pending"
        )

        created = smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(created, 0)
        self.assertEqual(self.count_alerts(), 0)

    def test_repeated_check_does_not_duplicate_alert(self):
        self.add_journey(balance_status="pending")

        first = smart_matatu_app.check_proximity_alerts(1)
        second = smart_matatu_app.check_proximity_alerts(1)

        self.assertEqual(first, 1)
        self.assertEqual(second, 0)
        self.assertEqual(self.count_alerts(1), 1)

    # Passenger manual issue tests

    def test_manual_issue_allowed_when_payment_awaits_confirmation(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )

        response = self.create_manual_issue()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.count_alerts(1), 1)

        alert = self.get_alert(1)
        self.assertEqual(alert["alert_type"], "passenger_issue")
        self.assertEqual(alert["status"], "active")

    def test_duplicate_manual_issue_is_rejected(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )

        first = self.create_manual_issue()
        second = self.create_manual_issue(
            description="Submitting the same issue again."
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(self.count_alerts(1), 1)

    def test_manual_issue_rejected_if_proximity_alert_exists(self):
        self.add_journey(balance_status="pending")
        smart_matatu_app.check_proximity_alerts(1)

        response = self.create_manual_issue()

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.count_alerts(1), 1)

    def test_manual_issue_rejects_wrong_passenger(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )

        response = self.create_manual_issue(
            passenger_id="WRONG_ID"
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.count_alerts(), 0)

    # Conductor alert retrieval tests

    def test_get_alerts_returns_active_alerts_and_history(self):
        self.add_journey()
        active_id = self.create_alert(
            journey_id=1,
            status="active"
        )

        self.add_journey(
            journey_id=2,
            passenger_id="P002"
        )
        history_id = self.create_alert(
            journey_id=2,
            status="acknowledged"
        )

        response = self.client.get(
            "/api/conductor/emergency-alerts/1"
        )

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["unresolved_count"], 1)
        self.assertEqual(len(data["active_alerts"]), 1)
        self.assertEqual(len(data["history"]), 1)
        self.assertEqual(
            data["active_alerts"][0]["alert_id"],
            active_id
        )
        self.assertEqual(
            data["history"][0]["alert_id"],
            history_id
        )

    def test_get_alerts_rejects_unknown_vehicle(self):
        response = self.client.get(
            "/api/conductor/emergency-alerts/999"
        )

        self.assertEqual(response.status_code, 404)

    # Conductor acknowledgement tests

    def test_acknowledgement_changes_only_alert_status(self):
        self.add_journey(
            balance_status="awaiting_confirmation"
        )
        alert_id = self.create_alert(
            alert_type="passenger_issue"
        )

        response = self.acknowledge(alert_id)

        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "acknowledged")
        self.assertFalse(data["balance_changed"])
        self.assertFalse(data["issue_resolved"])

        alert = self.get_alert(alert_id)
        self.assertEqual(alert["status"], "acknowledged")
        self.assertIsNotNone(alert["acknowledged_at"])

        connection = self.get_test_connection()
        balance = connection.execute(
            """
            SELECT status
            FROM passenger_balances
            WHERE passenger_destination_id = 1
            """
        ).fetchone()
        connection.close()

        self.assertEqual(
            balance["status"],
            "awaiting_confirmation"
        )

    def test_duplicate_acknowledgement_is_rejected(self):
        self.add_journey()
        alert_id = self.create_alert()

        first = self.acknowledge(alert_id)
        second = self.acknowledge(alert_id)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(
            self.get_alert(alert_id)["status"],
            "acknowledged"
        )

    def test_acknowledgement_rejects_wrong_vehicle(self):
        self.add_journey()
        alert_id = self.create_alert(matatu_id=1)

        response = self.acknowledge(
            alert_id,
            matatu_id=2
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.get_alert(alert_id)["status"],
            "active"
        )

    def test_acknowledgement_requires_valid_vehicle_id(self):
        self.add_journey()
        alert_id = self.create_alert()

        response = self.client.post(
            f"/api/conductor/emergency-alerts/{alert_id}/acknowledge",
            json={"matatu_id": "not-a-number"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            self.get_alert(alert_id)["status"],
            "active"
        )


if __name__ == "__main__":
    unittest.main()
