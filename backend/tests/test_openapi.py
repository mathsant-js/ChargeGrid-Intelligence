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
