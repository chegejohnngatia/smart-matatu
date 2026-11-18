from app import app


ADMIN_ENDPOINTS = (
    "/api/admin/dashboard",
    "/api/admin/matatus",
    "/api/admin/routes",
    "/api/admin/trips",
    "/api/admin/matatus/1/qr",
)


def test_admin_endpoints_require_an_authenticated_admin():
    client = app.test_client()

    for path in ADMIN_ENDPOINTS:
        response = client.get(path)
        assert response.status_code == 401, path
