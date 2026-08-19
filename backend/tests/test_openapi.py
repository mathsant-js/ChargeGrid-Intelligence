import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_openapi_is_available() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
