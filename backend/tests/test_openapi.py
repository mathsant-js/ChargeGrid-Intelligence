import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_openapi_is_available() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/users" in paths
    assert "/api/v1/vehicles" in paths
    assert "/api/v1/stations" in paths
    assert "/api/v1/chargers" in paths
    assert "/api/v1/sessions/start" in paths
    assert "/api/v1/sessions/{session_id}/stop" in paths
    assert "/api/v1/energy/current" in paths
    assert "/api/v1/energy/history" in paths
    assert "/api/v1/solar/current" in paths
    assert "/api/v1/solar/history" in paths
    assert "/api/v1/predictions/demand" in paths
    assert "/api/v1/system-configuration" in paths

    bearer = [{"HTTPBearer": []}]
    protected_operations = {
        ("/api/v1/auth/me", "get"),
        ("/api/v1/users", "get"),
        ("/api/v1/users", "post"),
        ("/api/v1/users/{user_id}", "get"),
        ("/api/v1/users/{user_id}", "patch"),
        ("/api/v1/vehicles", "get"),
        ("/api/v1/vehicles", "post"),
        ("/api/v1/vehicles/{vehicle_id}", "get"),
        ("/api/v1/vehicles/{vehicle_id}", "patch"),
        ("/api/v1/vehicles/{vehicle_id}", "delete"),
        ("/api/v1/stations", "get"),
        ("/api/v1/stations", "post"),
        ("/api/v1/stations/{station_id}", "get"),
        ("/api/v1/stations/{station_id}", "patch"),
        ("/api/v1/chargers", "get"),
        ("/api/v1/chargers", "post"),
        ("/api/v1/chargers/{charger_id}", "get"),
        ("/api/v1/chargers/{charger_id}", "patch"),
        ("/api/v1/sessions", "get"),
        ("/api/v1/sessions/{session_id}", "get"),
        ("/api/v1/sessions/start", "post"),
        ("/api/v1/sessions/{session_id}/stop", "post"),
    }
    for path, method in protected_operations:
        assert paths[path][method]["security"] == bearer

    assert "security" not in paths["/api/v1/health"]["get"]
    assert "security" not in paths["/api/v1/auth/login"]["post"]

    expected_error_responses = {
        ("/api/v1/auth/login", "post"): {"401"},
        ("/api/v1/auth/me", "get"): {"401"},
        ("/api/v1/users", "get"): {"401", "403"},
        ("/api/v1/users", "post"): {"401", "403", "409"},
        ("/api/v1/users/{user_id}", "get"): {"401", "404"},
        ("/api/v1/users/{user_id}", "patch"): {"401", "403", "404", "409"},
        ("/api/v1/vehicles", "get"): {"401"},
        ("/api/v1/vehicles", "post"): {"401", "403", "409"},
        ("/api/v1/vehicles/{vehicle_id}", "get"): {"401", "404"},
        ("/api/v1/vehicles/{vehicle_id}", "patch"): {"401", "403", "404", "409"},
        ("/api/v1/vehicles/{vehicle_id}", "delete"): {"401", "403", "404", "409"},
        ("/api/v1/stations", "get"): {"401"},
        ("/api/v1/stations", "post"): {"401", "403", "409"},
        ("/api/v1/stations/{station_id}", "get"): {"401", "404"},
        ("/api/v1/stations/{station_id}", "patch"): {"401", "403", "404", "409"},
        ("/api/v1/chargers", "get"): {"401"},
        ("/api/v1/chargers", "post"): {"401", "403", "404", "409"},
        ("/api/v1/chargers/{charger_id}", "get"): {"401", "404"},
        ("/api/v1/chargers/{charger_id}", "patch"): {"401", "403", "404", "409"},
        ("/api/v1/sessions", "get"): {"401"},
        ("/api/v1/sessions/{session_id}", "get"): {"401", "404"},
        ("/api/v1/sessions/start", "post"): {"401", "403", "404", "409"},
        ("/api/v1/sessions/{session_id}/stop", "post"): {"401", "403", "404", "409"},
    }
    for (path, method), expected_statuses in expected_error_responses.items():
        responses = paths[path][method]["responses"]
        assert expected_statuses <= responses.keys()
        for response_status in expected_statuses:
            schema = responses[response_status]["content"]["application/json"]["schema"]
            assert schema == {"$ref": "#/components/schemas/ErrorResponse"}
