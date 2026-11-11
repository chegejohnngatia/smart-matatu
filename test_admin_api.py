from app import app


def test_admin_dashboard_returns_real_resource_collections():
    client = app.test_client()
    response = client.get("/api/admin/dashboard")

    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"alerts", "matatus", "routes", "stats", "trips"}
    assert payload["stats"]["matatus"] == len(payload["matatus"])
    assert payload["stats"]["active_trips"] <= payload["stats"]["matatus"]


def test_admin_resource_endpoints_return_json_lists():
    client = app.test_client()

    for path, key in (
        ("/api/admin/matatus", "registration"),
        ("/api/admin/routes", "name"),
        ("/api/admin/trips", "id"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        payload = response.get_json()
        assert isinstance(payload, list)
        if payload:
            assert key in payload[0]


def test_admin_can_generate_a_matatu_qr_code():
    client = app.test_client()
    response = client.get("/api/admin/matatus/1/qr")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["registration"]
    assert payload["qr_url"].endswith("/passenger/1")
    assert payload["qr_data_url"].startswith("data:image/png;base64,")
